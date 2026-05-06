# build.ps1
# Requires PyInstaller and Pillow (pip install pyinstaller Pillow)

Write-Host "Building Simple Productivity Blocker for Windows..."

# Clean previous builds
Write-Host "Cleaning previous build artifacts and terminating running instances..."
Get-Process "SimpleProductivityBlocker" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process "SPB_Daemon" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2 # Wait for file handles to release

if (Test-Path "dist") { 
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
}
if (Test-Path "build") { 
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
}

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
    --collect-all pywin32 `
    --hidden-import=pywintypes `
    --hidden-import=pythoncom `
    --hidden-import=win32com `
    --exclude-module redis `
    --exclude-module opentelemetry `
    --name "SimpleProductivityBlocker" main.py

# Build the daemon
Write-Host "Building SPB_Daemon.exe..."
python -m PyInstaller --noconfirm --onefile --windowed `
    --icon="$tempIco" `
    --collect-all pywin32 `
    --collect-all dnslib `
    --hidden-import=pywintypes `
    --hidden-import=pythoncom `
    --hidden-import=win32com `
    --exclude-module redis `
    --exclude-module opentelemetry `
    --name "SPB_Daemon" daemon.py

# Assemble the package
Write-Host "Assembling package..."
$pkgDir = "dist\SimpleProductivityBlocker"
# Copy SPB_Daemon (onefile - just the exe)
Copy-Item "dist\SPB_Daemon.exe" -Destination "$pkgDir\"

# Build installer (Bundles the app as payload)
Write-Host "Building spb_installer.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" `
    --collect-all pywin32 `
    --add-data "dist/SimpleProductivityBlocker/*;." `
    --hidden-import=pywintypes `
    --hidden-import=pythoncom `
    --hidden-import=win32com `
    --name "spb_installer" spb_installer.py

# Build uninstaller (Logic only, NO payload)
Write-Host "Building spb_uninstaller.exe..."
python -m PyInstaller --noconfirm --onefile --console --uac-admin --icon="$tempIco" `
    --collect-all pywin32 `
    --hidden-import=pywintypes `
    --hidden-import=pythoncom `
    --hidden-import=win32com `
    --name "spb_uninstaller" spb_uninstaller.py

# Final Assembly: Copy installer and uninstaller into the package directory
Write-Host "Finalizing distribution package..."
Copy-Item "dist\spb_installer.exe" -Destination "$pkgDir\"
Copy-Item "dist\spb_uninstaller.exe" -Destination "$pkgDir\"

# Explicitly bundle pywin32 system DLLs to ensure Folder Monitoring works
Write-Host "Bundling pywin32 system components..."
$pywin32SysDir = "C:\Users\You\AppData\Roaming\Python\Python314\site-packages\pywin32_system32"
if (Test-Path $pywin32SysDir) {
    Copy-Item "$pywin32SysDir\*.dll" -Destination "$pkgDir\"
    Write-Host "COM Drivers bundled successfully."
} else {
    Write-Host "Warning: Could not find pywin32_system32. Folder monitoring may be limited."
}

# Copy Documentation
if (Test-Path "CHANGELOG.md") {
    Copy-Item "CHANGELOG.md" -Destination "$pkgDir\"
}

Write-Host "Build complete! Your deployable package is in dist\SimpleProductivityBlocker"
Write-Host "Zip the 'dist\SimpleProductivityBlocker' folder to distribute it to users."

# Post-build Cleanup
Write-Host "Cleaning up build artifacts..."
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Get-ChildItem -Path $PSScriptRoot -Filter "*.spec" | Remove-Item -Force
Write-Host "Cleanup complete."
