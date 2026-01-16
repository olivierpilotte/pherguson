#!/usr/bin/env python

import os
import platform
import shutil

from typing import Dict, List, Tuple

# Application settings
APPLICATION_HANDLER = "xdg-open" if platform.system() == "Linux" else "open"
DEFAULT_ROW_HEIGHT = 15
EXPERIMENTAL_MOUSE_NAVIGATION = False
HOME_DIRECTORY = os.path.expanduser("~")
THUMBNAIL_SIZE = (384, 256)
USE_BOLD_FONT = True

# Feature flags
SOUND_PREVIEW_ENABLED = True if shutil.which("mpv") else False
INLINE_IMAGES_ENABLED = True if shutil.which("ueberzug") else False

# Protocol support
GEMINI_ENABLED = True
GOPHER_ENABLED = True

# Color scheme for urwid
COLOR_MAP: List[Tuple[str, str, str]] = [
    # gopher types
    ("inf", f"{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("hex", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("gif", f"brown{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("img", f"brown{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("dir", f"dark blue{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("txt", f"dark blue{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("htm", f"dark green{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("htm_img", f"dark green{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("ask", f"dark blue{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("bin", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("snd", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("vid", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("pdf", f"dark magenta{',bold' if USE_BOLD_FONT else ''}", "default"),
    # ui elements
    ("url_label", "light blue", "default"),
    ("url_bar", f"{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("selection", f"light gray{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("divider", "light blue", "default"),
    ("search_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("download_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("bookmark_overlay", f"white{',bold' if USE_BOLD_FONT else ''}", "dark blue"),
    ("bookmark_entry", f"white{',bold' if USE_BOLD_FONT else ''}", "black"),
    ("exit_overlay", f"{',bold' if USE_BOLD_FONT else ''}", "dark red"),
    ("list", "default", "default"),
    # status bar levels
    ("ok", f"dark green{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("loading", f"brown{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("warning", f"brown{',bold' if USE_BOLD_FONT else ''}", "default"),
    ("error", f"dark red{',bold' if USE_BOLD_FONT else ''}", "default"),
]

# Gopher type mappings
TYPE_MAP: Dict[str, str] = {
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

# File type categories
SELECTABLES: List[str] = [
    "txt",
    "dir",
    "gif",
    "htm",
    "img",
    "gif",
    "ask",
    "bin",
    "png",
    "rtf",
    "snd",
    "vid",
    "pdf",
    "xml",
    "hex",
]
BINARIES: List[str] = ["txt", "hex", "img", "gif", "bin", "png", "rtf", "pdf", "xml"]

# Landing page content
LANDING_PAGE: List[List[str]] = [
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
