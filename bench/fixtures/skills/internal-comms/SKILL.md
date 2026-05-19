---
name: Internal Communications
description: Internal team communications, release announcements, and patch notifications
triggers: [internal, communication, announcement, release, patch, team, Slack, email]
---

# Internal Communications

## Release Announcements

Draft announcements with this structure:
1. **Version and what shipped**: name the version number
2. **The fix or feature**: clear description of what changed and why
3. **Team action**: call to action (update, restart, no action needed)
4. **Format**: use formatting (bold, emoji, hashtags) appropriate to channel

## Security Patch Notifications

When shipping a security patch:
1. **Subject**: clear `[Security]` prefix
2. **Vulnerability**: name the specific issue (e.g., "symlink-escape vulnerability")
3. **Status**: state it's shipped/fixed
4. **Action required**: tell recipients what they need to do

## Tone Guidelines

- Internal: direct and informational, not marketing
- No hype language (avoid "leverage", "synergy", "best-in-class")
- Include contact for questions
- For security: no panic tone, no "URGENT" unless genuinely critical
