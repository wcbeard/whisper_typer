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
    ],
    # Explicitly exclude packages known to cause issues
    "excludes": [
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "torch",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "tkinter",
    ],
    # Specify any needed frameworks
    "frameworks": ["/System/Library/Frameworks/Carbon.framework"],
}

setup(
    app=APP,
    name="WhisperTyper",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    install_requires=[
        "rumps",
        "openai-whisper",
        "pyaudio",
        "pyperclip",
        "pynput",
    ],
)
