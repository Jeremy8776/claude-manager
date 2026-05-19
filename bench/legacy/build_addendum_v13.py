#!/usr/bin/env python3
"""
Build Appendix C — v1.3 results. Honest correction of v1.1/v1.2's framing.
"""
from __future__ import annotations
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from PyPDF2 import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "app" / "bench"
ADDENDUM_PDF = BENCH / "addendum-v13.pdf"
SOURCE_PDF = ROOT / "Context Engine White Paper V1.2.pdf"
OUTPUT_PDF = ROOT / "Context Engine White Paper V1.3.pdf"

data = json.loads((BENCH / "results-v13-final.json").read_text(encoding="utf-8"))

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                    fontSize=18, leading=22, spaceAfter=12, textColor=colors.HexColor("#191919"))
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, leading=17, spaceBefore=14, spaceAfter=6,
                    textColor=colors.HexColor("#191919"))
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                    fontSize=11, leading=14, spaceBefore=8, spaceAfter=4,
                    textColor=colors.HexColor("#3a3a3a"))
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica",
                      fontSize=10.5, leading=14, spaceAfter=6, alignment=TA_LEFT,
                      textColor=colors.HexColor("#191919"))
QUOTE = ParagraphStyle("QUOTE", parent=BODY, leftIndent=14, rightIndent=14,
                       fontName="Helvetica-Oblique", textColor=colors.HexColor("#3a3a3a"),
                       spaceBefore=4, spaceAfter=10)
CAPTION = ParagraphStyle("CAPTION", parent=BODY, fontSize=9, leading=12,
                         textColor=colors.HexColor("#666666"), spaceAfter=10)
CODE = ParagraphStyle("CODE", parent=BODY, fontName="Courier", fontSize=9, leading=12,
                      leftIndent=10, textColor=colors.HexColor("#191919"))


def fmt(n): return f"{n:,}" if isinstance(n, (int, float)) else str(n)


def base_table(headers, rows, col_widths):
    t = Table([headers] + rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191919")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ee")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#191919")),
    ]))
    return t


story = []

story.append(Paragraph("Appendix C", H3))
story.append(Paragraph("Tokenomics Benchmark v1.3 — Full Pipeline, Cross-Model Judging", H1))
story.append(Paragraph(
    f"Added in v1.3. First full-pipeline run with a real task model "
    f"({data['task_model']}) and a cross-size judge ({data['judge_model']} "
    f"× {data['judge_runs']} runs) across all 15 corpus tasks. Total API cost: "
    f"~${sum(m['cost_usd_total'] for m in data['by_mode'].values()):.2f}. "
    f"<b>Result is materially different from v1.1 / v1.2 — and the difference is the point.</b> "
    "The earlier appendices used a session-as-judge which under-penalised the task model's "
    "own outputs; a separate Haiku judge with three runs per response exposes failure modes "
    "the earlier methodology missed.",
    QUOTE,
))

# C.1 Headline
story.append(Paragraph("C.1 Headline finding", H2))
sv = data["paired"]["smart_vs_no_context"]
srv = data["paired"]["search_vs_no_context"]
story.append(Paragraph(
    f"<b>In its v0.3.1 form, Smart Compile net-degrades quality.</b> "
    f"Mean composite delta vs no-context: <b>{sv['mean_delta']:+.2f} points on a 15-point scale</b>, "
    f"with {sv['wins']} wins, {sv['ties']} ties, and <b>{sv['losses']} losses</b> out of 15 tasks. "
    f"MCP Search also under-performs no-context on this corpus: mean delta "
    f"<b>{srv['mean_delta']:+.2f}</b> ({srv['wins']} wins / {srv['ties']} ties / {srv['losses']} losses). "
    "The naive 'load relevant skills in full as system prompt' implementation of "
    "Smart Compile hits an attention-dilution regime modern hosted models don't experience "
    "when given no skill context at all.",
    BODY,
))
story.append(Paragraph(
    "This appears to <b>contradict v1.1's headline</b> ('Smart holds at 9.0/10 across the "
    "subset'). It does not contradict the paper's thesis — Section 11 (Multi-Resolution "
    "Context Packaging) explicitly predicts this failure mode and argues that the "
    "implementation must chunk and summarise skills before injection. The v1.3 result is "
    "<b>empirical validation of the paper's own Section 11 prediction</b> and a clear signal "
    "that Smart Compile alone, without the chunking layer the paper specifies, is the wrong "
    "way to deliver context.",
    BODY,
))

