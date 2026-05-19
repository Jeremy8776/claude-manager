# Context Engine — Comprehensive Roadmap

> Updated: 2026-05-18. Author: Jeremy.
> What we've built, where we stand, and what ships next. Two-month horizon.

---

## Why This Exists

Context quality is the bottleneck in every AI workflow. Models are good and getting better — but the context you feed them is fragmented, stale, and unstructured. CE solves that: it ingests skills from anywhere, understands them semantically, deduplicates overlap, ranks quality, auto-selects the right subset per task, and delivers optimised context to any AI surface.

---

## Repo Layout — Canonical Context Root

All AI tool configs live in a single canonical location: `app/.context/`. Root-level dot-files and directories are NTFS junctions pointing into it.

```
app/.context/
├── claude/               → launch.json, settings.local.json
├── codex/                → instructions.md
├── continue/rules/       → context-engine.md
├── app-claude/           → launch.json (when running from app/)
├── instructions/         → AGENTS.md, CLAUDE.md
├── rules/                → cursorrules, windsurfrules, clinerules
└── kimi-system-prompt.md
```

Root-level junctions: `.claude/`, `.codex/`, `.continue/` all resolve to subdirectories of `.context/`. All file-based targets (`.clinerules`, `.cursorrules`, `.windsurfrules`, `.ampcoderc`, `.goosehints`, `.rules`, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, `CONVENTIONS.md`, `GEMINI.md`, `devin.md`, `.kimi-system-prompt.md`, `.github/copilot-instructions.md`) and remaining dirs (`.augment/`, `.junie/`, `.kiro/`, `.pearai/`, `.tmp/`, `.trae/`, `.void/`) are removed from root. **`app/.context/` is the single source of truth for every AI tool config.**

---

## What We've Shipped (v0.3.1)

### Architecture: 31 server/lib modules, ~14k files total

The backend is deep and production-grade. Everything written zero-dependency (Node builtins + Ollama HTTP).

### Phase 0 — Stabilised v3 Base

- Modular DRAM CSS with token system and lint guard
- Cleanup modal for tidy/overlap review with apply flow
- Local update detection with clickable update toast
- Release checklist covering syntax, line limits, Git scope

### P0 — Electron + TypeScript Quality Gate

- Strict TypeScript typecheck across server and renderer — zero errors
- ESLint with TS-aware rules, no-floating-promises enforcement
- All source files under 500/700 line limits
- Electron shell with main/preload/renderer boundary

### P0 — Windows Installer + Auto-Update

- NSIS installer + portable target via electron-builder
- Auto-update wired (8s after launch, then every 6h)
- Brand marks: icon/mono/simple SVGs, .ico, .icns, Linux set
- GitHub Actions release workflow (tag-driven + manual)
- First tagged release v0.2.1 cut and validated end-to-end
- **Blocked:** code signing certificate not procured (SmartScreen warnings)

### Phase 1 — Vector Foundation

- `chunker.js`: semantic heading/rule/knowledge/example parser with frontmatter
- `embeddings.js`: Ollama client for nomic-embed-text, batch embed, graceful fallback
- `vectorstore.js`: flat-file vector index, cosine search, <5ms for 500 chunks
- `POST /api/index`, `POST /api/index/skill/:id`, `POST /api/search`, `GET /api/index/status`
- UI: indexed chunk count, model, last indexed time

### Phase 2 — Dedup + Rank

- `dedup.js`: pairwise similarity clustering, Union-Find, duplicate/related thresholds
- `ranking.js`: specificity, coverage, source weight, freshness scoring
- `GET /api/dedup`, `POST /api/dedup/resolve` with reversible resolution history
- Quality Audit UI: duplicate clusters, low-specificity filler, side-by-side comparison

### Phase 3 — Smart Compile

- `POST /api/compile/smart`: task embedding → vector search → expand → budget-fit → compile
- Project-aware stack detection (package.json, README, Cargo.toml)
- Before-and-after token comparison vs manual All On mode
- Modes moving toward presets (Smart Preview on dashboard)

### Phase 1.5 (Promoted) — MCP Bridge to Daily Apps

- `mcp-server.mjs`: stdio transport, 4-tool contract (search, list_skills, get_skill, status)
- Remote Streamable HTTP MCP adapter with bearer-token auth
- Claude Desktop `.mcpb` wrapper bundle
- One-paste config snippets for Claude Desktop, Codex CLI
- Lifecycle: spawned by host app, independent of Electron shell
- Claude Desktop + Codex CLI validated end-to-end
- **Blocked:** ChatGPT remote connector needs HTTPS tunnel/hosting choice

