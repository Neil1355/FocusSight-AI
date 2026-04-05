param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Creating virtual environment at $VenvPath"
python -m venv $VenvPath

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment python not found at $pythonExe"
}

Write-Host "[2/4] Upgrading pip"
& $pythonExe -m pip install --upgrade pip

Write-Host "[3/4] Installing dependencies from requirements.txt"
& $pythonExe -m pip install -r requirements.txt

Write-Host "[4/4] Setup complete"
Write-Host "Run the app with:"
Write-Host "& $pythonExe -m focussight.tracker"
