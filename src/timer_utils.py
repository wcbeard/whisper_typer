"""
Timer utilities for macOS menu bar applications.

IMPORTANT NOTICE ABOUT RUMPS.TIMER:
rumps.Timer creates REPEATING timers by default. This means that when you create a timer with
rumps.Timer(callback, interval), the callback will be executed REPEATEDLY at the specified interval
until you explicitly call timer.stop(). This behavior is often unexpected and can lead to bugs
where callbacks are triggered multiple times when only a single execution was intended.

The OneTimeTimer class in this module wraps rumps.Timer to create timers that automatically
stop after firing once, which is usually the expected behavior for UI callbacks.

For detailed context:
- A rumps.Timer continues calling its callback at regular intervals until explicitly stopped
- When using timers for UI callbacks (like from keyboard shortcuts), you typically want the
  callback to execute exactly once, not repeatedly
- Failing to stop the timer leads to the same callback being triggered multiple times, causing
  unexpected behavior (e.g., multiple keypress events for a single physical keypress)
- This can be particularly problematic with debounce mechanisms, as they may not prevent
  repeated callbacks from the same timer

Example:
    # BAD - will call handle_callback repeatedly every 0.1 seconds forever
    timer = rumps.Timer(lambda _: handle_callback(), 0.1)
    timer.start()

    # GOOD - will call handle_callback exactly once after 0.1 seconds
    timer = OneTimeTimer(lambda _: handle_callback(), 0.1)
    timer.start()
"""

import logging
import rumps

logger = logging.getLogger(__name__)


class OneTimeTimer(rumps.Timer):
    """
    A timer that fires exactly once and then automatically stops itself.

    This class solves the common issue with rumps.Timer where callbacks are unexpectedly
    called multiple times because the timer continues running until explicitly stopped.

    Args:
        callback (callable): The function to call when the timer fires.
        interval (float): Time in seconds to wait before firing.
        identifier (str, optional): An identifier for logging/debugging purposes.

    Example:
        # Create a timer that executes callback once after 0.5 seconds
        timer = OneTimeTimer(callback, 0.5, "my_timer")
        timer.start()

    Warning:
        Never use regular rumps.Timer for one-time events like UI callbacks!
        Using rumps.Timer without stopping it will cause the callback to be
        executed repeatedly at the specified interval, which can lead to duplicate
        actions, race conditions, and other unexpected behavior.
    """

    def __init__(self, callback, interval, identifier=None):
        """
        Initialize a one-time timer.

        Args:
            callback (callable): The function to call when the timer fires.
            interval (float): Time in seconds to wait before firing.
            identifier (str, optional): An identifier for debugging.
        """
        # Store the identifier for debugging
        self.identifier = identifier

        # Create a wrapper callback that stops the timer after execution
        def wrapper(_):
            # Log timer firing if identifier is provided
            if self.identifier:
                logger.debug(f"Timer fired: {self.identifier}")

            # Call the original callback
            try:
                callback(_)
            except Exception as e:
                logger.error(
                    f"Error in timer callback {self.identifier}: {e}", exc_info=True
                )
            finally:
                # Critical: Stop the timer to prevent it from firing again
                # This is what makes this a one-time timer versus rumps.Timer's default repeating behavior
                try:
                    logger.debug(f"Stopping timer: {self.identifier}")
                    self.stop()
                except Exception as e:
                    logger.error(
                        f"Error stopping timer {self.identifier}: {e}", exc_info=True
                    )

        # Initialize the parent class with our wrapper
        super(OneTimeTimer, self).__init__(wrapper, interval)


class TimerManager:
    """
    A utility class for managing multiple timers.

    This class helps track active timers and clean up completed ones to prevent
    memory leaks and make debugging easier.

    Example:
        timer_manager = TimerManager()
        timer = timer_manager.create_timer(callback, 0.5, "my_timer")
        timer.start()

        # Later, clean up any completed timers
        timer_manager.clean_timers()
    """

    def __init__(self):
        """Initialize the timer manager."""
        self.active_timers = []

    def create_timer(self, callback, interval, identifier=None):
        """
        Create a one-time timer and add it to the active timers list.

        Args:
            callback (callable): The function to call when the timer fires.
            interval (float): Time in seconds to wait before firing.
            identifier (str, optional): An identifier for debugging.

        Returns:
            OneTimeTimer: The created timer (not yet started).
        """
        timer = OneTimeTimer(callback, interval, identifier)
        self.active_timers.append(timer)
        return timer

    def clean_timers(self):
        """
        Remove completed timers from the active timers list.

        Returns:
            int: The number of timers removed.
        """
        start_count = len(self.active_timers)
        self.active_timers = [t for t in self.active_timers if t.is_alive()]
        removed = start_count - len(self.active_timers)

        if removed > 0:
            logger.debug(
                f"Cleaned up {removed} completed timers. {len(self.active_timers)} remaining."
            )

        return removed

    def stop_all(self):
        """Stop all active timers."""
        for timer in self.active_timers:
            try:
                timer.stop()
            except Exception as e:
                logger.error(f"Error stopping timer {timer.identifier}: {e}", exc_info=True)
                pass

        self.active_timers = []
        logger.debug("Stopped all timers")
