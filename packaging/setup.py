"""
WhisperTyper setup.py script for creating a macOS menubar app
Uses increased recursion limit to handle complex dependency trees.

For Development:
    python setup.py py2app -A

For Distribution:
    python setup.py py2app
"""

import os
import shutil
import subprocess
import sys

# Increase recursion limit to avoid errors during packaging
# This is needed due to complex dependency chains in some libraries
sys.setrecursionlimit(5000)

from setuptools import setup  # noqa: E402


# Find FFmpeg on the system to include in the bundle
def find_ffmpeg():
    try:
        result = subprocess.run(
            ["which", "ffmpeg"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Check common locations
    common_locations = [
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]

    for location in common_locations:
        if os.path.exists(location) and os.access(location, os.X_OK):
            return location

    return None


# Find system FFmpeg
ffmpeg_path = find_ffmpeg()
APP = ["whisper_typer.py"]  # Main application file
_resource_files = [
    "resources/app.icns",
    "resources/menubar_icon.png",
    "resources/menubar_icon@2x.png",
    "resources/menubar_icon_template.png",
    "resources/menubar_icon_template@2x.png",
    "resources/menubar_icon_recording.png",
    "resources/menubar_icon_recording@2x.png",
    "resources/menubar_icon_processing.png",
    "resources/menubar_icon_processing@2x.png",
]

# If FFmpeg was found, include it in the bundle
if ffmpeg_path:
    # Check that we can create a copy for the app bundle
    try:
        # Create a resources directory if it doesn't exist
        if not os.path.exists("resources"):
            os.makedirs("resources")

        # Copy FFmpeg to resources
        shutil.copy2(ffmpeg_path, "resources/ffmpeg")
        # Make it executable
        os.chmod("resources/ffmpeg", 0o755)
        print(f"Copied FFmpeg from {ffmpeg_path} to resources/ffmpeg")

        # Include the FFmpeg binary in the app bundle
        _resource_files.append("resources/ffmpeg")
        print("FFmpeg is included in the app bundle.")
    except Exception as e:
        print(f"Failed to prepare FFmpeg for bundling: {e}")
else:
    print(
        "WARNING: FFmpeg not found on the system. The bundled app may not work correctly."
    )
    print("Please install FFmpeg using: brew install ffmpeg")

DATA_FILES = [("resources", _resource_files)]

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
        "ffmpeg_helper",
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
