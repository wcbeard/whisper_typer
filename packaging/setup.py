"""
WhisperTyper setup.py script for creating a macOS menubar app
Uses increased recursion limit to handle complex dependency trees.

For Development:
    python setup.py py2app -A

For Distribution:
    python setup.py py2app
"""

import sys

# Increase recursion limit to avoid errors during packaging
# This is needed due to complex dependency chains in some libraries
sys.setrecursionlimit(5000)

from setuptools import setup

APP = ["whisper_typer.py"]  # Main application file
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,  # Disabling to prevent issues with keyboard shortcuts
    "iconfile": "resources/app.icns",  # Updated icon file path
    "plist": {
        "LSUIElement": True,  # This makes it a menu bar app without a dock icon
        "CFBundleIdentifier": "com.wcbeard.whispertyper",
        "CFBundleName": "WhisperTyper",
        "CFBundleDisplayName": "WhisperTyper",
        "CFBundleVersion": "0.1.0",
        "NSHumanReadableCopyright": "Copyright © 2025 wcbeard",
        # Notification support
        "NSUserNotificationAlertStyle": "alert",
        "CFBundleShortVersionString": "0.1.0",
        # Microphone access description - required for permission prompt
        "NSMicrophoneUsageDescription": "WhisperTyper needs microphone access to convert speech to text",
        # Accessibility and input monitoring permissions
        "NSAccessibilityUsageDescription": "WhisperTyper requires accessibility permissions to monitor and control the keyboard.",
        "NSInputMonitoringUsageDescription": "WhisperTyper requires input monitoring permissions to detect keyboard inputs.",
    },
    # Include only essential packages to avoid dependency issues
    "packages": [
        "rumps",
        "pynput",
        "pyperclip",
    ],
    # Include required modules
    "includes": [
        "threading",
        "time",
        "logging",
        "os",
        "sys",
        "tempfile",
        "subprocess",
        "pynput.keyboard",
        "whisper",
        "torch",
        "numpy",
        "pyaudio",
        "wave",
        "AppKit",
        "Foundation",
        "objc",
        "rumps",
        "pynput.keyboard",
        # This is important - include the actual module that contains NSMakeRect
        "AppKit._inlines",
        "Foundation._inlines",
        # The following are dynamically loaded with importlib
        # and are not explicitly imported in the code
        "keyboard_handler_appkit",
        "keyboard_handler_quartz",
        "keyboard_handler_pynput",
    ],
    # This is sometimes needed to avoid packaging issues
    "prefer_ppc": False,
    # Explicitly exclude packages known to cause issues
    "excludes": [
        "scipy",
        "pandas",
        "matplotlib",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "tkinter",
    ],
    # Don't explicitly include the entire standard library--
    # let py2app find it
    # "frameworks": ["/System/Library/Frameworks/Carbon.framework"],
}

setup(
    app=APP,
    name="WhisperTyper",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app", "pyobjc-framework-Cocoa"],
    install_requires=[
        "rumps",
        "openai-whisper",
        "pyaudio",
        "pyperclip",
        "pynput",
    ],
)
