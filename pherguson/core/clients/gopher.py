#!/usr/bin/env python

from typing import Callable, List
import requests
import shutil
import socket
from urllib.parse import ParseResult, urlparse

from pherguson.core.models import Location, Line, Error, Cache
from pherguson.config.settings import TYPE_MAP
from pherguson.utils.helpers import shorten


class GopherClient:
    """Handles gopher protocol communication and content parsing"""

    def __init__(self, status_callback: Callable[[str, str], None]):
        self.status_callback = status_callback
        self.current_location_map = []

    def _get_socket(self, location: Location) -> socket.socket:
        """Create and configure socket for gopher connection"""
        crlf = "\r\n"

        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        skt.settimeout(2)

        try:
            with open("/tmp/pherguson.log", "w") as file:
                file.write(f"{location.host} {location.port}\n")

            skt.connect((location.host, location.port))
            skt.send(str.encode(location.url) + str.encode(crlf))
            skt.shutdown(1)

            return skt

        except (ConnectionRefusedError, socket.gaierror, OSError):
            raise Error(f"error connecting to {location.host}:{location.port}")

    def get_content(self, location: Location) -> List[List[str]]:
        """Fetch content from a gopher location"""
        sock = self._get_socket(location)
        file = sock.makefile("r")

        lines: List[List[str]] = []
        while True:
            try:
                line = file.readline()
                if not line or line == "":
                    break

                lines.append([part.strip("\n") for part in line.split("\t")])

            except Exception as e:
                if self.status_callback is not None:
                    self.status_callback(str(e), "warning")

        sock.close()
        return lines

    def download_http(self, url: str, file_path: str | None = None) -> str:
        """Download a file via HTTP"""
        parsed_url: ParseResult = urlparse(url)
        filename = url.split("/")[-1]

        if not file_path:
            download_directory = Cache.get_cache_directory(parsed_url.netloc)
            file_path = f"{download_directory}/{filename}"

            if Cache.file_exists(file_path):
                if self.status_callback is not None:
                    self.status_callback(f"cached: {shorten(file_path)}", "info")
                return file_path

        if self.status_callback is not None:
            self.status_callback(f"downloading: {url}", "loading")

        response = requests.get(url, stream=True)

        if response.status_code == 200:
            response.raw.decode_content = True

            with open(file_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        return file_path

    def download(self, location: Location, file_path: str | None = None) -> str:
        """Download a file via gopher protocol"""
        filename = location.url.split("/")[-1]
        if not file_path:
            download_directory = Cache.get_cache_directory(location.host)
            file_path = f"{download_directory}/{filename}"

            if Cache.file_exists(file_path):
                if self.status_callback is not None:
                    self.status_callback(f"cached: {shorten(file_path)}", "info")
                return file_path

        if self.status_callback is not None:
            self.status_callback(
                f"downloading: gopher://{location.host}{location.url}", "loading"
            )

        s = self._get_socket(location)
        f = s.makefile("rb")

        with open(file_path, "wb") as file:
            file.write(f.read())

        s.close()
        return file_path

    def _parse_line(self, line: List[str], current_location: Location) -> Line:
        """Parse a raw gopher line into a Line object"""
        text = line[0] if len(line) > 0 else ""
        url = line[1] if len(line) > 1 else ""
        host = line[2] if len(line) > 2 else ""

        try:
            port = int(line[3]) if len(line) > 3 else 70
        except Exception:
            port = 70

        with open("/tmp/pherguson.log", "w") as file:
            file.write(str(current_location.url))

        line_type = "inf"
        if current_location.walkable and len(text) > 0:
            line_type = TYPE_MAP.get(text[0], "inf")
            text = text[1:]

        return Line(line_type, text, Location(host, port, url))

    def crawl(self, location: Location) -> List[Line]:
        """Fetch and parse content from a gopher location"""
        try:
            self.status_callback(f"{location}", "loading")

            content = self.get_content(location)
            lines = [self._parse_line(line, location) for line in content]
            self.current_location_map = lines

            self.status_callback(f"{location}", "info")

            return lines

        except Error as e:
            self.status_callback(e.message, "error")
            return []
