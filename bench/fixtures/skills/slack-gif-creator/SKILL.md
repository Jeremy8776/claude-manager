---
name: Slack GIF Creator
description: Creating and formatting Slack messages with GIFs and rich formatting
triggers: [Slack, message, announcement, GIF, emoji, format, channel]
---

# Slack GIF Creator

## Slack Message Formatting

Use Slack mrkdwn for rich messages:
- `*bold*` for emphasis
- `:emoji:` for reactions and decoration
- `>blockquote` for quoted text
- `#channel` for channel references
- `@user` for user mentions

## Announcement Format

```markdown
*Release: v0.3.1 is here!* :rocket:

The data persistence fix has shipped. Your context is now saved reliably.

*What to do:* Update via auto-update or download from GitHub.
:inbox_tray: No action if auto-update is on.

Any questions, drop them in #dev-chat.
```

## Best Practices

- Include a clear headline (bold)
- Use 2-3 emojis max — don't overdo it
- State the call to action explicitly
- Keep it under 5 lines if possible
- Use threads for additional detail
