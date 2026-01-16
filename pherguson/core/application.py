#!/usr/bin/env python

import os
import pathlib
import queue
import signal
import sys
import threading
import time
import urwid
from typing import List

from .models import History, Location, Line
from .unified_client import UnifiedClient
from ..config.settings import (
    HOME_DIRECTORY,
    COLOR_MAP,
    APPLICATION_HANDLER,
    INLINE_IMAGES_ENABLED,
)
from ..ui.widgets import (
    UrlBar,
    StatusBar,
    SearchOverlay,
    BookmarkOverlay,
    DownloadOverlay,
    ExitOverlay,
)
from ..ui.content_window import ContentWindow
from ..utils.helpers import execute, is_image


class GopherApplication:
    """Main application class that coordinates all components"""

    def __init__(self) -> None:
        # Initialize history and client
        self.history = History()
        self.client = UnifiedClient(status_callback=self._status_callback)

        # Initialize UI components
        self._url_bar = urwid.AttrMap(
            UrlBar(
                self,
                on_navigate=self._handle_url_navigation,
                on_focus_change=self._handle_focus_change,
            ),
            "url",
        )
        self._content_window = urwid.AttrMap(ContentWindow(self), "list")
        self._status_bar = urwid.AttrMap(StatusBar(self), "status")

        # Create main window layout
        self.header_pile = urwid.Pile(
            [self._url_bar, urwid.AttrMap(urwid.Divider("─"), "divider")]
        )

        self.status_pile = urwid.Pile(
            [urwid.AttrMap(urwid.Divider("─"), "divider"), self._status_bar]
        )

        self.window = urwid.Frame(
            header=self.header_pile,
            body=self._content_window,
            footer=self.status_pile,
            focus_part="body",
        )

        # Initialize with default location
        self._initialize_default_location()
        self.crawl()

    def _initialize_default_location(self) -> None:
        """Initialize with provided URL or default to gopher.flatline.ltd"""
        try:
            # If a command line argument is provided, start with that URL
            if len(sys.argv) > 1:
                url = sys.argv[1]
                # Parse URL using unified client
                location = self.client.parse_url(url)
                self.history.forward(location)
            else:
                # Otherwise start with the default landing page
                self.history.forward(Location("gopher.flatline.ltd", 70, "/"))
        except Exception as e:
            print(e)
            time.sleep(3)

    def _status_callback(self, message: str, level: str = "ok") -> None:
        """Callback for status updates from the client"""
        self.status_bar.set_status(message, level)

    def _handle_url_navigation(self, url: str) -> None:
        """Handle URL navigation from URL bar"""
        # Parse URL using unified client
        location = self.client.parse_url(url)

        self.history.current_location.focus = self.content_window.current_highlight
        self.history.forward(location)
        self.crawl()
        self.window.focus_position = "body"

    def _handle_focus_change(self, focus_part: str) -> None:
        """Handle focus changes between UI components"""
        self.window.focus_position = focus_part

    @property
    def url_bar(self) -> UrlBar:
        return self._url_bar.base_widget

    @property
    def content_window(self) -> ContentWindow:
        return self._content_window.base_widget

    @property
    def status_bar(self) -> StatusBar:
        return self._status_bar.base_widget

    def crawl(self) -> None:
        """Fetch and display content for current location"""
        try:
            location = self.history.current_location
            lines = self.client.crawl(location)

            self.content_window.clear()
            self.content_window.set_content(lines, location.focus)
            self.url_bar.set_url(location)

        except Exception as e:
            self.status_bar.set_status(str(e), level="error")
            self.history.back()
            self.crawl()

    def navigate_forward(self, line: "Line") -> None:
        """Navigate to a new location"""
        try:
            walkable = line.type not in [
                "bin",
                "txt",
                "hex",
                "img",
                "gif",
                "png",
                "rtf",
                "pdf",
                "xml",
            ]

            self.history.current_location.focus = self.content_window.current_highlight
            line.location.walkable = walkable
            self.history.forward(line.location)
            self.history.current_location.walkable = walkable

            self.crawl()
        except Exception as e:
            self.status_bar.set_status(f"error: {e}")

    def navigate_back(self) -> None:
        """Navigate back in history"""
        self.history.back()
        self.crawl()
        self.content_window.set_highlight(self.history.current_location.focus)

    def refresh(self) -> None:
        """Refresh current content"""
        if self.content_window.sound_preview_thread is None:
            self.content_window.stop_sound()
        self.crawl()

    def open_http_link(self, line: "Line", offset: int = 0) -> None:
        """Open HTTP link in external application"""
        url = line.location.url.replace("URL:", "")

        if (
            self.content_window.image_preview
            and INLINE_IMAGES_ENABLED
            and is_image(url)
        ):
            self.content_window.display_image_inline(line, offset)
        else:
            execute(f"{APPLICATION_HANDLER} {url}")

    def open_file(self, line: "Line") -> None:
        """Open file in external application"""
        filename = (
            f"{os.path.expanduser('~')}/Downloads/{line.location.url.rsplit('/')[-1]}"
        )

        if line.location.url.startswith("URL"):
            url = line.location.url.replace("URL:", "")
            self.client.download_http(url, filename)
        else:
            self.client.download(line.location, filename)

        self.status_bar.set_status(f"opening: {filename}")
        execute(f"{APPLICATION_HANDLER} {filename}")

    def show_search_overlay(self, line: "Line") -> None:
        """Show search overlay"""
        widget = urwid.Filler(
            urwid.AttrMap(
                SearchOverlay(
                    self,
                    line,
                    on_search=self._handle_search,
                    on_cancel=self._hide_overlay,
                ),
                "search_overlay",
            )
        )

        search_overlay = urwid.AttrMap(
            urwid.Overlay(
                widget, self.main_loop.widget, "center", 50, valign="middle", height=3
            ),
            "search_overlay",
        )

        self.history.current_location.focus = self.content_window.current_highlight
        self.main_loop.widget = search_overlay

    def show_bookmark_overlay(self) -> None:
        """Show bookmark overlay"""
        widget = urwid.Filler(
            urwid.AttrMap(
                BookmarkOverlay(
                    self,
                    on_save=self._handle_bookmark_save,
                    on_cancel=self._hide_overlay,
                ),
                "bookmark_overlay",
            )
        )

        bookmark_overlay = urwid.AttrMap(
            urwid.Overlay(
                widget, self.main_loop.widget, "center", 50, valign="middle", height=3
            ),
            "bookmark_overlay",
        )

        self.main_loop.widget = bookmark_overlay

    def show_download_overlay(self, location: Location) -> None:
        """Show download overlay"""
        widget = urwid.Filler(
            urwid.AttrMap(
                DownloadOverlay(
                    self,
                    location,
                    on_download=self._handle_download,
                    on_cancel=self._hide_overlay,
                ),
                "download_overlay",
            )
        )

        download_overlay = urwid.AttrMap(
            urwid.Overlay(
                widget, self.main_loop.widget, "center", 70, valign="middle", height=3
            ),
            "download_overlay",
        )

        self.main_loop.widget = download_overlay

    def show_exit_overlay(self) -> None:
        """Show exit confirmation overlay"""
        widget = urwid.Filler(
            urwid.AttrMap(
                ExitOverlay(
                    self, on_exit=self._handle_exit, on_cancel=self._hide_overlay
                ),
                "exit_overlay",
            )
        )

        exit_overlay = urwid.AttrMap(
            urwid.Overlay(
                widget, self.main_loop.widget, "center", 50, valign="middle", height=3
            ),
            "exit_overlay",
        )

        self.main_loop.widget = exit_overlay

    def show_bookmarks(self) -> None:
        """Show bookmarks page"""
        content = [[""], ["i   B O O K M A R K S"], [""]]

        # Ensure config directory exists
        config_dir = f"{HOME_DIRECTORY}/.config/pherguson"
        pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)

        try:
            with open(f"{config_dir}/bookmarks") as file:
                for line in file.read().split("\n"):
                    if line == "":
                        break
                    content.append(line.split("\t"))
        except FileNotFoundError:
            pass

        self.history.show_bookmarks()
        lines = [
            self.client._parse_line(line, self.history.current_location)
            for line in content
        ]
        self.client.current_location_map = lines

        self.content_window.clear()
        self.content_window.set_content(lines, focus=0)

    def show_history(self) -> None:
        """Show history page"""
        content: List[List[str]] = []

        # Ensure config directory exists
        config_dir = f"{HOME_DIRECTORY}/.config/pherguson"
        pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)

        try:
            with open(f"{config_dir}/history") as file:
                for line in file.read().split("\n"):
                    if line == "":
                        break
                    content.append(line.split("\t"))
        except FileNotFoundError:
            pass

        content.append(["i"])
        content.append(["i   H I S T O R Y"])
        content.append(["i"])

        self.history.show_history()
        lines = [
            self.client._parse_line(line, self.history.current_location)
            for line in content[::-1]
        ]
        self.client.current_location_map = lines

        self.content_window.clear()
        self.content_window.set_content(lines, focus=0)

    def focus_url_bar(self) -> None:
        """Focus the URL bar"""
        self.window.focus_position = "header"

    def log_debug_info(self) -> None:
        """Log debug information"""
        with open("/tmp/pherguson.log", "a+") as f:
            for line in self.client.current_location_map:
                f.writelines(str(line))

    def _handle_search(self, line: Line, query: str) -> None:
        """Handle search submission"""
        line.location.url = f"{line.location.url}\t{query}"
        self.history.forward(line.location)
        self.main_loop.widget = self.window
        self.crawl()

    def _handle_bookmark_save(self, bookmark_name: str) -> None:
        """Handle bookmark save"""
        config_dir = f"{HOME_DIRECTORY}/.config/pherguson"
        pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)

        with open(f"{config_dir}/bookmarks", "a") as file:
            file.write(f"{self.history.current_location.get_link(bookmark_name)}\n")

        self.main_loop.widget = self.window

    def _handle_download(self, location: Location, file_path: str) -> None:
        """Handle file download"""
        if "URL" in location.url:
            url = location.url.replace("URL:", "")
            self.client.download_http(url, file_path)
        else:
            self.client.download(location, file_path)

        self.main_loop.widget = self.window

    def _handle_exit(self) -> None:
        """Handle application exit"""
        self.content_window.stop_sound()
        raise urwid.ExitMainLoop()

    def _hide_overlay(self) -> None:
        """Hide current overlay"""
        self.main_loop.widget = self.window

    def refresh_screen(
        self,
        main_loop: urwid.MainLoop,
        stop_event: threading.Event,
        message_queue: queue.Queue,
    ) -> None:
        """Refresh screen periodically"""
        while not stop_event.wait(timeout=0.5):
            message_queue.put(time.strftime("time %X"))
            main_loop.draw_screen()

    def run(self) -> None:
        """Run the application"""
        screen = urwid.raw_display.Screen()
        screen.set_terminal_properties(256)

        stop_event = threading.Event()
        message_queue = queue.Queue()

        self.main_loop = urwid.MainLoop(self.window, palette=COLOR_MAP, screen=screen)

        try:
            self.refresh_screen_thread = threading.Thread(
                target=self.refresh_screen,
                args=[self.main_loop, stop_event, message_queue],
            )

            self.refresh_screen_thread.start()
            self.main_loop.run()

        except (urwid.ExitMainLoop, KeyboardInterrupt):
            self.content_window.stop_image_preview_thread = True

            if self.content_window.sound_preview_thread:
                os.killpg(
                    os.getpgid(self.content_window.sound_preview_thread.pid),
                    signal.SIGTERM,
                )
                self.content_window.sound_preview_thread = None

        stop_event.set()
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                thread.join()

        exit(0)
