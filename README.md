# WhisperTyper

WhisperTyper is a macOS menu bar application that enables speech-to-text transcription using OpenAI's Whisper model. It allows you to quickly record audio and have it transcribed to text, which is then automatically typed into your active application.

## Features

- Lives in your macOS menu bar for easy access
- Toggle recording with a keyboard shortcut (Right Option + Enter)
- Transcribes speech using OpenAI's Whisper model
- Automatically types the transcribed text into your active application
- Multiple Whisper model options (tiny, base, small) for speed vs. accuracy tradeoffs
- Visual feedback through menu bar icon changes

## Requirements

- macOS 10.14 or later
- Python 3.7+
- OpenAI Whisper
- PyAudio
- rumps
- pynput
- pyperclip

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/whisper-typer.git
cd whisper-typer
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

To run the application directly:

```bash
python whisper_typer.py
```

## Building a Standalone Application

To build a standalone macOS application:

```bash
python setup.py py2app
```

This will create a standalone application in the `dist` folder.

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

## Troubleshooting

If you encounter any issues:

1. Check the log file at `~/whisper_typer.log` for error messages
2. Ensure your microphone is working correctly
3. Make sure you have the necessary permissions for microphone access
4. Verify that Whisper and PyAudio are properly installed

## Project Structure

- `whisper_typer.py`: Main application
- `keyboard_handler.py`: Handles keyboard shortcuts reliably
- `setup.py`: Configuration for building standalone application

## Known Issues

- First-time Whisper model loading may take some time
- Very noisy environments may affect transcription quality
- The keyboard shortcut might not work in all applications

## License

[MIT License](LICENSE)

## Acknowledgments

- [OpenAI's Whisper](https://github.com/openai/whisper)
- [rumps](https://github.com/jaredks/rumps)
- [pynput](https://github.com/moses-palmer/pynput)