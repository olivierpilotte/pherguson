#!/usr/bin/env python

import os
import subprocess
from ..config.settings import HOME_DIRECTORY


def shorten(path: str) -> str:
    """Shorten a path by replacing home directory with ~"""
    return path.replace(HOME_DIRECTORY, "~")


def execute(command: str):
    """Execute a shell command silently"""
    try:
        with open(os.devnull, "wb") as devnull:
            subprocess.check_call(command.split(" "), stdout=devnull, stderr=devnull)
    except Exception:
        pass


def is_image(url: str) -> bool:
    """Check if a URL points to an image file"""
    for image_type in ["jpg", "jpeg", "png", "gif"]:
        if image_type in url.lower():
            return True
    return False
