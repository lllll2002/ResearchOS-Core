# register_health_daemon_tasks.ps1
# Creates 3 scheduled tasks for health_daemon.
# RUN AS ADMINISTRATOR. This script only creates tasks, does not run them.

$TaskPrefix = "PersonalOS_HealthDaemon"
$PsExe      = "powershell.exe"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WrapperScript = Join-Path $PSScriptRoot "run_health_daemon.ps1"
$WrapperArg = "-ExecutionPolicy Bypass -File `"$WrapperScript`""
$WorkDir    = $ProjectRoot

# Settings: don't run if already running, stop after 10 min
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

$Action = New-ScheduledTaskAction `
    -Execute $PsExe `
    -Argument $WrapperArg `
    -WorkingDirectory $WorkDir

# --- Task 1: At startup (delay 10 min) ---
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerStartup.Delay = "PT10M"
Register-ScheduledTask `
    -TaskName "${TaskPrefix}_Startup" `
    -Action $Action `
    -Trigger $TriggerStartup `
    -Settings $Settings `
    -Description "Health check after system boot (10 min delay)" `
    -Force
Write-Host "Created: ${TaskPrefix}_Startup (at startup, 10 min delay)"

# --- Task 2: Daily morning 07:30 ---
$TriggerMorning = New-ScheduledTaskTrigger -Daily -At "07:30"
Register-ScheduledTask `
    -TaskName "${TaskPrefix}_Morning" `
    -Action $Action `
    -Trigger $TriggerMorning `
    -Settings $Settings `
    -Description "Morning health check" `
    -Force
Write-Host "Created: ${TaskPrefix}_Morning (daily 07:30)"

# --- Task 3: Daily evening 23:30 ---
$TriggerEvening = New-ScheduledTaskTrigger -Daily -At "23:30"
Register-ScheduledTask `
    -TaskName "${TaskPrefix}_Evening" `
    -Action $Action `
    -Trigger $TriggerEvening `
    -Settings $Settings `
    -Description "Evening health check + backup if stale" `
    -Force
Write-Host "Created: ${TaskPrefix}_Evening (daily 23:30)"

Write-Host "`nAll 3 tasks registered. Verify in Task Scheduler under 'PersonalOS_HealthDaemon_*'."
