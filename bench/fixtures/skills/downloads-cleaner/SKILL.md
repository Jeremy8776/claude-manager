---
name: Downloads Cleaner
description: Windows Downloads folder cleanup and file organization automation
triggers: [downloads, cleanup, organize, file management, archive, stale files, PowerShell]
---

# Downloads Cleaner

## Finding Stale Files

```powershell
$cutoff = (Get-Date).AddDays(-90)
$stale = Get-ChildItem "$env:USERPROFILE\Downloads" -File | Where-Object { $_.LastWriteTime -lt $cutoff }
$stale | Select-Object Name, LastWriteTime, Length
```

## Cleanup Plan

1. **Review**: first list stale files with dry-run
2. **Archive**: move to `_Archive` folder in Downloads
3. **Delete**: after confirming nothing is needed
4. **Report**: show size recovered and file counts

## Safety

Always use `-WhatIf` on destructive operations. Never delete without confirmation. Archive before removing. Create a report of what was moved/deleted.

## Automation

Schedule with Task Scheduler to run monthly. Log results to a file. Send summary via email if configured.
