<#
PowerShell wrapper to run the integration harness with elevation.
Usage: Right-click and Run as Administrator, or run from an elevated PowerShell prompt.
#>

Param(
    [string]$PythonExe = "python",
    [string]$Script = "integration_run.py"
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$scriptPath = Join-Path $here $Script

if (-not (Test-Path $scriptPath)){
    Write-Error "Integration script not found: $scriptPath"
    exit 2
}

# If already elevated just run
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    Write-Host "Running integration harness as Administrator..."
    & $PythonExe $scriptPath
    exit $LASTEXITCODE
}

# Otherwise re-launch elevated
$arg = "-NoProfile -ExecutionPolicy Bypass -Command \"& { $PythonExe '$scriptPath' }\""
Start-Process -FilePath "powershell.exe" -ArgumentList $arg -Verb RunAs -Wait
exit $LASTEXITCODE
