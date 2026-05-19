---
name: Startup Routine
description: Windows startup automation and morning routine configuration
triggers: [startup, morning, routine, launch, autostart, schedule, Start-Process]
---

# Startup Routine

## Morning Startup Script

Create a PowerShell script that launches your daily apps in order:

```powershell
# Morning startup routine
Write-Host "Starting morning routine..."

# First: communication apps
Start-Process "slack://"
Start-Process "C:\Users\jerem\AppData\Local\Programs\Microsoft VS Code\Code.exe"

# Second: wait, then browsers
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe"

Write-Host "Morning routine complete."
```

## Scheduling with Task Scheduler

Use `Register-ScheduledTask` to run the startup script at logon:

```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\scripts\morning-routine.ps1"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "MorningRoutine" -Action $action -Trigger $trigger
```

## Ordering

Start communication apps first (Slack), then editor (VS Code), then browsers (ChatGPT). Use `Start-Sleep` between launches to ensure each app is ready before the next starts.
