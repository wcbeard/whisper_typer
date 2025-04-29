"""
WhisperTyper setup.py script for creating a macOS menubar app

Usage:
For Development:
    python setup.py py2app -A

For Distribution:
    python setup.py py2app
"""

from setuptools import setup

APP = ["whisper_typer.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,  # Disabling to prevent issues
    "plist": {
        "LSUIElement": True,  # This makes it a menu bar app without a dock icon
        "CFBundleIdentifier": "com.yourusername.whispertyper",
        "CFBundleName": "WhisperTyper",
        "CFBundleDisplayName": "WhisperTyper",
        "CFBundleVersion": "0.1.0",
        "NSHumanReadableCopyright": "Copyright © 2025 Your Name",
        # Add these for better notification support
        "NSUserNotificationAlertStyle": "alert",
        "CFBundleShortVersionString": "0.1.0",
        # Add microphone usage description
        "NSMicrophoneUsageDescription": "WhisperTyper needs microphone access to convert speech to text",
    },
    "packages": [
        "rumps",
        "pyaudio",
        "wave",
        "whisper",
        "pyperclip",
        "pynput",
    ],
    # You might need to adjust this list based on your exact dependencies
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
    # Specify frameworks that PyAudio needs
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