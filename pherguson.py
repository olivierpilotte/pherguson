#!/usr/bin/env python

import hashlib
import ntpath
import os
import pathlib
import platform
import requests
import shutil
import signal
import socket
import subprocess
import threading
import time
import ueberzug.lib.v0 as ueberzug
import urwid

from PIL import Image
from urllib.parse import urlparse

DEFAULT_ROW_HEIGHT = 15
USE_BOLD_FONT = False
THUMBNAIL_SIZE = (384, 256)
INLINE_IMAGES_ENABLED = platform.system() == "Linux"
APPLICATION_HANDLER = "xdg-open" if platform.system() == "Linux" else "open"
HOME_DIRECTORY = os.path.expanduser("~")

STOP_IMAGE_PREVIEW_THREAD = False
SOUND_PREVIEW_THREAD = None
SOUND_PREVIEW_STATE = "STOPPED"
SOUND_PREVIEW_FILENAME = None

EXPERIMENTAL_MOUSE_NAVIGATION = False


COLOR_MAP = [
    # gopher types
    ("inf", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("gif", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("img", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("dir", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("txt", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm_img", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("ask", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("bin", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("snd", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),

    # ui elements
    ("url_label", "light blue", urwid.DEFAULT),
    ("url_bar", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT, "bold"),
    ("selection", f"light gray{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("divider", "light blue", urwid.DEFAULT),
    ("search_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("download_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
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
SELECTABLES = ["txt", "dir", "gif", "htm", "img", "gif", "ask", "bin", "snd"]
BINARIES = ["txt", "img", "gif", "bin"]

LANDING_PAGE = [
    ["iPHERGUSON"],
    ["i"],
    ["iPrototype gopher client with in-terminal image preview"],
    ["hgithub", "URL:https://github.com/olivierpilotte/pherguson"],
    ["i"],
    ["iKEYBINDINGS"],
    ["i"],
    ["iFocus URL bar: CTRL+l"],
    ["i"],
    ["iNAVIGATION"],
    ["i"],
    ["iUp: k, arrow-up"],
    ["iDown: j, arrow-down"],
    ["iPage Up: K, page-up"],
    ["iPage Down: J, page-down"],
    ["i"],
    ["iForward: l, arrow-right, enter"],
    ["iBack: h, arrow-left, backspace"],
    ["i"],
    ["iBookmarks"],
]


def shorten(path):
    return path.replace(HOME_DIRECTORY, "~")


class Cache:
    cache_directory = f"{HOME_DIRECTORY}/.config/pherguson/cache"

    @classmethod
    def get_cache_directory(cls, host):
        hash = hashlib.md5(host.encode()).hexdigest()[:8]

        cache_directory = f"{cls.cache_directory}/{hash}"
        path = pathlib.Path(cache_directory)
        path.mkdir(parents=True, exist_ok=True)

        return cache_directory

    @classmethod
    def file_exists(cls, file_path):
        return pathlib.Path(file_path).is_file()


class Line:
    def __init__(self, type, text, location):
        self.type = type
        self.text = text
        self.location = location

    def __repr__(self):
        return f"{self.type}\t{self.text}\t{self.location}\n"


class Location:
    def __init__(self, host, port, url, focus=0, walkable=True):
        self.host = host
        self.port = port
        self.url = url

        self.focus = focus
        self.walkable = walkable

    def __repr__(self):
        return f"gopher://{self.host}:{self.port}{self.url}"

    def gopher(self):
        url = "/" if self.url == "" else self.url
        return f"1a_bookmark{url}\t{self.host}\t{self.port}"


class Error(Exception):
    def __init__(self, message):
        self.message = message


class History:
    def __init__(self):
        self.history = []

    @property
    def current_location(self):
        if len(self.history) == 0:
            return Location(None, None, "LANDING")

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
# history.forward("gopher.flatline.ltd", 70, "/")


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
    def __init__(self, pixels, row_height=DEFAULT_ROW_HEIGHT, *args, **kwargs):
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
            expandable = _is_expandable(line.location.url)

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
            if len(self.walker) < 1:
                return

            # find first selectable element
            while not self.walker[focus].base_widget.selectable() and focus < len(self.walker) - 1:
                focus += 1

            self.set_highlight(focus)
            self.set_focus(focus)
            history.current_location.focus = focus

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

            line = self.gopher.current_location_map[focus]
            if "URL" in line.location.url:
                url = line.location.url.replace("URL:", "")

            else:
                url = f"gopher://{line.location.host}{line.location.url}"

            self.gopher.status_bar.set_status(url)

    def scroll(self):
        new_focus = self.get_focus()[1]
        history.current_location.focus = new_focus

        if self.walker[new_focus].base_widget.selectable():
            self.set_highlight(new_focus)

    def forward(self, line):
        try:
            walkable = line.type not in BINARIES

            history.current_location.focus = self.current_highlight
            history.forward(line.location.host, line.location.port, line.location.url)
            history.current_location.walkable = walkable

            self.gopher.crawl()

        except Exception as e:
            self.gopher.status_bar.set_status(f"{e}")

    def forward_htm(self, line, offset=0):
        url = line.location.url.replace("URL:", "")

        if INLINE_IMAGES_ENABLED and is_image(url):
            self.display_image_inline(line, offset)

        else:
            os.system(f"{APPLICATION_HANDLER} {url} > /dev/null 2>&1")

    def back(self):
        history.back()
        self.gopher.crawl()
        self.set_highlight(history.current_location.focus)

    def quit(self):
        widget = urwid.Filler(urwid.AttrMap(ExitOverlay(self.gopher), "exit_overlay"))
        exit_overlay = urwid.AttrMap(urwid.Overlay(
            widget, self.gopher.main_loop.widget,
            "center", 50, valign="middle", height=3), "exit_overlay")

        self.gopher.main_loop.widget = exit_overlay

    def refresh(self):
        self.gopher.crawl()

    def ask(self, line):
        widget = urwid.Filler(
            urwid.AttrMap(SearchOverlay(self.gopher, line), "search_overlay"))

        search_overlay = urwid.AttrMap(urwid.Overlay(
            widget, self.gopher.main_loop.widget,
            "center", 50, valign="middle", height=3), "search_overlay")

        history.current_location.focus = self.current_highlight
        self.gopher.main_loop.widget = search_overlay

    def open_image_preview(self, offset=0):
        line = self.gopher.current_location_map[self.current_highlight]

        if INLINE_IMAGES_ENABLED:
            self.display_image_inline(line, offset=offset)

        else:
            file_path = self.gopher.download(line.location)
            os.system(f"{APPLICATION_HANDLER} {file_path}")

    def close_image_preview(self):
        global STOP_IMAGE_PREVIEW_THREAD
        STOP_IMAGE_PREVIEW_THREAD = True

        highlighted_line = self.walker[self.current_highlight]

        if hasattr(highlighted_line, "old_text"):
            highlighted_line.base_widget.set_text(highlighted_line.old_text)

        self.walker.pop(self.current_highlight + 1)

        self.image_preview = None

    def bookmark(self):
        with open(f"{HOME_DIRECTORY}/.config/pherguson/bookmarks", "a") as file:
            file.write(f"{history.current_location.gopher()}\n")

    def _count_hidden_lines(self, size):
        focus = self.get_focus()[1]
        middle, top, bottom = self.calculate_visible(size, True)
        items_on_top = len(top[1])

        return focus - items_on_top

    def mouse_event(self, size, event, button, col, row, focus):
        if not EXPERIMENTAL_MOUSE_NAVIGATION:
            return

        if INLINE_IMAGES_ENABLED and not self.image_preview:
            if event == "mouse press":
                if button == 4.0:
                    self.base_widget._keypress_up(size)

                if button == 5.0:
                    self.base_widget._keypress_down(size)

                self.scroll()

        if event == "mouse release":
            focus = self.get_focus()[1]
            history.current_location.focus = focus
            self.set_highlight(focus)

        if event == "mouse press" and button == 1.0:  # left click
            if INLINE_IMAGES_ENABLED and self.image_preview:
                self.close_image_preview()

            else:
                self.back()

        if event == "mouse press" and button == 3.0:  # right click
            line = self.gopher.current_location_map[self.current_highlight]
            focus = self.get_focus()[1]

            if self.walker[focus].base_widget.selectable():
                self.set_highlight(focus)

            elif INLINE_IMAGES_ENABLED and self.image_preview:
                self.close_image_preview()

            elif line.type == "htm":
                self.forward_htm(line)

            elif line.type in ["img", "gif"]:
                self.open_image_preview()

            elif line.type in ["snd"]:
                self.play_sound(line)

            else:
                self.forward(line)

        super(ContentWindow, self).mouse_event(size, event, button, col, row, focus)

    def keypress(self, size, key):
        if history.current_location.walkable:
            line = self.gopher.current_location_map[self.current_highlight]

        if INLINE_IMAGES_ENABLED and self.image_preview:
            if key in ["h", "left", "q", "esc"]:
                self.close_image_preview()

            if key in ["l", "right", "enter"]:
                if line.type in ["img", "gif"]:
                    self.gopher.status_bar.set_status(f"open: {self.image_preview[0]}")
                    os.system(f"{APPLICATION_HANDLER} {self.image_preview[0]} > /dev/null 2>&1")

                if line.type == "htm":
                    url = line.location.url.replace("URL:", "")
                    os.system(f"{APPLICATION_HANDLER} {url} > /dev/null 2>&1")

        elif key in ["l", "right", "enter"]:
            if not history.current_location.walkable:
                return

            if line.type == "ask":
                self.ask(line)

            elif line.type == "htm":
                offset = self._count_hidden_lines(size)
                self.forward_htm(line, offset)

            elif line.type in ["img", "gif"]:
                offset = self._count_hidden_lines(size)

                self.open_image_preview(offset)

            elif line.type in ["snd"]:
                self.play_sound(line)

            else:
                self.forward(line)

        elif key in ["b"]:
            self.bookmark()

        elif key in ["r"]:
            self.refresh()

        elif key in ["s"]:
            self.stop_sound()

        elif key in ["p"]:
            pause = "false"

            global SOUND_PREVIEW_STATE
            if SOUND_PREVIEW_STATE == "PLAYING":
                SOUND_PREVIEW_STATE = "PAUSED"
                pause = "true"

            elif SOUND_PREVIEW_STATE == "PAUSED":
                SOUND_PREVIEW_STATE = "PLAYING"
                pause = "false"

            command = f"echo '{{\"command\": [\"set_property\", \"pause\", {pause}]}}' | socat - /tmp/mpvsocket > /dev/null 2>&1"
            os.system(command)

        elif key in ["i"]:
            with open("/tmp/pherguson.log", "a+") as f:
                for line in self.gopher.current_location_map:
                    f.writelines(str(line))

        elif key in ["tab", "ctrl l", ":"]:
            self.gopher.window.focus_position = "header"

        elif key in ["j", "J", "up", "page up", "k", "K", "down", "page down"]:

            if key in ["j", "down"]:
                self.base_widget._keypress_down(size)
            if key in ["J", "page down"]:
                self.base_widget._keypress_page_down(size)

            if key in ["k", "up"]:
                self.base_widget._keypress_up(size)
            if key in ["K", "page up"]:
                self.base_widget._keypress_page_up(size)

            self.scroll()

        elif key in ["h", "left", "backspace"]:
            self.back()

        elif key in ["q", "ctrl c"]:
            self.quit()

        elif key in ["d", "o"]:
            if history.current_location.walkable:
                line = self.gopher.current_location_map[self.current_highlight]
                location = line.location

                if line.type not in BINARIES:
                    return

            else:
                location = history.current_location

            if key in ["d"]:
                widget = urwid.Filler(urwid.AttrMap(DownloadOverlay(self.gopher, location), "download_overlay"))
                download_overlay = urwid.AttrMap(urwid.Overlay(
                    widget, self.gopher.main_loop.widget,
                    "center", 70, valign="middle", height=3), "download_overlay")

                self.gopher.main_loop.widget = download_overlay

            elif key in ["o"]:
                filename = f"{os.path.expanduser('~')}/Downloads/{location.url.rsplit('/')[-1]}"

                if location.url.startswith("URL"):
                    url = location.url.replace("URL:", "")
                    self.gopher.download_http(url, filename)

                else:
                    self.gopher.download(location, filename)

                self.gopher.status_bar.set_status(f"opening: {filename}")
                os.system(f"{APPLICATION_HANDLER} {filename} > /dev/null 2>&1")

    def play_sound(self, line):
        global SOUND_PREVIEW_FILENAME
        global SOUND_PREVIEW_THREAD
        if SOUND_PREVIEW_THREAD:
            return

        filename = self.gopher.download(line.location)
        SOUND_PREVIEW_FILENAME = filename

        command = f"mpv --input-ipc-server=/tmp/mpvsocket {filename} > /dev/null 2>&1"
        SOUND_PREVIEW_THREAD = subprocess.Popen(
            command, stdout=subprocess.PIPE,
            shell=True, preexec_fn=os.setsid)

        global SOUND_PREVIEW_STATE
        SOUND_PREVIEW_STATE = "PLAYING"

        self.gopher.status_bar.set_status(f"playing: {shorten(filename)}")

    def stop_sound(self):
        global SOUND_PREVIEW_THREAD
        if SOUND_PREVIEW_THREAD:
            os.killpg(os.getpgid(SOUND_PREVIEW_THREAD.pid), signal.SIGTERM)
            SOUND_PREVIEW_THREAD = None

        global SOUND_PREVIEW_STATE
        SOUND_PREVIEW_STATE = "STOPPED"

    def display_image_inline(self, line, offset=0):
        url = line.location.url.replace("URL:", "")

        if url.startswith("http"):
            filename = self.gopher.download_http(url)

        else:
            filename = self.gopher.download(line.location)

        highlighted_line = self.walker[self.current_highlight]
        highlighted_line.old_text = highlighted_line.base_widget.get_text()[0]
        highlighted_line.base_widget.set_text(f"- {highlighted_line.old_text[2:]}")

        img = Image.open(filename)
        img.thumbnail(THUMBNAIL_SIZE)

        thumbnail_filename, thumbnail_extension = os.path.splitext(filename)
        thumbnail_filename = f"{thumbnail_filename}-thumbnail{thumbnail_extension}"

        img.save(thumbnail_filename)
        img.close()

        thumbnail = Image.open(thumbnail_filename)
        thumbnail_width, thumbnail_height = thumbnail.size
        thumbnail.close()

        self.image_preview = (filename, thumbnail_filename)
        self.walker.insert(self.current_highlight + 1, Box(thumbnail_height))
        self.preview_image(thumbnail_filename, 0, self.current_highlight + 4 - offset)

    def preview_image(self, image_path, x, y):
        def thread_function(image_path, x, y):
            global STOP_IMAGE_PREVIEW_THREAD
            with ueberzug.Canvas() as canvas:
                canvas.create_placement(
                    "image", x=x, y=y, width=50,
                    scaler=ueberzug.ScalerOption.FIT_CONTAIN.value,
                    visibility=ueberzug.Visibility.VISIBLE,
                    path=image_path)

                while True:
                    if STOP_IMAGE_PREVIEW_THREAD:
                        STOP_IMAGE_PREVIEW_THREAD = False
                        break

                    time.sleep(0.01)

        threading.Thread(target=thread_function, args=(image_path, x, y)).start()


class SearchOverlay(urwid.Edit):
    def __init__(self, gopher, line):
        self.line = line
        self.gopher = gopher
        super(SearchOverlay, self).__init__(caption=" Search: ")

    def keypress(self, size, key):
        if key in ["enter"]:
            query = self.get_edit_text()
            history.forward(self.line.location.host, self.line.location.port,
                            f"{self.line.location.url}\t{query}")

            self.gopher.main_loop.widget = self.gopher.window
            self.gopher.crawl()

        if key in ["esc"]:
            self.gopher.main_loop.widget = self.gopher.window

        super(SearchOverlay, self).keypress(size, key)


class DownloadOverlay(urwid.Edit):
    def __init__(self, gopher, location):
        self.gopher = gopher
        self.location = location
        self.filename = f"{os.path.expanduser('~')}/Downloads/{location.url.rsplit('/')[-1]}"
        super(DownloadOverlay, self).__init__(
            caption=" download location: ", edit_text=self.filename,
            align="left")

    def keypress(self, size, key):
        if key in ["enter"]:
            if "URL" in self.location.url:
                url = self.location.url.replace("URL:", "")
                self.gopher.download_http(url, self.filename)

            else:
                self.gopher.download(self.location, self.filename)

            self.gopher.main_loop.widget = self.gopher.window

        if key in ["esc"]:
            self.gopher.main_loop.widget = self.gopher.window

        super(DownloadOverlay, self).keypress(size, key)


class ExitOverlay(urwid.Edit):
    def __init__(self, gopher):
        self.gopher = gopher
        super(ExitOverlay, self).__init__(
            caption="really exit? (press 'q'): ", align="center")

    def keypress(self, size, key):
        if key == "q":
            self.gopher.content_window.stop_sound()
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
        if SOUND_PREVIEW_STATE == "PLAYING":
            message = f"[playing: {ntpath.basename(SOUND_PREVIEW_FILENAME)}] {message}"

        self.attr.base_widget.set_text(message)
        self.attr = urwid.AttrMap(urwid.Text(message, align="right"), level)
        super(StatusBar, self).__init__(self.attr)


class Gopher:

    def __init__(self):
        self._url_bar = urwid.AttrMap(UrlBar(self), "url")
        self._content_window = urwid.AttrMap(ContentWindow(self), "list")
        self._status_bar = urwid.AttrMap(StatusBar(self), "status")

        self.header_pile = urwid.Pile([
            self._url_bar,
            urwid.AttrMap(urwid.Divider("─"), "divider")
        ])

        self.status_pile = urwid.Pile([
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            self._status_bar
        ])

        self.window = urwid.Frame(
            header=self.header_pile,
            body=self._content_window,
            footer=self.status_pile,
            focus_part="body"
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

    def _get_socket(self, location):
        crlf = "\r\n"

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)

        try:
            s.connect((location.host, location.port))
            s.send(str.encode(location.url) + str.encode(crlf))
            s.shutdown(1)

            return s

        except (ConnectionRefusedError, socket.gaierror):
            raise Error(f"error connecting to {location.host}:{location.port}")

    def get_content(self, location):
        sock = self._get_socket(location)
        file = sock.makefile("r")

        lines = []
        while True:
            try:
                line = file.readline()
                if not line:
                    break
                if line == "":
                    break

                lines.append([part.strip("\n") for part in line.split("\t")])
            except Exception:
                pass

        sock.close()

        self.url_bar.set_url(history.current_location)
        return lines

    def download_http(self, url, file_path=None):
        parsed_url = urlparse(url)
        filename = url.split("/")[-1]

        if not file_path:
            download_directory = Cache.get_cache_directory(parsed_url.netloc)

            file_path = f"{download_directory}/{filename}"

            if Cache.file_exists(file_path):
                self.status_bar.set_status(f"cached: {file_path.replace(HOME_DIRECTORY, '~')}")
                return file_path

        self.status_bar.set_status(f"downloading: {filename}")
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            response.raw.decode_content = True

            with open(file_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        self.status_bar.set_status(f"downloaded: {file_path.replace(HOME_DIRECTORY, '~')}")
        return file_path

    def download(self, location, file_path=None):
        filename = location.url.split("/")[-1]
        if not file_path:
            download_directory = Cache.get_cache_directory(location.host)

            file_path = f"{download_directory}/{filename}"
            if Cache.file_exists(file_path):
                self.status_bar.set_status(f"cached: {file_path.replace(HOME_DIRECTORY, '~')}")
                return file_path

        self.status_bar.set_status(f"downloading: {filename}")

        s = self._get_socket(location)
        f = s.makefile("rb")

        with open(file_path, "wb") as file:
            file.write(f.read())

        s.close()
        self.status_bar.set_status(f"downloaded: {file_path.replace(HOME_DIRECTORY, '~')}")

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

        return Line(line_type, text, Location(host, port, url))

    def crawl(self):
        try:
            location = history.current_location

            if location.url != "LANDING":
                self.status_bar.set_status(f"loading: {location}")
                content = self.get_content(location)

            else:
                content = LANDING_PAGE
                with open(f"{HOME_DIRECTORY}/.config/pherguson/bookmarks", "r") as file:
                    for line in file.read().split("\n"):
                        if line == "":
                            break

                        content.append(line.split("\t"))

            lines = [self._parse_line(line) for line in content]

            self.current_location_map = lines

            self.content_window.clear()
            self.content_window.set_content(lines, location.focus)

        except Error as e:
            self.status_bar.set_status(e.message, level="error")

            history.back()
            self.crawl()

    def run(self):
        screen = urwid.raw_display.Screen()
        screen.set_terminal_properties(256)

        self.main_loop = urwid.MainLoop(self.window, palette=COLOR_MAP, screen=screen)

        try:
            self.main_loop.run()

        except KeyboardInterrupt:
            global STOP_IMAGE_PREVIEW_THREAD
            STOP_IMAGE_PREVIEW_THREAD = True

            global SOUND_PREVIEW_THREAD
            if SOUND_PREVIEW_THREAD:
                os.killpg(os.getpgid(SOUND_PREVIEW_THREAD.pid), signal.SIGTERM)
                SOUND_PREVIEW_THREAD = None

            exit(0)


if __name__ == "__main__":
    Gopher().run()


