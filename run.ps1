<#
.SYNOPSIS
    One-command launcher for Job Hunt Automation.

.DESCRIPTION
    Boots the whole app from a single command. It will, in order:
      1. Neutralize a broken SSL_CERT_FILE env var if present (a known machine issue
         where it points at an unexpanded %VIRTUAL_ENV% path and breaks all HTTPS).
      2. Create the virtual environment and install dependencies on first run.
      3. Run the CLI, passing through any arguments you give it.

.EXAMPLE
    .\run.ps1                          # shows the sources table (a safe smoke test)

.EXAMPLE
    .\run.ps1 scan --source remotive   # any CLI args are passed straight through

.EXAMPLE
    .\run.ps1 jobs list --min-score 70

.EXAMPLE
    .\run.ps1 serve                    # launch the web UI at http://127.0.0.1:8000
#>

$ErrorActionPreference = "Stop"

# Always operate from the folder this script lives in.
$Root = $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

# --- 1. Defuse the broken SSL_CERT_FILE (machine-level config bug) ------------
# If it is set but the file it points to does not exist, drop it for this run so
# Python falls back to its built-in certifi bundle. Harmless if it is already clean.
if ($env:SSL_CERT_FILE -and -not (Test-Path -LiteralPath $env:SSL_CERT_FILE)) {
    Write-Host "[run] Ignoring broken SSL_CERT_FILE for this session." -ForegroundColor Yellow
    Remove-Item Env:SSL_CERT_FILE -ErrorAction SilentlyContinue
}

# --- 2. First-run setup: create venv + install -------------------------------
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "[run] First run: creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "[run] Installing dependencies (this happens only once)..." -ForegroundColor Cyan
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPython -m pip install -e ".[dev]" --quiet
    Write-Host "[run] Setup complete." -ForegroundColor Green
}

# --- 3. Run the app ----------------------------------------------------------
# Default to a safe, no-network command when no arguments are supplied.
if ($args.Count -eq 0) {
    Write-Host "[run] No command given - showing configured sources." -ForegroundColor DarkGray
    Write-Host "[run] Try:  .\run.ps1 scan --source remotive" -ForegroundColor DarkGray
    Write-Host ""
    & $VenvPython main.py sources list
}
else {
    & $VenvPython main.py @args
}

exit $LASTEXITCODE
