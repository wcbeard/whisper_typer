#!/usr/bin/env python3
"""
WhisperTyper Debug Tool

This script helps diagnose issues with the WhisperTyper application,
especially when launched through different methods.

Usage:
  python debug_whispertyper.py --check-permissions
  python debug_whispertyper.py --test-shortcuts
  python debug_whispertyper.py --check-paths
  python debug_whispertyper.py --test-all
"""

import argparse
import logging
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/whispertyper_debug.log"))
    ]
)

# Try to import pynput for keyboard testing
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - keyboard testing will be limited")

# Try to import rumps for menu bar testing
try:
    import rumps
    RUMPS_AVAILABLE = True
except ImportError:
    RUMPS_AVAILABLE = False
    logging.warning("rumps not available - menu bar testing will be limited")

# Try to import other dependencies
try:
    import pyaudio
    import wave
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("pyaudio/wave not available - audio testing will be limited")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("whisper not available - transcription testing will be limited")

class DebugHelper:
    """Main debug helper class"""
    
    def __init__(self):
        logging.info("Starting WhisperTyper Debug Helper")
        logging.info(f"Python version: {platform.python_version()}")
        logging.info(f"OS: {platform.system()} {platform.release()}")
        logging.info(f"Launch path: {sys.argv[0]}")
        
        # Track how the app was launched
        self.launched_from_finder = self._check_if_launched_from_finder()
        self.launched_from_terminal = not self.launched_from_finder
        
        logging.info(f"Launched from Finder: {self.launched_from_finder}")
        logging.info(f"Launched from Terminal: {self.launched_from_terminal}")
        
        # Keyboard tracking variables (if pynput is available)
        if PYNPUT_AVAILABLE:
            self.keys_pressed = set()
            self.shortcut_detected = False
    
    def _check_if_launched_from_finder(self):
        """Check if the app was launched from Finder vs Terminal"""
        # Check if parent process is finder or terminal
        if 'TERM_PROGRAM' in os.environ:
            return False
        
        # Additional check: are we running inside a .app bundle?
        executable_path = Path(sys.argv[0]).resolve()
        if '.app/Contents/MacOS' in str(executable_path):
            # Check if we were directly executed or via 'open'
            ppid = os.getppid()
            try:
                parent_process = subprocess.check_output(['ps', '-p', str(ppid), '-o', 'comm=']).decode().strip()
                if parent_process in ['open', 'launchd', 'Finder']:
                    return True
            except:
                pass
        
        return False
    
    def check_permissions(self):
        """Check if the app has the necessary permissions"""
        logging.info("Checking app permissions...")
        
        # Check for accessibility permissions by trying to listen for keyboard events
        perm_status = {
            "Accessibility": "Unknown",
            "Microphone": "Unknown"
        }
        
        # Check accessibility by trying to create a keyboard listener
        if PYNPUT_AVAILABLE:
            try:
                listener = keyboard.Listener(
                    on_press=lambda key: None,
                    on_release=lambda key: None
                )
                listener.start()
                time.sleep(0.5)
                if listener.is_alive():
                    perm_status["Accessibility"] = "Granted ✅"
                    listener.stop()
                else:
                    perm_status["Accessibility"] = "Denied ❌"
            except Exception as e:
                perm_status["Accessibility"] = f"Error: {str(e)} ❌"
        
        # Check microphone permissions if pyaudio is available
        if AUDIO_AVAILABLE:
            try:
                audio = pyaudio.PyAudio()
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024
                )
                stream.read(1024)
                stream.stop_stream()
                stream.close()
                audio.terminate()
                perm_status["Microphone"] = "Granted ✅"
            except Exception as e:
                perm_status["Microphone"] = f"Error: {str(e)} ❌"
        
        logging.info("Permission Status:")
        for perm, status in perm_status.items():
            logging.info(f"  - {perm}: {status}")
        
        return perm_status
    
    def test_shortcuts_method_1(self):
        """Test keyboard shortcuts using direct pynput approach (as in keyboard_test_2.py)"""
        if not PYNPUT_AVAILABLE:
            logging.error("pynput not available, cannot test shortcuts")
            return False
        
        logging.info("Testing keyboard shortcuts using Method 1 (direct tracking)...")
        
        # Reset variables
        self.alt_r_pressed = False
        self.enter_pressed = False
        self.shortcut_detected = False
        
        # Define callbacks
        def on_press(key):
            try:
                # Track specific keys
                if key == keyboard.Key.alt_r:
                    self.alt_r_pressed = True
                    logging.debug("Right Alt pressed")
                elif key == keyboard.Key.enter:
                    self.enter_pressed = True
                    logging.debug("Enter pressed")
                
                # Check for shortcut
                if self.alt_r_pressed and self.enter_pressed:
                    logging.info("Keyboard shortcut detected (Method 1)")
                    self.shortcut_detected = True
            except Exception as e:
                logging.error(f"Error in on_press: {str(e)}")
        
        def on_release(key):
            try:
                # Reset key state when released
                if key == keyboard.Key.alt_r:
                    self.alt_r_pressed = False
                    logging.debug("Right Alt released")
                elif key == keyboard.Key.enter:
                    self.enter_pressed = False
                    logging.debug("Enter released")
            except Exception as e:
                logging.error(f"Error in on_release: {str(e)}")
        
        # Set up listener
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        listener.start()
        
        # Wait for shortcut or timeout
        logging.info("Press Right Option + Enter to test shortcut detection")
        timeout = 10
        start_time = time.time()
        while not self.shortcut_detected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        # Clean up
        listener.stop()
        listener.join()
        
        # Report results
        if self.shortcut_detected:
            logging.info("✅ Shortcut detected successfully using Method 1")
        else:
            logging.info("❌ Shortcut not detected using Method 1 (timed out)")
        
        return self.shortcut_detected
    
    def test_shortcuts_method_2(self):
        """Test keyboard shortcuts using set tracking approach (as in keyboard_test_4.py)"""
        if not PYNPUT_AVAILABLE:
            logging.error("pynput not available, cannot test shortcuts")
            return False
        
        logging.info("Testing keyboard shortcuts using Method 2 (set tracking)...")
        
        # Reset variables
        self.keys_pressed = set()
        self.shortcut_detected = False
        
        # Define callbacks
        def on_press(key):
            try:
                # Add key to the set of pressed keys
                self.keys_pressed.add(key)
                logging.debug(f"Key pressed: {key}, total keys: {len(self.keys_pressed)}")
                
                # Check for our specific shortcut
                if (keyboard.Key.alt_r in self.keys_pressed and 
                    keyboard.Key.enter in self.keys_pressed):
                    logging.info("Keyboard shortcut detected (Method 2)")
                    self.shortcut_detected = True
            except Exception as e:
                logging.error(f"Error in on_press: {str(e)}")
        
        def on_release(key):
            try:
                # Remove key from the set of pressed keys
                if key in self.keys_pressed:
                    self.keys_pressed.remove(key)
                    logging.debug(f"Key released: {key}, remaining keys: {len(self.keys_pressed)}")
            except Exception as e:
                logging.error(f"Error in on_release: {str(e)}")
        
        # Set up listener
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        listener.start()
        
        # Wait for shortcut or timeout
        logging.info("Press Right Option + Enter to test shortcut detection")
        timeout = 10
        start_time = time.time()
        while not self.shortcut_detected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        # Clean up
        listener.stop()
        listener.join()
        
        # Report results
        if self.shortcut_detected:
            logging.info("✅ Shortcut detected successfully using Method 2")
        else:
            logging.info("❌ Shortcut not detected using Method 2 (timed out)")
        
        return self.shortcut_detected
    
    def test_shortcuts_method_3(self):
        """Test keyboard shortcuts using threading approach (as in keyboard_test_6.py)"""
        if not PYNPUT_AVAILABLE:
            logging.error("pynput not available, cannot test shortcuts")
            return False
        
        logging.info("Testing keyboard shortcuts using Method 3 (threading approach)...")
        
        # Reset variables
        self.keys_pressed = set()
        self.shortcut_detected = False
        self.toggle_lock = threading.Lock()
        
        # Define callbacks
        def on_press(key):
            try:
                # Add key to the set of pressed keys
                self.keys_pressed.add(key)
                
                # Check for our specific shortcut
                if (keyboard.Key.alt_r in self.keys_pressed and 
                    keyboard.Key.enter in self.keys_pressed):
                    
                    # Try to acquire the lock (non-blocking)
                    if not self.toggle_lock.locked():
                        logging.info("Keyboard shortcut detected (Method 3)")
                        
                        # Use a separate thread with the lock to prevent multiple executions
                        def do_toggle_with_lock():
                            with self.toggle_lock:
                                # Mark as detected
                                self.shortcut_detected = True
                                # Sleep to allow for keys to be released
                                time.sleep(1.0)
                        
                        thread = threading.Thread(target=do_toggle_with_lock)
                        thread.daemon = True
                        thread.start()
            except Exception as e:
                logging.error(f"Error in on_press: {str(e)}")
        
        def on_release(key):
            try:
                # Remove key from the set of pressed keys
                if key in self.keys_pressed:
                    self.keys_pressed.remove(key)
            except Exception as e:
                logging.error(f"Error in on_release: {str(e)}")
        
        # Set up listener
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        listener.start()
        
        # Wait for shortcut or timeout
        logging.info("Press Right Option + Enter to test shortcut detection")
        timeout = 10
        start_time = time.time()
        while not self.shortcut_detected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        # Clean up
        listener.stop()
        listener.join()
        
        # Report results
        if self.shortcut_detected:
            logging.info("✅ Shortcut detected successfully using Method 3")
        else:
            logging.info("❌ Shortcut not detected using Method 3 (timed out)")
        
        return self.shortcut_detected
    
    def test_shortcuts_method_4(self):
        """Test keyboard shortcuts using AppleScript approach (as in whisper_typer.py)"""
        logging.info("Testing keyboard shortcuts using Method 4 (AppleScript approach)...")
        
        # Create a temporary AppleScript file
        script_path = os.path.expanduser("~/whisper_debug_hotkey.scpt")
        detected_file = os.path.expanduser("~/whisper_debug_detected.txt")
        
        # Delete the detected file if it exists
        if os.path.exists(detected_file):
            os.remove(detected_file)
        
        # AppleScript to listen for our shortcut and write to a file when detected
        applescript = f"""
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
                            do shell script "echo Detected > {detected_file}"
                            exit repeat
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
        
        # Run the AppleScript in the background
        process = subprocess.Popen(
            ["osascript", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for shortcut detection or timeout
        logging.info("Press Right Option + Enter to test shortcut detection")
        timeout = 10
        start_time = time.time()
        shortcut_detected = False
        
        try:
            while not shortcut_detected and time.time() - start_time < timeout:
                if os.path.exists(detected_file):
                    shortcut_detected = True
                time.sleep(0.1)
        finally:
            # Kill the AppleScript process
            process.terminate()
            
            # Clean up temporary files
            if os.path.exists(script_path):
                os.remove(script_path)
            
            if os.path.exists(detected_file):
                os.remove(detected_file)
        
        # Report results
        if shortcut_detected:
            logging.info("✅ Shortcut detected successfully using Method 4")
        else:
            logging.info("❌ Shortcut not detected using Method 4 (timed out)")
        
        return shortcut_detected
    
    def check_paths(self):
        """Check path resolution and environment variables"""
        logging.info("Checking path resolution and environment variables...")
        
        # Get current working directory
        cwd = os.getcwd()
        logging.info(f"Current working directory: {cwd}")
        
        # Get executable path
        executable_path = os.path.abspath(sys.argv[0])
        logging.info(f"Executable path: {executable_path}")
        
        # Check if we're inside an app bundle
        in_app_bundle = '.app/Contents/MacOS' in executable_path
        logging.info(f"In app bundle: {in_app_bundle}")
        
        # Get app bundle path if applicable
        app_bundle_path = None
        if in_app_bundle:
            app_bundle_path = executable_path.split('.app/Contents/MacOS')[0] + '.app'
            logging.info(f"App bundle path: {app_bundle_path}")
        
        # Get resource path if applicable
        resource_path = None
        if in_app_bundle:
            resource_path = os.path.join(app_bundle_path, 'Contents', 'Resources')
            logging.info(f"Resource path: {resource_path}")
            
            # Check if the resource path exists
            if os.path.exists(resource_path):
                logging.info(f"Resource path exists: Yes")
                # List files in resource path
                logging.info("Files in resource path:")
                for file in os.listdir(resource_path):
                    logging.info(f"  - {file}")
            else:
                logging.info(f"Resource path exists: No")
        
        # Get temp directory
        temp_dir = tempfile.gettempdir()
        logging.info(f"Temp directory: {temp_dir}")
        
        # Get home directory
        home_dir = os.path.expanduser('~')
        logging.info(f"Home directory: {home_dir}")
        
        # Check if whisper_typer.log exists
        log_path = os.path.expanduser("~/whisper_typer.log")
        log_exists = os.path.exists(log_path)
        logging.info(f"whisper_typer.log exists: {log_exists}")
        
        # Check environment variables
        logging.info("Environment variables:")
        for var in [
            'PATH', 'PYTHONPATH', 'DYLD_LIBRARY_PATH', 'HOME', 'USER',
            'PWD', 'SHELL', 'TERM', 'TERM_PROGRAM'
        ]:
            if var in os.environ:
                value = os.environ[var]
                # Truncate long values
                if len(value) > 100:
                    value = value[:97] + '...'
                logging.info(f"  - {var}: {value}")
            else:
                logging.info(f"  - {var}: Not set")
        
        # Check if we're running as a menu bar app (no dock icon)
        is_menu_bar_app = False
        if in_app_bundle:
            # Check Info.plist for LSUIElement
            plist_path = os.path.join(app_bundle_path, 'Contents', 'Info.plist')
            if os.path.exists(plist_path):
                try:
                    with open(plist_path, 'r') as f:
                        plist_content = f.read()
                        if '<key>LSUIElement</key>' in plist_content and '<true/>' in plist_content:
                            is_menu_bar_app = True
                except:
                    pass
        
        logging.info(f"Running as menu bar app (no dock icon): {is_menu_bar_app}")
        
        # Return results
        return {
            "cwd": cwd,
            "executable_path": executable_path,
            "in_app_bundle": in_app_bundle,
            "app_bundle_path": app_bundle_path,
            "resource_path": resource_path,
            "temp_dir": temp_dir,
            "home_dir": home_dir,
            "log_exists": log_exists,
            "is_menu_bar_app": is_menu_bar_app
        }
    
    def run_rumps_test(self):
        """Test rumps functionality"""
        if not RUMPS_AVAILABLE:
            logging.error("rumps not available, cannot test menu bar app")
            return False
        
        logging.info("Testing rumps menu bar app functionality...")
        
        # Create a simple rumps app
        class TestApp(rumps.App):
            def __init__(self):
                super(TestApp, self).__init__("TestApp", "T")
                self.menu = [
                    rumps.MenuItem("Test", callback=self.test_callback),
                    None,
                    rumps.MenuItem("Quit", callback=rumps.quit_application)
                ]
            
            def test_callback(self, _):
                logging.info("Test menu item clicked")
                rumps.notification("TestApp", "Test", "Menu item clicked")
        
        # Run the app for a short time
        logging.info("Starting rumps test app (will quit after 3 seconds)")
        app = TestApp()
        
        # Quit after 3 seconds
        def quit_after_delay():
            time.sleep(3)
            rumps.quit_application()
        
        thread = threading.Thread(target=quit_after_delay)
        thread.daemon = True
        thread.start()
        
        try:
            app.run()
            logging.info("Rumps test app ran successfully")
            return True
        except Exception as e:
            logging.error(f"Error running rumps test app: {str(e)}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="WhisperTyper Debug Tool")
    parser.add_argument("--check-permissions", action="store_true", help="Check app permissions")
    parser.add_argument("--test-shortcuts", action="store_true", help="Test keyboard shortcuts")
    parser.add_argument("--check-paths", action="store_true", help="Check path resolution")
    parser.add_argument("--test-rumps", action="store_true", help="Test rumps functionality")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # If no args, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Create debug helper
    helper = DebugHelper()
    
    # Run tests based on args
    if args.check_permissions or args.test_all:
        helper.check_permissions()
        print()
    
    if args.test_shortcuts or args.test_all:
        print("\n=== Testing Keyboard Shortcuts ===\n")
        print("Please press Right Option + Enter when prompted for each test method.")
        
        # Test each method
        helper.test_shortcuts_method_1()
        print()
        helper.test_shortcuts_method_2()
        print()
        helper.test_shortcuts_method_3()
        print()
        helper.test_shortcuts_method_4()
        print()
    
    if args.check_paths or args.test_all:
        helper.check_paths()
        print()
    
    if args.test_rumps or args.test_all:
        helper.run_rumps_test()
        print()
    
    logging.info("Debug tests completed. See ~/whispertyper_debug.log for full details.")
    print("\nDebug tests completed. See ~/whispertyper_debug.log for full details.")

if __name__ == "__main__":
    main()