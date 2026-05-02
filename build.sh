#!/bin/bash
# build.sh
# Requires PyInstaller to be installed (pip install pyinstaller)

echo "Building Simple Productivity Blocker for Linux..."

# Clean previous builds
rm -rf dist build

# Build the main app
echo "Building spb..."
pyinstaller --noconfirm --onedir --windowed --name "spb" main.py

# Build the daemon
echo "Building daemon..."
pyinstaller --noconfirm --onedir --console --name "daemon" daemon.py

# Copy daemon into main app directory
cp dist/daemon/daemon dist/spb/

echo "Build complete! Your deployable package is in dist/spb"
echo "Distribute the 'dist/spb' folder. Users can run 'install.sh' to install it."
