$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -m pip install -e ".[app]"
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed with exit code $LASTEXITCODE"
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Ares `
    --icon (Join-Path $RepoRoot "assets\ares.ico") `
    --add-data "$RepoRoot\assets\ares_logo.png;assets" `
    --paths "$RepoRoot\src" `
    (Join-Path $RepoRoot "src\local_llm\ares_app.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "Built Ares executable at $RepoRoot\dist\Ares.exe"
