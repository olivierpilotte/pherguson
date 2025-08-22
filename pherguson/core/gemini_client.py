#!/usr/bin/env python

import urllib.parse
from urllib.parse import urlparse
import re
import Agunua

from .models import Location, Line, Error
from ..config.settings import TYPE_MAP, HOME_DIRECTORY
from ..utils.helpers import shorten


class GeminiClient:
    """Handles Gemini protocol communication and content parsing using agunua library"""

    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self.current_location_map = []

    def get_content(self, location):
        """Fetch content from a Gemini location using agunua"""
        try:
            # Construct the full Gemini URL
            gemini_url = f"gemini://{location.host}:{location.port}{location.url}"
            
            # Use agunua to fetch the content
            response = Agunua.GeminiUri(gemini_url, insecure=True, get_content=True)

            return self._parse_gemini_content(response.payload, location)
            
        except Exception as e:
            if self.status_callback:
                self.status_callback(str(e), level="warning")
            raise Error(f"Error fetching content from {location}: {str(e)}")

    def _parse_gemini_content(self, content, location):
        """Parse Gemini content into gopher-like format"""
        lines = []
        
        for line in content.split('\n'):
            line = line.rstrip('\r\n')
            
            # Skip empty lines
            if not line:
                continue
            
            # Parse Gemini links: =>[URL][TEXT]
            if line.startswith('=>'):
                link_match = re.match(r'^=>\s*([^\s]+)(?:\s+(.+))?$', line)
                if link_match:
                    url = link_match.group(1)
                    text = link_match.group(2) or url
                    
                    # Determine link type
                    link_type = self._determine_gemini_link_type(url)
                    
                    # Create gopher-like line
                    parsed_url = urlparse(url)
                    host = parsed_url.hostname or location.host
                    port = parsed_url.port or 1965
                    path = parsed_url.path or '/'
                    
                    gopher_line = [
                        link_type,  # Type
                        text,       # Display text
                        path,       # Path
                        host,       # Host
                        str(port)   # Port
                    ]
                    lines.append(gopher_line)
                    
            # Parse headings: # Heading (treat as normal text)
            elif line.startswith('#'):
                text = line.lstrip('#').strip()
                gopher_line = ['i', text, '', '', '']
                lines.append(gopher_line)
                
            # Parse list items: * List item (treat as normal text)
            elif line.startswith('*'):
                text = line.lstrip('*').strip()
                gopher_line = ['i', text, '', '', '']
                lines.append(gopher_line)
                
            # Regular text
            else:
                gopher_line = ['i', line, '', '', '']
                lines.append(gopher_line)
        
        return lines
    


    def _determine_gemini_link_type(self, url):
        """Determine gopher-like type for Gemini link"""
        parsed = urlparse(url)
        
        # Check if it's a different protocol
        if parsed.scheme and parsed.scheme != 'gemini':
            if parsed.scheme == 'http' or parsed.scheme == 'https':
                return 'h'  # HTML link
            elif parsed.scheme == 'gopher':
                return '1'  # Gopher directory
            else:
                return 'h'  # Default to HTML for other protocols
        
        # Check file extensions for Gemini URLs
        path = parsed.path.lower()
        
        if path.endswith(('.txt', '.md', '.text')):
            return '0'  # Text file
        elif path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'I'  # Image file
        elif path.endswith(('.mp3', '.wav', '.ogg', '.flac')):
            return 's'  # Sound file
        elif path.endswith(('.mp4', '.avi', '.mkv', '.webm')):
            return ';'  # Video file
        elif path.endswith(('.pdf')):
            return 'P'  # PDF file
        else:
            return '1'  # Default to directory

    def download(self, location, file_path=None):
        """Download a file via Gemini protocol using agunua"""
        try:
            # Construct the full Gemini URL
            gemini_url = f"gemini://{location.host}:{location.port}{location.url}"
            
            # Use agunua to fetch the content
            response = self.client.get(gemini_url)
            
            # Check if the request was successful
            if response.status != 20:
                raise Error(f"Gemini error {response.status}: {response.meta}")
            
            # Get the content as bytes for file download
            content = response.content()
            
            # Save to file if file_path is provided
            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(content)
                return file_path
            else:
                return content
                
        except Exception as e:
            if self.status_callback:
                self.status_callback(str(e), level="warning")
            raise Error(f"Error downloading file from {location}: {str(e)}")

    def _parse_line(self, line, current_location):
        """Parse a raw line into a Line object (same as gopher)"""
        text = line[0] if len(line) > 0 else ""
        url = line[1] if len(line) > 1 else ""
        host = line[2] if len(line) > 2 else ""
        
        try:
            port = int(line[3]) if len(line) > 3 else 1965
        except Exception:
            port = 1965

        line_type = "inf"
        if current_location.walkable and len(text) > 0:
            line_type = TYPE_MAP.get(text[0], "inf")
            text = text[1:]

        return Line(line_type, text, Location(host, port, url))

    def crawl(self, location):
        """Fetch and parse content from a Gemini location"""
        try:
            if self.status_callback:
                self.status_callback(f"{location}", level="loading")
                
            content = self.get_content(location)
            lines = [self._parse_line(line, location) for line in content]
            self.current_location_map = lines

            if self.status_callback:
                self.status_callback(f"{location}")
                
            return lines

        except Exception as e:
            print(e)