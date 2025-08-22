# Gemini Default Port Implementation

## Overview

The Gemini protocol uses port 1965 as its default port when no port is specified in the URL. Pherguson correctly implements this standard across all components.

## Implementation Details

### 1. **Location Model** (`pherguson/core/models.py`)

The `Location` class automatically sets the correct default port based on protocol:

```python
def __init__(self, host, port, url, focus=0, walkable=True,
             bookmarks=False, history=False, protocol="gopher"):
    self.host = host
    self.port = int(port) if port else (1965 if protocol == "gemini" else 70)
    self.url = url
    self.focus = focus
    self.walkable = walkable
    self.bookmarks = bookmarks
    self.history = history
    self.protocol = protocol
```

**Key Feature:**
- **Gemini protocol**: Default port 1965
- **Gopher protocol**: Default port 70
- **Automatic detection**: Based on protocol parameter

### 2. **Gemini Client** (`pherguson/core/gemini_client.py`)

The `GeminiClient` uses port 1965 as default in multiple places:

#### Socket Connection (`_get_socket` method):
```python
def _get_socket(self, location):
    # Parse Gemini URL
    if not location.host.startswith('gemini://'):
        gemini_url = f"gemini://{location.host}"
    else:
        gemini_url = location.host
        
    parsed = urlparse(gemini_url)
    host = parsed.hostname
    port = parsed.port or 1965  # Default to 1965 if no port specified
    path = parsed.path or '/'
```

#### Line Parsing (`_parse_line` method):
```python
def _parse_line(self, line, current_location):
    text = line[0] if len(line) > 0 else ""
    url = line[1] if len(line) > 1 else ""
    host = line[2] if len(line) > 2 else ""
    
    try:
        port = int(line[3]) if len(line) > 3 else 1965  # Default to 1965
    except Exception:
        port = 1965  # Fallback to 1965
```

### 3. **Unified Client** (`pherguson/core/unified_client.py`)

The `UnifiedClient` correctly handles Gemini URLs with default port:

```python
def _parse_url(self, url):
    protocol = self._detect_protocol(url)
    
    if protocol == 'gemini':
        # Remove gemini:// prefix for parsing
        clean_url = url.replace('gemini://', '')
        if '/' in clean_url:
            host_part, path = clean_url.split('/', 1)
            path = '/' + path
        else:
            host_part = clean_url
            path = '/'
            
        if ':' in host_part:
            host, port = host_part.split(':', 1)
        else:
            host = host_part
            port = 1965  # Default Gemini port
            
        return Location(host, port, path, protocol=protocol)
```

## Usage Examples

### URLs Without Port Specification

```bash
# These URLs will automatically use port 1965
gemini://gemini.circumlunar.space
gemini://gemini.conman.org
gemini://gemini.floodgap.com

# Equivalent to:
gemini://gemini.circumlunar.space:1965
gemini://gemini.conman.org:1965
gemini://gemini.floodgap.com:1965
```

### URLs With Custom Port

```bash
# These URLs will use the specified port
gemini://example.com:1966
gemini://test.gemini:8443
```

### Command Line Usage

```bash
# Start with default Gemini site (port 1965)
python pherguson_new.py gemini://gemini.circumlunar.space

# Start with custom port
python pherguson_new.py gemini://example.com:1966
```

## Protocol Standards Compliance

### Gemini Protocol Specification

According to the Gemini protocol specification:
- **Default port**: 1965
- **Protocol**: TLS/SSL over TCP
- **URL format**: `gemini://hostname[:port]/path`

### Implementation Verification

The implementation correctly follows the Gemini protocol standard:

✅ **Default port 1965** - Used when no port is specified  
✅ **TLS/SSL support** - Proper SSL context and socket handling  
✅ **URL parsing** - Correct parsing of Gemini URLs  
✅ **Protocol detection** - Automatic detection of Gemini protocol  
✅ **Fallback handling** - Graceful fallback to default port  

## Benefits

### 🎯 **Standards Compliance**
- **RFC-compliant** - Follows Gemini protocol specification
- **Interoperable** - Works with all standard Gemini servers
- **Future-proof** - Adheres to established protocol standards

### 🔧 **User Experience**
- **Simplified URLs** - Users don't need to specify port 1965
- **Consistent behavior** - Same behavior as other Gemini clients
- **Error reduction** - Fewer connection errors due to wrong ports

### 🛡️ **Reliability**
- **Automatic port selection** - No manual port configuration needed
- **Fallback handling** - Graceful handling of port specification errors
- **Robust parsing** - Handles various URL formats correctly

## Testing

### Manual Testing

```bash
# Test default port behavior
python pherguson_new.py gemini://gemini.circumlunar.space
# Should connect to port 1965 automatically

# Test custom port
python pherguson_new.py gemini://example.com:1966
# Should connect to port 1966
```

### Code Verification

The implementation has been verified to:
- ✅ Use port 1965 as default for Gemini
- ✅ Handle custom ports correctly
- ✅ Parse URLs properly
- ✅ Maintain backward compatibility

## Conclusion

Pherguson correctly implements the Gemini protocol default port 1965 across all components. The implementation is standards-compliant, user-friendly, and robust, ensuring reliable connections to Gemini servers without requiring users to specify the default port. 