### Handoffs — Full Lifecycle

- Project handoffs (repo-bound), thread handoffs (topic-bound), dual-bound
- Git staleness detection (auto-archive at 5+ commits)
- Thread staleness (archive after 14 days idle), purge after 30 days
- 9 REST endpoints + MCP tool + admin UI (peer to Memory tab)
- Migrated existing llm-handoff.md entries into structured format

### Projects — CRUD + Scoped Context

- Project directories with seed memory.json + rules.json
- Collision-safe slugs, directory lifecycle, path management
- REST endpoints + 91-pass smoke test

### PR #2 (James Chapman) — Priority Rules, Auth, Security

- Priority-based rules model (hard/soft per section) with auto-migration
- API token auth (bearer, 48-hex, encrypted at rest, fully opt-in)
- Rule-files CRUD (`data/rules/*.json`)
- CI workflow (typecheck + lint + lint:css)
- 12 new smoke test suites (backup, crypto, mode-apply, mutex, projects, ranking, security, validation, etc.)

### Benchmark v1.3 — Evidence Pack

- Report PDF + chart PNGs under `bench/charts/`
- Smart Compile token accounting fixed (same output surface comparison)
- Manifest chunking for skill name/description/trigger search
- **Not yet green:** quality gate (Recall@8, no-context paired comparison)

---

## Current State Summary

| Area                          | Status          | Notes                                                                      |
| ----------------------------- | --------------- | -------------------------------------------------------------------------- |
| Backend architecture          | Shipped         | 31 modules, zero-dependency                                                |
| Vector index + search         | Shipped         | Works, needs quality tuning                                                |
| Dedup + rank                  | Shipped         | Exists but quality-gated                                                   |
| Smart Compile                 | Shipped         | Token savings proven, quality unproven                                     |
| MCP bridge (local)            | Shipped         | Claude Desktop + Codex validated                                           |
| MCP bridge (remote)           | Blocked         | ChatGPT needs HTTPS tunnel decision                                        |
| Handoffs                      | Shipped         |                                                                            |
| Projects                      | Shipped         |                                                                            |
| Priority rules                | Shipped         | PR #2 merged                                                               |
| API auth                      | Shipped         | Opt-in, encrypted                                                          |
| Benchmark gates               | **Not green**   | Recall@8 ≠ 1.00, no-context not compared                                   |
| System detection + onboarding | **Not started** | Broad spec written. Replaces old skill-sources + onboarding-redesign       |
| `scanSystem()` backend        | Exists (narrow) | Currently only SKILL.md dirs. Must broaden to rules/instructions/MCP/hosts |
| MCP discovery                 | **Not started** |                                                                            |
| AIModelDB bridge              | **Not started** |                                                                            |
| Modes-as-presets              | **Partial**     | Smart Preview on dashboard, tab grid not replaced                          |
| Code signing cert             | **Blocked**     | SmartScreen warnings on installer                                          |

---

## Two-Month Roadmap

### Week 1-2: Quality Gate (P0) — Make the Benchmark Honest

Before any new features, CE must prove it doesn't make answers worse.

| Task                                                                                         | Est. | Owner  |
| -------------------------------------------------------------------------------------------- | ---- | ------ |
| Rebuild vector index + re-run v1.3 benchmark after manifest chunking                         | 2d   | Jeremy |
| Add retrieval-quality smoke gate: expected-source Recall@8 = 1.00                            | 2d   | Jeremy |
| Add no-context paired quality gate: Smart/Search must beat or tie no-context                 | 2d   | Jeremy |
| Hybrid reranking: vector score + lexical match on id/name/triggers/section                   | 3d   | Jeremy |
| Fix any retrieval misses identified by the benchmark                                         | 2d   | Jeremy |
| Dashboard/reporting copy: "token reduction measured; quality gate pending" → remove warning  | 1d   | Jeremy |
| Promote multi-resolution packaging: manifest → relevant chunks → full skill only when needed | 3d   | Jeremy |

**Gate:** Smoke CI fails if Recall@8 < 1.00 or quality drops below no-context.

### Week 3-4: System Detection Phase 1 + MCP Remote (P0/P1)

