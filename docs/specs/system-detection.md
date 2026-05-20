# System Detection & Unified Context Ingestion

> Replaces: [skill-sources.md](skill-sources.md) + [onboarding-redesign.md](onboarding-redesign.md)
> Status: proposed. 2026-05-18.

---

## The Vision

CE is the single source of truth for every AI tool on the machine. You install CE once, it scans everything, you click confirm, and every tool on your system — Claude Code, Cursor, Codex CLI, OpenCode, Continue, Cline, Windsurf, Kimi, GitHub Copilot — reads from CE's unified context. You never touch a tool config again.

### Flow

```
Install CE                          (single download)
  → Launch Electron app             (first run)
  → Onboarding: "Scanning system…"  (auto, 2-5 seconds)
  → Shows: 4 hosts, 247 skills, 53 rules, 12 MCP servers found
  → User clicks "Link All & Continue"
  → CE imports everything, builds index, wires junctions
  → Dashboard: "All systems ready. 0 configs to maintain."
  → Done.
```

---

## What `scanHostSkillPaths()` Currently Scopes

| Path                           | Type   | Detects          |
| ------------------------------ | ------ | ---------------- |
| `~/.claude/skills/`            | skills | SKILL.md files   |
| `~/.opencode/skills/`          | skills | SKILL.md files   |
| `<workspace>/.claude/skills/`  | skills | SKILL.md files   |
| `<workspace>/.clinerules`      | rules  | Single rule file |
| `<workspace>/.continue/rules/` | rules  | Rule files       |

### What It's Missing

#### MCP Servers

