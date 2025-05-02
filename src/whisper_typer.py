"""
WhisperTyper - A macOS menu bar app for voice-to-text transcription using OpenAI's Whisper model.
Uses modular keyboard shortcut handlers to start/stop recording and automatically transcribes speech to text.
"""

import rumps
import threading
import time
import logging
import os
import sys
import tempfile
import subprocess
import pyperclip

# Import the keyboard interface
from keyboard_interface import create_keyboard_handler

# Icon configuration - easy to customize
ICON_IDLE = "W"  # Icon when not recording
ICON_RECORDING = "●"  # Red circle icon for recording
ICON_PROCESSING = "◎"  # Processing icon

# Try to import Whisper, but make it optional
try:
    import pyaudio
    import wave
    import whisper

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning(
        "Some dependencies are missing. Full functionality may not be available."
    )


# Set up logging to file and console
def setup_logging():
    """Configure logging to output to both file and stdout."""
    log_file = os.path.expanduser("~/whisper_typer.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Set up file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Set up stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not root_logger.hasHandlers():
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stdout_handler)


# Set up logging
setup_logging()
logging.info("Starting WhisperTyperApp")


class WhisperTyperApp(rumps.App):
    """A menu bar app for voice-to-text transcription using Whisper."""

    def __init__(self):
        # Use the idle icon from configuration
        super(WhisperTyperApp, self).__init__("WhisperTyper", ICON_IDLE)
        logging.info("Initializing WhisperTyperApp")

        # Internal state
        self.recording = False
        self.processing = False
        self.whisper_model = None
        self.current_model = "tiny"
        self.keyboard_handler = None
        self.keyboard_method = None

        # Create menu items as instance variables
        self.status_item = rumps.MenuItem("Status: Ready")
        self.record_button = rumps.MenuItem(
            "Start Recording", callback=self.toggle_recording
        )
        self.shortcut_info = rumps.MenuItem("Shortcut: Right Option + Enter")

        # Add model selection if Whisper is available
        if WHISPER_AVAILABLE:
            self.tiny_model = rumps.MenuItem(
                "Tiny (Fast, Less Accurate)", callback=lambda _: self.set_model("tiny")
            )
            self.base_model = rumps.MenuItem(
                "Base (Balanced)", callback=lambda _: self.set_model("base")
            )
            self.small_model = rumps.MenuItem(
                "Small (More Accurate, Slower)",
                callback=lambda _: self.set_model("small"),
            )
            self.tiny_model.state = True  # Set tiny as default

            self.model_menu = rumps.MenuItem("Whisper Model")
            self.model_menu.add(self.tiny_model)
            self.model_menu.add(self.base_model)
            self.model_menu.add(self.small_model)
        else:
            self.model_menu = rumps.MenuItem("Whisper Not Installed")

        # Add keyboard handler selection menu
        self.keyboard_menu = rumps.MenuItem("Keyboard Handler")
        self.keyboard_pynput = rumps.MenuItem(
            "pynput", callback=lambda _: self.set_keyboard_method("pynput")
        )
        self.keyboard_quartz = rumps.MenuItem(
            "Quartz", callback=lambda _: self.set_keyboard_method("quartz")
        )
        self.keyboard_appkit = rumps.MenuItem(
            "AppKit", callback=lambda _: self.set_keyboard_method("appkit")
        )
        self.keyboard_applescript = rumps.MenuItem(
            "AppleScript", callback=lambda _: self.set_keyboard_method("applescript")
        )

        self.keyboard_menu.add(self.keyboard_pynput)
        self.keyboard_menu.add(self.keyboard_quartz)
        self.keyboard_menu.add(self.keyboard_appkit)
        self.keyboard_menu.add(self.keyboard_applescript)

        # Setup menu
        self.menu = [
            self.status_item,
            None,  # Separator
            self.record_button,
            self.shortcut_info,
            None,  # Separator
            self.model_menu,
            self.keyboard_menu,
            None,  # Separator
            rumps.MenuItem("Open Log", callback=self.open_log),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        # Audio recording parameters
        if WHISPER_AVAILABLE:
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = 16000
            self.CHUNK = 1024

            # Create a temporary file for the recording
            self.temp_dir = tempfile.gettempdir()
            self.temp_file = os.path.join(self.temp_dir, "whisper_recording.wav")

        # Set up keyboard shortcut handler - try methods in order of reliability
        self.initialize_keyboard_handler()

        logging.info("Initialization complete")

    def initialize_keyboard_handler(self):
        """Initialize the keyboard shortcut handler with the best available method"""
        # Try different methods in order of reliability (for packaged apps)
        methods_to_try = ["quartz", "appkit", "pynput", "applescript"]

        # Check if we're running as a packaged app
        is_packaged = getattr(sys, "frozen", False)
        if is_packaged:
            # In packaged apps, pynput often doesn't work, so try other methods first
            logging.info(
                "Running as packaged app, prioritizing Quartz and AppKit methods"
            )
        else:
            # In development, pynput usually works fine and is simpler
            logging.info("Running in development mode, prioritizing pynput method")
            methods_to_try.insert(0, "appkit")  # Try appkit first in development

        # Try each method until one works
        for method in methods_to_try:
            try:
                success = self.set_keyboard_method(method, show_notification=False)
                if success:
                    break
            except Exception as e:
                logging.error(f"Failed to initialize {method} keyboard handler: {e}")
                continue

        # If no method worked, show a warning
        if not self.keyboard_handler:
            logging.warning("No keyboard handler could be initialized")
            self.show_notification(
                "Warning",
                "Could not initialize keyboard shortcuts. Menu options will still work.",
            )

    def set_keyboard_method(self, method, show_notification=True):
        """Change the keyboard shortcut handler method"""
        logging.info(f"Setting keyboard method to: {method}")

        # Store previous method for menu state updates
        previous_method = self.keyboard_method

        # Stop existing handler if any
        if self.keyboard_handler:
            logging.info("Stopping existing keyboard handler")
            self.keyboard_handler.stop()
            self.keyboard_handler = None

        # Debug active monitors (AppKit-specific)
        if method == "appkit":
            logging.info("Checking for active AppKit monitors before initialization")

        # Try to create the new handler
        try:
            self.keyboard_handler = create_keyboard_handler(
                method=method,
                callback=self.handle_keyboard_shortcut,
                shortcut_keys=None,  # Use default for each method
                debounce_seconds=1.0,
            )

            if self.keyboard_handler:
                self.keyboard_method = method
                logging.info(f"Successfully set keyboard method to: {method}")

                # Update menu checkmarks
                self.keyboard_appkit.state = method == "appkit"
                self.keyboard_pynput.state = method == "pynput"
                self.keyboard_quartz.state = method == "quartz"
                self.keyboard_applescript.state = method == "applescript"

                if show_notification:
                    self.show_notification("Keyboard Method", f"Changed to: {method}")

                return True
            else:
                logging.error(f"Failed to create keyboard handler for method: {method}")

                # Restore previous method if it was working
                if previous_method:
                    logging.info(f"Restoring previous method: {previous_method}")
                    self.set_keyboard_method(previous_method, show_notification=False)

                if show_notification:
                    self.show_notification(
                        "Error", f"Failed to set keyboard method to: {method}"
                    )

                return False

        except Exception as e:
            logging.error(f"Error setting keyboard method to {method}: {e}")

            # Restore previous method if it was working
            if previous_method:
                logging.info(f"Restoring previous method: {previous_method}")
                self.set_keyboard_method(previous_method, show_notification=False)

            if show_notification:
                self.show_notification(
                    "Error", f"Failed to set keyboard method to: {method}"
                )

            return False

    def handle_keyboard_shortcut(self):
        """Handle keyboard shortcut callback"""
        logging.info("Keyboard shortcut triggered callback")

        # Only toggle if we're not already processing
        if not self.processing:
            self.toggle_recording(self.record_button)
        else:
            logging.info("Ignoring shortcut while processing")

    def open_log(self, _):
        """Open the log file"""
        log_file = os.path.expanduser("~/whisper_typer.log")
        try:
            subprocess.run(["open", log_file])
        except Exception as e:
            logging.error(f"Error opening log file: {e}")
            self.show_notification("Error", f"Could not open log file: {e}")

    def set_model(self, model_name):
        """Set the Whisper model to use"""
        logging.info(f"Setting model to {model_name}")
        self.current_model = model_name

        # Update menu checkmarks
        self.tiny_model.state = model_name == "tiny"
        self.base_model.state = model_name == "base"
        self.small_model.state = model_name == "small"

        # Clear the loaded model to force reloading
        self.whisper_model = None

    def toggle_recording(self, sender):
        """Toggle recording state"""
        logging.info("Toggle recording called.")
        logging.info(f"Recording state before toggle: {self.recording}")
        logging.info(f"Processing state before toggle: {self.processing}")

        # Don't allow toggling while processing
        if self.processing:
            logging.info("Ignoring toggle request while processing")
            return

        if self.recording:
            # Stop recording
            logging.info("Stopping recording")
            self.recording = False
            self.processing = True  # Enter processing state
            sender.title = "Start Recording"
            self.status_item.title = "Status: Processing..."
            # Use the processing icon from configuration
            self.title = ICON_PROCESSING
        else:
            # Start recording
            logging.info("Starting recording")

            # Check for required dependencies
            if not WHISPER_AVAILABLE:
                logging.error("Whisper or audio libraries not available")
                self.show_notification(
                    "Missing Dependencies",
                    "Please install whisper, pyaudio, and wave libraries",
                )
                return

            self.recording = True
            sender.title = "Stop Recording"
            self.status_item.title = "Status: Recording..."
            # Use the recording icon from configuration
            self.title = ICON_RECORDING

            # Start a background thread for recording
            logging.info("Starting recording thread")
            thread = threading.Thread(target=self.record_audio)
            thread.daemon = True
            thread.start()

    def show_notification(self, title, message):
        """Show a notification safely"""
        try:
            rumps.notification("WhisperTyper", title, message)
        except Exception as e:
            logging.error(f"Failed to show notification: {str(e)}")

    def record_audio(self):
        """Record audio and transcribe it using Whisper"""
        logging.info("Record audio method started")

        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        frames = []
        stream = None

        try:
            logging.info("Starting audio capture")
            # Start recording
            stream = audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            # Record until self.recording becomes False
            count = 0
            while self.recording:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                count += 1
                # Log occasionally to avoid verbose output
                if count % 100 == 0:
                    logging.debug(
                        f"Recorded {count * self.CHUNK / self.RATE:.1f} seconds"
                    )

            logging.info(f"Recording stopped, captured {len(frames)} frames")

            # If we have some frames, process them
            if len(frames) > 0:
                # Stop recording and close stream
                if stream:
                    stream.stop_stream()
                    stream.close()

                # Save the recording to the temporary file
                wf = wave.open(self.temp_file, "wb")
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b"".join(frames))
                wf.close()
                logging.info(f"Saved recording to {self.temp_file}")

                # Update status directly (avoid using Timer)
                self.status_item.title = "Status: Transcribing..."

                # Load Whisper model if not already loaded
                if self.whisper_model is None:
                    logging.info(f"Loading Whisper model: {self.current_model}")
                    self.whisper_model = whisper.load_model(self.current_model)
                    logging.info("Whisper model loaded")

                # Transcribe
                logging.info("Starting transcription")
                result = self.whisper_model.transcribe(self.temp_file)
                logging.info("Transcription complete")

                # Get the transcribed text
                text = result["text"].strip()
                logging.info(f"Transcribed text: {text[:50]}...")

                # Copy to clipboard
                pyperclip.copy(text)
                logging.info("Text copied to clipboard")

                # Type the text to the active application (macOS specific)
                self._type_text(text)

                # Show a notification
                preview = text[:50] + "..." if len(text) > 50 else text
                self.show_notification(
                    "Transcription Complete", f"Transcribed: {preview}"
                )

                # Update status back to ready
                self.status_item.title = "Status: Ready"
                self.title = ICON_IDLE  # Back to idle icon
                self.processing = False  # Exit processing state
            else:
                logging.warning("No audio frames captured")
                self.show_notification("Warning", "No audio captured")

                # Update status back to ready
                self.status_item.title = "Status: Ready"
                self.title = ICON_IDLE  # Back to idle icon
                self.processing = False  # Exit processing state

        except Exception as e:
            logging.error(f"Error in record_audio method: {str(e)}")

            # Update status to error
            self.record_button.title = "Start Recording"
            self.status_item.title = f"Status: Error - See log"
            self.title = ICON_IDLE  # Back to idle icon
            self.recording = False
            self.processing = False  # Exit processing state

            self.show_notification("Recording Error", str(e))
        finally:
            # Ensure resources are cleaned up
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass

            try:
                audio.terminate()
            except:
                pass

            # Clean up temp file
            if os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except:
                    logging.warning(f"Failed to remove temp file: {self.temp_file}")

            logging.info("record_audio method finished")

    def _type_text(self, text):
        """Type the text to the active application using AppleScript"""
        try:
            logging.info("Typing text to active application")
            # Escape double quotes for AppleScript
            escaped_text = text.replace('"', '\\"')

            apple_script = f"""
            tell application "System Events"
                keystroke "{escaped_text}"
            end tell
            """

            subprocess.run(["osascript", "-e", apple_script])
            logging.info("Text typed to active application")
        except Exception as e:
            logging.error(f"Error typing text: {str(e)}")
            self.show_notification("Error", f"Failed to type text: {str(e)}")

    def quit_app(self, _):
        """Quit the application properly"""
        logging.info("Quitting application")
        # Stop recording if active
        self.recording = False
        self.processing = False

        # Stop keyboard shortcut handler
        if self.keyboard_handler:
            self.keyboard_handler.stop()

        # Clean up temp file
        if hasattr(self, "temp_file") and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                logging.warning(f"Failed to remove temp file: {self.temp_file}")

        # Quit the app
        rumps.quit_application()


if __name__ == "__main__":
    try:
        logging.info("Starting application")
        app = WhisperTyperApp()
        app.run()
    except Exception as e:
        logging.error(f"Unhandled exception in main: {str(e)}")
