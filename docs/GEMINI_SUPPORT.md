# Gemini Protocol Support

## Overview

Pherguson now supports the Gemini protocol alongside Gopher, allowing you to browse both protocols from the same application. The Gemini protocol is a modern, lightweight alternative to HTTP that focuses on simplicity and privacy.

## Features

### 🔗 **Dual Protocol Support**
- Browse Gopher sites (gopher://)
- Browse Gemini sites (gemini://)
- Automatic protocol detection
- Unified interface for both protocols

### 🌐 **Gemini Protocol Features**
- SSL/TLS encrypted connections
- Text-based content parsing
- Link parsing and navigation
- Heading and formatting support
- Cross-protocol linking

### 🎯 **Unified Experience**
- Same keyboard shortcuts for both protocols
- Consistent UI and navigation
- Shared history and bookmarks
- Unified URL bar support

## Usage

### Starting with Specific URLs

```bash
# Start with default landing page (gopher://gopher.flatline.ltd)
python pherguson_new.py

# Start directly with a Gemini site
python pherguson_new.py gemini://gemini.circumlunar.space

# Start directly with a specific Gemini page
python pherguson_new.py gemini://gemini.circumlunar.space/docs/specification.gmi

# Start directly with a Gopher site
python pherguson_new.py gopher://gopher.floodgap.com/
```

### URL Bar Navigation

You can navigate to any Gemini or Gopher URL using the URL bar:

1. Press `Tab` or `Ctrl+L` to focus the URL bar
2. Type a Gemini URL: `gemini://gemini.circumlunar.space`
3. Press `Enter` to navigate

### Supported URL Formats

- `gemini://hostname/` - Gemini site
- `gemini://hostname:port/` - Gemini site with custom port
- `gopher://hostname/` - Gopher site
- `hostname` - Defaults to Gopher (backward compatibility)

### Default Landing Page

The application starts with `gopher://gopher.flatline.ltd/` as the default landing page when no command line argument is provided. If a command line argument is provided, the application will start directly at that URL.

## Technical Implementation

### Architecture

The Gemini support is implemented through a modular architecture:

```
pherguson/core/
├── gopher_client.py      # Gopher protocol client
├── gemini_client.py      # Gemini protocol client
├── unified_client.py     # Unified client for both protocols
└── models.py            # Updated models with protocol support
```

### Key Components

#### 1. **GeminiClient**
- Handles SSL/TLS connections
- Parses Gemini text format
- Converts Gemini content to gopher-like format
- Supports Gemini link syntax (`=>[URL][TEXT]`)

#### 2. **UnifiedClient**
- Automatically detects protocol from URL
- Routes requests to appropriate client
- Provides unified interface for both protocols
- Handles URL parsing for both protocols

#### 3. **Updated Models**
- `Location` class now supports protocol field
- Proper URL representation for both protocols
- Protocol-aware link generation

### Content Parsing

Gemini content is parsed and converted to a gopher-like format:

- **Links**: `=>[URL][TEXT]` → Gopher link format
- **Headings**: `# Heading` → Info lines with formatting
- **Text**: Regular text → Info lines
- **Preformatted**: ```text``` → Info lines

### Link Type Detection

The client automatically detects link types based on:
- File extensions (.txt, .md, .jpg, .mp3, etc.)
- Protocol schemes (http://, https://, gopher://)
- Default to directory for unknown types

## Example Gemini Sites

### Popular Gemini Capsules
- `gemini://gemini.circumlunar.space/` - Gemini specification and documentation
- `gemini://gemini.conman.org/` - Personal blog and resources
- `gemini://gemini.ctrl-c.club/` - Community and resources
- `gemini://gemini.bortzmeyer.org/` - Technical articles

### Navigation Examples

```bash
# Navigate to Gemini specification
gemini://gemini.circumlunar.space/docs/specification.gmi

# Browse a Gemini blog
gemini://gemini.conman.org/

# Access Gemini community
gemini://gemini.ctrl-c.club/
```

## Configuration

### Protocol Support Settings

In `pherguson/config/settings.py`:

```python
# Protocol support
GEMINI_ENABLED = True
GOPHER_ENABLED = True
```

### SSL/TLS Settings

The Gemini client uses Python's built-in SSL library with:
- Default SSL context
- Hostname verification disabled (for compatibility)
- Certificate verification disabled (for development)

## Limitations

### Current Limitations
- File downloads via Gemini not yet implemented
- Limited support for Gemini-specific features
- Basic content parsing (no advanced formatting)

### Future Enhancements
- Direct file downloads via Gemini
- Better content formatting support
- Gemini-specific features (client certificates, etc.)
- Enhanced error handling for SSL issues

## Troubleshooting

### Common Issues

1. **SSL Connection Errors**
   - Some Gemini sites may have SSL issues
   - Try different Gemini capsules
   - Check if the site is accessible

2. **Content Display Issues**
   - Gemini content is converted to gopher format
   - Some formatting may be simplified
   - Links should work normally

3. **Protocol Detection**
   - URLs starting with `gemini://` are automatically detected
   - Other URLs default to Gopher protocol
   - You can always specify the protocol explicitly

## Development

### Adding Gemini Features

To extend Gemini support:

1. **Modify `GeminiClient`** for new features
2. **Update content parsing** in `_parse_gemini_content`
3. **Add new link types** in `_determine_gemini_link_type`
4. **Test with real Gemini capsules**

### Testing

Test Gemini support with:
```bash
python pherguson_new.py gemini://gemini.circumlunar.space/
```

## Conclusion

The Gemini protocol support makes Pherguson a truly multi-protocol browser, allowing you to explore both the classic Gopher space and the modern Gemini web from a single, unified interface. The implementation maintains backward compatibility while adding modern protocol support. 