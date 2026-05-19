#!/usr/bin/env python3
"""
Build Appendix B for the v1.2 white paper.

Appendix B replaces the v1.1 measurement methodology with the critique-addressed
version:
 - Gold-answer fact recall (deterministic)
 - Decomposed rubric (factual / specific / complete / hallucinations)
 - No-context baseline column
 - Retrieval quality (Precision@K / Recall@K / MRR)
 - Latency + cost
 - Failure-mode taxonomy
 - Multi-judge support (architecture in code; v1.2 results are still single-judge
   pending API keys, with a flagged caveat)

Source: bench/results-v12-final.json
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
ADDENDUM_PDF = BENCH / "addendum-v12.pdf"
SOURCE_PDF = ROOT / "Context Engine White Paper V1.1.pdf"
OUTPUT_PDF = ROOT / "Context Engine White Paper V1.2.pdf"

data = json.loads((BENCH / "results-v12-final.json").read_text(encoding="utf-8"))
s = data["summary"]
rows = data["rows"]

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


def kv_table(pairs, col_widths=(60*mm, 100*mm)):
    t = Table(pairs, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191919")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ee")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


story = []

story.append(Paragraph("Appendix B", H3))
story.append(Paragraph("Tokenomics Benchmark v1.2 — Critique-Addressed Methodology", H1))
story.append(Paragraph(
    "Added in v1.2 of this paper. Supersedes Appendix A's measurement methodology while "
    "preserving A as the historical record. The v1.1 critique identified seven concrete "
    "weaknesses in A's grading apparatus — same-model self-evaluation, single judge run, "
    "no gold answers, no no-context baseline, no retrieval-quality scoring, holistic "
    "rubric, single task model. B addresses all of these in the harness, and reports the "
    "in-session results from the subset that can be measured without external API keys.",
    QUOTE,
))

# ---------- B.1 What changed ----------
story.append(Paragraph("B.1 What changed between A and B", H2))

changes = [
    ("Gold-answer fact recall",
     "Per-task labeled facts (must_include, may_include, forbidden) in "
     "bench/gold-answers.json. Scoring is deterministic keyword-match with negation "
     "guarding and an 'all'/'any' match mode per fact. Coverage % is now a measurement, not an opinion."),
    ("Decomposed rubric",
     "Four independent axes — factual_correctness (1-5), specificity (1-5), "
     "completeness (1-5), hallucination_count (integer) — replacing the single "
     "holistic 1-10 score from A. Hallucination as a count, not a grade, exposes the "
     "failure mode MCP hosts care about most."),
    ("No-context baseline",
     "Fourth measurement path: same task, zero skill context. Distinguishes 'CE added "
     "value' from 'the model already knew this'. Without this column, A's quality "
     "numbers were unanchored."),
    ("Retrieval quality (Precision@K, Recall@K, MRR)",
     "Labeled expected_sources per task in gold-answers.json. Scores search results "
     "before any LLM call. Predicts when search will underperform without spending tokens."),
    ("Latency + cost columns",
     "End-to-end milliseconds per call, dollar cost from a per-model price table. "
     "Token counts don't equal pricing; reporting both removes the ambiguity."),
    ("Failure-mode taxonomy",
     "Enumerated tags per task (wrong_os, wrong_sdk, missing_loop, no_safety_step, etc) "
     "inferred from gold-miss patterns. Failures get categorised, not just counted."),
    ("Multi-judge cross-family architecture",
     "grade_v2.py supports anthropic + openai judges, N runs each, with median + IQR "
     "aggregation. In v1.2 the in-session run still uses a single session judge (no "
     "external API keys available); the harness is wired for cross-family multi-run "
     "to break self-evaluation bias as soon as keys are in scope."),
]
for title, body in changes:
    story.append(Paragraph(f"<b>{title}.</b> {body}", BODY))

# ---------- B.2 Results table ----------
story.append(PageBreak())
story.append(Paragraph("B.2 Results — 5-task subset, three context paths", H2))
story.append(Paragraph(
    "Same 5 representative tasks as Appendix A (system-ops, image-gen, claude-api, "
    "design, comms). Now scored against gold facts and on the decomposed rubric, with "
    "the no-context baseline as a fourth row per task.",
    BODY,
))

t_rows = [["Task", "Mode", "Tokens", "Cov", "Bonus", "Fact", "Spec", "Comp", "Comp%"]]
for r in rows:
    t_rows.append([
        r["task_id"],
        r["mode"],
        fmt(r["input_tokens"]),
        f"{r['fact_coverage_pct']:.0f}%",
        f"{r['fact_bonus_pct']:.0f}%",
        str(r["factual"]),
        str(r["specific"]),
        str(r["complete"]),
        f"{r['composite_pct']:.0f}%",
    ])
t = Table(t_rows, colWidths=[40*mm, 18*mm, 18*mm, 12*mm, 14*mm, 12*mm, 12*mm, 12*mm, 16*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191919")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ee")]),
    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#191919")),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(t)
story.append(Paragraph(
    "Table B.1. Per-task per-mode results. Tokens = system-prompt context tokens. "
    "Cov = must_include facts hit (deterministic). Bonus = may_include facts hit "
    "(deterministic). Fact / Spec / Comp = decomposed rubric axes 1-5 (session-judged). "
    "Comp% = mean of three axes normalised to 100.",
    CAPTION,
))

# ---------- B.3 Per-mode aggregates ----------
story.append(Paragraph("B.3 Per-mode aggregates (5 tasks)", H2))

agg_rows = [["Mode", "Median tk", "Saving vs raw_all", "Cov", "Bonus", "Composite Q", "Tokens / Q-pt"]]
for k in ("no_context", "smart", "search"):
    tk = s["tokens"]["by_mode_input_tokens"][k]["median"]
    cov = s["fact_recall"]["coverage_must_include_pct"][k]["mean"]
    bonus = s["fact_recall"]["bonus_may_include_pct"][k]["mean"]
    comp = s["decomposed_rubric"]["composite_pct"][k]["median"]
    tpqp = s["tokens_per_quality_point"][k]
    saving = (f"{round(100 * (1 - tk / 186654), 1)}%"
              if k != "no_context" else "n/a")
    agg_rows.append([
        k, fmt(tk), saving, f"{cov:.1f}%", f"{bonus:.1f}%",
        f"{comp:.1f}%", fmt(tpqp),
    ])
agg = Table(agg_rows, colWidths=[26*mm, 24*mm, 30*mm, 16*mm, 18*mm, 26*mm, 26*mm], repeatRows=1)
agg.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191919")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ee")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(agg)
story.append(Paragraph(
    "Table B.2. Aggregate per mode across the 5-task subset. Cov and Bonus are means; "
    "all other columns are medians.",
    CAPTION,
))

story.append(Paragraph("B.4 Retrieval quality (search mode)", H2))
retr = s["retrieval_quality_mean"]
story.append(kv_table([
    ["Metric", "Mean (5 tasks)"],
    ["Precision@8", f"{retr['precision_at_k']:.2f}"],
    ["Recall@8",    f"{retr['recall_at_k']:.2f}"],
    ["MRR",         f"{retr['mrr']:.2f}"],
]))
story.append(Paragraph(
    "Table B.3. Retrieval-quality metrics from MCP search vs the labeled "
    "expected_sources gold set. Per-task: brand-poster scores cleanly "
    "(P@8=0.50, R@8=1.00, MRR=1.00 — both relevant skills appear at ranks 1 and 2). "
    "internal-release-note is a complete miss (P@8=0, R@8=0) — neither internal-comms "
    "nor slack-gif-creator appears in the top 8. This metric predicts the observed "
    "quality drop on that task without spending an LLM call.",
    CAPTION,
))

story.append(PageBreak())

# ---------- B.5 Interpretation ----------
story.append(Paragraph("B.5 Interpretation", H2))

h = s["headline"]
story.append(Paragraph(
    f"<b>Smart Compile delivers {h['smart_saving_vs_raw_all_pct']}% token savings "
    f"vs the raw_all baseline and adds {h['smart_quality_lift_vs_no_context_pct']} composite "
    f"quality points above the no-context baseline.</b> Quality is a flat 100% on all 5 "
    "tasks — Smart consistently brings every bonus fact (cache_control, AUMID, exact hex codes, "
    "env var names). Cost: ~3,876 tokens per quality point above no-context.",
    BODY,
))

story.append(Paragraph(
    f"<b>MCP Search delivers {h['search_saving_vs_raw_all_pct']}% token savings and adds "
    f"only {h['search_quality_lift_vs_no_context_pct']} composite quality points above no-context.</b> "
    "This is a more sober result than v1.1 suggested. On 4 of 5 tasks, search adds 5-15 "
    "quality points; on internal-release-note it adds zero because retrieval missed the "
    "relevant skills entirely. Cost: ~58 tokens per quality point above no-context — "
    "67× more efficient than Smart per quality-point of lift.",
    BODY,
))

story.append(Paragraph(
    "<b>The honest framing</b> the v1.2 numbers force: a modern hosted model with general "
    "world knowledge already gets to 80% composite on these tasks with zero context. CE "
    "Smart Compile closes the remaining 20% reliably at a known token cost. CE Search "
    "closes about a third of that remaining gap at a tiny token cost, but the gap it closes "
    "is conditional on retrieval succeeding — which Precision@K predicts before the LLM "
    "is invoked.",
    BODY,
))

story.append(Paragraph(
    "The Hypothesis 1 claim ('Smart Compile reduces token load without reducing task quality') "
    "remains supported and is now measured against four axes instead of one. Hypothesis 2 "
    "(multi-resolution packaging) is partially probed by Retrieval Quality — search loses where "
    "the relevant chunks aren't surfaced. Hypothesis 3 (model-aware budgets) and "
    "Hypothesis 5 (usage-learned reranking) remain unmeasured.",
    BODY,
))

# ---------- B.6 Known limitations ----------
story.append(Paragraph("B.6 Known limitations of v1.2 (what's still pending)", H2))

caveats = [
    "<b>Single judge, single run.</b> grade_v2.py supports anthropic + openai judges with "
    "N=3 runs each and median+IQR aggregation, but the in-session run uses one judge "
    "(the same Claude session) once. Cross-family multi-run grading is the v1.3 milestone "
    "and requires only API keys, not new code.",
    "<b>5-task quality subset.</b> Gold answers are written for all 15 corpus tasks; "
    "response capture and grading covers 5. Expanding to 15 is a 2-hour task with a key.",
    "<b>Single task model.</b> claude-sonnet-4-5 only. Hypothesis 3 demands the same corpus "
    "across Haiku / Sonnet / a local 8B model to test whether smaller models benefit more "
    "from CE. Wired in PRICING table; runner is one CLI flag away.",
    "<b>One retrieval call per task.</b> Real MCP hosts iterate; production search traffic "
    "sits between our Smart and Search numbers. A multi-call host simulator is on the "
    "v1.3 backlog.",
    "<b>Gold-answer authoring bias.</b> Gold facts were written by the same person who "
    "wrote the tasks. Independent authoring (e.g. via crowdsourced labels) would harden "
    "the must_include set.",
    "<b>Task corpus is single-user.</b> 116 skills, 15 tasks, all reflecting one user's "
    "workload. Cross-user generalisation requires either a community corpus or telemetry-"
    "sampled real prompts.",
]
for c in caveats:
    story.append(Paragraph(f"• {c}", BODY))

story.append(Paragraph("B.7 Reproducibility", H2))
story.append(Paragraph("Full v1.2 pipeline:", BODY))
story.append(Paragraph("python bench/tokenomics.py                                   # token-only, all 15", CODE))
story.append(Paragraph("python bench/fetch_contexts.py                               # pre-fetch contexts to disk", CODE))
story.append(Paragraph("python bench/run_v12.py --responses bench/responses-v12.json # deterministic scoring", CODE))
story.append(Paragraph("python bench/run_v12.py --judges anthropic:haiku,openai:gpt-4o-mini --runs 3   # full v1.3 with API keys", CODE))
story.append(Paragraph("python bench/aggregate_v12.py                                # final summary + JSON", CODE))
story.append(Paragraph(
    "Source files: <font face='Courier'>bench/gold-answers.json</font>, "
    "<font face='Courier'>bench/grade_v2.py</font>, "
    "<font face='Courier'>bench/run_v12.py</font>, "
    "<font face='Courier'>bench/aggregate_v12.py</font>, "
    "<font face='Courier'>bench/responses-v12.json</font>, "
    "<font face='Courier'>bench/session_grades.json</font>, "
    "<font face='Courier'>bench/results-v12-final.json</font>. "
    "All in the repo; no external services required for the deterministic half of the pipeline.",
    BODY,
))

story.append(Spacer(1, 14))
story.append(Paragraph(
    "<i>The headline-defensible finding the v1.2 numbers support: a brokered context layer "
    "(Smart Compile) buys a measurable, consistent ~20-point composite quality lift over "
    "zero-context modern hosted models at ~69% of the naive baseline's token cost. MCP "
    "search retrieves at a fraction of a percent of the baseline cost but its quality "
    "contribution is conditional on retrieval success, which Precision@K predicts cheaply. "
    "Both findings argue for the brokered-context architecture, but with different framings "
    "than v1.1's looser methodology suggested.</i>",
    QUOTE,
))


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawString(20*mm, 12*mm, "Context Engine White Paper — v1.2 Appendix B")
    canvas.drawRightString(A4[0] - 20*mm, 12*mm, f"B-{doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(ADDENDUM_PDF), pagesize=A4,
    leftMargin=22*mm, rightMargin=22*mm, topMargin=22*mm, bottomMargin=22*mm,
    title="Context Engine White Paper v1.2 — Appendix B",
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
