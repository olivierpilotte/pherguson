#!/usr/bin/env python

import datetime
import hashlib
import ntpath
import os
import pathlib
import platform
import queue
import requests
import shutil
import signal
import socket
import sys
import subprocess
import threading
import time
import urwid

from urllib.parse import urlparse


APPLICATION_HANDLER = "xdg-open" if platform.system() == "Linux" else "open"
DEFAULT_ROW_HEIGHT = 15
EXPERIMENTAL_MOUSE_NAVIGATION = False
HOME_DIRECTORY = os.path.expanduser("~")
THUMBNAIL_SIZE = (384, 256)
USE_BOLD_FONT = True

SOUND_PREVIEW_ENABLED = True if shutil.which("mpv") else False
sound_preview_thread = None
sound_preview_state = "STOPPED"
sound_preview_filename = None

INLINE_IMAGES_ENABLED = True if shutil.which("ueberzug") else False
stop_image_preview_thread = False

if INLINE_IMAGES_ENABLED:
    from PIL import Image
    import ueberzug.lib.v0 as ueberzug


COLOR_MAP = [
    # gopher types
    ("inf", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("hex", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("gif", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("img", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("dir", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("txt", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("htm_img", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("ask", f"dark blue{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("bin", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("snd", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("vid", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("pdf", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),

    # ui elements
    ("url_label", "light blue", urwid.DEFAULT),
    ("url_bar", f"{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT, "bold"),
    ("selection", f"light gray{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("divider", "light blue", urwid.DEFAULT),
    ("search_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("download_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("bookmark_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("bookmark_entry", f"white{',bold' if USE_BOLD_FONT else ''}", "black"),
    ("exit_overlay", f"{',bold' if USE_BOLD_FONT else ''}", "dark red"),
    ("list", urwid.DEFAULT, urwid.DEFAULT),

    # status bar levels
    ("ok", f"dark green{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("loading", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("warning", f"brown{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
    ("error", f"dark red{',bold' if USE_BOLD_FONT else ''}", urwid.DEFAULT),
]

TYPE_MAP = {
    # canonical types
    "0": "txt",  # text file
    "1": "dir",  # submenu
    "2": "cns",  # CCSO Nameserver
    "3": "err",  # Error
    "4": "hex",  # Error
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
    "p": "png",  # image file
    "r": "rtf",  # rft file
    "s": "snd",  # sound file
    ";": "vid",  # video file
    "P": "pdf",  # pdf file
    "X": "xml",  # xml file
}
SELECTABLES = ["txt", "dir", "gif", "htm", "img", "gif", "ask",
               "bin", "png", "rtf", "snd", "vid", "pdf", "xml", "hex"]
BINARIES = ["txt", "hex", "img", "gif", "bin", "png", "rtf", "pdf", "xml"]

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


def execute(command):
    try:
        with open(os.devnull, "wb") as devnull:
            subprocess.check_call(command.split(" "), stdout=devnull, stderr=devnull)

    except Exception:
        pass


class Cache:
    cache_directory = f"{HOME_DIRECTORY}/.cache/pherguson"

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
    def __init__(self, host, port, url, focus=0, walkable=True,
                 bookmarks=False, history=False):

        self.host = host
        self.port = int(port) if port else 70
        self.url = url

        self.focus = focus
        self.walkable = walkable

        self.bookmarks = bookmarks
        self.history = history

    def __repr__(self):
        return f"gopher://{self.host}:{self.port}{self.url}"

    def get_link(self, name=None):
        url = "/" if self.url == "" else self.url
        return (
            f"{'1' if self.walkable else '0'}"
            f"{name if name else url}\t{url}\t{self.host}\t{self.port}"
        )


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

    def forward(self, location):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        link = location.get_link(name=f"{timestamp} {str(location)}")

        with open(f"{HOME_DIRECTORY}/.config/pherguson/history", "a") as file:
            file.write(f"{link}\n")

        self.history.append(location)

    def set_focus(self, focus):
        history.current_location.focus = focus

    def back(self):
        if len(self.history) > 1:
            self.history.pop()

    def show_bookmarks(self):
        self.history.append(Location("", 70, "", bookmarks=True))

    def show_history(self):
        self.history.append(Location("", 70, "", history=True))


try:
    history = History()
    if len(sys.argv) > 1:
        url = sys.argv[1]

        if not url.startswith("gopher://"):
            url = f"gopher://{url}"

        url = urlparse(url)
        host, port = url.netloc.split(":") if ":" in url.netloc else (url.netloc, 70)
        history.forward(Location(host, port, url.path))

    else:
        history.forward(Location("gopher.flatline.ltd", 70, "/"))

except Exception as e:
    print(e)
    time.sleep(3)


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

    def keypress(self, size, key):
        super(Selectable, self).keypress(size, key)


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
            return INLINE_IMAGES_ENABLED and is_image(url.lower())

        for line in lines:
            selectable = line.type in SELECTABLES
            expandable = _is_expandable(line.location.url)

            type = line.type

            if expandable and line.type == "htm":
                type = "htm_img"

            formatted_text = (
                f"{line.type.upper() if selectable else ''}"
                f"{' ' if selectable else ''}{line.text}"
            )
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
            while (not self.walker[focus].base_widget.selectable() and focus < len(self.walker) - 1):
                focus += 1

            if focus == len(self.walker) - 1:
                return

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
            line.location.walkable = walkable
            history.forward(line.location)
            history.current_location.walkable = walkable

            self.gopher.crawl()

        except Exception as e:
            self.gopher.status_bar.set_status(f"error: {e}")

    def forward_htm(self, line, offset=0):
        url = line.location.url.replace("URL:", "")

        if INLINE_IMAGES_ENABLED and is_image(url):
            self.display_image_inline(line, offset)

        else:
            execute(f"{APPLICATION_HANDLER} {url}")

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
        global sound_preview_thread
        if sound_preview_thread is None:
            self.stop_sound()

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
            execute(f"{APPLICATION_HANDLER} {file_path}")

    def close_image_preview(self):
        global stop_image_preview_thread
        stop_image_preview_thread = True

        highlighted_line = self.walker[self.current_highlight]

        if hasattr(highlighted_line, "old_text"):
            highlighted_line.base_widget.set_text(highlighted_line.old_text)

        self.walker.pop(self.current_highlight + 1)

        self.image_preview = None

    def add_bookmark(self):
        widget = urwid.Filler(
            urwid.AttrMap(BookmarkOverlay(self.gopher), "bookmark_overlay"))

        bookmark_overlay = urwid.AttrMap(urwid.Overlay(
            widget, self.gopher.main_loop.widget,
            "center", 50, valign="middle", height=3), "bookmark_overlay")

        self.gopher.main_loop.widget = bookmark_overlay

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

            elif line.type in ["snd", "vid"]:
                if SOUND_PREVIEW_ENABLED:
                    self.play_sound(line)

                else:
                    file_path = self.gopher.download(line.location)
                    execute(f"{APPLICATION_HANDLER} {file_path}")

            else:
                self.forward(line)

        super(ContentWindow, self).mouse_event(size, event, button, col, row, focus)

    def keypress(self, size, key):
        line = None

        def _open(location):
            filename = f"{os.path.expanduser('~')}/Downloads/{location.url.rsplit('/')[-1]}"

            if location.url.startswith("URL"):
                url = location.url.replace("URL:", "")
                self.gopher.download_http(url, filename)

            else:
                self.gopher.download(location, filename)

            self.gopher.status_bar.set_status(f"opening: {filename}")
            execute(f"{APPLICATION_HANDLER} {filename}")

        if history.current_location.walkable:
            try:
                line = self.gopher.current_location_map[self.current_highlight]

            except IndexError:
                pass

        if INLINE_IMAGES_ENABLED and self.image_preview:
            if key in ["h", "left", "q", "esc"]:
                self.close_image_preview()

            if key in ["l", "right", "enter"]:
                if line.type in ["img", "gif"]:
                    self.gopher.status_bar.set_status(f"open: {self.image_preview[0]}")
                    execute(f"{APPLICATION_HANDLER} {self.image_preview[0]}")

                if line.type == "htm":
                    url = line.location.url.replace("URL:", "")
                    execute(f"{APPLICATION_HANDLER} {url}")

        elif key in ["l", "right", "enter"]:
            if not line:
                return

            if not history.current_location.walkable:
                return

            if line.type == "ask":
                self.ask(line)

            elif line.type == "htm":
                offset = self._count_hidden_lines(size)
                self.forward_htm(line, offset)

            elif line.type in ["img", "gif"]:
                offset = self._count_hidden_lines(size)

                try:
                    self.open_image_preview(offset)

                except Exception:
                    self.close_image_preview(offset)

            elif line.type in ["snd", "vid"]:
                if SOUND_PREVIEW_ENABLED:
                    self.play_sound(line)

                else:
                    file_path = self.gopher.download(line.location)
                    execute(f"mplayer {file_path}")

            elif line.type in ["bin", "rtf", "pdf", "xml"]:
                line = self.gopher.current_location_map[self.current_highlight]
                location = line.location
                _open(line.location)

            else:
                self.forward(line)

        elif key in ["b"]:
            self.add_bookmark()

        elif key in ["r"]:
            self.refresh()

        elif key in ["s"]:
            self.stop_sound()
            self.refresh()

        elif key in ["p"]:
            pause = "false"

            global sound_preview_state
            if sound_preview_state == "PLAYING":
                sound_preview_state = "PAUSED"
                pause = "true"

            elif sound_preview_state == "PAUSED":
                sound_preview_state = "PLAYING"
                pause = "false"

            command = f"echo '{{\"command\": [\"set_property\", \"pause\", {pause}]}}' | socat - /tmp/mpvsocket"
            execute(command)

        elif key in ["i"]:
            with open("/tmp/pherguson.log", "a+") as f:
                for line in self.gopher.current_location_map:
                    f.writelines(str(line))

        elif key in ["tab", "ctrl l", "meta f", ":"]:
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

            else:
                location = history.current_location

            if key in ["d"]:
                widget = urwid.Filler(
                    urwid.AttrMap(
                        DownloadOverlay(self.gopher, location),
                        "download_overlay"
                    )
                )
                download_overlay = urwid.AttrMap(
                    urwid.Overlay(
                        widget, self.gopher.main_loop.widget,
                        "center", 70, valign="middle", height=3
                    ),
                    "download_overlay"
                )

                self.gopher.main_loop.widget = download_overlay

            elif key in ["o"]:
                location = line.location
                _open(location)

        elif key in ["B", "ctrl b"]:
            content = [[""], ["i   B O O K M A R K S"], [""]]
            with open(f"{HOME_DIRECTORY}/.config/pherguson/bookmarks") as file:
                for line in file.read().split("\n"):
                    if line == "":
                        break

                    content.append(line.split("\t"))

            history.show_bookmarks()

            lines = [self.gopher._parse_line(line) for line in content]
            self.gopher.current_location_map = lines

            self.clear()
            self.set_content(lines, focus=0)

        elif key in ["H", "ctrl h"]:
            content = []
            with open(f"{HOME_DIRECTORY}/.config/pherguson/history") as file:
                for line in file.read().split("\n"):
                    if line == "":
                        break

                    content.append(line.split("\t"))

            content.append(["i"])
            content.append(["i   H I S T O R Y"])
            content.append(["i"])

            history.show_history()

            lines = [self.gopher._parse_line(line) for line in content[::-1]]
            self.gopher.current_location_map = lines

            self.clear()
            self.set_content(lines, focus=0)

    def play_sound(self, line):
        global sound_preview_filename
        global sound_preview_thread
        if sound_preview_thread:
            return

        filename = self.gopher.download(line.location)
        sound_preview_filename = filename

        command = f"mpv --really-quiet --input-ipc-server=/tmp/mpvsocket {filename}"
        sound_preview_thread = subprocess.Popen(
            command, stdout=subprocess.PIPE,
            shell=True, preexec_fn=os.setsid)

        global sound_preview_state
        sound_preview_state = "PLAYING"
        self.refresh()

    def stop_sound(self):
        global sound_preview_thread
        if sound_preview_thread:
            os.killpg(os.getpgid(sound_preview_thread.pid), signal.SIGTERM)
            sound_preview_thread = None

        global sound_preview_state
        sound_preview_state = "STOPPED"

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
            global stop_image_preview_thread
            with ueberzug.Canvas() as canvas:
                canvas.create_placement(
                    "image", x=x, y=y, width=50,
                    scaler=ueberzug.ScalerOption.FIT_CONTAIN.value,
                    visibility=ueberzug.Visibility.VISIBLE,
                    path=image_path)

                while True:
                    if stop_image_preview_thread:
                        stop_image_preview_thread = False
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
            query = self.get_edit_text().replace(" ", "_")

            self.line.location.url = f"{self.line.location.url}\t{query}"
            history.forward(self.line.location)

            self.gopher.main_loop.widget = self.gopher.window
            self.gopher.crawl()

        if key in ["esc"]:
            self.gopher.main_loop.widget = self.gopher.window

        super(SearchOverlay, self).keypress(size, key)


class BookmarkOverlay(urwid.Edit):
    def __init__(self, gopher):
        self.gopher = gopher
        super(BookmarkOverlay, self).__init__(caption=" Bookmark: ")

    def keypress(self, size, key):
        if key in ["enter"]:
            bookmark_name = self.get_edit_text()

            with open(f"{HOME_DIRECTORY}/.config/pherguson/bookmarks", "a") as file:
                file.write(f"{history.current_location.get_link(bookmark_name)}\n")

            self.gopher.main_loop.widget = self.gopher.window

        if key in ["esc"]:
            self.gopher.main_loop.widget = self.gopher.window

        super(BookmarkOverlay, self).keypress(size, key)


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
            caption="press 'q' again to exit", align="center")

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
        if key in ["tab", "esc", "ctrl l", "meta f"]:
            self.gopher.window.focus_position = "body"

        if key == "enter":
            url = self.url_edit.base_widget.get_edit_text()
            if self.scheme not in url:
                url = f"{self.scheme}{url}"

            url = urlparse(url)
            host, port = \
                url.netloc.split(":") if ":" in url.netloc else (url.netloc, 70)

            history.current_location.focus = \
                self.gopher.content_window.current_highlight

            history.forward(Location(host, port, url.path))
            self.gopher.crawl()

            self.gopher.window.focus_position = "body"

        super(UrlBar, self).keypress(size, key)


class StatusBar(urwid.WidgetWrap):
    def __init__(self, gopher):
        self.gopher = gopher

        self.attr = urwid.AttrMap(urwid.Text("status", align="right"), "ok")
        super(StatusBar, self).__init__(self.attr)

    def set_status(self, message, level="ok", align="right"):
        if sound_preview_state == "PLAYING":
            width, _ = os.get_terminal_size()
            sound_preview_message = (
                f"[playing: {ntpath.basename(sound_preview_filename)}]")
            spacing = width - len(message) - len(sound_preview_message) - 2

            message = f"{sound_preview_message} {' ' * spacing} {message}"

        self.attr.base_widget.set_text(message)
        self.attr = urwid.AttrMap(urwid.Text(message, align=align), level)
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

        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        skt.settimeout(10)

        try:
            with open("/tmp/pherguson.log", "w") as file:
                file.write(f"{location.host} {location.port}\n")

            skt.connect((location.host, location.port))
            skt.send(str.encode(location.url) + str.encode(crlf))
            skt.shutdown(1)

            return skt

        except (ConnectionRefusedError, socket.gaierror, OSError):
            raise Error(f"error connecting to {location.host}:{location.port}")

    def get_content(self, location):
        sock = self._get_socket(location)
        file = sock.makefile("r")

        lines = []
        while True:
            try:
                line = file.readline()
                if not line or line == "":
                    break

                lines.append([part.strip("\n") for part in line.split("\t")])

            except Exception as e:
                self.status_bar.set_status(str(e), level="warning")

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
                self.status_bar.set_status(
                    f"cached: {file_path.replace(HOME_DIRECTORY, '~')}")
                return file_path

        self.status_bar.set_status(
            f"downloading: {url}", level="loading")
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            response.raw.decode_content = True

            with open(file_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        return file_path

    def download(self, location, file_path=None):
        filename = location.url.split("/")[-1]
        if not file_path:
            download_directory = Cache.get_cache_directory(location.host)

            file_path = f"{download_directory}/{filename}"
            if Cache.file_exists(file_path):
                self.status_bar.set_status(
                    f"cached: {file_path.replace(HOME_DIRECTORY, '~')}")
                return file_path

        self.status_bar.set_status(
            f"downloading: gopher://{location.host}{location.url}",
            level="loading")

        s = self._get_socket(location)
        f = s.makefile("rb")

        with open(file_path, "wb") as file:
            file.write(f.read())

        s.close()

        return file_path

    def _parse_line(self, line):
        text = line[0] if len(line) > 0 else ""
        url = line[1] if len(line) > 1 else ""
        host = line[2] if len(line) > 2 else ""
        try:
            port = int(line[3]) if len(line) > 3 else 70

        except Exception:
            port = 70

        with open("/tmp/pherguson.log", "w") as file:
            file.write((str(history.current_location.url)))

        line_type = "inf"
        if history.current_location.walkable and len(text) > 0:
            line_type = TYPE_MAP.get(text[0], "inf")
            text = text[1:]

        return Line(line_type, text, Location(host, port, url))

    def crawl(self):
        try:
            location = history.current_location
            self.status_bar.set_status(f"{location}", level="loading")
            content = self.get_content(location)

            lines = [self._parse_line(line) for line in content]
            self.current_location_map = lines

            self.content_window.clear()
            self.status_bar.set_status(f"{location}")
            self.content_window.set_content(lines, location.focus)

        except Error as e:
            self.status_bar.set_status(e.message, level="error")

            history.back()
            self.crawl()

    def refresh_screen(self, main_loop, stop_event, message_queue):
        while not stop_event.wait(timeout=0.5):
            message_queue.put(time.strftime('time %X'))
            main_loop.draw_screen()

    def run(self):
        screen = urwid.raw_display.Screen()
        screen.set_terminal_properties(256)

        stop_event = threading.Event()
        message_queue = queue.Queue()

        self.main_loop = urwid.MainLoop(
            self.window, palette=COLOR_MAP, screen=screen)

        try:
            self.refresh_screen_thread = threading.Thread(
                target=self.refresh_screen,
                args=[self.main_loop, stop_event, message_queue])

            self.refresh_screen_thread.start()
            self.main_loop.run()

        except (urwid.ExitMainLoop, KeyboardInterrupt):
            global stop_image_preview_thread
            stop_image_preview_thread = True

            global sound_preview_thread
            if sound_preview_thread:
                os.killpg(os.getpgid(sound_preview_thread.pid), signal.SIGTERM)
                sound_preview_thread = None

        stop_event.set()
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                thread.join()

        exit(0)


if __name__ == "__main__":
    Gopher().run()
