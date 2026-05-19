---
name: File Search
description: Windows file search and discovery utilities
triggers: [search, file, find, Get-ChildItem, directory, locate, Path]
---

# File Search

## Searching Files

```powershell
Get-ChildItem -Path "$env:USERPROFILE\Downloads" -Recurse -File | Where-Object { $_.Extension -in ".pdf", ".docx", ".zip" }
```

## Finding Specific Files

Search by pattern, date, or size:
```powershell
Get-ChildItem -Path C:\ -Recurse -File -Filter "*.log" -ErrorAction SilentlyContinue
Get-ChildItem -Path $HOME -Recurse -File | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) }
Get-ChildItem -Path $HOME -Recurse -File | Sort-Object Length -Descending | Select-Object -First 20
```

## Date Filtering

Use `LastWriteTime` and `CreationTime` properties. Common filters: `-gt (Get-Date).AddDays(-90)` for files modified in the last 90 days, or `-lt` for files older than a threshold.