# C.2 Aggregate table
story.append(Paragraph("C.2 Per-mode aggregates (N=15 tasks, 3 judge runs each)", H2))
mode_rows = []
for m in ("no_context", "smart", "search"):
    a = data["by_mode"][m]
    mode_rows.append([
        m,
        fmt(a["input_tokens_median"]),
        f"{a['coverage_pct_mean']:.0f}%",
        f"{a['bonus_pct_mean']:.0f}%",
        f"{a['factual_median']:.1f}",
        f"{a['specific_median']:.1f}",
        f"{a['complete_median']:.1f}",
        f"{a['hallucinations_mean']:.2f}",
        f"{a['composite_15_median']:.1f}",
        f"${a['cost_usd_total']:.2f}",
    ])
story.append(base_table(
    ["Mode", "med tk", "Cov", "Bonus", "Fact", "Spec", "Comp", "Halluc", "Comp/15", "Cost"],
    mode_rows,
    [22*mm, 16*mm, 12*mm, 14*mm, 13*mm, 13*mm, 13*mm, 16*mm, 17*mm, 16*mm],
))
story.append(Paragraph(
    "Table C.1. Per-mode aggregates. Fact/Spec/Comp are median axes (1-5) across judge runs. "
    "Halluc is mean fabricated facts per response. Comp/15 is median composite (sum of axes). "
    "Cost is total API spend for the corpus at this mode.",
    CAPTION,
))

# Paired comparisons
story.append(Paragraph("C.3 Paired comparisons (per-task delta)", H2))
pc_rows = []
for k in ("smart_vs_no_context", "search_vs_no_context", "smart_vs_search"):
    p = data["paired"][k]
    worst = p["worst_task"][0] if p["worst_task"] else "—"
    best = p["best_task"][0] if p["best_task"] else "—"
    pc_rows.append([
        k.replace("_", " "),
        str(p["n"]),
        f"{p['mean_delta']:+.2f}",
        f"{p['wins']}/{p['ties']}/{p['losses']}",
        worst,
        best,
    ])
story.append(base_table(
    ["Comparison", "n", "mean delta", "W/T/L", "Worst task", "Best task"],
    pc_rows,
    [42*mm, 10*mm, 22*mm, 20*mm, 38*mm, 38*mm],
))
story.append(Paragraph(
    "Table C.2. Paired per-task deltas, composite (0-15 scale). 'Worst task' is the task "
    "with the largest negative delta; 'best' the largest positive. Smart Compile loses on "
    "more than half the corpus.",
    CAPTION,
))

story.append(PageBreak())

# C.4 What happens when smart loses?
story.append(Paragraph("C.4 The failure mode, concretely", H2))
story.append(Paragraph(
    "The single worst Smart-vs-no_context result was <b>comfy-prompt-fantasy "
    "(delta = -10)</b>. The task asks for a ComfyUI prompt. The no-context response delivered "
    "exactly that — positive prompt, negative prompt, sampler / steps / CFG / resolution / "
    "model recommendations (Haiku judge: factual=4 specific=5 complete=4, hallucinations=1).",
    BODY,
))
story.append(Paragraph(
    "The smart-mode response, given 36k tokens of skill context including theme-factory "
    "themes and prompt-builder bodies, instead wrote a 700-token philosophical essay called "
    "<i>'Mystral Dusk: an algorithmic philosophy of atmospheric emergence and temporal "
    "liminal states.'</i> It described the aesthetic at length, never produced an actual "
    "prompt, never named a sampler or resolution. (Haiku judge: factual=1 specific=1 "
    "complete=1, hallucinations=2.67.) The user could not run anything from the response.",
    BODY,
))
story.append(Paragraph(
    "This is not a quirk. It's the predicted-by-Section-11 attention-dilution regime: when "
    "a model is given many full skill bodies as a single system prompt, it picks up on the "
    "meta-content (style discussion, philosophy of design, when-to-use prose) and produces "
    "meta-content of its own, drifting away from the concrete task. The smaller, terser "
    "search-mode context (1.1k tokens) does not trigger this, and neither does no-context.",
    BODY,
))

