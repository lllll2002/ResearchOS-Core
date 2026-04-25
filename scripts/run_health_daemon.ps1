# run_health_daemon.ps1 — Task Scheduler wrapper for health_daemon.py
# Called by Windows Task Scheduler. Do not run interactively unless testing.

$ErrorActionPreference = "Continue"

# --- Configuration ---
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VaultRoot   = if ($env:RESEARCH_OS_VAULT) { $env:RESEARCH_OS_VAULT } else { Join-Path $ProjectRoot "vault" }
$PythonExe   = "python"
$Script      = Join-Path $PSScriptRoot "health_daemon.py"
$LogDir      = Join-Path $ProjectRoot "generated\logs"
$Timestamp   = Get-Date -Format "yyyy-MM-dd"

# --- Ensure log directory ---
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# --- Log files (daily rotation by date suffix) ---
$StdoutLog = "$LogDir\health_daemon_$Timestamp.log"
$StderrLog = "$LogDir\health_daemon_$Timestamp.err"

# --- Run ---
$process = Start-Process -FilePath $PythonExe `
    -ArgumentList $Script `
    -WorkingDirectory $VaultRoot `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -NoNewWindow `
    -Wait `
    -PassThru

exit $process.ExitCode
