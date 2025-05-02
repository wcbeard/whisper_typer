"""
Pynput-based keyboard shortcut handler.
This approach uses the pynput library for keyboard event detection.
Works well in development but may have issues in packaged apps.
"""

import time
import logging
import rumps
import threading
from keyboard_interface import KeyboardHandlerBase

# Configure logging
logger = logging.getLogger(__name__)

# Try to import pynput
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logger.error("Failed to import pynput. PynputKeyboardHandler will not be available.")

class PynputKeyboardHandler(KeyboardHandlerBase):
    """
    Keyboard shortcut handler using pynput.
    Works well in development but may have issues in packaged apps.
    """
    
    def __init__(self, callback, shortcut_keys=None, debounce_seconds=1.0):
        """
        Initialize the pynput keyboard handler.
        
        Args:
            callback: Function to call when the shortcut is detected
            shortcut_keys: Tuple of pynput.keyboard.Key objects that make up the shortcut
                          If None, uses default (Key.alt_r, Key.enter)
            debounce_seconds: Minimum time between shortcut activations
        """
        # Default shortcut is Right Alt + Enter
        if not PYNPUT_AVAILABLE:
            raise ImportError("pynput is not available. Cannot create PynputKeyboardHandler.")
        
        self.shortcut_keys = shortcut_keys or (keyboard.Key.alt_r, keyboard.Key.enter)
        self.shortcut_set = set(self.shortcut_keys)
        
        # Initialize base class
        super().__init__(callback, self.shortcut_keys, debounce_seconds)
        
        # Pynput specific state
        self.listener = None
        self.keys_pressed = set()
        self.last_trigger_time = 0
        self.running = False
    
    def start(self):
        """Start listening for keyboard shortcuts using pynput."""
        logger.info("Starting pynput keyboard handler")
        
        if not PYNPUT_AVAILABLE:
            logger.error("Cannot start pynput keyboard handler - pynput is not available")
            return False
        
        try:
            self.running = True
            
            # Set up keyboard listener
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            logger.info("pynput keyboard listener started")
            
            return True
        except Exception as e:
            logger.error(f"Error starting pynput keyboard handler: {e}", exc_info=True)
            return False
    
    def on_press(self, key):
        """Handle key press events"""
        try:
            logger.debug(f"Key pressed: {key}")
            # Add key to the set of pressed keys
            self.keys_pressed.add(key)
            
            # Check if all shortcut keys are pressed
            if self.shortcut_set.issubset(self.keys_pressed):
                current_time = time.time()
                if current_time - self.last_trigger_time >= self.debounce_seconds:
                    self.last_trigger_time = current_time
                    logger.info("Keyboard shortcut detected (pynput)")
                    
                    # Execute callback on main thread via rumps.Timer
                    def do_callback(_):
                        self.callback()
                    
                    timer = rumps.Timer(do_callback, 0.1)
                    timer.start()
        except Exception as e:
            logger.error(f"Error in on_press: {e}", exc_info=True)
    
    def on_release(self, key):
        """Handle key release events"""
        try:
            logger.debug(f"Key released: {key}")
            # Remove key from the set of pressed keys
            if key in self.keys_pressed:
                self.keys_pressed.remove(key)
        except Exception as e:
            logger.error(f"Error in on_release: {e}", exc_info=True)
    
    def stop(self):
        """Stop listening for keyboard shortcuts."""
        logger.info("Stopping pynput keyboard handler")
        
        self.running = False
        
        try:
            if self.listener and self.listener.is_alive():
                self.listener.stop()
                logger.info("pynput keyboard listener stopped")
            
            return True
        except Exception as e:
            logger.error(f"Error stopping pynput keyboard handler: {e}", exc_info=True)
            return False
    
    @classmethod
    def supports_packaged_app(cls):
        """
        Check if pynput is available and works in packaged apps.
        While pynput may be importable, it often doesn't work in packaged apps,
        so we return False if we detect that we're running in a packaged app.
        """
        import sys
        is_packaged = getattr(sys, 'frozen', False)
        
        if is_packaged:
            logger.warning("Running as packaged app - pynput may not work properly")
            return False
        
        return PYNPUT_AVAILABLE