- `~/.claude/plugins/` — installed Claude Desktop plugins (each is an MCP server)
- `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/*/.claude-plugin` — official plugin metadata
- `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` — VS Code/Cline MCP config
- `claude_desktop_config.json` — Claude Desktop MCP server config (at `%APPDATA%\Claude\` on Windows)

#### Instructions Files

- `AGENTS.md` — OpenCode / Codex agent instructions
- `CLAUDE.md` — Claude Code project instructions
- `GEMINI.md` — Gemini Code Assist instructions
- `devin.md` — Devin instructions
- `.kimi-system-prompt.md` — Kimi system prompt
- `.github/copilot-instructions.md` — GitHub Copilot instructions

#### Rule Files

- `.cursorrules` — Cursor rules
- `.windsurfrules` — Windsurf rules
- `.clinerules` — Cline/Roo rules
- `.rules` — Generic rules
- `.ampcoderc` — Ampcoder config
- `.goosehints` — Goose hints
- `CONVENTIONS.md` — Project conventions

#### Home-Dir Tool Configs (for context, not import)

- `~/.cursor/` — Cursor settings (detect presence, don't import)
- `~/.codex/` — Codex CLI config and skills
- `~/.kimi/` — Kimi session data (detect, don't import sessions)
- `~/.continue/` — Continue.dev config (detect, don't import)

---

## Expanded Scan: Full Probe Map

```js
function scanSystem() {
  return [
    // === SKILLS ===
    ...probeSkillDirs(),
    // === RULES ===
    ...probeRuleFiles(),
    // === INSTRUCTIONS ===
    ...probeInstructionFiles(),
    // === MCP SERVERS ===
    ...probeMcpServers(),
    // === HOST PRESENCE ===
    ...probeHostConfigs(),
  ];
}
```

### Skills

| Probe                  | Label                    | Reads                              |
| ---------------------- | ------------------------ | ---------------------------------- |
| `~/.claude/skills/`    | Claude Code (global)     | dir → SKILL.md count               |
| `~/.opencode/skills/`  | OpenCode (global)        | dir → SKILL.md count               |
| `~/.codex/skills/`     | Codex CLI (global)       | dir → SKILL.md count               |
| `<ws>/.claude/skills/` | Claude Code in {project} | dir → SKILL.md count               |
| `<ws>/.codex/`         | Codex CLI in {project}   | dir → SKILL.md and instructions.md |

### Rules (single-file sources)

| Probe                           | Label               | Reads              | CE Target                     |
| ------------------------------- | ------------------- | ------------------ | ----------------------------- |
| `<project-root>/.clinerules`    | Cline / Roo         | file content       | `rules/clinerules`            |
| `<project-root>/.cursorrules`   | Cursor              | file content       | `rules/cursorrules`           |
| `<project-root>/.windsurfrules` | Windsurf            | file content       | `rules/windsurfrules`         |
| `<project-root>/.rules`         | Generic rules       | file content       | `rules/rules`                 |
| `<project-root>/.ampcoderc`     | Ampcoder            | file content       | `rules/ampcoderc`             |
| `<project-root>/.goosehints`    | Goose               | file content       | `rules/goosehints`            |
| `<ws>/.continue/rules/`         | Continue.dev        | dir → file content | `rules/continue/*`            |
| `<project-root>/CONVENTIONS.md` | Project conventions | file content       | `instructions/CONVENTIONS.md` |

### Instructions

| Probe                                            | Label              | Reads        | CE Target                       |
| ------------------------------------------------ | ------------------ | ------------ | ------------------------------- |
| `<project-root>/AGENTS.md`                       | OpenCode / Codex   | file content | `instructions/AGENTS.md`        |
| `<project-root>/CLAUDE.md`                       | Claude Code        | file content | `instructions/CLAUDE.md`        |
| `<project-root>/GEMINI.md`                       | Gemini Code Assist | file content | `instructions/GEMINI.md`        |
| `<project-root>/devin.md`                        | Devin              | file content | `instructions/devin.md`         |
| `<project-root>/.kimi-system-prompt.md`          | Kimi               | file content | `kimi-system-prompt.md`         |
| `<project-root>/.github/copilot-instructions.md` | GitHub Copilot     | file content | `rules/copilot-instructions.md` |
| `<project-root>/CONTEXT.md`                      | CE manifest        | file content | `instructions/CONTEXT.md`       |

### MCP Servers

| Probe                                         | Label                  |
| --------------------------------------------- | ---------------------- |
| `%APPDATA%\Claude\claude_desktop_config.json` | Claude Desktop MCP     |
| `~/.claude/plugins/`                          | Claude Desktop plugins |
| `{vscode-config}/cline_mcp_settings.json`     | Cline MCP              |
| `~/.codex/mcp.json`                           | Codex CLI MCP          |

### Host Presence (informational)

| Probe                                  | Label                |
| -------------------------------------- | -------------------- |
| `~/.claude/` exists                    | Claude Code (global) |
| `~/.cursor/` exists                    | Cursor               |
| `~/.codex/` exists                     | Codex CLI (global)   |
| `~/.kimi/` exists                      | Kimi                 |
| `~/.continue/` exists                  | Continue.dev         |
| `~/.opencode/` exists                  | OpenCode             |
| where.exe cursor, where.exe code, etc. | Host CLI on PATH     |

---

## Detection Returns

Each probe returns a unified result shape:

```json
{
  "id": "claude-global-skills",
  "category": "skills",
  "label": "Claude Code (global skills)",
  "path": "C:\\Users\\jerem\\.claude\\skills",
  "exists": true,
  "size": 12,
  "unit": "SKILL.md files",
  "alreadyManaged": true,
  "contentSummary": "React, TypeScript, Python, ..."
}
```

`category` is one of: `skills`, `rules`, `instructions`, `mcp`, `host`.

---

## Onboarding Flow (Revised)

Four steps, but the emphasis shifts from "config your tools" to "scan, review, done."

### Step 1: System Scan (was "Connect")

Auto-run on open. Shows a spinner for 2-5s while CE probes every known path.

Result: a grouped list:

```
Context Engine found AI tooling across your system:

Skills          3 locations · 247 skill files
  Claude Code (global)           ~/.claude/skills          12 SKILL.md  [linked]
  OpenCode (global)              ~/.opencode/skills        230 SKILL.md [linked]
  Codex CLI (project)            project/.codex/           5 SKILL.md   [link]

Rules           4 locations · 3 files + 1 directory
  Cursor rules                   .cursorrules              53KB          [link]
  Continue.dev                   .continue/rules/          1 rule        [link]
  Cline / Roo                    .clinerules               17KB          [link]

Instructions    3 files
  OpenCode / Codex               AGENTS.md                 18KB          [link]
  Claude Code                    CLAUDE.md                 3.5KB         [link]
  Project conventions            CONVENTIONS.md            8.7KB         [link]

MCP Servers     2 found
  Claude Desktop                 claude_desktop_config.json 4 servers     [link]
  Cline                          cline_mcp_settings.json   2 servers     [link]

Hosts Detected  6 tools
  Claude Code ✓  Cursor ✓  Codex CLI ✓  Continue ✓  Kimi ✓  OpenCode ✓

[ Link All ]  [ Review Individually ]
```

### Step 2: Verify & Customize

Folded into step 1 if "Review Individually" is clicked, or shown as an expandable section after auto-link:

- Checkboxes per probe row
- "Path to skills folder:" text input + Browse button
- Linked sources show with an Unlink affordance
- Paths that are already in CE's `.context/` show as "Managed"

### Step 3: Build & Confirm

- CE imports all confirmed sources
- Rebuilds vector index (shows progress)
- Writes compiled context to `app/.context/`
- Shows result: "247 skills indexed | 53 rules consolidated | 4 MCP servers registered"

### Step 4: Done

Dashboard. No celebration step. The modal closes and the app is live.

---

## What "Link" Actually Means Now

Not just tracking a source in JSON. Full pipeline:

1. **Register** the source in `skill-sources.json`
2. **Copy or junction** the content into `app/.context/`
   - Directories → NTFS junction (instant, zero-copy)
   - Files → copy (until Windows symlinks are available)
3. **Ingest** skills into CE's vector index
4. **Register** MCP servers in CE's MCP registry
5. **Scan** rule/instruction content for dedup against existing CE rules
6. **Write** compiled output back to `app/.context/`
7. **Update** the dashboard stat grid immediately

---

## Post-Onboarding: "Set & Forget"

After onboarding, CE maintains itself:

### Periodic Health Check

Every 24h (configurable):

- Re-scan known paths for new/removed skills
- Flag stale index
- Check if new AI tools were installed (detect new `~/.<tool>` directories)
- Show notification: "New skills found in ~/.claude/skills — Link?"

### Auto-Compile on Change

When skills are added/removed to any linked source:

- CE detects the change (on next read or periodic scan)
- Marks index as stale
- Shows: "Context has changed: [N] skills added, [M] removed. Rebuild?"

### Manual Overrides

- Connections tab shows all linked sources with per-source controls
- Unlink, Re-scan, Force Rebuild per source
- Custom path picker for power users

---

## What the User Never Does

- Never edits a config file directly
- Never copies skills between tool directories
- Never wonders which `.cursorrules` is current
- Never maintains duplicate `AGENTS.md` and `CLAUDE.md`
- Never manually wires MCP servers into each host

---

## Implementation Plan

### Phase 1: Broadened Scan + Onboarding (this sprint)

| Task                                                                                                                       | Est. |
| -------------------------------------------------------------------------------------------------------------------------- | ---- |
| Rewrite `scanHostSkillPaths()` → `scanSystem()` with all probe categories                                                  | 2d   |
| Add probe functions: probeRuleFiles, probeInstructionFiles, probeMcpServers, probeHostConfigs                              | 2d   |
| New data model: `data/system-context.json` with full detected state                                                        | 1d   |
| Add endpoints: `GET /api/system/scan`, `POST /api/system/link-all`, `POST /api/system/link`, `DELETE /api/system/link/:id` | 2d   |
| Rewrite onboarding UI with the 4-step scan → review → build → done flow                                                    | 3d   |
| Update dashboard stat grid to reflect linked sources                                                                       | 1d   |
| Smoke test: scan against fixture directories, verify all categories detected                                               | 1d   |

### Phase 2: Import Pipeline + MCP Registration

| Task                                                                    | Est. |
| ----------------------------------------------------------------------- | ---- |
| Auto-junction for directory sources (moved into `.context/<category>/`) | 1d   |
| Rule/instruction file import into `app/.context/`                       | 1d   |
| MCP server registration from detected configs                           | 2d   |
| "Set & forget" periodic health check (24h timer)                        | 2d   |
| Notification system for new/changed sources                             | 1d   |
| Connections tab UI (post-onboarding source management)                  | 2d   |

### Phase 3: CE as Sole Author

| Task                                                                | Est. |
| ------------------------------------------------------------------- | ---- |
| CE rewrite root tool files on every compile (not just home dir)     | 2d   |
| CE writes to `app/.context/` AND to root-level junctions/copies     | 2d   |
| Kill the need for tool-specific config edits entirely               | 1d   |
| Benchmark: measure time from "install CE" to "all tools configured" | 1d   |
