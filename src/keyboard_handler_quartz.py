"""
Quartz-based keyboard shortcut handler for macOS.
This approach uses the Quartz event tap API for reliable keyboard event detection,
including in packaged applications.
"""

import time
import logging
import threading
import rumps
from keyboard_interface import KeyboardHandlerBase

# Configure logging
logger = logging.getLogger(__name__)

class QuartzKeyboardHandler(KeyboardHandlerBase):
    """
    Keyboard shortcut handler using Quartz event tap API.
    This is reliable for detecting global shortcuts in macOS,
    including in packaged applications.
    """
    
    def __init__(self, callback, shortcut_keys=None, debounce_seconds=1.0):
        """
        Initialize the Quartz keyboard handler.
        
        Args:
            callback: Function to call when the shortcut is detected
            shortcut_keys: Dictionary mapping key names to keycodes, e.g. {'alt_r': 61, 'enter': 36}
                           If None, uses default Right Alt + Enter
            debounce_seconds: Minimum time between shortcut activations
        """
        # Default shortcut is Right Alt (61) + Enter (36)
        self.shortcut_keycodes = shortcut_keys or {'alt_r': 61, 'enter': 36}
        
        # Initialize base class
        super().__init__(callback, self.shortcut_keycodes, debounce_seconds)
        
        # Quartz-specific state
        self.tap = None
        self.run_loop_source = None
        self.run_loop_thread = None
        self.keys_pressed = set()
        self.last_trigger_time = 0
        self.running = False
    
    def start(self):
        """Start listening for keyboard shortcuts using Quartz event tap."""
        logger.info("Starting Quartz keyboard handler")
        
        try:
            # Import Quartz
            from Quartz import (
                CGEventMaskBit, kCGEventKeyDown, kCGEventKeyUp, CFRunLoopGetCurrent,
                CFRunLoopAddSource, kCFRunLoopDefaultMode, CGEventTapCreate,
                kCGSessionEventTap, kCGHeadInsertEventTap, CGEventTapEnable,
                CFMachPortCreateRunLoopSource
            )
            
            # Define the event callback
            def event_tap_callback(proxy, event_type, event, refcon):
                try:
                    if event_type == kCGEventKeyDown:
                        from Quartz import CGEventGetIntegerValueField, kCGKeyboardEventKeycode
                        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                        logger.debug(f"Key down: {keycode}")
                        
                        # Check for shortcut keys by keycode
                        for key_name, code in self.shortcut_keycodes.items():
                            if keycode == code:
                                self.keys_pressed.add(key_name)
                        
                        # Check if all shortcut keys are pressed
                        if set(self.shortcut_keycodes.keys()).issubset(self.keys_pressed):
                            current_time = time.time()
                            if current_time - self.last_trigger_time >= self.debounce_seconds:
                                self.last_trigger_time = current_time
                                logger.info("Keyboard shortcut detected (Quartz)")
                                
                                # Execute callback on main thread via rumps.Timer
                                def do_callback(_):
                                    self.callback()
                                
                                timer = rumps.Timer(do_callback, 0.1)
                                timer.start()
                    
                    elif event_type == kCGEventKeyUp:
                        from Quartz import CGEventGetIntegerValueField, kCGKeyboardEventKeycode
                        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                        logger.debug(f"Key up: {keycode}")
                        
                        # Remove released keys
                        for key_name, code in self.shortcut_keycodes.items():
                            if keycode == code and key_name in self.keys_pressed:
                                self.keys_pressed.remove(key_name)
                    
                    return event  # Pass event to next handler
                except Exception as e:
                    logger.error(f"Error in event_tap_callback: {e}", exc_info=True)
                    return event  # Ensure we return the event even on error
            
            # Create event tap
            event_mask = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp)
            self.tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                0,  # options (pass-through)
                event_mask,
                event_tap_callback,
                None
            )
            
            if self.tap:
                self.run_loop_source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
                CFRunLoopAddSource(CFRunLoopGetCurrent(), self.run_loop_source, kCFRunLoopDefaultMode)
                CGEventTapEnable(self.tap, True)
                logger.info("Quartz event tap registered and enabled")
                
                # Set up the run loop in a separate thread
                def run_tap():
                    try:
                        self.running = True
                        from Quartz import CFRunLoopRun, CFRunLoopStop, CFRunLoopGetCurrent
                        logger.info("Starting Quartz event tap run loop")
                        
                        # Run the loop until self.running becomes False
                        CFRunLoopRun()
                        
                        logger.info("Quartz event tap run loop exited")
                    except Exception as e:
                        logger.error(f"Error in Quartz event tap run loop: {e}", exc_info=True)
                
                self.run_loop_thread = threading.Thread(target=run_tap)
                self.run_loop_thread.daemon = True
                self.run_loop_thread.start()
                
                return True
            else:
                logger.error("Failed to create Quartz event tap")
                return False
        
        except ImportError as e:
            logger.error(f"Failed to import Quartz modules: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting up Quartz keyboard handler: {e}", exc_info=True)
            return False
    
    def stop(self):
        """Stop listening for keyboard shortcuts."""
        logger.info("Stopping Quartz keyboard handler")
        
        self.running = False
        
        try:
            if self.tap:
                from Quartz import CGEventTapEnable, CFRunLoopStop, CFRunLoopGetCurrent
                CGEventTapEnable(self.tap, False)
                CFRunLoopStop(CFRunLoopGetCurrent())
                logger.info("Quartz event tap disabled")
            
            # Wait for the run loop thread to exit
            if self.run_loop_thread and self.run_loop_thread.is_alive():
                self.run_loop_thread.join(timeout=1.0)
            
            return True
        except Exception as e:
            logger.error(f"Error stopping Quartz keyboard handler: {e}", exc_info=True)
            return False
    
    @classmethod
    def supports_packaged_app(cls):
        """Check if Quartz is available for packaged apps."""
        try:
            import Quartz
            return True
        except ImportError:
            return False