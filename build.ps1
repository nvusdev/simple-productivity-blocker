# build.ps1
# Requires PyInstaller to be installed (pip install pyinstaller)

Write-Host "Building Simple Productivity Blocker for Windows..."

# Clean previous builds
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Build the main app
Write-Host "Building spb.exe..."
python -m PyInstaller --noconfirm --onedir --windowed --icon="icon.ico" --name "spb" main.py

# Build the daemon
Write-Host "Building daemon.exe..."
python -m PyInstaller --noconfirm --onedir --console --name "daemon" daemon.py

# Copy daemon into main app directory
Copy-Item "dist\daemon\daemon.exe" -Destination "dist\spb\"

# Build the installer
Write-Host "Building spb_installer.exe..."
python -m PyInstaller --noconfirm --onefile --console --icon="icon.ico" --name "spb_installer" spb_installer.py

# Move installer to the package directory
Copy-Item "dist\spb_installer.exe" -Destination "dist\spb\"

Write-Host "Build complete! Your deployable package is in dist\spb"
Write-Host "Zip the 'dist\spb' folder to distribute it to users."
