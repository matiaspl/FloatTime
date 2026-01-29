"""Build script for creating executable with PyInstaller."""
import PyInstaller.__main__
import sys
import os
import shutil
from pathlib import Path

def build():
    """Build the application executable."""
    app_name = "floattime"
    
    # Determine separator for --add-data (Windows uses ;, Unix uses :)
    separator = ";" if sys.platform == "win32" else ":"
    
    # PyInstaller arguments
    # Using --onedir instead of --onefile for faster startup (no extraction needed)
    args = [
        "src/main.py",
        "--name", app_name,
        "--onedir",  # Faster startup than --onefile (no temp extraction)
        "--windowed",  # No console window
        "--noupx",  # Disable UPX compression (faster startup)
        "--paths", "src",  # Add src to Python path
        f"--add-data=src{separator}src",  # Include src directory
        # Hidden imports
        "--hidden-import", "config",
        "--hidden-import", "ontime_client",
        "--hidden-import", "timer_widget",
        "--hidden-import", "tray_manager",
        "--hidden-import", "logger",
        "--hidden-import", "ui.config_dialog",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "requests",
        "--hidden-import", "websocket",
        "--hidden-import", "websocket_client",
        "--hidden-import", "socketio",
        "--hidden-import", "engineio",
        # Exclude unused modules to reduce size and startup time
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "PIL",
        "--exclude-module", "tkinter",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide2",
        "--exclude-module", "PySide6",
        "--exclude-module", "PyQt6.QtMultimedia",
        "--exclude-module", "PyQt6.QtMultimediaWidgets",
        "--exclude-module", "PyQt6.QtWebEngineCore",
        "--exclude-module", "PyQt6.QtWebEngineWidgets",
        "--exclude-module", "PyQt6.QtQuick",
        "--exclude-module", "PyQt6.QtQuickWidgets",
        "--exclude-module", "PyQt6.QtQml",
        "--exclude-module", "PyQt6.QtSql",
        "--exclude-module", "PyQt6.QtNetworkAuth",
        "--exclude-module", "PyQt6.QtBluetooth",
        "--exclude-module", "PyQt6.QtNfc",
        "--exclude-module", "PyQt6.QtPositioning",
        "--exclude-module", "PyQt6.QtSensors",
        "--exclude-module", "PyQt6.QtSerialPort",
        "--exclude-module", "PyQt6.QtWebChannel",
        "--exclude-module", "PyQt6.QtXml",
        "--exclude-module", "PyQt6.QtTest",
        "--exclude-module", "PyQt6.QtDesigner",
        "--exclude-module", "PyQt6.QtPrintSupport",
        "--exclude-module", "PyQt6.QtOpenGL",
        "--exclude-module", "PyQt6.QtOpenGLWidgets",
        "--exclude-module", "PyQt6.QtPdf",
        "--exclude-module", "PyQt6.QtPdfWidgets",
        # Exclude unused standard library components
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "html",
        "--exclude-module", "http.server",
        "--exclude-module", "distutils",
        "--exclude-module", "setuptools",
        "--exclude-module", "lib2to3",
        # Custom hook in hooks/ directory will handle PyQt6 plugin collection
        # Only essential plugins (platforms, styles) will be included
        # Optimize Python bytecode
        "--optimize", "2",
        "--clean",
        "--noconfirm",
    ]
    
    # Add icon if it exists
    icon_path = Path("icon.ico")
    if not icon_path.exists():
        icon_path = Path("icon.png")
    
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
    
    print(f"Building {app_name}...")
    print(f"Platform: {sys.platform}")
    PyInstaller.__main__.run(args)
    
    # Post-build cleanup: Remove unnecessary PyQt6 plugins and DLLs
    dist_path = Path("dist") / app_name / "_internal"
    pyqt6_bin_path = dist_path / "PyQt6" / "Qt6" / "bin"
    pyqt6_plugins_path = dist_path / "PyQt6" / "Qt6" / "plugins"
    
    # List of plugin directories to remove (everything except platforms and styles)
    excluded_plugins = [
        'multimedia', 'mediaservice', 'webengine', 'webview', 'quick', 
        'qmltooling', 'sqldrivers', 'geoservices', 'position', 
        'sensorgestures', 'sensors', 'serialbus', 'serialport', 
        'texttospeech', 'assetimporters', 'sceneparsers', 'renderers', 
        'printsupport'
    ]
    
    # Remove excluded plugin directories
    if pyqt6_plugins_path.exists():
        for plugin_dir in excluded_plugins:
            plugin_path = pyqt6_plugins_path / plugin_dir
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
                print(f"Removed plugin directory: {plugin_dir}")
    
    # Remove unnecessary DLLs from bin directory
    if pyqt6_bin_path.exists():
        unwanted_dlls = [
            # Multimedia/FFmpeg
            'avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'ffmpeg',
            # 3D/Asset importers
            'assimp', 'gltf',
            # PDF (we excluded QtPdf modules)
            'Qt6Pdf',
            # WebEngine (we excluded QtWebEngine)
            'Qt6WebEngine', 'Qt6WebEngineCore', 'Qt6WebEngineWidgets',
            # Quick/QML (we excluded QtQuick/QtQml)
            'Qt6Quick', 'Qt6Qml', 'Qt6QuickWidgets',
            # SQL (we excluded QtSql)
            'Qt6Sql',
            # Other excluded modules
            'Qt6Multimedia', 'Qt6Bluetooth', 'Qt6Positioning', 'Qt6Sensors',
            'Qt6SerialPort', 'Qt6OpenGL', 'Qt6PrintSupport'
        ]
        for dll_pattern in unwanted_dlls:
            for dll_file in pyqt6_bin_path.glob(f"*{dll_pattern}*"):
                try:
                    dll_file.unlink()
                    print(f"Removed DLL: {dll_file.name}")
                except Exception as e:
                    print(f"Warning: Could not remove {dll_file.name}: {e}")
    
    # Determine executable extension and path
    ext = ".exe" if sys.platform == "win32" else ""
    print(f"Build complete! Executable should be in dist/{app_name}/{app_name}{ext}")
    print(f"Note: Using --onedir for faster startup. All files are in dist/{app_name}/")
    print(f"Cleaned up unnecessary PyQt6 plugins and multimedia DLLs.")

if __name__ == "__main__":
    build()

