# build.ps1
# Requires PyInstaller and Pillow (pip install pyinstaller Pillow)

Write-Host "Building Simple Productivity Blocker for Windows..."

# Clean previous builds
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Prepare icon from newlogo.png
$iconPng = Join-Path $PSScriptRoot "newlogo.png"
$tempIco = Join-Path $PSScriptRoot "icon.ico"

if (-not (Test-Path $iconPng)) {
    Write-Host "Error: Missing newlogo.png in the project root."
    exit 1
}

# Convert PNG to ICO using a temporary script for robustness
$scriptPath = Join-Path $env:TEMP "spb_icon_gen.py"
$py = @"
import sys
from PIL import Image
try:
    img = Image.open(r'$iconPng')
    img.save(r'$tempIco', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
except Exception as e:
    print(e)
    sys.exit(1)
"@
Set-Content -Path $scriptPath -Value $py -Encoding UTF8
python $scriptPath
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Icon conversion failed."
    exit $LASTEXITCODE 
}
Remove-Item $scriptPath -Force

# Build the main app (Bundled with assets for a clean dist folder)
Write-Host "Building SimpleProductivityBlocker.exe..."
python -m PyInstaller --noconfirm --onedir --windowed --uac-admin `
    --icon="$tempIco" `
    --add-data "newlogo.png;." `
    --add-data "icon.ico;." `
    --name "SimpleProductivityBlocker" main.py

# Build the daemon
Write-Host "Building SPB_Daemon.exe..."
python -m PyInstaller --noconfirm --onedir --windowed `
    --icon="$tempIco" `
    --name "SPB_Daemon" daemon.py

# Assemble the package
Write-Host "Assembling package..."
$pkgDir = "dist\SimpleProductivityBlocker"
Copy-Item "dist\SPB_Daemon\SPB_Daemon.exe" -Destination "$pkgDir\"

# Build and copy installer/uninstaller
Write-Host "Building spb_installer.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" --name "spb_installer" spb_installer.py
Copy-Item "dist\spb_installer.exe" -Destination "$pkgDir\"

Write-Host "Building spb_uninstaller.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" --name "spb_uninstaller" spb_uninstaller.py
Copy-Item "dist\spb_uninstaller.exe" -Destination "$pkgDir\"

# Copy Documentation
if (Test-Path "CHANGELOG.md") {
    Copy-Item "CHANGELOG.md" -Destination "$pkgDir\"
}

Write-Host "Build complete! Your deployable package is in dist\SimpleProductivityBlocker"
Write-Host "Zip the 'dist\SimpleProductivityBlocker' folder to distribute it to users."
