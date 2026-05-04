# build.ps1
# Requires PyInstaller to be installed (pip install pyinstaller)

Write-Host "Building Simple Productivity Blocker for Windows..."

# Clean previous builds
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Prepare icon from newlogo.png
$iconPng = Join-Path $PSScriptRoot "newlogo.png"
$tempIco = Join-Path $PSScriptRoot "newlogo_temp.ico"
$scriptPath = Join-Path $env:TEMP "spb_icon_convert.py"

if (-not (Test-Path $iconPng)) {
    Write-Host "Missing newlogo.png in the project root."
    exit 1
}

$py = @"
import sys
from PIL import Image

png = r"$iconPng"
ico = r"$tempIco"

try:
    img = Image.open(png)
    img.save(ico)
except Exception as e:
    print(f"Icon conversion failed: {e}")
    sys.exit(1)
"@

Set-Content -Path $scriptPath -Value $py -Encoding ASCII
python $scriptPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Build the main app
Write-Host "Building spb.exe..."
python -m PyInstaller --noconfirm --onedir --windowed --uac-admin --icon="$tempIco" --name "spb" main.py

# Build the daemon
Write-Host "Building daemon.exe..."
python -m PyInstaller --noconfirm --onedir --windowed --name "daemon" daemon.py

# Copy daemon into main app directory
Copy-Item "dist\daemon\daemon.exe" -Destination "dist\spb\"

# Copy newlogo.png into the app directory
Copy-Item $iconPng -Destination "dist\spb\"

# Build the installer
Write-Host "Building spb_installer.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" --name "spb_installer" spb_installer.py

# Move installer to the package directory
Copy-Item "dist\spb_installer.exe" -Destination "dist\spb\"

# Build the uninstaller
Write-Host "Building spb_uninstaller.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" --name "spb_uninstaller" spb_uninstaller.py

# Move uninstaller to the package directory
Copy-Item "dist\spb_uninstaller.exe" -Destination "dist\spb\"

# Copy CHANGELOG.md
if (Test-Path "CHANGELOG.md") {
    Copy-Item "CHANGELOG.md" -Destination "dist\spb\"
}

Write-Host "Build complete! Your deployable package is in dist\spb"
Write-Host "Zip the 'dist\spb' folder to distribute it to users."

# Cleanup temporary icon conversion artifacts
if (Test-Path $tempIco) { Remove-Item $tempIco -Force }
if (Test-Path $scriptPath) { Remove-Item $scriptPath -Force }
