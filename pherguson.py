#!/usr/bin/env python

import hashlib
import os
import pathlib
import platform
import requests
import shutil
import socket
import threading
import time
import urwid

from PIL import Image
from urllib.parse import urlparse

import ueberzug.lib.v0 as ueberzug

USE_BOLD_FONT = True
STOP_THREAD = False
THUMBNAIL_SIZE = (384, 256)
INLINE_IMAGES_ENABLED = platform.system() == "Linux"

COLOR_MAP = [
    # gopher types
    ("inf", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("gif", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("img", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("dir", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("txt", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm_img", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("ask", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),

    # ui elements
    ("url_label", "light blue", urwid.DEFAULT),
    ("url_bar", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT, "bold"),
    ("selection", f"light gray{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("divider", "light blue", urwid.DEFAULT),
    ("search_overlay", "white", "dark blue"),
    ("exit_overlay", f"{',bold' if USE_BOLD_FONT else ''}", "dark red"),
    ("list", urwid.DEFAULT, urwid.DEFAULT),

    # status bar levels
    ("ok", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("warning", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("error", f"dark red{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
]

TYPE_MAP = {
    # canonical types
    "0": "txt",  # text file
    "1": "dir",  # submenu
    "3": "cns",  # CCSO Nameserver
    "4": "err",  # Error
    "5": "dos",  # DOS file
    "6": "utf",  # uuencoded file
    "7": "ask",  # full text search
    "8": "tnt",  # telnet
    "9": "bin",  # binary file
    "+": "mir",  # mirror
    "g": "gif",  # gif file
    "I": "img",  # image file
    "T": "tn3",  # telnet 3270
    # non-canonical types
    "d": "doc",  # pdf / .doc
    "h": "htm",  # html file / link
    "i": "inf",  # info message
    "s": "snd",  # sound file
}
SELECTABLES = ["txt", "dir", "gif", "htm", "img", "gif", "ask"]


class Cache():
    cache_directory = f"{os.path.expanduser('~')}/.config/pherguson/cache"

    @classmethod
    def get_cache_directory(cls, host):
        hash = hashlib.md5(host.encode()).hexdigest()

        dir = f"{cls.cache_directory}/{hash}"
        path = pathlib.Path(dir)
        path.mkdir(parents=True, exist_ok=True)

        return dir

    @classmethod
    def file_exists(cls, file_path):
        return pathlib.Path(file_path).is_file()


class Line:
    def __init__(self, type, text, url, host, port):
        self.type = type
        self.text = text
        self.url = url
        self.host = host
        self.port = port

    def __repr__(self):
        return f"{self.type}\t{self.text}\t{self.url}\t{self.host}\t{self.port}\n"


class Location:
    def __init__(self, host, port, url, focus=0, walkable=True):
        self.host = host
        self.port = port
        self.url = url

        self.focus = focus
        self.walkable = walkable


class Error(Exception):
    def __init__(self, message):
        self.message = message


class History:
    def __init__(self):
        self.history = []

    @property
    def current_location(self):
        if len(self.history) == 1:
            return self.history[0]

        return self.history[-1]

    def forward(self, host, port, url):
        self.history.append(Location(host, port, url))

    def set_focus(self, focus):
        history.current_location.focus = focus

    def back(self):
        if len(self.history) > 1:
            self.history.pop()


history = History()
history.forward("gopher.flatline.ltd", 70, "/")


class Highlight(urwid.AttrMap):
    def __init__(self, attr_map):
        urwid.AttrMap.__init__(
            self,
            urwid.Text(attr_map.base_widget.text),
            "selection",
        )
        self.backup = attr_map


class Selectable(urwid.WidgetWrap):
    def __init__(self, text, type, expandable=False, *args, **kwargs):
        self.text = text
        if expandable:
            self.text = f"+ {self.text}"

        self.attr_map = urwid.AttrMap(urwid.Text(self.text), type)
        super(Selectable, self).__init__(self.attr_map)

    def selectable(self):
        return True


class Unselectable(Selectable):
    def selectable(self):
        return False


class Box(urwid.Pile):
    def __init__(self, pixels, row_height=15, *args, **kwargs):
        super(Box, self).__init__([
            urwid.Text("")
            for i in range(int(pixels / row_height))
        ])

    def selectable(self):
        return False


def is_image(url):
    for image_type in ["jpg", "jpeg", "png", "gif"]:
        if image_type in url.lower():
            return True

    return False


class ContentWindow(urwid.ListBox):
    def __init__(self, gopher):
        self.gopher = gopher
        self.walker = urwid.SimpleFocusListWalker([])
        super(ContentWindow, self).__init__(self.walker)

        self.image_preview = None
        self.current_highlight = None

    def clear(self):
        for i in range(len(self.walker)):
            self.walker.pop()

    def set_content(self, lines, focus):
        def _is_expandable(url):
            url = url.lower()
            if not INLINE_IMAGES_ENABLED:
                return False

            return is_image(url)

        for line in lines:
            selectable = line.type in SELECTABLES
            expandable = _is_expandable(line.url)

            type = line.type

            if expandable and line.type == "htm":
                type = "htm_img"

            formatted_text = f"{line.type.upper() if selectable else ''}{' ' if selectable else ''}{line.text}"
            self.walker.append(
                Selectable(formatted_text, type, expandable=expandable)
                if selectable else
                Unselectable(formatted_text, type)
            )

        if focus > len(self.walker):
            focus = 0

        if not history.current_location.walkable and len(self.walker) > 0:
            self.set_focus(0)

        else:
            # find first selectable element
            if len(self.walker) < 1:
                return

            while not self.walker[focus].base_widget.selectable() and focus < len(self.walker) - 1:
                focus += 1

            self.set_highlight(focus)
            self.set_focus(focus)

    def set_highlight(self, focus):
        if self.current_highlight is not None:
            try:
                old = self.body[self.current_highlight]
                self.body[self.current_highlight] = old.backup

            except Exception:
                pass

        if focus is None:
            self.current_highlight = None
        else:
            self.body[focus] = Highlight(self.body[focus])
            self.current_highlight = focus

            location = self.gopher.current_location_map[focus]
            if "URL" in location.url:
                url = location.url.replace("URL:", "")

            else:
                url = f"gopher://{location.host}{location.url}"

            self.gopher.status_bar.set_status(url)

    def keypress(self, size, key):
        if INLINE_IMAGES_ENABLED and self.image_preview:
            if key in ["h", "left", "q", "esc"]:
                global STOP_THREAD
                STOP_THREAD = True

                highlighted_line = self.walker[self.current_highlight]
                highlighted_line.base_widget.set_text(highlighted_line.old_text)
                self.walker.pop(self.current_highlight + 1)

                self.image_preview = None

            if key in ["l", "right", "enter"]:
                line = self.gopher.current_location_map[self.current_highlight]

                if line.type in ["img", "gif"]:
                    program = "feh"

                    self.gopher.status_bar.set_status(f"open: {self.image_preview[0]}")
                    os.system(f"{program} {self.image_preview[0]} > /dev/null 2>&1")

                if line.type == "htm":
                    url = line.url.replace("URL:", "")
                    if platform.system() == "Linux":
                        if is_image(url):
                            program = "feh"
                        else:
                            program = "qute"

                    elif platform.system() == "Darwin":
                        program = "open"

                    os.system(f"{program} {url} > /dev/null 2>&1")
                    return

            return

        if key in ["l", "right", "enter"]:
            line = self.gopher.current_location_map[self.current_highlight]
            walkable = line.type not in ["txt"]

            if line.type == "ask":
                widget = urwid.Filler(
                    urwid.AttrMap(SearchOverlay(self.gopher, line), "search_overlay"))

                overlay = urwid.Overlay(
                    widget, self.gopher.main_loop.widget,
                    "center", 30, valign="middle", height=3)

                history.current_location.focus = self.current_highlight
                self.gopher.main_loop.widget = overlay
                return

            if line.type == "htm":
                url = line.url.replace("URL:", "")

                if INLINE_IMAGES_ENABLED and is_image(url):
                    self.display_image_inline(line)
                    return

                else:
                    if platform.system() == "Linux":
                        program = "xdg-open"

                        if is_image(url):
                            program = "feh"

                    elif platform.system() == "Darwin":
                        program = "open"

                    os.system(f"{program} {url} > /dev/null 2>&1")
                    return

            if line.type in ["img", "gif"]:
                if INLINE_IMAGES_ENABLED:
                    self.display_image_inline(line)
                    return

                file_path = self.gopher.download(line.host, line.port, line.url)
                program = "feh"
                os.system(f"{program} {file_path} > /dev/null 2>&1")
                return

            try:
                history.current_location.focus = self.current_highlight
                history.forward(line.host, line.port, line.url)
                history.current_location.walkable = walkable

                self.gopher.crawl()

            except Exception:
                pass

        if key in ["r"]:
            self.gopher.crawl()

        if key in ["i"]:
            with open("/tmp/pherguson.log", "a+") as f:
                for line in self.gopher.current_location_map:
                    f.writelines(str(line))

        if key in ["tab", "ctrl l"]:
            self.gopher.window.focus_position = "header"

        if key in ["j", "J", "up", "page up", "k", "K", "down", "page down"]:

            if key in ["j", "down"]:
                self.base_widget._keypress_down(size)
            if key in ["J", "page down"]:
                self.base_widget._keypress_page_down(size)

            if key in ["k", "up"]:
                self.base_widget._keypress_up(size)
            if key in ["K", "page up"]:
                self.base_widget._keypress_page_up(size)

            new_focus = self.get_focus()[1]

            if self.walker[new_focus].base_widget.selectable():
                self.set_highlight(new_focus)

        if key in ["h", "left", "backspace"]:
            history.back()
            self.gopher.crawl()
            self.set_highlight(history.current_location.focus)

        if key in ["q", "ctrl c"]:
            widget = urwid.Filler(urwid.AttrMap(ExitOverlay(self.gopher), "exit_overlay"))
            overlay = urwid.Overlay(
                widget, self.gopher.main_loop.widget,
                "center", 27, valign="middle", height=3)

            self.gopher.main_loop.widget = overlay
            return

    def display_image_inline(self, line):
        url = line.url.replace("URL:", "")

        if url.startswith("http"):
            filename = self.gopher.download_http(url)

        else:
            filename = self.gopher.download(line.host, line.port, line.url)

        highlighted_line = self.walker[self.current_highlight]

        self.old_line = highlighted_line
        highlighted_line.old_text = highlighted_line.base_widget.get_text()[0]
        highlighted_line.base_widget.set_text(f"- {highlighted_line.old_text[2:]}")

        img = Image.open(filename)

        img.thumbnail(THUMBNAIL_SIZE)
        thumbnail_filename, thumbnail_extension = os.path.splitext(filename)
        with open("/tmp/pherguson.log", "a+") as f:
            f.write(f"{thumbnail_filename}-thumbnail{thumbnail_extension}")

        thumbnail_filename = f"{thumbnail_filename}-thumbnail{thumbnail_extension}"
        img.save(thumbnail_filename)
        img.close()

        thumbnail = Image.open(thumbnail_filename)
        thumbnail_width, thumbnail_height = thumbnail.size
        thumbnail.close()

        self.image_preview = filename, thumbnail_filename
        self.walker.insert(self.current_highlight + 1, Box(thumbnail_height))
        self.display_image(thumbnail_filename, 0, self.current_highlight + 4)
        return

    def display_image(self, image_path, x, y):
        def thread_function(image_path, x, y):
            global STOP_THREAD
            with ueberzug.Canvas() as c:
                paths = [image_path]
                placement = c.create_placement("image", x=x, y=y, scaler=ueberzug.ScalerOption.FIT_CONTAIN.value, width=50)
                placement.path = paths[0]
                placement.visibility = ueberzug.Visibility.VISIBLE

                while True:
                    with c.synchronous_lazy_drawing:
                        placement.path = paths[0]

                    if STOP_THREAD:
                        STOP_THREAD = False
                        break

                    time.sleep(0.1)

        x = threading.Thread(target=thread_function, args=(image_path, x, y))
        x.start()


class SearchOverlay(urwid.Edit):

    def __init__(self, gopher, line):
        self.line = line
        self.gopher = gopher
        super(SearchOverlay, self).__init__(caption="Search: ")

    def keypress(self, size, key):
        if key == "enter":
            query = self.get_edit_text()

            history.forward(self.line.host, self.line.port, f"{self.line.url}\t{query}")

            self.gopher.main_loop.widget = self.gopher.window
            self.gopher.crawl()

        if key == "esc":
            self.gopher.main_loop.widget = self.gopher.window

        super(SearchOverlay, self).keypress(size, key)


class ExitOverlay(urwid.Edit):

    def __init__(self, gopher):
        self.gopher = gopher
        super(ExitOverlay, self).__init__(caption="really exit? (press 'q'): ")

    def keypress(self, size, key):
        if key == "q":
            raise urwid.ExitMainLoop()

        else:
            self.gopher.main_loop.widget = self.gopher.window
            return


class UrlBar(urwid.Columns):
    def __init__(self, gopher):
        self.gopher = gopher
        self.url_edit = urwid.AttrMap(urwid.Edit(caption=""), "url_bar")
        self.scheme = "gopher://"

        content = [
            ("pack", urwid.AttrMap(urwid.Text("// "), "url_label")),
            self.url_edit,
        ]

        super(UrlBar, self).__init__(content)

    def set_url(self, history_location):
        port = f":{history_location.port}" if history_location.port != 70 else ""

        edit_text = f"{history_location.host}{port}{history_location.url}"

        self.url_edit.base_widget.set_edit_text(edit_text)
        self.url_edit.base_widget.set_edit_pos(len(edit_text))

    def keypress(self, size, key):
        if key in ["tab", "esc"]:
            self.gopher.window.focus_position = "body"

        if key == "enter":
            url = self.url_edit.base_widget.get_edit_text()
            if self.scheme not in url:
                url = f"{self.scheme}{url}"

            url = urlparse(url)
            host, port = url.netloc.split(":") if ":" in url.netloc else (url.netloc, 70)

            history.current_location.focus = self.gopher.content_window.current_highlight
            history.forward(host, port, url.path)
            self.gopher.crawl()

            self.gopher.window.focus_position = "body"

        super(UrlBar, self).keypress(size, key)


class StatusBar(urwid.WidgetWrap):
    def __init__(self, gopher):
        self.gopher = gopher

        self.attr = urwid.AttrMap(urwid.Text("status", align="right"), "ok")
        super(StatusBar, self).__init__(self.attr)

    def set_status(self, message, level="ok"):
        self.attr.base_widget.set_text(message)
        self.attr = urwid.AttrMap(urwid.Text(message, align="right"), level)
        super(StatusBar, self).__init__(self.attr)


class Gopher():

    def __init__(self):
        self._url_bar = urwid.AttrMap(UrlBar(self), "url")
        self._content_window = urwid.AttrMap(ContentWindow(self), "list")
        self._status_bar = urwid.AttrMap(StatusBar(self), "status")

        self.header_pile = urwid.Pile([
            self._url_bar,
            urwid.AttrMap(urwid.Divider('─'), "divider")
        ])

        self.status_pile = urwid.Pile([
            urwid.AttrMap(urwid.Divider('─'), "divider"),
            self._status_bar
        ])

        self.window = urwid.Frame(
            header=self.header_pile,
            body=self._content_window,
            footer=self.status_pile,
            focus_part='body'
        )

        self.crawl()

    @property
    def url_bar(self):
        return self._url_bar.base_widget

    @property
    def content_window(self):
        return self._content_window.base_widget

    @property
    def status_bar(self):
        return self._status_bar.base_widget

    def _get_bytes(self, host, port, url):
        crlf = "\r\n"

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)

        try:
            s.connect((host, port))
            s.send(str.encode(url) + str.encode(crlf))
            s.shutdown(1)

            return s

        except (ConnectionRefusedError, socket.gaierror):
            raise Error(f"error while connecting to {host}:{port}")

    def get_content(self, host, port, url):
        s = self._get_bytes(host, port, url)
        f = s.makefile("r")

        lines = []
        while True:
            try:
                line = f.readline()
                if not line:
                    break
                if line == "":
                    break
                if line == ".":
                    break

                lines.append([part.strip('\n') for part in line.split("\t")])
            except Exception:
                pass

        s.close()

        self.url_bar.set_url(history.current_location)
        return lines

    def download_http(self, url):
        parsed_url = urlparse(url)
        download_directory = Cache.get_cache_directory(parsed_url.netloc)

        filename = url.split('/')[-1]
        file_path = f"{download_directory}/{filename}"

        if Cache.file_exists(file_path):
            self.status_bar.set_status(f"cached: {file_path}")
            return file_path

        response = requests.get(url, stream=True)

        if response.status_code == 200:
            response.raw.decode_content = True

            with open(file_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        self.status_bar.set_status(f"downloaded: {file_path}")
        return file_path

    def download(self, host, port, url):
        download_directory = Cache.get_cache_directory(host)
        filename = url.split('/')[-1]

        file_path = f"{download_directory}/{filename}"
        if Cache.file_exists(file_path):
            self.status_bar.set_status(f"cached: {file_path}")
            return file_path

        self.status_bar.set_status(f"downloading: {filename}")

        s = self._get_bytes(host, port, url)
        f = s.makefile("rb")

        with open(file_path, "wb") as file:
            file.write(f.read())

        s.close()
        self.status_bar.set_status(f"downloaded: {file_path}")

        return file_path

    def _parse_line(self, line):
        text = line[0] if len(line) > 0 else ""
        url = line[1] if len(line) > 1 else ""
        host = line[2] if len(line) > 2 else ""
        port = int(line[3]) if len(line) > 3 else 70

        line_type = "inf"
        if history.current_location.walkable and len(text) > 0:
            line_type = TYPE_MAP.get(text[0], "inf")
            text = text[1:]

        return Line(line_type, text, url, host, port)

    def crawl(self):
        try:
            location = history.current_location

            content = self.get_content(location.host, location.port, location.url)
            lines = [self._parse_line(line) for line in content]

            self.current_location_map = lines

            self.content_window.clear()
            self.content_window.set_content(lines, location.focus)

        except Error as e:
            self.status_bar.set_status(e.message, level="error")

            history.back()
            self.crawl()

    def run(self):
        self.main_loop = urwid.MainLoop(self.window, palette=COLOR_MAP)
        self.main_loop.run()


if __name__ == "__main__":
    Gopher().run()