Two parallel streams. This replaces the old "Skill Sources" and "Onboarding Redesign" — now unified into System Detection.

**Stream A — MCP Remote (Jeremy):**
| Task | Est. |
|------|------|
| Choose HTTPS tunnel/hosting (e.g. Cloudflare Tunnel, ngrok, or $5 VPS) | 1d |
| Set `MCP_OAUTH_PASSWORD`, expose `/mcp` | 1d |
| Register URL in Claude/ChatGPT connector, validate `context_engine_status` | 1d |
| Document the setup for self-hosted users | 1d |

**Stream B — System Detection Backend (Jeremy or James):**
| Task | Est. |
|------|------|
| Rewrite `scanHostSkillPaths()` → `scanSystem()` with 5 categories (skills, rules, instructions, MCP, hosts) | 2d |
| Add probe functions: probeRuleFiles, probeInstructionFiles, probeMcpServers, probeHostConfigs | 2d |
| New endpoint: `GET /api/system/scan` — runs all probes, returns grouped results | 2d |
| New endpoints: `POST /api/system/link-all`, `POST /api/system/link`, `DELETE /api/system/link/:id` | 2d |
| New data model: `data/system-context.json` (tracks all linked sources with timestamps) | 1d |
| Refactor `server/lib/skills.js` → `findAllSkillDirs()` with sourceId for unified skill listing | 2d |

### Week 5-6: Onboarding + Import Pipeline (P1)

**Stream A — Onboarding Rewrite (Jeremy):**
| Task | Est. |
|------|------|
| 4-step scan → review → build → done flow. Step 1 runs `GET /api/system/scan` on open | 3d |
| Grouped result cards: skills count, rules count, instructions count, MCP count, hosts detected | 2d |
| "Link All" button links every unmanaged source in one click | 1d |
| Per-source Link/Unlink with inline feedback | 1d |
| Step 3: import + rebuild index with progress | 2d |
| CSS budget ≤ 250 lines, reuse DRAM tokens | 1d |

**Stream B — Link-Import Pipeline (James):**
| Task | Est. |
|------|------|
| Directory sources → NTFS junction into `app/.context/<category>/<id>` | 2d |
| File sources → copy into `app/.context/` | 1d |
| MCP server registration from detected configs | 2d |
| Auto-rebuild index after link/import | 1d |
| Per-source linking: collision-safe ID prefixing (`<sourceId>:<bareId>`) | 1d |
| Smoke tests: full scan → link → verify → unlink roundtrip | 2d |

### Week 7-8: Set & Forget + Polish (P1/P2)

**Jeremy:**
| Task | Est. |
|------|------|
| Periodic health check (24h timer re-scan, notify on new/changed sources) | 2d |
| Connections tab (post-onboarding source management UI, sibling to Skills/Memory/Handoffs) | 3d |
| Replace Modes tab grid with preset library | 2d |
| Smart Preview can promote selected skill sets into presets | 2d |
| Code signing certificate procurement + wiring | 2d |

**James:**
| Task | Est. |
|------|------|
| CE becomes sole author — compile writes to `app/.context/` AND root junctions (where they exist) | 3d |
| CE writes compiled output to tool root paths when no junction exists (file fallback) | 2d |
| Handoff rate-limit-aware heartbeat/update API | 1d |
| `context_engine_dedup_report` MCP tool | 2d |
| Validation + edge-case hardening across all system detection endpoints | 2d |

---

## Beyond Two Months (Next)

- **Phase 5 — AIModelDB Bridge:** model-aware compile budget, dashboard display, model comparison MCP tool
- **`context_engine_model_lookup` MCP tool**
- **Multi-platform native installers** (macOS dmg, Linux deb/rpm) — runners exist in the release workflow, just need testing
- **Plugin/skill marketplace** — network effects, the real moat

---

## Key Principles

1. **Quality gate is the door.** Nothing ships to users until the benchmark proves it doesn't make answers worse.
2. **Daily use is the signal.** If Jeremy wouldn't reach for it in Claude Desktop or Codex tomorrow morning, it waits.
3. **James audits and hardens.** Jeremy drives the main roadmap. James catches edge cases, adds tests, and prevents regressions.
4. **Zero new deps.** Node builtins + Ollama HTTP. This is a product principle, not an accident.
5. **Under 500 lines.** Every module stays under 500 lines soft limit, 700 absolute. New modules get split early.
