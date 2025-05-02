# Known Issues

This document tracks current known issues with WhisperTyper and their workarounds.

## Launch Method Compatibility

| Launch Method | Status | Notes |
|---------------|--------|-------|
| `build/dist/WhisperTyper.app/Contents/MacOS/WhisperTyper` | ✅ Working | Launch directly from Terminal |
| `python src/whisper_typer.py` | ✅ Working | Direct Python execution |
| `open build/dist/WhisperTyper.app` | ❌ Not Working | Launching via Finder or `open` command fails |

### Workaround
Until this issue is fixed, use one of the following methods to launch the application:

```bash
# Method 1: Launch directly from Terminal
./build/dist/WhisperTyper.app/Contents/MacOS/WhisperTyper

# Method 2: Create an alias in your .zshrc or .bashrc
echo 'alias whispertyper="~/path/to/build/dist/WhisperTyper.app/Contents/MacOS/WhisperTyper"' >> ~/.zshrc
source ~/.zshrc
```

## Suspected Causes and Investigation

Several potential issues might be causing the app to fail when launched via Finder:

1. **Accessibility Permissions**:
   - When launched through Terminal, macOS might handle permissions differently
   - Check System Preferences → Security & Privacy → Privacy → Accessibility
   - Make sure WhisperTyper.app is in the list and checked

2. **URL Scheme Registration**:
   - The URL handler registration might fail when launched through Finder
   - The code at lines 384-402 in whisper_typer.py attempts to register a URL scheme

3. **Path Resolution**:
   - Resource paths might resolve differently when launched via Finder vs Terminal
   - Check for hardcoded paths that might need to be relative to the app bundle

4. **Environment Variables**:
   - Terminal might provide environment variables that Finder doesn't

## Debug Strategy

To investigate further, implement enhanced logging:

1. Add log output for app launch method detection
2. Check permissions status on startup
3. Verify URL scheme registration status
4. Test keyboard shortcut handler with different launch methods

### Debug Code

A debugging helper has been added to the repository that can be used to test different aspects of the application's functionality. Run it with:

```bash
python src/debug_whispertyper.py --check-permissions
python src/debug_whispertyper.py --test-shortcuts
python src/debug_whispertyper.py --check-paths
```

### Latest Findings

- When launched via Finder, the app may not be receiving keyboard events correctly
- The KeyboardShortcutHandler class seems to work more reliably than the previous implementations
- The threading approach in keyboard_test_6.py shows the most promise for fixing the issue