# C.5 Retrieval quality
story.append(Paragraph("C.5 Retrieval quality (search mode)", H2))
r = data["retrieval_quality"]
story.append(Paragraph(
    f"Precision@8 mean = <b>{r['precision_at_k_mean']:.2f}</b>  ·  "
    f"Recall@8 mean = <b>{r['recall_at_k_mean']:.2f}</b>  ·  "
    f"MRR mean = <b>{r['mrr_mean']:.2f}</b>.  "
    f"<b>{len(r['complete_misses'])} of {r['n']} tasks</b> had complete retrieval misses — "
    "zero relevant chunks in the top 8. Search quality is the bottleneck.",
    BODY,
))
story.append(Paragraph(
    "Where retrieval works (brand-poster P@8=0.5, R@8=1.0, MRR=1.0) the search-mode response "
    "matches or exceeds no-context. Where retrieval fails completely (5 tasks including "
    "internal-release-note, pc-cpu-hog, claude-api-migrate) the search-mode response "
    "degrades. The deterministic Precision@K predictor identifies these cases before the LLM "
    "is invoked — improving retrieval is the highest-leverage fix in the v1.x roadmap.",
    BODY,
))

# C.6 Why v1.1 and v1.2 looked different
story.append(Paragraph("C.6 Why v1.1 and v1.2 looked positive", H2))
story.append(Paragraph(
    "v1.1 used a single Claude session as both task model and judge, scoring on a holistic "
    "1-10 rubric without gold facts or hallucination counting. v1.2 added gold facts and a "
    "decomposed rubric but kept session-as-judge for the LLM axes. Both runs scored Smart at "
    "100% composite on the 5-task subset.",
    BODY,
))
story.append(Paragraph(
    "v1.3's three changes — different judge model (Haiku, not Sonnet), three runs per "
    "response (variance instead of point estimates), and full 15-task coverage — "
    "uncovered the failure mode. Same-model self-evaluation systematically under-penalises "
    "verbose, on-style outputs that miss the task; cross-model judging exposes them. The "
    "v1.1 and v1.2 numbers were not lies, but they were biased in a predictable direction.",
    BODY,
))

# C.7 What the paper should now claim
story.append(Paragraph("C.7 What the paper should claim", H2))
story.append(Paragraph(
    "<b>Validated claims</b> (from this run):",
    BODY,
))
validated = [
    "<b>Token reduction works.</b> Smart cuts naive baseline by ~60%; Search by 99.5%. These "
    "are reproducible, deterministic measurements unaffected by judging.",
    "<b>Section 11 (Multi-Resolution Packaging) is necessary, not optional.</b> Full-body "
    "skill injection produces measurable attention-dilution failures that no-context "
    "responses do not exhibit. This is the strongest empirical signal in the appendix.",
    "<b>Retrieval quality is the bottleneck.</b> Precision@8 of 0.23 and 5/15 complete "
    "misses cap how much value Search can deliver. Improving retrieval (Phase 2 in the "
    "build roadmap) has the highest expected payoff.",
    "<b>The brokered-context architecture is correct; the v0.3.x implementation isn't done.</b> "
    "CE's job is to broker context. v0.3.x brokers by selection + retrieval. The data says it "
    "also needs to broker by summarising, chunking, deduplicating, and reranking before "
    "anything reaches the model.",
]
for v in validated:
    story.append(Paragraph(f"• {v}", BODY))

story.append(Paragraph("<b>Retracted or revised claims</b> (vs v1.1):", BODY))
retracted = [
    "Smart Compile does NOT 'hold quality flat at 9.0/10'. It loses 8/15 tasks on composite "
    "quality vs no-context under a cross-model judge. Hypothesis 1 is contradicted in the "
    "v0.3.x implementation form.",
    "MCP Search does NOT 'add value' on every task; it adds value where retrieval succeeds "
    "(2/15 clear wins, 5/15 ties at no-context-equivalent quality) and degrades quality "
    "where retrieval fails. Both wins and losses correlate with Precision@K.",
    "The 'tokens per quality point' framing was misleading at face value. The right number "
    "is tokens per quality point <i>of lift</i> over no-context — and that number is negative "
    "for Smart on most tasks (no lift achieved at any token cost).",
]
for v in retracted:
    story.append(Paragraph(f"• {v}", BODY))

