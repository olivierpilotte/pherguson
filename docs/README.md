# Pherguson Documentation

This directory contains comprehensive documentation for the Pherguson Gopher Protocol client, including the refactoring process, feature implementations, and technical details.

## 📚 Documentation Index

### 🏗️ **Project Structure & Refactoring**
- **[README_REFACTORED.md](README_REFACTORED.md)** - Complete guide to the refactored project structure and improvements
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Detailed summary of the refactoring work and accomplishments

### 🐛 **Bug Fixes & Issues**
- **[INDEX_ERROR_FIX.md](INDEX_ERROR_FIX.md)** - Fix for IndexError crashes on startup and navigation
- **[GEMINI_SSL_FIX.md](GEMINI_SSL_FIX.md)** - Fix for Gemini SSL socket AttributeError
- **[GEMINI_PROTOCOL_FIX.md](GEMINI_PROTOCOL_FIX.md)** - Fix for Gemini "59 invalid request" errors
- **[VIDEO_CRASH_FIX.md](VIDEO_CRASH_FIX.md)** - Documentation of video playback crash fixes
- **[CONFIG_ACCESS_FIXES.md](CONFIG_ACCESS_FIXES.md)** - Summary of configuration access issues and solutions

### ⚙️ **Configuration & Behavior**
- **[DEFAULT_LANDING_PAGE.md](DEFAULT_LANDING_PAGE.md)** - Default landing page configuration and behavior

### ✨ **New Features**
- **[SOUND_AUTO_STOP_FEATURE.md](SOUND_AUTO_STOP_FEATURE.md)** - Documentation of automatic sound detection and cleanup
- **[GEMINI_SUPPORT.md](GEMINI_SUPPORT.md)** - Gemini protocol support and dual-protocol browsing
- **[GEMINI_DEFAULT_PORT.md](GEMINI_DEFAULT_PORT.md)** - Gemini protocol default port 1965 implementation

### 🧪 **Testing & Development**
- **[test_sound_monitoring.py](test_sound_monitoring.py)** - Test script for sound monitoring functionality

## 🚀 **Quick Start**

### Running the Application
```bash
# Run the refactored version (supports Gopher and Gemini)
# Starts with gopher://gopher.flatline.ltd/ (default)
python pherguson_new.py

# Start directly with specific URL
python pherguson_new.py gemini://gemini.circumlunar.space
python pherguson_new.py gopher://gopher.floodgap.com
python pherguson_new.py gemini://geminiquickst.art/

# Run the original version (Gopher only)
python pherguson.py
```

### Project Structure
```
pherguson/
├── config/           # Configuration and settings
├── core/             # Core application logic
├── ui/               # User interface components
├── utils/            # Utility functions
└── main.py          # Entry point
```

## 📋 **Key Improvements**

### 1. **Modular Architecture**
- Separated concerns into distinct modules
- Clear dependency management
- Improved maintainability

### 2. **Enhanced Features**
- Automatic sound detection and cleanup
- Gemini protocol support
- Dual-protocol browsing (Gopher + Gemini)
- Robust error handling
- Better configuration management

### 3. **Bug Fixes**
- Fixed video playback crashes
- Resolved configuration access issues
- Improved stability

## 🔧 **Development**

### Adding New Features
1. Identify the appropriate module for your feature
2. Follow the established patterns for imports and configuration
3. Update documentation in this directory

### Configuration
All configuration is centralized in `pherguson/config/settings.py`:
- Color schemes
- Feature flags
- Application settings
- Gopher type mappings

### Testing
Use the provided test scripts and follow the established testing patterns.

## 📖 **Documentation Guidelines**

When adding new documentation:
1. Use clear, descriptive filenames
2. Include overview, implementation details, and usage examples
3. Update this README.md index
4. Follow the established markdown formatting

## 🤝 **Contributing**

1. Follow the modular architecture
2. Import configuration from settings module
3. Add appropriate documentation
4. Test thoroughly before submitting

---

*For more information, see the individual documentation files listed above.* 