"""
Base interface and factory for keyboard shortcut detection.
This module provides a consistent interface for different keyboard shortcut detection methods.
"""

import abc
import logging
import importlib
import sys

# Configure logging
logger = logging.getLogger(__name__)

# Try to determine if we're running as a packaged app
is_packaged = getattr(sys, "frozen", False)


class KeyboardHandlerBase(abc.ABC):
    """Abstract base class for keyboard shortcut handlers."""

    def __init__(self, callback, shortcut_keys=None, debounce_seconds=1.0):
        """
        Initialize the keyboard handler.

        Args:
            callback: Function to call when the shortcut is detected
            shortcut_keys: Keys that make up the shortcut (implementation specific)
            debounce_seconds: Minimum time between shortcut activations
        """
        self.callback = callback
        self.shortcut_keys = shortcut_keys
        self.debounce_seconds = debounce_seconds
        logging.info(f"Initializing {self.__class__.__name__}")

    @abc.abstractmethod
    def start(self):
        """Start listening for keyboard shortcuts."""
        pass

    @abc.abstractmethod
    def stop(self):
        """Stop listening for keyboard shortcuts."""
        pass

    @classmethod
    def supports_packaged_app(cls):
        """
        Check if this handler supports packaged apps.
        Default implementation returns True.
        """
        return True


def create_keyboard_handler(method, callback, shortcut_keys=None, debounce_seconds=1.0):
    """
    Factory function to create a keyboard handler based on the specified method.

    Args:
        method: String name of the method to use ('pynput', 'quartz', 'appkit', 'applescript')
        callback: Function to call when the shortcut is detected
        shortcut_keys: Keys that make up the shortcut (implementation specific)
        debounce_seconds: Minimum time between shortcut activations

    Returns:
        A KeyboardHandlerBase instance

    Raises:
        ImportError: If the specified method is not available
        ValueError: If the specified method is not supported
    """
    # Map method names to module names
    method_map = {
        "appkit": "keyboard_handler_appkit",
        "pynput": "keyboard_handler_pynput",
        "quartz": "keyboard_handler_quartz",
        "applescript": "keyboard_handler_applescript",
    }

    # Get the module name for the specified method
    module_name = method_map.get(method.lower())
    if not module_name:
        raise ValueError(f"Unsupported keyboard handler method: {method}")

    try:
        # Import the module
        module = importlib.import_module(module_name)

        # Get the handler class
        # We expect each module to have a class named [Method]KeyboardHandler
        class_name = f"{method.capitalize()}KeyboardHandler"
        if not hasattr(module, class_name):
            raise ImportError(
                f"Module {module_name} does not contain class {class_name}"
            )

        handler_class = getattr(module, class_name)

        # Check if this handler supports packaged apps
        if is_packaged and not handler_class.supports_packaged_app():
            logging.warning(f"{handler_class.__name__} does not support packaged apps")
            return None

        # Create and return the handler
        handler = handler_class(callback, shortcut_keys, debounce_seconds)
        handler.start()
        return handler

    except ImportError as e:
        logging.error(f"Failed to import keyboard handler method {method}: {e}")
        raise
