# register_morning_setup_task.ps1
# Creates a scheduled task for daily morning-setup at 07:30.
# RUN AS ADMINISTRATOR.

$TaskName   = "PersonalOS_MorningSetup"
$PsExe      = "powershell.exe"
$WrapperArg = "-ExecutionPolicy Bypass -File E:\Obsidian\scripts\run_morning_setup.ps1"
$WorkDir    = "E:\Obsidian"

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

# Daily at 07:30
$Trigger = New-ScheduledTaskTrigger -Daily -At "07:30"

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily morning plan generation via Claude CLI /morning-setup" `
    -Force

Write-Host "Created: $TaskName (daily 07:30)"
Write-Host ""
Write-Host "Verify in Task Scheduler under '$TaskName'."
Write-Host "Test with: schtasks /run /tn $TaskName"
