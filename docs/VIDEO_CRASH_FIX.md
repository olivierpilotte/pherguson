# Video Crash Fix

## Issue

When trying to open a video file, the application crashed with:
```
AttributeError: 'GopherApplication' object has no attribute 'config'
```

## Root Cause

The `ContentWindow` class was trying to access `self.gopher.config.EXPERIMENTAL_MOUSE_NAVIGATION` in the `mouse_event` method, but the main `GopherApplication` class doesn't have a `config` attribute.

## Solution

### 1. Import Configuration Directly

Added `EXPERIMENTAL_MOUSE_NAVIGATION` to the imports from the settings module:

```python
from ..config.settings import (
    SELECTABLES, BINARIES, INLINE_IMAGES_ENABLED, 
    SOUND_PREVIEW_ENABLED, APPLICATION_HANDLER, THUMBNAIL_SIZE,
    EXPERIMENTAL_MOUSE_NAVIGATION  # Added this import
)
```

### 2. Fix Configuration Access

Changed the problematic lines in both `mouse_event` and `open_file` methods:

```python
# Before (causing crash):
if not hasattr(self.gopher, 'config') or not getattr(self.gopher.config, 'EXPERIMENTAL_MOUSE_NAVIGATION', False):
execute(f"{self.config.APPLICATION_HANDLER} {filename}")

# After (fixed):
if not EXPERIMENTAL_MOUSE_NAVIGATION:
execute(f"{APPLICATION_HANDLER} {filename}")
```

## Files Modified

- `pherguson/ui/content_window.py` - Fixed configuration access in mouse_event method
- `pherguson/core/application.py` - Fixed configuration access in open_file method

## Testing

The fix has been tested and verified:
- Video files can now be opened without crashes
- Mouse navigation still works correctly
- All other functionality remains intact

## Impact

- ✅ **Video playback now works** - No more crashes when opening video files
- ✅ **File opening now works** - No more crashes when opening any files
- ✅ **Mouse navigation preserved** - Experimental mouse navigation still functions
- ✅ **No breaking changes** - All existing functionality remains the same
- ✅ **Cleaner code** - Direct import instead of attribute access

## Usage

Video files and other files can now be opened normally:
1. Navigate to any file in gopher
2. Press `l`, `right`, or `enter` to open the file
3. File will open in external application (xdg-open/open)
4. Auto-stop monitoring will work for media files too 