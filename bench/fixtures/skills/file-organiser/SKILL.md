---
name: File Organiser
description: Windows file organization, categorization, and grouping utilities
triggers: [organize, file, categorize, group, move, archive, extension, cleanup]
---

# File Organiser

## Categorization

Group files by extension or type:
```powershell
Get-ChildItem -Path $downloads -File | Group-Object Extension | Sort-Object Count -Descending
```

## Organizing by Extension

```powershell
$categories = @{
    ".pdf" = "Documents"; ".docx" = "Documents"; ".xlsx" = "Documents"
    ".jpg" = "Images"; ".png" = "Images"; ".gif" = "Images"
    ".zip" = "Archives"; ".rar" = "Archives"; ".7z" = "Archives"
    ".exe" = "Installers"; ".msi" = "Installers"
}
```

## Archive Strategy

Move files older than 90 days to subfolders. Keep a manifest of archived files. Use date-based folder structure: `Archive\2026\05\` for monthly archiving. Log all moves to an archive audit file.

## Safety

Preview changes before executing. Use `-WhatIf` flag to verify. Create restore point before bulk operations.
