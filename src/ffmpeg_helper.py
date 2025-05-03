"""
ffmpeg_helper.py - Ensures FFmpeg is available for WhisperTyper

This module provides functions to:
1. Find an existing FFmpeg installation
2. Install FFmpeg inside the app bundle if needed
3. Configure Whisper to use the correct FFmpeg path
"""

import os
import sys
import subprocess
import logging
import shutil
import whisper

def get_bundle_path():
    """Get the path to the app bundle resources directory"""
    if getattr(sys, 'frozen', False):
        # Running as a bundled app
        bundle_dir = os.path.dirname(sys.executable)
        # Navigate up to the Resources directory
        # For a macOS app, the structure is: App.app/Contents/MacOS/executable
        resources_dir = os.path.abspath(os.path.join(bundle_dir, '..', 'Resources'))
        return resources_dir
    else:
        # Running in development mode
        return os.path.dirname(os.path.abspath(__file__))

def find_ffmpeg():
    """Find ffmpeg executable, looking in multiple locations"""
    logging.info("Searching for FFmpeg...")
    
    # 1. First check if ffmpeg exists in the standard PATH
    try:
        result = subprocess.run(
            ["which", "ffmpeg"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            ffmpeg_path = result.stdout.strip()
            logging.info(f"Found FFmpeg in PATH: {ffmpeg_path}")
            return ffmpeg_path
    except Exception as e:
        logging.warning(f"Error checking for FFmpeg in PATH: {e}")
    
    # 2. Check in the app bundle resources directory
    bundle_ffmpeg = os.path.join(get_bundle_path(), "ffmpeg")
    if os.path.exists(bundle_ffmpeg) and os.access(bundle_ffmpeg, os.X_OK):
        logging.info(f"Found FFmpeg in bundle: {bundle_ffmpeg}")
        return bundle_ffmpeg
    
    # 3. Check common installation locations on macOS
    common_locations = [
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/bin/ffmpeg"
    ]
    
    for location in common_locations:
        if os.path.exists(location) and os.access(location, os.X_OK):
            logging.info(f"Found FFmpeg at: {location}")
            return location
    
    logging.warning("FFmpeg not found in any standard location")
    return None

def install_ffmpeg_in_bundle():
    """Install FFmpeg in the app bundle if possible"""
    logging.info("Attempting to install FFmpeg in bundle...")
    bundle_dir = get_bundle_path()
    bundle_ffmpeg = os.path.join(bundle_dir, "ffmpeg")
    
    # First try to find FFmpeg in the system
    system_ffmpeg = None
    try:
        result = subprocess.run(
            ["which", "ffmpeg"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        if result.returncode == 0:
            system_ffmpeg = result.stdout.strip()
    except Exception as e:
        logging.warning(f"Error finding system FFmpeg: {e}")
    
    if system_ffmpeg and os.path.exists(system_ffmpeg):
        try:
            # Copy FFmpeg to the bundle
            shutil.copy2(system_ffmpeg, bundle_ffmpeg)
            # Make it executable
            os.chmod(bundle_ffmpeg, 0o755)
            logging.info(f"Copied FFmpeg from {system_ffmpeg} to {bundle_ffmpeg}")
            return bundle_ffmpeg
        except Exception as e:
            logging.error(f"Failed to copy FFmpeg to bundle: {e}")
    else:
        logging.warning("No system FFmpeg found to copy")
    
    # If we failed to copy from system, we could potentially download it here
    # but that's beyond the scope of this example
    
    return None

def configure_whisper_ffmpeg():
    """Configure Whisper to use the correct FFmpeg path"""
    # First try to find an existing FFmpeg
    ffmpeg_path = find_ffmpeg()
    
    # If not found, try to install it in the bundle
    if not ffmpeg_path:
        ffmpeg_path = install_ffmpeg_in_bundle()
    
    if ffmpeg_path:
        # Configure environment variable for Whisper
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        
        # Patch the whisper module to use our FFmpeg path
        # This is a hack but necessary because Whisper hardcodes "ffmpeg" in some places
        try:
            # Check which attribute contains the FFmpeg command
            if hasattr(whisper, "_FFMPEG_COMMAND"):
                whisper._FFMPEG_COMMAND = ffmpeg_path
            
            # For newer whisper versions
            if hasattr(whisper, "audio") and hasattr(whisper.audio, "FFMPEG_COMMAND"):
                whisper.audio.FFMPEG_COMMAND = ffmpeg_path
            
            logging.info(f"Configured Whisper to use FFmpeg at: {ffmpeg_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to patch Whisper FFmpeg path: {e}")
    
    logging.error("Failed to configure FFmpeg for Whisper")
    return False

def update_sys_path():
    """Add common FFmpeg locations to the system PATH"""
    common_paths = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        get_bundle_path()
    ]
    
    for path in common_paths:
        if path not in os.environ["PATH"] and os.path.exists(path):
            os.environ["PATH"] = f"{path}:{os.environ['PATH']}"
    
    logging.info(f"Updated PATH: {os.environ['PATH']}")

def ensure_ffmpeg_available():
    """Main entry point to ensure FFmpeg is available for Whisper"""
    logging.info("Ensuring FFmpeg is available...")
    
    # Update system PATH first
    update_sys_path()
    
    # Configure Whisper to use our FFmpeg
    success = configure_whisper_ffmpeg()
    
    if not success:
        logging.warning("Failed to configure FFmpeg. Whisper might not work properly.")
        return False
    
    # Verify FFmpeg works by running a simple command
    try:
        ffmpeg_path = os.environ.get("FFMPEG_BINARY", "ffmpeg")
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            logging.info(f"FFmpeg verification successful: {result.stdout.splitlines()[0]}")
            return True
        else:
            logging.error(f"FFmpeg verification failed: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"Error verifying FFmpeg: {e}")
        return False

if __name__ == "__main__":
    # Configure simple logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Test the module
    success = ensure_ffmpeg_available()
    print(f"FFmpeg configuration {'successful' if success else 'failed'}")