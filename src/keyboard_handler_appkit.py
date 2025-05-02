"""
AppKit-based keyboard shortcut handler for macOS.
This approach uses the NSEvent global monitor for keyboard events.

IMPORTANT: This implementation uses the OneTimeTimer to avoid multiple callback executions
from a single keyboard shortcut. See timer_utils.py for detailed explanation.
"""

import time
import logging
from keyboard_interface import KeyboardHandlerBase
from timer_utils import OneTimeTimer, TimerManager

# Configure logging
logger = logging.getLogger(__name__)


class AppkitKeyboardHandler(KeyboardHandlerBase):
    """
    Keyboard shortcut handler using AppKit NSEvent monitoring.
    This uses higher-level macOS APIs for global keyboard event monitoring.
    """

    def __init__(self, callback, shortcut_keys=None, debounce_seconds=1.0):
        """
        Initialize the AppKit keyboard handler.

        Args:
            callback: Function to call when the shortcut is detected
            shortcut_keys: Dictionary mapping key names to keycodes, e.g. {'option': None, 'space': 49}
                           If None, uses default shortcut (Option + Space)
            debounce_seconds: Minimum time between shortcut activations
        """
        # Default shortcut is Option + Space (49)
        self.shortcut_keycodes = shortcut_keys or {"option": None, "space": 49}

        # Initialize base class
        super().__init__(callback, self.shortcut_keycodes, debounce_seconds)

        # AppKit specific state
        self.monitor = None
        self.keys_pressed = set()
        self.key_down_state = {}  # Maps keycode -> timestamp of last keydown
        self.last_trigger_time = 0
        self.callback_lock = False

        # Create a timer manager to handle all our timers
        self.timer_manager = TimerManager()

        # Parse modifier flags
        self.modifier_flags = [
            shortcut
            for shortcut in self.shortcut_keycodes.keys()
            if shortcut in ["option", "control", "command", "shift"]
        ]
        self.non_modifier_keys = {
            k: v
            for k, v in self.shortcut_keycodes.items()
            if k not in self.modifier_flags
        }

        # Validate shortcut configuration
        if len(self.non_modifier_keys) != 1:
            logger.error(
                "AppKit keyboard handler requires exactly one non-modifier key"
            )
            raise ValueError(
                "AppKit keyboard handler requires exactly one non-modifier key"
            )
        self.key_name, self.key_code = list(self.non_modifier_keys.items())[0]
        logger.info(
            f"AppKit handler configured with shortcut: {self.modifier_flags} + {self.key_name} (code {self.key_code})"
        )

    def start(self):
        """Start listening for keyboard shortcuts using AppKit."""
        logger.info("Starting AppKit keyboard handler")

        try:
            # Import AppKit
            from AppKit import (
                NSEvent,
                NSKeyDownMask,
                NSKeyUpMask,
                NSKeyUp,
                NSKeyDown,
                NSEventModifierFlagOption,
                NSEventModifierFlagControl,
                NSEventModifierFlagCommand,
                NSEventModifierFlagShift,
                NSEventModifierFlagDeviceIndependentFlagsMask,
            )

            # Create modifier flag mask
            MODIFIER = 0
            for modifier in self.modifier_flags:
                if modifier == "option":
                    MODIFIER = MODIFIER | NSEventModifierFlagOption
                elif modifier == "control":
                    MODIFIER = MODIFIER | NSEventModifierFlagControl
                elif modifier == "command":
                    MODIFIER = MODIFIER | NSEventModifierFlagCommand
                elif modifier == "shift":
                    MODIFIER = MODIFIER | NSEventModifierFlagShift
                else:  # Unsupported modifier
                    logger.error(f"Unsupported modifier: {modifier}")
                    return False
            MASK = NSEventModifierFlagDeviceIndependentFlagsMask  # strips device-specific bits

            # Define key event handler
            def key_handler(event):
                try:
                    # Get key info
                    keycode = event.keyCode()
                    flags = event.modifierFlags() & MASK
                    event_type = event.type()

                    # Generate a unique ID for this event for tracing in logs
                    event_id = f"evt_{int(time.time() * 1000) % 10000}_{keycode}"
                    logger.debug(
                        f"Key event {event_id}: type={event_type}, keycode={keycode}, flags={flags}"
                    )

                    if event_type == NSKeyDown:
                        # Add key to pressed keys set
                        self.keys_pressed.add(keycode)

                        # Check if this key is already being tracked (repeat prevention)
                        current_time = time.time()
                        if keycode in self.key_down_state:
                            # This is a key repeat event, not a new keypress
                            last_time = self.key_down_state[keycode]
                            logger.debug(
                                f"Key repeat detected for keycode {keycode}, ignoring"
                            )
                            return

                        # Track this keydown event
                        self.key_down_state[keycode] = current_time

                        # Check for shortcut conditions
                        if keycode == self.key_code and (flags & MODIFIER) == MODIFIER:
                            # Verify we're not in a callback-locked state
                            if self.callback_lock:
                                logger.debug(
                                    f"Ignoring shortcut - callback lock is active"
                                )
                                return

                            # Apply time-based debounce
                            time_since_last = current_time - self.last_trigger_time
                            if time_since_last < self.debounce_seconds:
                                logger.debug(
                                    f"Ignoring shortcut - within debounce period ({time_since_last:.2f}s < {self.debounce_seconds}s)"
                                )
                                return

                            # Log shortcut detection
                            logger.info(f"Keyboard shortcut detected - {event_id}")
                            self.last_trigger_time = current_time

                            # Set the callback lock to prevent concurrent executions
                            self.callback_lock = True

                            # Execute callback using OneTimeTimer to ensure it only fires once
                            # This is critical to avoid multiple callbacks from a single keypress
                            callback_timer = self.timer_manager.create_timer(
                                lambda _: self.execute_callback(event_id),
                                0.1,  # 100ms delay
                                f"callback_{event_id}",
                            )
                            callback_timer.start()

                            # Set up another OneTimeTimer to release the lock after the debounce period
                            release_timer = self.timer_manager.create_timer(
                                lambda _: self.release_callback_lock(event_id),
                                self.debounce_seconds,
                                f"release_{event_id}",
                            )
                            release_timer.start()

                    elif event_type == NSKeyUp:
                        # Remove from tracking collections
                        if keycode in self.keys_pressed:
                            self.keys_pressed.remove(keycode)

                        # Clear key down state for this key
                        if keycode in self.key_down_state:
                            del self.key_down_state[keycode]
                            logger.debug(f"Cleared key state for keycode {keycode}")

                        # Clean up any completed timers
                        self.timer_manager.clean_timers()

                except Exception as e:
                    logger.error(f"Error in AppKit key_handler: {e}", exc_info=True)

            # Set up global monitor for key events
            mask = NSKeyDownMask | NSKeyUpMask
            self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask, key_handler
            )

            if self.monitor:
                logger.info("AppKit global keyboard monitor registered")
                return True
            else:
                logger.error("Failed to register AppKit global keyboard monitor")
                return False

        except ImportError as e:
            logger.error(f"Failed to import AppKit modules: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Error setting up AppKit keyboard handler: {e}", exc_info=True
            )
            return False

    def execute_callback(self, event_id):
        """Execute the callback function safely."""
        try:
            logger.debug(f"Executing callback for event {event_id}")
            self.callback()
        except Exception as e:
            logger.error(f"Error in keyboard shortcut callback: {e}", exc_info=True)

    def release_callback_lock(self, event_id):
        """Release the callback lock after debounce period."""
        logger.debug(f"Releasing callback lock for event {event_id}")
        self.callback_lock = False

    def stop(self):
        """Stop listening for keyboard shortcuts."""
        logger.info("Stopping AppKit keyboard handler")

        try:
            # Stop all timers
            if hasattr(self, "timer_manager"):
                self.timer_manager.stop_all()

            # Remove monitor
            if self.monitor:
                from AppKit import NSEvent

                NSEvent.removeMonitor_(self.monitor)
                self.monitor = None
                logger.info("AppKit global keyboard monitor removed")
            return True
        except Exception as e:
            logger.error(f"Error stopping AppKit keyboard handler: {e}", exc_info=True)
            return False

    @classmethod
    def supports_packaged_app(cls):
        """Check if AppKit is available for packaged apps."""
        try:
            import AppKit

            return True
        except ImportError:
            return False
