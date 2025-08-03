# Configuration Access Fixes Summary

## Overview

Fixed multiple instances where the code was incorrectly trying to access configuration through `self.config` or `self.gopher.config` attributes that don't exist in the refactored structure.

## Issues Fixed

### 1. Mouse Event Configuration Access
**File:** `pherguson/ui/content_window.py`  
**Issue:** `self.gopher.config.EXPERIMENTAL_MOUSE_NAVIGATION`  
**Fix:** Import `EXPERIMENTAL_MOUSE_NAVIGATION` directly from settings

### 2. Application Handler Configuration Access
**File:** `pherguson/core/application.py`  
**Issue:** `self.config.APPLICATION_HANDLER`  
**Fix:** Import `APPLICATION_HANDLER` directly from settings

## Root Cause

During the refactoring, configuration constants were moved to the `config/settings.py` module, but some code was still trying to access them through non-existent `config` attributes on the application objects.

## Solution Pattern

Instead of accessing configuration through object attributes:
```python
# Wrong (causing crashes):
self.gopher.config.EXPERIMENTAL_MOUSE_NAVIGATION
self.config.APPLICATION_HANDLER
```

Import and use constants directly:
```python
# Correct:
from ..config.settings import EXPERIMENTAL_MOUSE_NAVIGATION, APPLICATION_HANDLER
EXPERIMENTAL_MOUSE_NAVIGATION
APPLICATION_HANDLER
```

## Files Modified

1. **`pherguson/ui/content_window.py`**
   - Added `EXPERIMENTAL_MOUSE_NAVIGATION` to imports
   - Fixed mouse event configuration access

2. **`pherguson/core/application.py`**
   - Added `APPLICATION_HANDLER` to imports
   - Fixed file opening configuration access

## Testing

All fixes have been tested and verified:
- ✅ Video files can be opened without crashes
- ✅ Mouse navigation works correctly
- ✅ File opening works for all file types
- ✅ All existing functionality preserved

## Impact

- **No more crashes** when opening files or using mouse navigation
- **Cleaner code** with direct imports instead of attribute access
- **Better maintainability** with centralized configuration
- **Consistent pattern** for accessing configuration throughout the codebase

## Prevention

To prevent similar issues in the future:
1. Always import configuration constants directly from `config/settings.py`
2. Never access configuration through object attributes
3. Use the established import pattern consistently 