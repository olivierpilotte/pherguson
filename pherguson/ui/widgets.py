#!/usr/bin/env python

import ntpath
import os
from typing import Callable

import urwid

from pherguson.config.settings import DEFAULT_ROW_HEIGHT


class Highlight(urwid.AttrMap):
    """Widget for highlighting selected items"""

    def __init__(self, attr_map):
        urwid.AttrMap.__init__(
            self,
            urwid.Text(attr_map.base_widget.text),
            "selection",
        )
        self.backup = attr_map


class Selectable(urwid.WidgetWrap):
    """A selectable text widget"""

    def __init__(self, text: str, type: str, expandable: bool = False, *args, **kwargs):
        self.text = text
        if expandable:
            self.text = f"+ {self.text}"

        self.attr_map = urwid.AttrMap(urwid.Text(self.text), type)
        super(Selectable, self).__init__(self.attr_map)

    def selectable(self):
        return True

    def keypress(self, size: tuple[int, int], key: str) -> None:
        super(Selectable, self).keypress(size, key)


class Unselectable(Selectable):
    """A non-selectable text widget"""

    def selectable(self) -> bool:
        return False


class Box(urwid.Pile):
    """A box widget for spacing"""

    def __init__(self, pixels, row_height=DEFAULT_ROW_HEIGHT, *args, **kwargs):
        super(Box, self).__init__(
            [urwid.Text("") for i in range(int(pixels / row_height))]
        )

    def selectable(self):
        return False


class SearchOverlay(urwid.Edit):
    """Search overlay widget"""

    def __init__(self, line, on_search=None, on_cancel=None):
        self.line = line
        self.on_search = on_search
        self.on_cancel = on_cancel
        super(SearchOverlay, self).__init__(caption=" Search: ")

    def keypress(self, size, key):
        if key in ["enter"]:
            query = self.get_edit_text().replace(" ", "_")
            if self.on_search:
                self.on_search(self.line, query)

        if key in ["esc"]:
            if self.on_cancel:
                self.on_cancel()

        super(SearchOverlay, self).keypress(size, key)


class BookmarkOverlay(urwid.Edit):
    """Bookmark overlay widget"""

    def __init__(self, on_save=None, on_cancel=None):
        self.on_save = on_save
        self.on_cancel = on_cancel
        super(BookmarkOverlay, self).__init__(caption=" Bookmark: ")

    def keypress(self, size, key):
        if key in ["enter"]:
            bookmark_name = self.get_edit_text()
            if self.on_save:
                self.on_save(bookmark_name)

        if key in ["esc"]:
            if self.on_cancel:
                self.on_cancel()

        super(BookmarkOverlay, self).keypress(size, key)


class DownloadOverlay(urwid.Edit):
    """Download overlay widget"""

    def __init__(self, location, on_download=None, on_cancel=None):
        self.location = location
        self.on_download = on_download
        self.on_cancel = on_cancel
        self.filename = (
            f"{os.path.expanduser('~')}/Downloads/{location.url.rsplit('/')[-1]}"
        )
        super(DownloadOverlay, self).__init__(
            caption=" download location: ", edit_text=self.filename, align="left"
        )

    def keypress(self, size, key):
        if key in ["enter"]:
            if self.on_download:
                self.on_download(self.location, self.get_edit_text())

        if key in ["esc"]:
            if self.on_cancel:
                self.on_cancel()

        super(DownloadOverlay, self).keypress(size, key)


class ExitOverlay(urwid.Edit):
    """Exit confirmation overlay widget"""

    def __init__(self, on_exit=None, on_cancel=None):
        self.on_exit = on_exit
        self.on_cancel = on_cancel
        super(ExitOverlay, self).__init__(
            caption="press 'q' again to exit", align="center"
        )

    def keypress(self, size, key):
        if key == "q":
            if self.on_exit:
                self.on_exit()
        else:
            if self.on_cancel:
                self.on_cancel()


class UrlBar(urwid.Columns):
    """URL bar widget"""

    def __init__(self, on_navigate=None, on_focus_change=None):
        self.on_navigate = on_navigate
        self.on_focus_change = on_focus_change
        self.url_edit = urwid.AttrMap(urwid.Edit(caption=""), "url_bar")
        self.scheme = "gopher://"  # Default scheme

        content = [
            ("pack", urwid.AttrMap(urwid.Text("> "), "url_label")),
            self.url_edit,
        ]

        super(UrlBar, self).__init__(content)

    def set_url(self, history_location):
        """Set the URL in the bar"""
        if history_location.protocol == "gemini":
            port = f":{history_location.port}" if history_location.port != 1965 else ""
            edit_text = f"gemini://{history_location.host}{port}{history_location.url}"
        else:
            port = f":{history_location.port}" if history_location.port != 70 else ""
            edit_text = f"gopher://{history_location.host}{port}{history_location.url}"
        self.url_edit.base_widget.set_edit_text(edit_text)
        self.url_edit.base_widget.set_edit_pos(len(edit_text))

    def keypress(self, size, key):
        if key in ["tab", "esc", "ctrl l", "meta f"]:
            if self.on_focus_change:
                self.on_focus_change("body")

        if key == "enter":
            url = self.url_edit.base_widget.get_edit_text()
            # Don't add scheme if URL already has one
            if not (url.startswith("gopher://") or url.startswith("gemini://")):
                url = f"{self.scheme}{url}"

            if self.on_navigate:
                self.on_navigate(url)

        super(UrlBar, self).keypress(size, key)


class StatusBar(urwid.WidgetWrap):
    """Status bar widget"""

    def __init__(self, on_get_content_window: Callable[[], urwid.AttrMap]):
        self.on_get_content_window = on_get_content_window
        self.attr = urwid.AttrMap(urwid.Text("status", align="right"), "ok")
        super(StatusBar, self).__init__(self.attr)

    def set_status(self, message: str, level: str = "ok", align: str = "right"):
        """Set status message"""
        # Handle sound preview status if needed
        content_window: urwid.AttrMap = self.on_get_content_window()

        if (
            content_window
            and hasattr(content_window, "sound_preview_state")
            and content_window.sound_preview_state == "PLAYING"
            and hasattr(content_window, "sound_preview_filename")
            and content_window.sound_preview_filename
        ):
            width, _ = os.get_terminal_size()
            sound_preview_message = (
                f" {ntpath.basename(content_window.sound_preview_filename)}"
            )
            spacing = width - len(message) - len(sound_preview_message) - 2
            message = f"{sound_preview_message} {' ' * spacing} {message}"

        self.attr.base_widget.set_text(message)
        self.attr = urwid.AttrMap(urwid.Text(message, align=align), level)
        super(StatusBar, self).__init__(self.attr)
