# run_morning_setup.ps1 — Task Scheduler wrapper for morning setup
# Called by Windows Task Scheduler at 07:30. Do not run interactively unless testing.

$ErrorActionPreference = "Continue"

# --- Configuration ---
$VaultRoot   = "E:\Obsidian"
$PythonExe   = "D:\Python\Python312\python.exe"
$Script      = "$VaultRoot\scripts\run_morning_setup.py"
$LogDir      = "$VaultRoot\07_System_Optimization\generated\logs"
$Timestamp   = Get-Date -Format "yyyy-MM-dd"

# --- Ensure log directory ---
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# --- Log files (daily rotation by date suffix) ---
$StdoutLog = "$LogDir\morning_setup_$Timestamp.log"
$StderrLog = "$LogDir\morning_setup_$Timestamp.err"

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
