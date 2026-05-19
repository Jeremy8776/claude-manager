---
name: System Monitor
description: System performance monitoring and resource tracking on Windows
triggers: [performance, system, monitor, resource, task manager, perfmon, Resource Monitor]
---

# System Monitor

## Resource Monitor

Launch Resource Monitor (`resmon.exe`) to see real-time CPU, memory, disk, and network usage. The CPU tab shows per-process utilization with expandable views.

## Performance Monitor

Use Performance Monitor (`perfmon.exe`) to create data collector sets. Track counters like:
- `\Processor(_Total)\% Processor Time`
- `\Memory\Available MBytes`
- `\LogicalDisk(*)\% Disk Time`

## Task Manager

Task Manager shows per-process CPU, memory, disk, and network columns. Sort by any column to identify resource hogs. The Performance tab shows overall system utilization graphs.

## Identifying Worst Offender

Use `Get-Process | Sort-Object CPU -Descending | Select-Object Name, CPU, WorkingSet -First 5` to quickly identify the process using the most CPU time.
