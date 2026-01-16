#!/usr/bin/env python

import datetime
import hashlib
import pathlib
from typing import List

from pherguson.config.settings import HOME_DIRECTORY


class Location:
    def __init__(
        self,
        host: str,
        port: int,
        url: str,
        focus: int = 0,
        walkable: bool = True,
        bookmarks: bool = False,
        history: bool = False,
        protocol: str = "gopher",
    ):
        self.host: str = host
        self.port: int = (
            int(port) if port > 0 else (1965 if protocol == "gemini" else 70)
        )
        self.url: str = url
        self.focus: int = focus
        self.walkable: bool = walkable
        self.bookmarks: bool = bookmarks
        self.history: bool = history
        self.protocol: str = protocol

    def __repr__(self):
        if self.protocol == "gemini":
            return f"gemini://{self.host}:{self.port}{self.url}"
        else:
            return f"gopher://{self.host}:{self.port}{self.url}"

    def get_link(self, name: str = "") -> str:
        """Generate a link string"""
        url = "/" if self.url == "" else self.url
        if self.protocol == "gemini":
            return f"gemini://{self.host}:{self.port}{url}"
        else:
            return (
                f"{'1' if self.walkable else '0'}"
                f"{name if name else url}\t{url}\t{self.host}\t{self.port}"
            )


class Line:
    def __init__(self, type: str, text: str, location: Location):
        self.type = type
        self.text = text
        self.location: Location = location

    def __repr__(self):
        return f"{self.type}\t{self.text}\t{self.location}\n"


class Error(Exception):
    def __init__(self, message: str):
        self.message = message


class History:
    def __init__(self):
        self.history: List[Location] = []

    @property
    def current_location(self) -> Location:
        if len(self.history) == 1:
            return self.history[0]
        return self.history[-1]

    def forward(self, location: Location):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        link = location.get_link(name=f"{timestamp} {str(location)}")

        # Ensure config directory exists
        config_dir = f"{HOME_DIRECTORY}/.config/pherguson"
        pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)

        with open(f"{config_dir}/history", "a") as file:
            file.write(f"{link}\n")

        self.history.append(location)

    def set_focus(self, focus: int):
        """Set focus position for current location"""
        self.current_location.focus = focus

    def back(self):
        """Go back in history"""
        if len(self.history) > 1:
            self.history.pop()

    def show_bookmarks(self):
        """Show bookmarks page"""
        self.history.append(Location("", 70, "", bookmarks=True))

    def show_history(self):
        """Show history page"""
        self.history.append(Location("", 70, "", history=True))


class Cache:
    """Handles caching of downloaded files"""

    cache_directory = f"{HOME_DIRECTORY}/.cache/pherguson"

    @classmethod
    def get_cache_directory(cls, host: str) -> str:
        """Get cache directory for a specific host"""
        hash = hashlib.md5(host.encode()).hexdigest()[:8]
        cache_directory = f"{cls.cache_directory}/{hash}"
        path = pathlib.Path(cache_directory)
        path.mkdir(parents=True, exist_ok=True)
        return cache_directory

    @classmethod
    def file_exists(cls, file_path: str) -> bool:
        """Check if a file exists in cache"""
        return pathlib.Path(file_path).is_file()
