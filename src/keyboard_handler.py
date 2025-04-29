"""
Reliable keyboard shortcut handler for macOS menubar applications.
This module provides a clean interface for detecting keyboard shortcuts
without the issues of multiple triggers.
"""

import threading
import time
import logging
from pynput import keyboard

class KeyboardShortcutHandler:
    """
    A reliable handler for keyboard shortcuts that prevents multiple triggers
    from a single key press combination.
    """
    
    def __init__(self, shortcut_keys, callback, debounce_seconds=1.0):
        """
        Initialize the keyboard shortcut handler.
        
        Args:
            shortcut_keys: A tuple of keyboard.Key objects that make up the shortcut
            callback: Function to call when the shortcut is detected
            debounce_seconds: Minimum time between shortcut activations
        """
        self.shortcut_keys = set(shortcut_keys)
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        # State variables
        self.keys_pressed = set()
        self.last_trigger_time = 0
        self.shortcut_lock = threading.Lock()
        self.shortcut_callback_requested = False
        self.running = True
        
        # Start the keyboard listener
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        
        # Start a checker thread to handle executing the callback
        # This avoids using rumps.Timer which can cause multiple triggers
        self.checker_thread = threading.Thread(target=self.check_for_callback_requests)
        self.checker_thread.daemon = True
        
        # Start both threads
        self.listener.start()
        self.checker_thread.start()
        
        logging.info(f"Started keyboard shortcut handler for {shortcut_keys}")
    
    def on_press(self, key):
        """Handle key press events"""
        try:
            # Add key to the set of pressed keys
            self.keys_pressed.add(key)
            
            # Check if all shortcut keys are pressed
            if self.shortcut_keys.issubset(self.keys_pressed):
                # Debounce check
                current_time = time.time()
                if current_time - self.last_trigger_time < self.debounce_seconds:
                    return
                
                self.last_trigger_time = current_time
                logging.info("Keyboard shortcut detected")
                
                # Request a callback, which will be executed by the checker thread
                with self.shortcut_lock:
                    self.shortcut_callback_requested = True
                
        except Exception as e:
            logging.error(f"Error in on_press: {str(e)}")
    
    def on_release(self, key):
        """Handle key release events"""
        try:
            # Remove key from the set of pressed keys
            if key in self.keys_pressed:
                self.keys_pressed.remove(key)
        except Exception as e:
            logging.error(f"Error in on_release: {str(e)}")
    
    def check_for_callback_requests(self):
        """Thread that checks for callback requests"""
        logging.info("Started callback request checker thread")
        while self.running:
            try:
                # Check if a callback was requested
                callback_requested = False
                with self.shortcut_lock:
                    if self.shortcut_callback_requested:
                        self.shortcut_callback_requested = False
                        callback_requested = True
                
                # Execute the callback if requested
                if callback_requested:
                    try:
                        self.callback()
                    except Exception as e:
                        logging.error(f"Error in shortcut callback: {str(e)}")
            except Exception as e:
                logging.error(f"Error in callback checker: {str(e)}")
            
            # Sleep to avoid consuming too much CPU
            time.sleep(0.1)
    
    def stop(self):
        """Stop the keyboard listener and checker thread"""
        logging.info("Stopping keyboard shortcut handler")
        self.running = False
        if self.listener.is_alive():
            self.listener.stop()
        # No need to stop the checker thread, it will exit when self.running is False