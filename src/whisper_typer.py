import rumps
import threading
import time
import logging
import os
import sys
import tempfile
import subprocess
import pyperclip

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
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stdout_handler)


# Set up logging
setup_logging()
logging.info("Starting WhisperTyperApp")


# Use AppleScript for global hotkey instead of pynput
def register_hotkey():
    """
    Register a global hotkey using macOS's built-in tools.
    This creates a small AppleScript application that listens for
    the keyboard shortcut and triggers our app.
    """
    try:
        # Create a temporary AppleScript file
        script_path = os.path.expanduser("~/whisper_hotkey.scpt")

        # AppleScript to listen for our shortcut and send a notification
        applescript = """
        on run
            tell application "System Events"
                -- Listen for right option + enter
                set enterDown to false
                set optionDown to false
                set lastTriggered to 0
                
                repeat
                    -- Check for Option+Enter combination
                    if (key code 36 is down) then
                        set enterDown to true
                    else
                        set enterDown to false
                    end if
                    
                    if (key code 61 is down) then
                        set optionDown to true
                    else
                        set optionDown to false
                    end if
                    
                    if (enterDown and optionDown) then
                        set currentTime to (do shell script "date +%s") as integer
                        if currentTime - lastTriggered > 1 then
                            set lastTriggered to currentTime
                            do shell script "open 'whispertyper://toggle'"
                        end if
                    end if
                    
                    delay 0.1
                end repeat
            end tell
        end run
        """

        # Write the AppleScript to a file
        with open(script_path, "w") as f:
            f.write(applescript)

        # Compile and run the AppleScript
        subprocess.Popen(
            ["osascript", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        logging.info("Registered global hotkey using AppleScript")
        return True
    except Exception as e:
        logging.error(f"Failed to register global hotkey: {str(e)}")
        return False


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

        # Setup menu
        self.menu = [
            self.status_item,
            None,  # Separator
            self.record_button,
            self.shortcut_info,
            None,  # Separator
            self.model_menu,
            None,  # Separator
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

        # Register URL handler for hotkey callback
        self.register_url_handlers()

        # Register the hotkey
        register_hotkey()

        logging.info("Initialization complete")

    def register_url_handlers(self):
        """Register URL handlers for AppleScript communication"""
        try:
            # Create a LSHandlers file to register our custom URL scheme
            handlers_path = os.path.expanduser(
                "~/Library/Preferences/com.apple.LaunchServices/LSHandlers.plist"
            )

            # Check if the file exists
            if not os.path.exists(handlers_path):
                # We'll use defaults command instead
                app_path = sys.argv[0]
                subprocess.run(
                    [
                        # "defaults",
                        # "write",
                        # "com.apple.LaunchServices",
                        # "LSHandlers",
                        # "-array-add",
                        # f'{{"LSHandlerURLScheme":"whispertyper","LSHandlerRole":"Editor","LSHandlerPath":"{app_path}"}}',
                        "defaults",
                        "write",
                        "com.apple.LaunchServices",
                        "LSHandlers",
                        "-array-add",
                        f"'LSHandlerURLScheme'='whispertyper';'LSHandlerRole'='Editor';'LSHandlerPath'='{app_path}'",
                    ]
                )

            logging.info("Registered URL handlers")
        except Exception as e:
            logging.error(f"Failed to register URL handlers: {str(e)}")

    def handle_open_url(self, url):
        """Handle URL callback from AppleScript"""
        logging.info(f"Received URL callback: {url}")
        if url == "whispertyper://toggle":
            # Schedule a timer to toggle recording on main thread
            def do_toggle(_):
                if not self.processing:
                    self.toggle_recording(self.record_button)

            timer = rumps.Timer(do_toggle, 0.1)
            timer.start()

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
        logging.info(f"Toggle recording called. Current state: {self.recording}")

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

                # Update status to transcribing
                def update_to_transcribing(_):
                    self.status_item.title = "Status: Transcribing..."
                    # Keep the processing icon during transcription

                timer = rumps.Timer(update_to_transcribing, 0.1)
                timer.start()

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
                def update_to_ready(_):
                    self.status_item.title = "Status: Ready"
                    self.title = ICON_IDLE  # Back to idle icon
                    self.processing = False  # Exit processing state

                timer = rumps.Timer(update_to_ready, 0.1)
                timer.start()
            else:
                logging.warning("No audio frames captured")
                self.show_notification("Warning", "No audio captured")

                # Update status back to ready
                def update_to_ready(_):
                    self.status_item.title = "Status: Ready"
                    self.title = ICON_IDLE  # Back to idle icon
                    self.processing = False  # Exit processing state

                timer = rumps.Timer(update_to_ready, 0.1)
                timer.start()

        except Exception as e:
            logging.error(f"Error in record_audio method: {str(e)}")

            # Update status to error
            def update_to_error(_):
                self.record_button.title = "Start Recording"
                self.status_item.title = f"Status: Error - See log"
                self.title = ICON_IDLE  # Back to idle icon
                self.recording = False
                self.processing = False  # Exit processing state

            timer = rumps.Timer(update_to_error, 0.1)
            timer.start()

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

    def quit_app(self, sender):
        """Quit the application properly"""
        logging.info("Quitting application")
        # Stop recording if active
        self.recording = False
        self.processing = False

        # Kill the AppleScript process
        try:
            subprocess.run(["pkill", "-f", "whisper_hotkey.scpt"])
        except:
            pass

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

        # Check if started with URL argument (from AppleScript)
        if len(sys.argv) > 1 and sys.argv[1].startswith("whispertyper://"):
            app.handle_open_url(sys.argv[1])

        app.run()
    except Exception as e:
        logging.error(f"Unhandled exception in main: {str(e)}")
