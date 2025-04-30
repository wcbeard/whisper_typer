# WhisperTyper

WhisperTyper is a macOS menu bar application that enables speech-to-text transcription using OpenAI's Whisper model. It allows you to quickly record audio and have it transcribed to text, which is then automatically typed into your active application.

## Features

- Lives in your macOS menu bar for easy access
- Toggle recording with a keyboard shortcut (Right Option + Enter)
- Transcribes speech using OpenAI's Whisper model
- Automatically types the transcribed text into your active application
- Multiple Whisper model options (tiny, base, small) for speed vs. accuracy tradeoffs
- Visual feedback through menu bar icon changes

## Project Structure

The project is organized to keep source code separate from build artifacts:

```
whisper_typer/
├── src/                   # Source code
│   ├── whisper_typer_final.py
│   └── keyboard_handler.py
├── packaging/             # Build configuration
│   └── setup.py
├── build/                 # Temporary build files (generated)
├── dist/                  # Distribution files (generated)
│   └── WhisperTyper.app/
├── Makefile               # Build automation
└── requirements.txt       # Python dependencies
```

## Requirements

- macOS 10.14 or later
- Python 3.7+ (Python 3.9 recommended)
- OpenAI Whisper
- PyAudio
- rumps
- pynput
- pyperclip

## Building the Application

This project uses `make` to automate the build process.

### Prerequisites

1. Ensure you have the following installed:
   - macOS 10.14 or later
   - Python 3.7 or later
   - pip
   - make

2. Clone the repository:
```bash
git clone https://github.com/wcbeard/whisper_typer.git
cd whisper_typer
```

### Setup

1. Create the required directories (if they don't exist):
```bash
mkdir -p src packaging build dist
```

2. Install dependencies:
```bash
make install
```

### Development Build

For quick testing during development, use:
```bash
make dev
```

This creates an "alias" build that links to your source files instead of copying them. Changes to your source files will be immediately reflected without rebuilding.

### Production Build

To create a standalone application:
```bash
make build
```

This will:
1. Clean previous build artifacts
2. Copy source files to the build directory
3. Run py2app to create the application bundle
4. Place the built app in the `dist/` directory

### Running the Application

After building, you can run the application:
- Directly from Finder: Navigate to `dist/WhisperTyper.app` and double-click
- From the command line: `open dist/WhisperTyper.app`
- For development: `make run-dev`

### Distribution

To create a distributable DMG file:
```bash
make dist
```

This will create `dist/WhisperTyper.dmg` which can be shared with others.

### Code Signing (Optional)

If you have an Apple Developer ID, you can sign the application:
```bash
# Edit the Makefile first to add your Developer ID
make sign
```

## Troubleshooting Build Issues

If you encounter build errors with py2app, especially recursion errors:

1. **Check the setup.py file**: The provided setup.py includes an increased recursion limit and carefully manages dependencies to avoid packaging issues.

2. **Use development mode for testing**: If you still can't build a standalone app, try using development mode (`make dev`) which is more reliable but requires Python to be installed on the user's system.

3. **Simplified test builds**: The repository includes a simplified version of the app (`src/whisper_typer_simplified_fixed.py`) that can be used to test packaging without the complex Whisper dependencies.

4. **Clean build directory**: Always try running `make clean` before building if you encounter errors.

## Usage

1. Click the "W" icon in the menu bar or press Right Option + Enter to start recording
2. Speak clearly into your microphone
3. Click the icon again or press the keyboard shortcut to stop recording
4. Wait for the transcription to complete
5. The transcribed text will be automatically typed into your active application

## Whisper Model Selection

You can choose between different Whisper models based on your needs:

- **Tiny**: Fastest, but less accurate
- **Base**: Balanced speed and accuracy
- **Small**: More accurate, but slower

## Known Issues

- First-time Whisper model loading may take some time
- Very noisy environments may affect transcription quality
- Some keyboard shortcuts might not work in all applications
- Complex Python dependencies can cause packaging issues

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request