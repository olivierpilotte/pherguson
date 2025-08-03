# Pherguson (Refactored)

A refactored version of the Pherguson Gopher Protocol client with separated concerns and improved modularity.

## Project Structure

The refactored version separates the code into logical modules:

```
pherguson/
├── config/           # Configuration and settings
│   ├── __init__.py
│   └── settings.py   # All constants, color schemes, type mappings
├── core/             # Core application logic
│   ├── __init__.py
│   ├── models.py     # Data models (Line, Location, History, Cache)
│   ├── gopher_client.py  # Gopher protocol client logic
│   └── application.py    # Main application coordinator
├── ui/               # User interface components
│   ├── __init__.py
│   ├── widgets.py    # Reusable UI widgets
│   └── content_window.py # Main content display window
├── utils/            # Utility functions
│   ├── __init__.py
│   └── helpers.py    # Helper functions
├── __init__.py       # Package initialization
└── main.py          # Entry point
```

## Key Improvements

### 1. Separation of Concerns
- **Configuration**: All settings, constants, and color schemes are centralized in `config/settings.py`
- **Core Logic**: Gopher protocol handling and data models are separated from UI code
- **UI Components**: All urwid widgets and UI logic are isolated in the `ui/` module
- **Utilities**: Helper functions are organized in the `utils/` module

### 2. Modular Design
- Each module has a single responsibility
- Dependencies are clearly defined through imports
- Components can be tested and modified independently

### 3. Improved Maintainability
- Code is easier to understand and navigate
- Changes to UI don't affect core logic
- Configuration changes are centralized
- New features can be added without touching existing code

## Usage

### Running the Refactored Version

```bash
# Run the new refactored version
python pherguson_new.py

# Or run the original version
python pherguson.py
```

### Development

The refactored structure makes it easier to:

1. **Add new features**: Create new modules or extend existing ones
2. **Modify UI**: Changes to UI components are isolated
3. **Update configuration**: All settings are in one place
4. **Test components**: Each module can be tested independently

## Migration from Original

The refactored version maintains the same functionality as the original but with:

- Better code organization
- Clearer separation of responsibilities
- Improved maintainability
- Easier testing and debugging

## Key Classes

### Core Classes
- `GopherApplication`: Main application coordinator
- `GopherClient`: Handles gopher protocol communication
- `History`: Manages navigation history
- `Location`: Represents gopher locations
- `Line`: Represents gopher menu items

### UI Classes
- `ContentWindow`: Main content display
- `UrlBar`: URL input bar
- `StatusBar`: Status display
- Various overlay widgets for search, bookmarks, etc.

## Configuration

All configuration is now centralized in `config/settings.py`:

- Color schemes
- Gopher type mappings
- Feature flags
- Application settings

This makes it easy to customize the application behavior without digging through the code. 