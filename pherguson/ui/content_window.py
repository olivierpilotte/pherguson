#!/usr/bin/env python

import json
import os
import signal
import subprocess
import threading
import time
import urwid
from urllib.parse import urlparse

from .widgets import Highlight, Selectable, Unselectable, Box
from ..config.settings import (
    SELECTABLES, BINARIES, INLINE_IMAGES_ENABLED, 
    SOUND_PREVIEW_ENABLED, APPLICATION_HANDLER, THUMBNAIL_SIZE,
    EXPERIMENTAL_MOUSE_NAVIGATION
)
from ..utils.helpers import is_image, execute

if INLINE_IMAGES_ENABLED:
    from PIL import Image
    import ueberzug.lib.v0 as ueberzug


class ContentWindow(urwid.ListBox):
    """Main content display window"""
    
    def __init__(self, gopher):
        self.gopher = gopher
        self.walker = urwid.SimpleFocusListWalker([])
        super(ContentWindow, self).__init__(self.walker)

        self.image_preview = None
        self.current_highlight = None
        
        # Sound preview state
        self.sound_preview_thread = None
        self.sound_preview_state = "STOPPED"
        self.sound_preview_filename = None
        
        # Image preview state
        self.stop_image_preview_thread = False

    def clear(self):
        """Clear all content from the window"""
        for i in range(len(self.walker)):
            self.walker.pop()

    def set_content(self, lines, focus):
        """Set content in the window"""
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

        if not self.gopher.history.current_location.walkable and len(self.walker) > 0:
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
            self.gopher.history.current_location.focus = focus

    def set_highlight(self, focus):
        """Set highlight on a specific item"""
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

            line = self.gopher.client.current_location_map[focus]
            if "URL" in line.location.url:
                url = line.location.url.replace("URL:", "")
            else:
                url = f"gopher://{line.location.host}{line.location.url}"

            self.gopher.status_bar.set_status(url)

    def scroll(self):
        """Handle scrolling and update focus"""
        new_focus = self.get_focus()[1]
        self.gopher.history.current_location.focus = new_focus

        if self.walker[new_focus].base_widget.selectable():
            self.set_highlight(new_focus)

    def _count_hidden_lines(self, size):
        """Count lines hidden above the current view"""
        focus = self.get_focus()[1]
        middle, top, bottom = self.calculate_visible(size, True)
        items_on_top = len(top[1])
        return focus - items_on_top

    def mouse_event(self, size, event, button, col, row, focus):
        """Handle mouse events"""
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
            self.gopher.history.current_location.focus = focus
            self.set_highlight(focus)

        if event == "mouse press" and button == 1.0:  # left click
            if INLINE_IMAGES_ENABLED and self.image_preview:
                self.close_image_preview()
            else:
                self.gopher.navigate_back()

        if event == "mouse press" and button == 3.0:  # right click
            line = self.gopher.client.current_location_map[self.current_highlight]
            focus = self.get_focus()[1]

            if self.walker[focus].base_widget.selectable():
                self.set_highlight(focus)
            elif INLINE_IMAGES_ENABLED and self.image_preview:
                self.close_image_preview()
            elif line.type == "htm":
                self.gopher.open_http_link(line)
            elif line.type in ["img", "gif"]:
                self.open_image_preview()
            elif line.type in ["snd", "vid"]:
                if SOUND_PREVIEW_ENABLED:
                    self.play_sound(line)
                else:
                    file_path = self.gopher.client.download(line.location)
                    execute(f"{APPLICATION_HANDLER} {file_path}")
            else:
                self.gopher.navigate_forward(line)

        super(ContentWindow, self).mouse_event(size, event, button, col, row, focus)

    def keypress(self, size, key):
        """Handle keyboard input"""
        line = None

        if self.gopher.history.current_location.walkable:
            try:
                line = self.gopher.client.current_location_map[self.current_highlight]
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
            if not line or not self.gopher.history.current_location.walkable:
                return

            if line.type == "ask":
                self.gopher.show_search_overlay(line)
            elif line.type == "htm":
                offset = self._count_hidden_lines(size)
                self.gopher.open_http_link(line, offset)
            elif line.type in ["img", "gif"]:
                offset = self._count_hidden_lines(size)
                try:
                    self.open_image_preview(offset)
                except Exception:
                    self.close_image_preview(offset)
            elif line.type in ["snd", "vid"]:
                if SOUND_PREVIEW_ENABLED:
                    if line.type == "snd":
                        self.play_sound(line)
                    if line.type == "vid":
                        self.play_video(line)
                else:
                    file_path = self.gopher.client.download(line.location)
                    execute(f"mplayer {file_path}")
            elif line.type in ["bin", "rtf", "pdf", "xml"]:
                self.gopher.open_file(line)
            else:
                self.gopher.navigate_forward(line)

        elif key in ["b"]:
            self.gopher.show_bookmark_overlay()

        elif key in ["r"]:
            self.gopher.refresh()

        elif key in ["s"]:
            self.stop_sound()
            self.gopher.refresh()

        elif key in ["p"]:
            self.toggle_sound_pause()

        elif key in ["i"]:
            self.gopher.log_debug_info()

        elif key in ["tab", "ctrl l", "meta f", ":"]:
            self.gopher.focus_url_bar()

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
            self.gopher.navigate_back()

        elif key in ["q", "ctrl c"]:
            self.gopher.show_exit_overlay()

        elif key in ["d", "o"]:
            if self.gopher.history.current_location.walkable:
                line = self.gopher.client.current_location_map[self.current_highlight]
                location = line.location
            else:
                location = self.gopher.history.current_location

            if key in ["d"]:
                self.gopher.show_download_overlay(location)
            elif key in ["o"]:
                self.gopher.open_file(line)

        elif key in ["B", "ctrl b"]:
            self.gopher.show_bookmarks()

        elif key in ["H", "ctrl h"]:
            self.gopher.show_history()

    def play_sound(self, line):
        """Play sound file"""
        self.play_media(line)

    def play_video(self, line):
        """Play video file"""
        self.play_media(line, video=True)

    def play_media(self, line, video=False):
        """Play media file"""
        if self.sound_preview_thread:
            return

        filename = self.gopher.client.download(line.location)
        self.sound_preview_filename = filename

        command = f"mpv {'--no-video' if not video else ''} --really-quiet --input-ipc-server=/tmp/mpvsocket {filename}"
        self.sound_preview_thread = subprocess.Popen(
            command, stdout=subprocess.PIPE,
            shell=True, preexec_fn=os.setsid)

        self.sound_preview_state = "PLAYING"
        self.gopher.refresh()
        
        # Start monitoring thread to detect when playback ends
        self._start_sound_monitoring()

    def _start_sound_monitoring(self):
        """Start a background thread to monitor sound playback status"""
        def monitor_sound():
            while self.sound_preview_thread and self.sound_preview_state == "PLAYING":
                try:
                    # Check if the process is still running
                    if self.sound_preview_thread.poll() is not None:
                        # Process has ended, reset state
                        self.sound_preview_thread = None
                        self.sound_preview_state = "STOPPED"
                        self.sound_preview_filename = None
                        # Trigger a refresh to update the status bar
                        self.gopher.refresh()
                        break
                    
                    # Check if playback has ended using mpv socket
                    try:
                        import json
                        import socket as socket_lib
                        
                        # Try to connect to mpv socket to check playback status
                        sock = socket_lib.socket(socket_lib.AF_UNIX, socket_lib.SOCK_STREAM)
                        sock.settimeout(0.1)
                        sock.connect('/tmp/mpvsocket')
                        
                        # Send a command to check if mpv is still playing
                        command = '{"command": ["get_property", "idle-active"]}\n'
                        sock.send(command.encode())
                        
                        response = sock.recv(1024).decode()
                        sock.close()
                        
                        # Parse response
                        try:
                            data = json.loads(response)
                            if data.get('data', False):  # idle-active is True when playback has ended
                                # Playback has ended, reset state
                                self.sound_preview_thread = None
                                self.sound_preview_state = "STOPPED"
                                self.sound_preview_filename = None
                                self.gopher.refresh()
                                break
                        except (json.JSONDecodeError, KeyError):
                            pass
                            
                    except (socket_lib.error, FileNotFoundError):
                        # Socket not available, fall back to process monitoring
                        pass
                        
                except Exception:
                    # If any error occurs, reset state
                    self.sound_preview_thread = None
                    self.sound_preview_state = "STOPPED"
                    self.sound_preview_filename = None
                    self.gopher.refresh()
                    break
                
                time.sleep(0.5)  # Check every 500ms
        
        # Start monitoring in background thread
        monitoring_thread = threading.Thread(target=monitor_sound, daemon=True)
        monitoring_thread.start()

    def stop_sound(self):
        """Stop sound playback"""
        if self.sound_preview_thread:
            try:
                os.killpg(os.getpgid(self.sound_preview_thread.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass  # Process might already be terminated
            self.sound_preview_thread = None
        self.sound_preview_state = "STOPPED"
        self.sound_preview_filename = None

    def toggle_sound_pause(self):
        """Toggle sound pause/play"""
        pause = "false"
        if self.sound_preview_state == "PLAYING":
            self.sound_preview_state = "PAUSED"
            pause = "true"
        elif self.sound_preview_state == "PAUSED":
            self.sound_preview_state = "PLAYING"
            pause = "false"

        command = f"echo '{{\"command\": [\"set_property\", \"pause\", {pause}]}}' | socat - /tmp/mpvsocket"
        execute(command)

    def open_image_preview(self, offset=0):
        """Open image preview"""
        line = self.gopher.client.current_location_map[self.current_highlight]

        if INLINE_IMAGES_ENABLED:
            self.display_image_inline(line, offset)
        else:
            file_path = self.gopher.client.download(line.location)
            execute(f"{APPLICATION_HANDLER} {file_path}")

    def close_image_preview(self):
        """Close image preview"""
        self.stop_image_preview_thread = True

        highlighted_line = self.walker[self.current_highlight]
        if hasattr(highlighted_line, "old_text"):
            highlighted_line.base_widget.set_text(highlighted_line.old_text)

        self.walker.pop(self.current_highlight + 1)
        self.image_preview = None

    def display_image_inline(self, line, offset=0):
        """Display image inline in terminal"""
        if not INLINE_IMAGES_ENABLED:
            return

        url = line.location.url.replace("URL:", "")

        if url.startswith("http"):
            filename = self.gopher.client.download_http(url)
        else:
            filename = self.gopher.client.download(line.location)

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
        """Preview image using ueberzug"""
        if not INLINE_IMAGES_ENABLED:
            return

        def thread_function(image_path, x, y):
            with ueberzug.Canvas() as canvas:
                canvas.create_placement(
                    "image", x=x, y=y, width=50,
                    scaler=ueberzug.ScalerOption.FIT_CONTAIN.value,
                    visibility=ueberzug.Visibility.VISIBLE,
                    path=image_path)

                while True:
                    if self.stop_image_preview_thread:
                        self.stop_image_preview_thread = False
                        break
                    time.sleep(0.01)

        threading.Thread(target=thread_function, args=(image_path, x, y)).start() 