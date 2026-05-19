---
name: Health Tracker Analyst
description: Health data analysis, step tracking, and fitness trend analysis
triggers: [health, step, fitness, analysis, tracking, Apple Health, Google Fit, daily goal]
---

# Health Tracker Analyst

## Step Data Analysis

Analyze step data from Apple Health or Google Fit exports:

```python
import pandas as pd
df = pd.read_csv("steps_export.csv")
daily_avg = df["steps"].mean()
weekly_median = df.resample("W", on="date")["steps"].median()
```

## Key Metrics

- **Daily average**: mean steps per day
- **Median**: more robust against outlier days
- **Trend**: rolling 7-day average shows direction
- **Streak**: consecutive days above 10,000 steps

## Goal Tracking

Compare current performance against the 10,000 steps daily goal. Calculate percentage of days on track, longest streak, and weekly averages. Visualize with a 7-day rolling average chart to see trends clearly.

## Data Sources

- Apple Health: export via Health app (XML or CSV)
- Google Fit: Takeout export
- Fitbit: account data export
- Garmin: Connect web export
