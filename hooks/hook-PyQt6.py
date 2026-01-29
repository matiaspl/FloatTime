"""PyInstaller hook to exclude unnecessary PyQt6 plugins."""
# This hook prevents collection of unnecessary PyQt6 plugins
# Only essential plugins (platforms, styles) will be collected by default PyInstaller behavior
# Post-build cleanup in build.py will remove any that slip through

# Don't collect all PyQt6 plugins - let default behavior handle only what's imported
datas = []
binaries = []

# The default PyInstaller hook for PyQt6 will collect plugins automatically
# We rely on post-build cleanup to remove unwanted ones
