# 🎨 Theme Documentation

This directory contains comprehensive documentation for escmd's Universal Theme System.

## 📚 Available Guides

### [ESTERM_THEMES_README.md](ESTERM_THEMES_README.md)
**ESTERM Interactive Terminal Theme System**
- Independent theme system for ESTERM interactive terminal
- 8 built-in themes (rich, plain, cyberpunk, ocean, fire, matrix, midnight, corporate)
- Real-time theme switching without restart
- Complete separation from ESCMD command output themes
- Configuration management and troubleshooting

### [CUSTOM_THEMES_GUIDE.md](CUSTOM_THEMES_GUIDE.md)
**Complete guide to creating custom themes**
- YAML configuration structure
- Available Rich colors and styles
- Example custom themes (Ocean, Midnight, Fire)
- Theme properties reference
- Troubleshooting tips
- Best practices

### [UNIVERSAL_THEME_SYSTEM_GUIDE.md](UNIVERSAL_THEME_SYSTEM_GUIDE.md)  
**Implementation and usage guide**
- Overview of the universal theme system
- Complete list of themed commands
- Theme categories and properties
- Advanced features and configuration
- Benefits and compatibility information

### [THEME_GUIDE.md](THEME_GUIDE.md)
**Basic theme usage and configuration**
- Built-in theme comparison (rich, plain, cyberpunk)
- Basic usage examples
- Visual differences between themes
- Quick start information

## 🚀 Quick Start

### ESCMD Command Themes
1. **View available themes:**
   ```bash
   python3 theme_switcher.py
   ```

2. **Switch theme:**
   ```bash
   python3 theme_switcher.py ocean
   ```

3. **Test themed output:**
   ```bash
   ./escmd.py --help
   ./escmd.py indices
   ```

4. **Create custom themes:**
   Edit `themes.yml` and add your custom theme configuration.

### ESTERM Interactive Terminal Themes
1. **Start ESTERM:**
   ```bash
   ./esterm.py
   ```

2. **View available ESTERM themes:**
   ```bash
   esterm> theme
   ```

3. **Switch ESTERM theme:**
   ```bash
   esterm> theme cyberpunk
   ```

4. **Preview themes:**
   ```bash
   esterm> theme preview ocean
   ```

## 🎯 Theme Configuration

### ESCMD Command Themes
Themes are stored in the **`themes.yml`** file in the root directory, allowing users to:

- ♾️ Create unlimited custom themes
- 🎨 Define complete color schemes  
- 🔄 Switch themes without restart
- 📁 Keep main configuration clean
- 🔧 Share theme configurations easily

### ESTERM Interactive Terminal Themes
ESTERM themes are **completely independent** and stored in **`esterm_themes.yml`** and configured via **`esterm_config.yml`**:

- 🖥️ **Independent system** - No interference with ESCMD command output
- 🎨 **8 built-in themes** - From professional to fun
- ⚡ **Real-time switching** - Change themes instantly in terminal
- 👁️ **Theme previews** - Preview before switching  
- 🔧 **Persistent configuration** - Settings saved automatically

## 📖 Learn More

For detailed implementation information, see the individual guide files in this directory.
