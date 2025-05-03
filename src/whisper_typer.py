"""
WhisperTyper - A macOS menu bar app for voice-to-text transcription using OpenAI's Whisper model.
Uses modular keyboard shortcut handlers to start/stop recording and automatically transcribes speech to text.
"""

import rumps
import threading
import logging
import os
import sys
import tempfile
import subprocess
import pyperclip

# Need to manually import these for py2app to include them
import objc  # noqa: F401
import Foundation  # noqa: F401
import AppKit  # noqa: F401
from AppKit import NSApp, NSStatusBar, NSMenu, NSMenuItem, NSMakeRect  # noqa: F401

# Import the keyboard interface
from keyboard_interface import create_keyboard_handler

# Define icon constants
TEXT_ICON_IDLE = "W"
TEXT_ICON_RECORDING = "●"
TEXT_ICON_PROCESSING = "◎"

# Try to import Whisper, but make it optional
try:
    import pyaudio
    import wave
    import whisper

    WHISPER_AVAILABLE = True
except ImportError as e:
    logging.error(f"Import error: {e}")
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
        super(WhisperTyperApp, self).__init__(
            "WhisperTyper",
            TEXT_ICON_IDLE,
        )
        logging.info("Initializing WhisperTyperApp")

        # Try to load image icons
        self.using_image_icons = False
        self.try_load_image_icons()

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

    def is_retina_display(self):
        """Check if we're running on a Retina display"""
        try:
            import Cocoa

            # Get the main screen
            screen = Cocoa.NSScreen.mainScreen()
            # Check if it's a Retina display
            return screen.backingScaleFactor() > 1.0
        except Exception as e:
            # If we can't determine, assume not Retina
            logging.warning(f"Could not detect Retina display: {e}")
            return False

    def try_load_image_icons(self):
        """Attempt to load image icons with Retina support"""
        try:
            # Resources directory
            resources_dir = os.path.join(os.path.abspath("."), "resources")

            # Check if resources directory exists
            if not os.path.exists(resources_dir):
                logging.warning(f"Resources directory not found: {resources_dir}")
                return

            # Log the contents of the resources directory
            logging.info(f"Resources directory contents: {os.listdir(resources_dir)}")

            # Check if we're on a Retina display
            is_retina = self.is_retina_display()
            logging.info(f"Is Retina display: {is_retina}")

            # Find icon files - use @2x versions for Retina displays
            suffix = "@2x" if is_retina else ""

            # Set up paths for all icon states
            template_path = os.path.join(
                resources_dir, f"menubar_icon_template{suffix}.png"
            )
            regular_path = os.path.join(resources_dir, f"menubar_icon{suffix}.png")
            recording_path = os.path.join(
                resources_dir, f"menubar_icon_recording{suffix}.png"
            )
            processing_path = os.path.join(
                resources_dir, f"menubar_icon_processing{suffix}.png"
            )

            # Check which files exist and fall back to non-retina versions if needed
            if os.path.exists(template_path):
                self.icon_idle = template_path
                is_template = True
            elif os.path.exists(regular_path):
                self.icon_idle = regular_path
                is_template = False
            elif os.path.exists(
                os.path.join(resources_dir, "menubar_icon_template.png")
            ):
                self.icon_idle = os.path.join(
                    resources_dir, "menubar_icon_template.png"
                )
                is_template = True
            elif os.path.exists(os.path.join(resources_dir, "menubar_icon.png")):
                self.icon_idle = os.path.join(resources_dir, "menubar_icon.png")
                is_template = False
            else:
                self.icon_idle = None
                is_template = False

            # Recording icon
            if os.path.exists(recording_path):
                self.icon_recording = recording_path
            elif os.path.exists(
                os.path.join(resources_dir, "menubar_icon_recording.png")
            ):
                self.icon_recording = os.path.join(
                    resources_dir, "menubar_icon_recording.png"
                )
            else:
                self.icon_recording = self.icon_idle  # Fall back to idle icon

            # Processing icon
            if os.path.exists(processing_path):
                self.icon_processing = processing_path
            elif os.path.exists(
                os.path.join(resources_dir, "menubar_icon_processing.png")
            ):
                self.icon_processing = os.path.join(
                    resources_dir, "menubar_icon_processing.png"
                )
            else:
                self.icon_processing = self.icon_idle  # Fall back to idle icon

            # Log icon paths
            logging.info(
                f"Idle icon: {self.icon_idle}, exists: {self.icon_idle and os.path.exists(self.icon_idle)}"
            )
            logging.info(
                f"Recording icon: {self.icon_recording}, exists: {self.icon_recording and os.path.exists(self.icon_recording)}"
            )
            logging.info(
                f"Processing icon: {self.icon_processing}, exists: {self.icon_processing and os.path.exists(self.icon_processing)}"
            )

            # If we found the idle icon, try to use it
            if self.icon_idle and os.path.exists(self.icon_idle):
                logging.info(f"Using icon: {self.icon_idle}")

                try:
                    # Set the icon
                    self.icon = self.icon_idle

                    # Set template mode if using template icon
                    if is_template:
                        logging.info("Setting template mode")
                        self._template = True
                        if hasattr(self, "template"):
                            self.template = True

                    self.using_image_icons = True
                    logging.info("Successfully set initial icon")
                except Exception as e:
                    logging.error(f"Failed to set icon: {e}")
                    self.title = TEXT_ICON_IDLE
                    self.using_image_icons = False
            else:
                # Fall back to text icon
                logging.warning("No suitable icons found, using text")
                self.title = TEXT_ICON_IDLE
                self.using_image_icons = False

        except Exception as e:
            logging.error(f"Error loading icons: {str(e)}")
            import traceback

            logging.error(traceback.format_exc())
            self.using_image_icons = False

    def set_app_icon_state(self, state):
        """Set the app icon based on state with improved error handling"""
        try:
            if state == "idle":
                icon_path = self.icon_idle
                text_icon = TEXT_ICON_IDLE
            elif state == "recording":
                icon_path = self.icon_recording
                text_icon = TEXT_ICON_RECORDING
            elif state == "processing":
                icon_path = self.icon_processing
                text_icon = TEXT_ICON_PROCESSING
            else:
                logging.warning(f"Unknown icon state: {state}")
                icon_path = self.icon_idle
                text_icon = TEXT_ICON_IDLE

            if self.using_image_icons and icon_path and os.path.exists(icon_path):
                logging.info(f"Setting {state} icon: {icon_path}")
                self.icon = icon_path
            else:
                logging.info(f"Setting {state} text icon: {text_icon}")
                self.title = text_icon

        except Exception as e:
            logging.error(f"Error setting icon state {state}: {e}")
            # Fall back to text icon
            if state == "idle":
                self.title = TEXT_ICON_IDLE
            elif state == "recording":
                self.title = TEXT_ICON_RECORDING
            elif state == "processing":
                self.title = TEXT_ICON_PROCESSING

    def initialize_keyboard_handler(self):
        """Initialize the keyboard shortcut handler with the best available method"""
        # Try different methods in order of reliability (for packaged apps)
        methods_to_try = ["appkit", "quartz", "pynput", "applescript"]

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

            # Set the processing icon
            self.set_app_icon_state("processing")
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

            # Set the recording icon
            self.set_app_icon_state("recording")

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
                self.set_app_icon_state("idle")
                self.processing = False  # Exit processing state
            else:
                logging.warning("No audio frames captured")
                self.show_notification("Warning", "No audio captured")

                # Update status back to ready
                self.status_item.title = "Status: Ready"
                self.set_app_icon_state("idle")
                self.processing = False  # Exit processing state

        except Exception as e:
            logging.error(f"Error in record_audio method: {str(e)}")

            # Update status to error
            self.record_button.title = "Start Recording"
            self.status_item.title = "Status: Error - See log"
            self.set_app_icon_state("idle")
            self.recording = False
            self.processing = False  # Exit processing state

            self.show_notification("Recording Error", str(e))
        finally:
            # Ensure resources are cleaned up
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass

            try:
                audio.terminate()
            except Exception:
                pass

            # Clean up temp file
            if os.path.exists(self.temp_file):
                try:
                    os.remove(self.temp_file)
                except Exception:
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
            except Exception:
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
