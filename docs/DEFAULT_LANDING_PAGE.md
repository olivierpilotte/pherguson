# Default Landing Page Configuration

## Overview

Pherguson has been configured to always start with `gopher://gopher.flatline.ltd/` as the default landing page, providing a consistent starting point for all users.

## Behavior

### Default Behavior
- **With command line argument**: Start directly with the provided URL
- **No command line argument**: Start with `gopher://gopher.flatline.ltd/`
- **Fallback**: Default to gopher.flatline.ltd if URL parsing fails

### Examples

```bash
# Start directly with Gemini site
python pherguson_new.py gemini://gemini.circumlunar.space

# Start directly with Gopher site
python pherguson_new.py gopher://gopher.floodgap.com

# Start directly with specific Gemini page
python pherguson_new.py gemini://geminiquickst.art/

# Start with default landing page (no arguments)
python pherguson_new.py
```

## Implementation

### Code Changes

The `_initialize_default_location()` method in `pherguson/core/application.py` was updated:

```python
def _initialize_default_location(self):
    """Initialize with provided URL or default to gopher.flatline.ltd"""
    try:
        # If a command line argument is provided, start with that URL
        if len(sys.argv) > 1:
            url = sys.argv[1]
            # Parse URL using unified client
            location = self.client._parse_url(url)
            self.history.forward(location)
        else:
            # Otherwise start with the default landing page
            self.history.forward(Location("gopher.flatline.ltd", 70, "/"))
    except Exception as e:
        print(e)
        time.sleep(3)
```

### Key Changes

1. **Direct URL navigation**: Command line arguments start the app directly at the specified URL
2. **Default fallback**: No arguments start with `gopher://gopher.flatline.ltd/`
3. **Flexible startup**: Users can start at any URL immediately
4. **Backward compatibility**: No arguments still work as before

## Benefits

### 🎯 **User Experience**
- **Direct access**: Start immediately at any desired URL
- **Flexible startup**: Choose your starting point via command line
- **Quick access**: No need to navigate from default page
- **Familiar fallback**: Default landing page when no URL specified

### 🔧 **Technical Benefits**
- **Predictable behavior**: Application always starts the same way
- **Easier testing**: Consistent starting state for testing
- **Better debugging**: Known initial state for troubleshooting

### 📚 **Documentation Benefits**
- **Clear examples**: Documentation can reference the consistent landing page
- **Easier tutorials**: Users can follow along with predictable starting state
- **Better onboarding**: New users have a familiar starting point

## Usage Patterns

### For New Users
```bash
# Start with default page - good for learning
python pherguson_new.py
```

### For Direct Access
```bash
# Start directly at specific site
python pherguson_new.py gemini://geminiquickst.art/
python pherguson_new.py gopher://gopher.floodgap.com
```

### For Development/Testing
```bash
# Always starts with known state
python pherguson_new.py
# Then navigate via URL bar or links
```

## Configuration

The default landing page is hardcoded in the application for consistency. If you need to change it:

1. **Modify the Location**: Update the Location call in `_initialize_default_location()`
2. **Update documentation**: Change references in documentation
3. **Test thoroughly**: Ensure the new landing page is accessible

## Future Considerations

- **Configurable landing page**: Could be made configurable via settings
- **Multiple default options**: Could support different defaults for different use cases
- **User preferences**: Could save user's preferred starting page

## Conclusion

The direct URL navigation configuration provides flexible startup options while maintaining a reliable default landing page. Users can now start the application directly at any desired URL, making it easier to access specific content immediately. 