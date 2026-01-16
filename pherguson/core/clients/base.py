#!/usr/bin/env python

from typing import Callable, List

from .gopher import GopherClient
from .gemini import GeminiClient
from ..models import Line, Location


class Client:
    """Unified client that handles both Gopher and Gemini protocols"""

    def __init__(self, status_callback: Callable[[str, str], None]):
        self.status_callback = status_callback
        self.gopher_client = GopherClient(status_callback)
        self.gemini_client = GeminiClient(status_callback)
        self.current_location_map = []

    def _detect_protocol(self, url: str) -> str:
        """Detect protocol from URL"""
        if url.startswith("gemini://"):
            return "gemini"
        elif url.startswith("gopher://"):
            return "gopher"
        else:
            # Default to gopher for backward compatibility
            return "gopher"

    def parse_url(self, url: str) -> Location:
        """Parse URL and return Location object"""
        protocol = self._detect_protocol(url)

        if url.startswith("gemini://"):
            host = url.split("://")[1].split(":")[0]

            try:
                port = url.split("://")[1].split(":")[1]
            except Exception:
                port = 1965

            try:
                path = url.split("://")[1].split(":")[2]
            except Exception:
                path = "/"

            return Location(host, int(port), path, protocol=protocol)
        else:
            # Handle gopher URLs
            if url.startswith("gopher://"):
                clean_url = url.replace("gopher://", "")
            else:
                clean_url = url

            if "/" in clean_url:
                host_part, path = clean_url.split("/", 1)
                path = "/" + path
            else:
                host_part = clean_url
                path = "/"

            if ":" in host_part:
                host, port = host_part.split(":", 1)
            else:
                host = host_part
                port = 70

            return Location(host, int(port), path, protocol=protocol)

    def crawl(self, location: Location) -> List[Line]:
        """Fetch and parse content from a location (Gopher or Gemini)"""
        try:
            if location.protocol == "gemini":
                lines = self.gemini_client.crawl(location)
                self.current_location_map = self.gemini_client.current_location_map
                return lines
            else:
                lines = self.gopher_client.crawl(location)
                self.current_location_map = self.gopher_client.current_location_map
                return lines
        except Exception as e:
            self.status_callback(str(e), "error")
            raise e

    def download(self, location: Location, file_path: str | None = None) -> str:
        """Download a file (Gopher only for now)"""
        if location.protocol == "gemini":
            return self.gemini_client.download(location, file_path)
        else:
            return self.gopher_client.download(location, file_path)

    def download_http(self, url: str, file_path: str | None = None) -> str:
        """Download a file via HTTP (delegates to gopher client)"""
        return self.gopher_client.download_http(url, file_path)

    def _parse_line(self, line: List[str], current_location: Location) -> Line:
        """Parse a raw line into a Line object"""
        if current_location.protocol == "gemini":
            return self.gemini_client._parse_line(line, current_location)
        else:
            return self.gopher_client._parse_line(line, current_location)
