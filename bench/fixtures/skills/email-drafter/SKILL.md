---
name: Email Drafter
description: Professional email drafting for internal and external communications
triggers: [email, draft, subject, message, internal, security, announcement]
---

# Email Drafter

## Security Patch Email Template

**Subject:** `[Security] Symlink-escape vulnerability patched in v0.3.1`

**Body:**
1. **What happened**: brief description of the symlink-escape path traversal vulnerability
2. **Impact**: what the vulnerability could allow (local file access, but no remote exploit observed)
3. **Fix**: shipped in v0.3.1 — the path sanitization now prevents symlink traversal
4. **Action**: update to v0.3.1 via auto-update or manual download
5. **Questions**: reply to this thread or DM the security lead

## Tone Guidelines

- Professional but direct
- No alarmist language
- State severity clearly
- Include concrete action items
- Sign with sender name and role

## Structure

Use `Subject:` line with clear prefix. Body divided into: context, impact, resolution, action items. End with contact info.
