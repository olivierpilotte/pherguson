# Pherguson Documentation

This directory contains comprehensive documentation for the Pherguson Gopher Protocol client, including the refactoring process, feature implementations, and technical details.

## 📚 Documentation Index

### 🏗️ **Project Structure & Refactoring**
- **[README_REFACTORED.md](README_REFACTORED.md)** - Complete guide to the refactored project structure and improvements
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Detailed summary of the refactoring work and accomplishments

### 🐛 **Bug Fixes & Issues**
- **[VIDEO_CRASH_FIX.md](VIDEO_CRASH_FIX.md)** - Documentation of video playback crash fixes
- **[CONFIG_ACCESS_FIXES.md](CONFIG_ACCESS_FIXES.md)** - Summary of configuration access issues and solutions

### ✨ **New Features**
- **[SOUND_AUTO_STOP_FEATURE.md](SOUND_AUTO_STOP_FEATURE.md)** - Documentation of automatic sound detection and cleanup

### 🧪 **Testing & Development**
- **[test_sound_monitoring.py](test_sound_monitoring.py)** - Test script for sound monitoring functionality

## 🚀 **Quick Start**

### Running the Application
```bash
# Run the refactored version
python pherguson_new.py

# Run the original version
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