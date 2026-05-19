---
name: App Launcher
description: Windows application launcher shortcuts and automation
triggers: [launch, open, start, Start-Process, shortcut, application, automation]
---

# App Launcher

## Launching Applications

Use `Start-Process` to launch any application:

```powershell
Start-Process "C:\Program Files\Slack\slack.exe"
Start-Process "code"  # via PATH
Start-Process "https://chat.openai.com"  # default browser
```

## Finding Application Paths

Get installed app paths from the registry:

```powershell
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\*" | Select-Object '(default)'
```

## Startup Folder Automation

Place shortcuts in `shell:startup` for automatic launch at logon. Use `$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup` for per-user startup items.

## Launch Order

Use `Start-Process -Wait` to launch apps sequentially, ensuring each is fully loaded before the next starts. Combine with Start-Sleep for apps that need extra initialization time.
