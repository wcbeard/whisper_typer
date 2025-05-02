# WhisperTyper Makefile
# Automates the build and packaging process for the macOS app

.PHONY: clean build dev install sign dist

# Default target
all: build

# Install dependencies
install:
	brew install portaudio
	pip install -r requirements.txt
	pip install py2app

# Development (alias) mode - for quick testing
dev:
	mkdir -p build
	mkdir -p build/resources
	cp src/whisper_typer.py build/whisper_typer.py
	cp src/keyboard_handler.py build/
	cp packaging/setup.py build/
	cp resources/app.icns build/resources/
	cd build && python setup.py py2app -A

# Production build
build: clean
	# Create build directory
	mkdir -p build
	mkdir -p build/resources
	# Copy resources
	cp -R resources/* build/resources/
	# Copy source files
	cp src/whisper_typer.py build/whisper_typer.py
	cp src/keyboard_handler.py build/
	# Copy setup.py
	cp packaging/setup.py build/
	# Move to build dir and run py2app
	cd build && python setup.py py2app

# Clean build artifacts
clean:
	rm -rf build dist *.egg-info
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Run the development app
run-dev:
	./dist/WhisperTyper.app/Contents/MacOS/WhisperTyper

# Sign the app with your developer ID (optional)
sign:
	codesign --force --deep --sign "Developer ID Application: YOUR_NAME_HERE" dist/WhisperTyper.app

# Package for distribution (creates a DMG)
dist: build
	# Create a folder for DMG contents
	mkdir -p dist/dmg
	# Copy app to DMG folder
	cp -R dist/WhisperTyper.app dist/dmg/
	# Create symbolic link to Applications folder
	ln -s /Applications dist/dmg/
	# Create DMG
	hdiutil create -volname "WhisperTyper" -srcfolder dist/dmg -ov -format UDZO dist/WhisperTyper.dmg
	# Clean up
	rm -rf dist/dmg