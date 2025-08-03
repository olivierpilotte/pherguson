#!/usr/bin/env python

import datetime
import hashlib
import os
import pathlib
from ..config.settings import HOME_DIRECTORY


class Line:
    """Represents a single line in a gopher menu"""
    def __init__(self, type, text, location):
        self.type = type
        self.text = text
        self.location = location

    def __repr__(self):
        return f"{self.type}\t{self.text}\t{self.location}\n"


class Location:
    """Represents a gopher location (host, port, url)"""
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
        """Generate a gopher link string"""
        url = "/" if self.url == "" else self.url
        return (
            f"{'1' if self.walkable else '0'}"
            f"{name if name else url}\t{url}\t{self.host}\t{self.port}"
        )


class Error(Exception):
    """Custom exception for gopher protocol errors"""
    def __init__(self, message):
        self.message = message


class Cache:
    """Handles caching of downloaded files"""
    cache_directory = f"{HOME_DIRECTORY}/.cache/pherguson"

    @classmethod
    def get_cache_directory(cls, host):
        """Get cache directory for a specific host"""
        hash = hashlib.md5(host.encode()).hexdigest()[:8]
        cache_directory = f"{cls.cache_directory}/{hash}"
        path = pathlib.Path(cache_directory)
        path.mkdir(parents=True, exist_ok=True)
        return cache_directory

    @classmethod
    def file_exists(cls, file_path):
        """Check if a file exists in cache"""
        return pathlib.Path(file_path).is_file()


class History:
    """Manages navigation history"""
    def __init__(self):
        self.history = []

    @property
    def current_location(self):
        """Get the current location from history"""
        if len(self.history) == 1:
            return self.history[0]
        return self.history[-1]

    def forward(self, location):
        """Add a new location to history"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        link = location.get_link(name=f"{timestamp} {str(location)}")

        # Ensure config directory exists
        config_dir = f"{HOME_DIRECTORY}/.config/pherguson"
        pathlib.Path(config_dir).mkdir(parents=True, exist_ok=True)

        with open(f"{config_dir}/history", "a") as file:
            file.write(f"{link}\n")

        self.history.append(location)

    def set_focus(self, focus):
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