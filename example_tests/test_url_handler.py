#!/usr/bin/env python3
"""
Test script for registering URL handlers on macOS.
This script tests different methods to register a custom URL scheme.
"""

import os
import sys
import subprocess
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_method_1(app_path):
    """Method 1: Using defaults with dictionary syntax"""
    logging.info("Testing Method 1: defaults with dictionary syntax")
    
    cmd = [
        "defaults", "write", "com.apple.LaunchServices", "LSHandlers",
        "-array-add",
        f'{{"LSHandlerURLScheme":"whispertyper","LSHandlerRole":"Editor","LSHandlerPath":"{app_path}"}}'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Method 1 SUCCESS")
        return True
    else:
        logging.error(f"Method 1 FAILED: {result.stderr}")
        return False

def test_method_2(app_path):
    """Method 2: Using defaults with single quotes"""
    logging.info("Testing Method 2: defaults with single quotes")
    
    cmd = [
        "defaults", "write", "com.apple.LaunchServices", "LSHandlers",
        "-array-add",
        f"'LSHandlerURLScheme'='whispertyper';'LSHandlerRole'='Editor';'LSHandlerPath'='{app_path}'"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Method 2 SUCCESS")
        return True
    else:
        logging.error(f"Method 2 FAILED: {result.stderr}")
        return False

def test_method_3(app_path):
    """Method 3: Using AppleScript"""
    logging.info("Testing Method 3: Using AppleScript")
    
    # Escape any single quotes in the path
    escaped_path = app_path.replace("'", "'\\''")
    
    # Create an AppleScript to register the URL handler
    applescript = f"""
    tell application "System Events"
        tell property list file "/Users/$USER/Library/Preferences/com.apple.LaunchServices.plist"
            set theList to make new property list item at end of property list items with properties {{value:{{}}}}
            tell theList
                make new property list item at end with properties {{key:"LSHandlerURLScheme", value:"whispertyper"}}
                make new property list item at end with properties {{key:"LSHandlerRole", value:"Editor"}}
                make new property list item at end with properties {{key:"LSHandlerPath", value:"{escaped_path}"}}
            end tell
        end tell
    end tell
    """
    
    # Write to temporary file
    with open("/tmp/register_url.scpt", "w") as f:
        f.write(applescript)
    
    # Execute
    result = subprocess.run(["osascript", "/tmp/register_url.scpt"], capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Method 3 SUCCESS")
        return True
    else:
        logging.error(f"Method 3 FAILED: {result.stderr}")
        return False

def test_method_4(app_path):
    """Method 4: Direct plist modification with PlistBuddy"""
    logging.info("Testing Method 4: Using PlistBuddy")
    
    # Create a temporary plist file with our handler
    temp_plist = "/tmp/whispertyper_handler.plist"
    
    # Create commands for PlistBuddy
    commands = [
        f"Add :LSHandlerURLScheme string whispertyper",
        f"Add :LSHandlerRole string Editor",
        f"Add :LSHandlerPath string {app_path}"
    ]
    
    # Write commands to a file
    with open("/tmp/plistbuddy_commands.txt", "w") as f:
        f.write("\n".join(commands))
    
    # Create the plist
    create_result = subprocess.run(
        ["/usr/libexec/PlistBuddy", "-c", "Save", temp_plist],
        capture_output=True, text=True
    )
    
    # Execute the commands
    for cmd in commands:
        cmd_result = subprocess.run(
            ["/usr/libexec/PlistBuddy", "-c", cmd, temp_plist],
            capture_output=True, text=True
        )
        if cmd_result.returncode != 0:
            logging.error(f"PlistBuddy command failed: {cmd_result.stderr}")
    
    # Now try to add this to the LSHandlers array
    add_result = subprocess.run(
        ["defaults", "write", "com.apple.LaunchServices", "LSHandlers", "-array-add", f"$(cat {temp_plist})"],
        shell=True, capture_output=True, text=True
    )
    
    if add_result.returncode == 0:
        logging.info("Method 4 SUCCESS")
        return True
    else:
        logging.error(f"Method 4 FAILED: {add_result.stderr}")
        return False

def verify_registration():
    """Verify if the URL handler is registered"""
    logging.info("Verifying URL handler registration")
    
    result = subprocess.run(
        ["defaults", "read", "com.apple.LaunchServices", "LSHandlers"],
        capture_output=True, text=True
    )
    
    if "whispertyper" in result.stdout:
        logging.info("Verification SUCCESS: URL handler is registered")
        return True
    else:
        logging.warning("Verification FAILED: URL handler not found in registry")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test URL handler registration methods")
    parser.add_argument("--app-path", default=sys.argv[0], help="Path to the application executable")
    parser.add_argument("--method", type=int, choices=[1, 2, 3, 4], help="Specific method to test (1-4)")
    args = parser.parse_args()
    
    app_path = os.path.abspath(args.app_path)
    logging.info(f"Using application path: {app_path}")
    
    success = False
    
    if args.method:
        # Test specific method
        if args.method == 1:
            success = test_method_1(app_path)
        elif args.method == 2:
            success = test_method_2(app_path)
        elif args.method == 3:
            success = test_method_3(app_path)
        elif args.method == 4:
            success = test_method_4(app_path)
    else:
        # Try all methods in sequence until one succeeds
        methods = [test_method_1, test_method_2, test_method_3, test_method_4]
        for i, method in enumerate(methods, 1):
            logging.info(f"Trying method {i} of {len(methods)}")
            if method(app_path):
                success = True
                break
    
    # Verify registration
    if success:
        verify_registration()
    
    logging.info("Test completed")