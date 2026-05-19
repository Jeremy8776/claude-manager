# Handoff to Codex — Tokenomics Benchmark Writeup

You're picking up a three-iteration tokenomics benchmark of the Context Engine (CE) and producing a final consolidated PDF with tables, charts, and a critical analysis. The benchmark went through v1.1 → v1.2 → v1.3 and the headline result changed materially each time — the writeup must handle that arc honestly, not paper over it.

## Your job

Produce **one consolidated PDF** that:

1. Cross-references all three benchmark iterations against each other (claims, retractions, methodology changes)
2. Cross-references the v1.3 findings against the white paper's own predictions (especially Section 11 — Multi-Resolution Context Packaging — and Hypothesis 1 in Section 32)
3. Includes every relevant table and chart (specs below)
4. Calls out what's defensible, what's been retracted, and what's still pending
5. Lands on a publication-grade summary the team can use to make product decisions

Format: A4 PDF, ~15-25 pages. Same restrained design language as the existing white paper (Anthropic-ish: ivory background, slate text, single coral accent, generous whitespace). Use reportlab — it's already installed.

Output file: `Context Engine Benchmark Report v1.0.pdf` at the repo root.

## Source files (all in `app/bench/`)

| File                                  | What it is                                                                        |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `tasks.json`                          | The 15-task corpus                                                                |
| `gold-answers.json`                   | Per-task must/may/forbidden facts + expected_sources for retrieval scoring        |
| `results-latest.json`                 | v1.1: 15-task token-only run, no quality grading                                  |
| `results-graded-sample.json`          | v1.1: 5-task session-as-judge grading (holistic 1-10)                             |
| `results-v12-final.json`              | v1.2: 5-task subset with deterministic gold scoring + session decomposed rubric   |
| `results-v13.json`                    | v1.3: raw 15-task × 3-mode × 3-judge-run rows                                     |
| `results-v13-final.json`              | v1.3: aggregated v1.3 with paired comparisons, retrieval quality, lift efficiency |
| `responses-v13.json`                  | All 45 task-model responses (Sonnet 4.5) captured during v1.3                     |
| `contexts/manifest.json`              | Per-task smart and search context token counts                                    |
| `contexts/*.smart.md` / `*.search.md` | The actual contexts each mode injected                                            |

## Source PDFs (read for cross-reference, especially Sections 11, 19, 32, 34)

| File                                  | What it is                                  |
| ------------------------------------- | ------------------------------------------- |
| `Context Engine White Paper V1.pdf`   | Original paper (41p)                        |
| `Context Engine White Paper V1.1.pdf` | V1 + Appendix A (v1.1 benchmark)            |
| `Context Engine White Paper V1.2.pdf` | V1.1 + Appendix B (v1.2 critique-addressed) |
| `Context Engine White Paper V1.3.pdf` | V1.2 + Appendix C (v1.3 full pipeline)      |

## The narrative arc — handle this carefully

**v1.1** (5-task, session-as-judge, holistic 1-10): "Smart 9.0/10, Search 7.6/10, Smart-Compile saves 65% tokens with no quality cost." → optimistic, claimed Hypothesis 1 holds.

**v1.2** (5-task, gold facts + decomposed rubric, still session-judge): added no-context baseline. Found Smart adds +20 composite points over no-context at ~58k tokens; Search adds +6.7 at ~700 tokens. More sober but still positive.

**v1.3** (15-task, Sonnet task model, Haiku judge × 3 runs, full pipeline): **Smart Compile in its v0.3.x form NET-DEGRADES quality vs no-context** — loses on 8/15 tasks, mean delta -1.27 composite/15. Search also slightly under-performs no-context (-0.80). Both v1.1 and v1.2 headlines retracted.

**Why the change**: same-model self-evaluation in v1.1/v1.2 under-penalised verbose, on-style outputs that drift away from the task. A cross-model judge (Haiku, smaller than the Sonnet task model) caught the failure. The single worst case: `comfy-prompt-fantasy` smart-mode — given 36k tokens of skill context, Sonnet wrote a philosophical essay titled "Mystral Dusk" instead of a ComfyUI prompt.

