---
name: Process Manager
description: Windows process management, CPU monitoring, and task management
triggers: [cpu, process, task manager, performance, high usage, Get-Process, Stop-Process]
---

# Process Manager

## Monitoring CPU Usage

Use `Get-Process | Sort-Object CPU -Descending | Select-Object -First 10` to find the top CPU consumers. The CPU column shows total processor time in seconds.

## Identifying High CPU

When a process is using high CPU:
1. Run `Get-Process -Name <name> | Select-Object Id, ProcessName, CPU, WorkingSet`
2. Check if it's a known system process or third-party
3. Note the process ID for targeted investigation

## Taking Action

- `Stop-Process -Id <id> -Force` to terminate
- `taskkill /PID <id> /F` as cmd alternative
- Use Task Manager (Ctrl+Shift+Esc) for GUI monitoring

## Prevention

Set up Resource Monitor alerts for sustained CPU > 80%. Use Performance Monitor to log CPU trends over time.