# C.8 Implications for build roadmap
story.append(Paragraph("C.8 Implications for the build roadmap (Section 34)", H2))
story.append(Paragraph(
    "<b>Phase 2 (Dedup and Rank) gains urgency.</b> Reducing skill-body noise via dedup, and "
    "promoting the most-useful chunks via reranking, directly addresses the attention-"
    "dilution failures observed here. The dedup report should run before any Smart Compile "
    "output is materialised.",
    BODY,
))
story.append(Paragraph(
    "<b>Phase 3 (Smart Compile) needs to be re-scoped.</b> The current implementation selects "
    "skills, then loads their full bodies. It should select skills, then load their compressed "
    "summaries plus relevant chunks — the multi-resolution packaging from Section 11. Until "
    "that ships, recommending Smart Compile to users is recommending a quality regression on "
    "more than half their tasks.",
    BODY,
))
story.append(Paragraph(
    "<b>Phase 1 (Vector Foundation) needs a retrieval-quality dashboard.</b> P@K, R@K, and "
    "MRR per task should be visible in the CE UI. Users (and the team) should see when "
    "retrieval is failing for a task class, not discover it via downstream quality drops.",
    BODY,
))

# C.9 Methodology + reproducibility
story.append(Paragraph("C.9 Methodology and reproducibility", H2))
story.append(Paragraph(
    f"Pipeline: <font face='Courier'>app/bench/run_v13.py</font> + "
    f"<font face='Courier'>aggregate_v13.py</font>. Task model {data['task_model']}; "
    f"judge {data['judge_model']} × {data['judge_runs']} runs. 15 tasks × 3 modes = 45 task "
    "calls + 135 judge calls = 180 API calls. Deterministic scoring (fact recall + retrieval "
    "quality) runs alongside LLM judging — same numbers reproducible without any API key.",
    BODY,
))
story.append(Paragraph("Reproduce:", BODY))
story.append(Paragraph("export ANTHROPIC_API_KEY=...", CODE))
story.append(Paragraph("python bench/fetch_contexts.py     # rebuild contexts/", CODE))
story.append(Paragraph("python bench/run_v13.py            # full pipeline", CODE))
story.append(Paragraph("python bench/aggregate_v13.py      # summary + per-task table", CODE))

story.append(Paragraph("C.10 Honest limitations still standing", H2))
limits = [
    "<b>Single judge family.</b> Anthropic Haiku × 3 runs gives variance but doesn't break "
    "intra-family bias. Adding GPT-4o-mini or Gemini Flash as a second judge is the v1.4 step.",
    "<b>Sonnet as the task model.</b> Smaller models may benefit more from injected context — "
    "the attention-dilution regime is model-size-dependent. Re-run on Haiku and on a local "
    "8B model to test Hypothesis 3.",
    "<b>Skill corpus written for retrieval, not injection.</b> Many skill bodies have meta-"
    "prose (when to use, anti-patterns, lifecycle notes) that hurts when shown in full. "
    "Authoring skills with both retrieval-shape and injection-shape variants is on the table.",
    "<b>One retrieval call per task.</b> Real MCP hosts iterate; production search traffic "
    "may close some of the search-mode gap observed here.",
]
for c in limits:
    story.append(Paragraph(f"• {c}", BODY))

story.append(Spacer(1, 14))
story.append(Paragraph(
    "<i>The v1.3 finding is the most useful result this benchmark has produced. It validates "
    "the paper's core architectural thesis (a context broker is needed; multi-resolution "
    "packaging is necessary) while invalidating the current implementation's claim to "
    "deliver that thesis. The right product response is to ship Phase 2 (Dedup and Rank) and "
    "the multi-resolution layer before claiming Smart Compile is production-ready, and to "
    "communicate to users that v0.3.x's Smart Compile is a token-saving feature, not a "
    "quality-improving one. The benchmark itself now stands as the test these phases must "
    "pass to ship.</i>",
    QUOTE,
))


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawString(20*mm, 12*mm, "Context Engine White Paper — v1.3 Appendix C")
    canvas.drawRightString(A4[0] - 20*mm, 12*mm, f"C-{doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(ADDENDUM_PDF), pagesize=A4,
    leftMargin=22*mm, rightMargin=22*mm, topMargin=22*mm, bottomMargin=22*mm,
    title="Context Engine White Paper v1.3 — Appendix C",
    author="Jeremy Walder-Willows",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"Wrote: {ADDENDUM_PDF}")

writer = PdfWriter()
for p in PdfReader(str(SOURCE_PDF)).pages:
    writer.add_page(p)
for p in PdfReader(str(ADDENDUM_PDF)).pages:
    writer.add_page(p)
with OUTPUT_PDF.open("wb") as f:
    writer.write(f)
print(f"Wrote: {OUTPUT_PDF}")