**What v1.3 _validates_** (don't bury this):

- Token reduction is real (Smart -60%, Search -99.5%) — deterministic, judge-independent
- Section 11's prediction (multi-resolution packaging is necessary) is empirically confirmed
- Retrieval quality (P@8 = 0.23, 5/15 complete misses) is the bottleneck — Phase 2 in build roadmap (dedup + rank) is the highest-leverage fix
- The brokered-context architecture is right; the v0.3.x _implementation_ isn't done

## Suggested visualisations

Each chart should have a one-sentence caption that names the takeaway, not just labels the axes.

### Chart 1 — Token cost by mode (log-scale bar chart)

- X: mode (raw_all baseline, smart, search, no_context)
- Y: median input tokens, log scale
- Bars: raw_all 186,654 / smart 74,279 / search 903 / no_context 29
- Takeaway caption: "Four orders of magnitude separate the cheapest path from the naive baseline."

### Chart 2 — Composite quality per mode, all 15 tasks (grouped bar or heatmap)

- X: 15 task IDs
- Y: composite quality (0-15 scale)
- 3 bars/cells per task: no_context, smart, search
- Source: `results-v13-final.json` → `detail[i].{mode}.composite_15`
- Takeaway: "Smart Compile loses on 8 of 15 tasks despite costing 2,500× more tokens than no-context."

### Chart 3 — Paired delta plot (waterfall or dot)

- X: 15 tasks, sorted by smart-vs-no_context delta
- Y: delta in composite points (positive = Smart wins)
- Source: `results-v13-final.json` → `detail` → compute per-task `smart.composite_15 - no_context.composite_15`
- Annotate `comfy-prompt-fantasy` (worst, -10) and `memory-consolidate` (best, +4)
- Takeaway: "When Smart Compile fails, it fails catastrophically; when it wins, it wins modestly."

### Chart 4 — Hallucination distribution (box plot or strip)

- X: mode
- Y: hallucinations_mean (judge runs averaged) per task
- Show: no_context cluster around 0.98, smart at 1.49 mean with high outliers (4.33 on claude-api-migrate), search at 1.20
- Takeaway: "Loading more context creates more fabricated facts, not fewer."

### Chart 5 — Retrieval quality predicts quality outcome (scatter)

- X: Precision@8 per task (search mode, from `results-v13-final.json` → `retrieval_quality`)
- Y: search-mode composite quality delta vs no_context
- Trend line + labels for outliers
- Takeaway: "Where retrieval surfaces relevant chunks, search adds value; where it misses, search degrades."

### Chart 6 — Cost per quality-point-of-lift over no-context

- Bar: smart vs search
- Y: tokens per +1 composite point of lift (when lift > 0)
- Smart: 80,373 tk/+1pt | Search: 1,052 tk/+1pt | also show count of "negative-lift" tasks (smart 8/15, search 8/15)
- Takeaway: "Search is 76× more efficient per quality-point of lift, but both modes show negative lift on the majority of tasks."

### Chart 7 — Methodology change vs result (narrative figure)

- Three rows (v1.1 / v1.2 / v1.3), three columns showing: N, judge config, headline composite quality of Smart
- Visually emphasises how methodology drove the result
- Takeaway: "Self-evaluation bias accounted for ~3 composite points of inflation in the v1.1 result."

### Chart 8 — Latency & cost per mode (small multiples)

- Two side-by-side bars: median latency (ms) and total cost (USD) per mode for the v1.3 run
- Source: `results-v13-final.json` → `by_mode` per-mode `latency_ms_median`, `cost_usd_total`

## Tables to include (verbatim from existing appendices)

1. **Per-mode aggregate, all 15 tasks** (from Appendix C Table C.1)
2. **Paired comparison** (Smart/Search vs no_context, Smart vs Search) (Appendix C Table C.2)
3. **Per-task detail** (15 rows × 3 modes × {tokens, cov%, bonus%, fact/spec/comp/halluc, composite/15}) — pull from `results-v13-final.json` → `detail`
4. **Retrieval quality per task** (P@8, R@8, MRR, hits) — pull from `results-v13.json` → rows where mode == "search" → `retrieval_quality`
5. **Methodology evolution** (v1.1 → v1.2 → v1.3 differences in N, judge, rubric, gold answers, modes measured) — synthesise

## Structure suggestion (15-25 pages)

1. Executive summary (1 page) — headline numbers, big finding, the methodology-changed-the-result story
2. Methodology evolution (2 pages) — what each iteration changed and why
3. Headline results — v1.3 numbers (3-4 pages) — tables 1, 2, charts 1, 2, 3
4. Cross-reference: white paper predictions vs v1.3 measurements (2 pages) — especially Section 11 vindication, Hypothesis 1 retraction
5. The failure mode in detail (1-2 pages) — comfy-prompt-fantasy Mystral Dusk case study (the actual responses are in `responses-v13.json`)
6. Hallucinations + retrieval-quality findings (2-3 pages) — charts 4, 5, table 4
7. What's validated, what's retracted (1 page) — the honest list
8. Implications for build roadmap (1-2 pages) — Phase 2 urgency, re-scoping Phase 3, retrieval-quality dashboard
9. Honest limitations still standing (1 page) — single judge family, single task model, etc.
10. Appendix: full per-task detail table

## Things the writeup MUST get right

- **Don't bury the retraction.** v1.1 said "Smart holds at 9.0/10". v1.3 says Smart loses on 8/15 tasks. Both numbers are in the data; the writeup needs to say _why_ they differ (judge bias).
- **Don't bury the validation either.** Token reduction is real and large. Section 11 prediction is empirically confirmed. The architecture is right.
- **The product framing matters.** Current Smart Compile (v0.3.x) is a token-saving feature, not a quality-improving one. Recommending it to users today is recommending a quality regression on most tasks. That's the honest framing; don't soften it.
- **The roadmap framing matters.** Phase 2 (dedup + rank) and the Section 11 chunked-smart-compile aren't nice-to-haves; they're load-bearing for the product's value claim. Make that visible.

## Files Codex should not modify

The existing `Context Engine White Paper V1.x.pdf` series is the historical record. Don't rebuild those. Don't modify `tokenomics.py`, `grade_v2.py`, `run_v13.py`, `aggregate_v13.py`, or any of the JSON result files. Read-only.

## Files Codex creates

- `Context Engine Benchmark Report v1.0.pdf` (the main deliverable, at repo root)
- `app/bench/charts/*.png` (rendered chart images, kept around for re-use)
- `app/bench/build_report.py` (the reportlab/matplotlib script that produces the PDF; future-runnable)

## Done criteria

- PDF builds end-to-end from a single `python app/bench/build_report.py` invocation
- All 8 charts present, each with a take-away caption (not a label)
- All 5 tables present
- The v1.1 → v1.3 retraction is clearly explained, not euphemistic
- Section 11 vindication and Hypothesis 1 retraction both flagged in the executive summary
- File size under 10 MB (use 200 DPI for charts, not 600)
