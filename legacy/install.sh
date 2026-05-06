#!/bin/bash
# install.sh
# Installs Simple Productivity Blocker on Linux

echo "Welcome to the Simple Productivity Blocker Installer!"
echo "-----------------------------------------------------"

if [ "$EUID" -ne 0 ]; then
  echo "Administrator privileges required. Please run with sudo: sudo ./install.sh"
  exit 1
fi

DEST_DIR="/opt/simple-productivity-blocker"
echo "Installing to $DEST_DIR..."

mkdir -p "$DEST_DIR"
cp -r * "$DEST_DIR/"

# Create desktop entry
DESKTOP_FILE="/usr/share/applications/simple-productivity-blocker.desktop"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Simple Productivity Blocker
Comment=Block distracting apps and websites
Exec=$DEST_DIR/spb
Terminal=false
Type=Application
Categories=Utility;
EOF

chmod +x "$DEST_DIR/spb"
chmod +x "$DEST_DIR/daemon"
chmod +x "$DESKTOP_FILE"

echo "Installation Complete!"
echo "You can now run 'Simple Productivity Blocker' from your application menu."
