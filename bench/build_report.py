#!/usr/bin/env python3
"""Build the consolidated Context Engine benchmark report."""

from __future__ import annotations

import html
import json
import math
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "app" / "bench"
CHARTS = BENCH / "artifacts" / "charts"
OUT = BENCH / "artifacts" / "reports" / "Context Engine Benchmark Report v1.0.pdf"

IVORY = "#f7f3ea"
SLATE = "#222832"
MUTED = "#62666f"
CORAL = "#d8664f"
GOLD = "#c99a42"
BLUE = "#4f6f8f"
GREEN = "#5f8d69"
RED = "#b8524b"
GRID = "#d9d2c6"

MODES = ["no_context", "smart", "search"]
MODE_LABEL = {"no_context": "No context", "smart": "Smart", "search": "Search"}


def load_json(name: str):
    return json.loads((BENCH / name).read_text(encoding="utf-8"))


tasks = load_json("tasks.json")
task_order = [t["id"] for t in tasks]
v11 = load_json("data/v1.1/results-graded-sample.json")
v12 = load_json("data/v1.2/results-v12-final.json")
v13 = load_json("data/v1.3/results-v13-final.json")
v13_rows = load_json("data/v1.3/results-v13.json")["rows"]
responses = load_json("data/v1.3/responses-v13.json")


def esc(text) -> str:
    return html.escape(str(text)).replace("\n", "<br/>")


def pct(x, d=1) -> str:
    return f"{x:.{d}f}%"


def num(x) -> str:
    if isinstance(x, float):
        return f"{x:,.1f}"
    return f"{x:,}"


def font(size=28, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


FONT = font(24)
FONT_B = font(24, True)
FONT_S = font(18)
FONT_SB = font(18, True)
FONT_XS = font(15)


def new_chart(title: str, subtitle: str = "", w=1600, h=900):
    img = Image.new("RGB", (w, h), IVORY)
    d = ImageDraw.Draw(img)
    d.text((60, 42), title, fill=SLATE, font=font(38, True))
    if subtitle:
        d.text((62, 92), subtitle, fill=MUTED, font=FONT_S)
    return img, d


def save_chart(img: Image.Image, name: str) -> Path:
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / name
    img.save(path, "PNG", optimize=True)
    return path


def text_center(d, xy, text, fill=SLATE, fnt=FONT):
    box = d.textbbox((0, 0), text, font=fnt)
    d.text((xy[0] - (box[2] - box[0]) / 2, xy[1]), text, fill=fill, font=fnt)


def chart_token_cost():
    data = [
        ("Raw all", v13["raw_all_baseline_tokens"], SLATE),
        ("Smart", v13["by_mode"]["smart"]["input_tokens_median"], CORAL),
        ("Search", v13["by_mode"]["search"]["input_tokens_median"], BLUE),
        ("No ctx", v13["by_mode"]["no_context"]["input_tokens_median"], GREEN),
    ]
    img, d = new_chart("Token Cost by Mode", "Median input tokens on a log scale")
    x0, y0, x1, y1 = 160, 740, 1480, 170
    for tick in [10, 100, 1000, 10000, 100000]:
        y = y0 - (math.log10(tick) - 1) / 4.4 * (y0 - y1)
        d.line((x0, y, x1, y), fill=GRID, width=2)
        d.text((62, y - 12), f"{tick:,}", fill=MUTED, font=FONT_XS)
    bw = 190
    gap = 105
    for i, (label, value, color) in enumerate(data):
        x = x0 + 90 + i * (bw + gap)
        y = y0 - (math.log10(value) - 1) / 4.4 * (y0 - y1)
        d.rounded_rectangle((x, y, x + bw, y0), radius=10, fill=color)
        text_center(d, (x + bw / 2, y - 42), f"{value:,}", SLATE, FONT_SB)
        text_center(d, (x + bw / 2, y0 + 22), label, SLATE, FONT_S)
    d.text((160, 812), "Takeaway: four orders of magnitude separate the cheapest path from the naive baseline.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "01-token-cost-log.png")


def mode_value(task_id, mode, field):
    row = next(r for r in v13["detail"] if r["task_id"] == task_id)
    return row[mode][field]


def chart_quality_heatmap():
    img, d = new_chart("Composite Quality by Task", "Composite score on 0-15 scale")
    left, top = 340, 155
    cell_w, cell_h = 260, 38
    for j, mode in enumerate(MODES):
        text_center(d, (left + j * cell_w + cell_w / 2, top - 44), MODE_LABEL[mode], SLATE, FONT_SB)
    for i, tid in enumerate(task_order):
        y = top + i * cell_h
        d.text((54, y + 8), tid, fill=SLATE, font=FONT_XS)
        for j, mode in enumerate(MODES):
            val = mode_value(tid, mode, "composite_15")
            ratio = max(0, min(1, val / 15))
            r = int(245 - ratio * 60)
            g = int(225 - ratio * 95)
            b = int(210 - ratio * 115)
            x = left + j * cell_w
            d.rectangle((x, y, x + cell_w - 8, y + cell_h - 6), fill=(r, g, b))
            text_center(d, (x + cell_w / 2 - 4, y + 5), f"{val:g}", SLATE, FONT_XS)
    d.text((60, 812), "Takeaway: Smart Compile loses on 8 of 15 tasks despite costing far more tokens than no-context.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "02-quality-heatmap.png")


def chart_smart_delta():
    rows = []
    for tid in task_order:
        rows.append((tid, mode_value(tid, "smart", "composite_15") - mode_value(tid, "no_context", "composite_15")))
    rows.sort(key=lambda x: x[1])
    img, d = new_chart("Smart vs No-Context Delta", "Positive values mean Smart wins")
    x0, y0, x1, y1 = 780, 760, 1480, 160
    zero = x0 + (0 + 10) / 16 * (x1 - x0)
    d.line((zero, y1, zero, y0), fill=SLATE, width=3)
    for tick in [-10, -5, 0, 5]:
        x = x0 + (tick + 10) / 16 * (x1 - x0)
        d.line((x, y1, x, y0), fill=GRID, width=1)
        text_center(d, (x, y0 + 20), str(tick), MUTED, FONT_XS)
    bh = 30
    for i, (tid, delta) in enumerate(rows):
        y = y1 + i * 39
        d.text((60, y + 5), tid, fill=SLATE, font=FONT_XS)
        x = x0 + (delta + 10) / 16 * (x1 - x0)
        color = GREEN if delta > 0 else RED if delta < 0 else MUTED
        d.rectangle((min(zero, x), y, max(zero, x), y + bh), fill=color)
        d.text((max(zero, x) + 8 if delta >= 0 else min(zero, x) - 42, y + 4), f"{delta:+g}", fill=SLATE, font=FONT_XS)
    d.text((60, 812), "Takeaway: when Smart fails, it fails catastrophically; when it wins, it wins modestly.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "03-smart-delta.png")


def chart_hallucinations():
    img, d = new_chart("Hallucination Distribution", "Mean fabricated facts per response")
    x_positions = [380, 800, 1220]
    y0, y1 = 730, 160
    for tick in range(0, 6):
        y = y0 - tick / 5 * (y0 - y1)
        d.line((180, y, 1420, y), fill=GRID, width=1)
        d.text((120, y - 10), str(tick), fill=MUTED, font=FONT_XS)
    for j, mode in enumerate(MODES):
        xs = x_positions[j]
        vals = [mode_value(tid, mode, "halluc") for tid in task_order]
        for i, val in enumerate(vals):
            y = y0 - val / 5 * (y0 - y1)
            x = xs + ((i % 5) - 2) * 18
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=[GREEN, CORAL, BLUE][j], outline=SLATE)
        med = statistics.mean(vals)
        y = y0 - med / 5 * (y0 - y1)
        d.line((xs - 95, y, xs + 95, y), fill=SLATE, width=4)
        text_center(d, (xs, y0 + 24), MODE_LABEL[mode], SLATE, FONT_S)
        text_center(d, (xs, y - 34), f"mean {med:.2f}", SLATE, FONT_XS)
    d.text((160, 812), "Takeaway: loading more context creates more fabricated facts, not fewer.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "04-hallucinations.png")


def search_retrieval_rows():
    return [r for r in v13_rows if r["mode"] == "search"]


def chart_retrieval_scatter():
    points = []
    for row in search_retrieval_rows():
        tid = row["task_id"]
        p = row["retrieval_quality"]["precision_at_k"]
        y = mode_value(tid, "search", "composite_15") - mode_value(tid, "no_context", "composite_15")
        points.append((tid, p, y))
    img, d = new_chart("Retrieval Quality vs Outcome", "Search Precision@K against quality delta")
    x0, y0, x1, y1 = 170, 720, 1460, 170
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + tick * (x1 - x0)
        d.line((x, y0, x, y1), fill=GRID)
        text_center(d, (x, y0 + 22), f"{tick:.2f}", MUTED, FONT_XS)
    for tick in [-4, -2, 0, 2, 4]:
        y = y0 - (tick + 4) / 8 * (y0 - y1)
        d.line((x0, y, x1, y), fill=GRID)
        d.text((110, y - 10), f"{tick:+d}", fill=MUTED, font=FONT_XS)
    xs = [p[1] for p in points]
    ys = [p[2] for p in points]
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    denom = sum((x - mean_x) ** 2 for x in xs) or 1
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    tx0, tx1 = 0, 1
    ty0, ty1 = intercept, intercept + slope
    d.line((x0, y0 - (ty0 + 4) / 8 * (y0 - y1), x1, y0 - (ty1 + 4) / 8 * (y0 - y1)), fill=CORAL, width=4)
    for tid, p, delta in points:
        x = x0 + p * (x1 - x0)
        y = y0 - (delta + 4) / 8 * (y0 - y1)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=BLUE, outline=SLATE)
        if p in (0, 1) or abs(delta) >= 3:
            d.text((x + 12, y - 8), tid[:18], fill=SLATE, font=FONT_XS)
    d.text((170, 812), "Takeaway: where retrieval surfaces relevant chunks, search adds value; misses degrade output.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "05-retrieval-scatter.png")


def chart_lift_efficiency():
    img, d = new_chart("Cost per Positive Quality Lift", "Tokens per +1 composite point over no-context")
    data = [("Smart", v13["lift_efficiency"]["smart"], CORAL), ("Search", v13["lift_efficiency"]["search"], BLUE)]
    maxv = max(item["median_tk_per_lift_pt"] for _, item, _ in data)
    x0, y0, x1, y1 = 260, 700, 1350, 180
    for i, (label, item, color) in enumerate(data):
        val = item["median_tk_per_lift_pt"]
        h = val / maxv * (y0 - y1)
        x = x0 + i * 500
        d.rounded_rectangle((x, y0 - h, x + 260, y0), radius=12, fill=color)
        text_center(d, (x + 130, y0 - h - 42), f"{val:,.0f}", SLATE, FONT_SB)
        text_center(d, (x + 130, y0 + 24), label, SLATE, FONT_S)
        d.text((x - 10, y0 + 68), f"negative-lift tasks: {item['n_negative_lift']}/{item['n_total']}", fill=MUTED, font=FONT_XS)
    d.text((200, 812), "Takeaway: Search is 76x cheaper per positive lift point, but both modes lose on most tasks.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "06-lift-efficiency.png")


def chart_methodology():
    img, d = new_chart("Methodology Changed the Result", "Why v1.1 and v1.2 were retracted")
    rows = [
        ("v1.1", "5 tasks", "Session as judge, holistic 1-10", "Smart 9.0/10; optimistic"),
        ("v1.2", "5 tasks", "Gold facts + decomposed rubric, same session judge", "Smart +20 composite pts vs no-context"),
        ("v1.3", "15 tasks", "Sonnet task model, Haiku judge x3", "Smart -1.27 pts; loses 8/15"),
    ]
    x = [90, 300, 540, 1040]
    y = 190
    headers = ["Run", "N", "Judge/rubric", "Headline"]
    for j, h in enumerate(headers):
        d.text((x[j], y), h, fill=SLATE, font=FONT_SB)
    for i, row in enumerate(rows):
        yy = y + 80 + i * 155
        fill = "#fffaf1" if i % 2 == 0 else "#eee8dc"
        d.rounded_rectangle((70, yy - 24, 1510, yy + 92), radius=16, fill=fill, outline=GRID, width=2)
        for j, cell in enumerate(row):
            d.text((x[j], yy), cell, fill=SLATE if i < 2 else RED, font=FONT_S if j else FONT_B)
    d.text((90, 812), "Takeaway: self-evaluation bias accounted for roughly three composite points of inflation.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "07-methodology.png")


def chart_latency_cost():
    img, d = new_chart("Latency and Cost by Mode", "Median latency and total API cost in v1.3")
    panels = [("Median latency (ms)", "latency_ms_median", 150, 720, 680), ("Total cost (USD)", "cost_usd_total", 880, 720, 1410)]
    for title, field, x0, y0, x1 in panels:
        d.text((x0, 150), title, fill=SLATE, font=FONT_SB)
        vals = [v13["by_mode"][m][field] for m in MODES]
        maxv = max(vals)
        for i, (mode, val) in enumerate(zip(MODES, vals)):
            x = x0 + i * 170
            h = val / maxv * 430
            d.rounded_rectangle((x, y0 - h, x + 110, y0), radius=8, fill=[GREEN, CORAL, BLUE][i])
            label = f"${val:.2f}" if field == "cost_usd_total" else f"{int(val):,}"
            text_center(d, (x + 55, y0 - h - 34), label, SLATE, FONT_XS)
            text_center(d, (x + 55, y0 + 22), MODE_LABEL[mode].replace(" ", "\n"), SLATE, FONT_XS)
    d.text((150, 812), "Takeaway: Smart is slower and materially more expensive while under-performing no-context.", fill=SLATE, font=FONT_SB)
    return save_chart(img, "08-latency-cost.png")


def build_charts():
    return [
        chart_token_cost(),
        chart_quality_heatmap(),
        chart_smart_delta(),
        chart_hallucinations(),
        chart_retrieval_scatter(),
        chart_lift_efficiency(),
        chart_methodology(),
        chart_latency_cost(),
    ]


styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor(SLATE), spaceAfter=10)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor(SLATE), spaceBefore=10, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor(CORAL), spaceBefore=6, spaceAfter=3)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13, textColor=colors.HexColor(SLATE), alignment=TA_LEFT, spaceAfter=6)
QUOTE = ParagraphStyle("QUOTE", parent=BODY, leftIndent=10, rightIndent=10, fontName="Helvetica-Oblique", textColor=colors.HexColor(MUTED), backColor=colors.HexColor("#eee8dc"), borderPadding=6, spaceAfter=8)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=8.4, leading=11, textColor=colors.HexColor(MUTED), spaceAfter=8)
TITLE = ParagraphStyle("TITLE", parent=H1, fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=14)
SUB = ParagraphStyle("SUB", parent=BODY, fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor(MUTED))
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=7.5, leading=9)


def para(text, style=BODY):
    return Paragraph(esc(text), style)


def rich(text, style=BODY):
    return Paragraph(text, style)


def table(headers, rows, widths, small=False):
    body = [[rich(f"<b>{esc(h)}</b>", SMALL if small else BODY) for h in headers]]
    for row in rows:
        body.append([rich(esc(c), SMALL if small else BODY) for c in row])
    t = LongTable(body, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(SLATE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2ede3")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(GRID)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def chart_flow(path: Path, caption: str):
    return KeepTogether([
        RLImage(str(path), width=170 * mm, height=95 * mm),
        rich(f"<b>Caption.</b> {esc(caption)}", CAP),
    ])


def cover(story):
    story.append(Spacer(1, 65 * mm))
    story.append(rich("Context Engine<br/>Benchmark Report v1.0", TITLE))
    story.append(rich("Token efficiency, quality regression, and roadmap implications across v1.1 to v1.3", SUB))
    story.append(Spacer(1, 18 * mm))
    story.append(rich("<b>Publication-grade summary:</b> Context Engine saves tokens. The current v0.3.x retrieval and Smart Compile implementation does not yet preserve quality. v1.3 retracts the earlier headline while validating the paper's multi-resolution architecture.", QUOTE))
    story.append(PageBreak())


def executive_summary(story):
    story.append(rich("Executive Summary", H1))
    story.append(rich("<b>The honest result:</b> v1.3 retracts the v1.1/v1.2 headline. Smart Compile in its current v0.3.x form net-degrades quality versus no-context: mean delta <b>-1.27</b> composite points on a 15-point scale, with <b>8 losses, 2 ties, and 5 wins</b> across 15 tasks. Search also under-performs no-context on the corpus: <b>-0.80</b> mean delta, with 8 losses.", BODY))
    story.append(rich("<b>The validation:</b> token reduction is real and large. Median input tokens fall from <b>186,654</b> in the raw-all baseline to <b>74,279</b> in Smart and <b>903</b> in Search. This validates the token-efficiency part of the architecture but not the quality-preservation claim.", BODY))
    story.append(rich("<b>White paper cross-reference:</b> Section 11 predicted that binary include/exclude selection would not be enough; skills need multi-resolution packaging. v1.3 empirically confirms that prediction. Section 32 Hypothesis 1 - Smart Compile reduces token load without reducing task quality - is not supported by the current implementation.", BODY))
    story.append(rich("<b>Product decision:</b> CE should be framed today as a token-saving and retrieval research system, not as a quality-improving context broker. Phase 2 ranking/dedup and Section 11 multi-resolution packaging are load-bearing, not polish.", BODY))
    story.append(PageBreak())


def methodology(story, charts):
    story.append(rich("Methodology Evolution", H1))
    story.append(rich("The result changed because the measurement became harder to fool. v1.1 used the active session as a holistic judge. v1.2 added gold facts and a decomposed rubric but retained session judging. v1.3 used Sonnet 4.5 as the task model and Haiku 4.5 as a separate judge over three runs per response.", BODY))
    rows = [
        ["v1.1", "5", "Session-as-judge; holistic 1-10", "Smart 9.0/10, Search 7.6/10", "Retracted as over-optimistic"],
        ["v1.2", "5", "Gold facts + decomposed rubric; session judge", "Smart +20 composite pts vs no-context", "Directionally useful, still biased"],
        ["v1.3", "15", "Sonnet task model; Haiku judge x3", "Smart -1.27; Search -0.80 vs no-context", "Current decision baseline"],
    ]
    story.append(table(["Run", "N", "Judge/rubric", "Headline", "Status"], rows, [18*mm, 10*mm, 48*mm, 50*mm, 40*mm]))
    story.append(Spacer(1, 6))
    story.append(chart_flow(charts[6], "Self-evaluation bias made earlier runs look better than the full v1.3 pipeline."))
    story.append(PageBreak())


def headline_results(story, charts):
    story.append(rich("Headline Results", H1))
    story.append(chart_flow(charts[0], "Four orders of magnitude separate the cheapest path from the naive raw-all baseline."))
    rows = []
    for mode in MODES:
        a = v13["by_mode"][mode]
        rows.append([MODE_LABEL[mode], num(a["input_tokens_median"]), pct(a["coverage_pct_mean"]), pct(a["bonus_pct_mean"]), f"{a['factual_median']:.1f}", f"{a['specific_median']:.1f}", f"{a['complete_median']:.1f}", f"{a['hallucinations_mean']:.2f}", f"{a['composite_15_median']:.1f}", f"${a['cost_usd_total']:.2f}"])
    story.append(table(["Mode", "med tk", "Cov", "Bonus", "Fact", "Spec", "Comp", "Halluc", "Comp/15", "Cost"], rows, [24*mm, 18*mm, 14*mm, 15*mm, 12*mm, 12*mm, 12*mm, 16*mm, 17*mm, 16*mm], small=True))
    story.append(rich("Table 1. Per-mode aggregate, all 15 tasks. Fact/Spec/Comp are judge medians on 1-5 axes; composite is on a 0-15 scale.", CAP))
    story.append(PageBreak())
    story.append(chart_flow(charts[1], "Smart Compile loses on 8 of 15 tasks despite costing about 2,500x more input tokens than no-context."))
    story.append(chart_flow(charts[2], "The worst Smart failure is large enough to dominate the mean; positive wins are smaller."))
    story.append(PageBreak())
    paired_rows = []
    for key, label in [("smart_vs_no_context", "Smart vs no-context"), ("search_vs_no_context", "Search vs no-context"), ("smart_vs_search", "Smart vs Search")]:
        p = v13["paired"][key]
        paired_rows.append([label, str(p["n"]), f"{p['mean_delta']:+.2f}", f"{p['median_delta']:+.1f}", f"{p['wins']}/{p['ties']}/{p['losses']}", f"{p['worst_task'][0]} ({p['worst_task'][1]:+g})", f"{p['best_task'][0]} ({p['best_task'][1]:+g})"])
    story.append(table(["Comparison", "n", "mean", "median", "W/T/L", "Worst", "Best"], paired_rows, [38*mm, 10*mm, 16*mm, 16*mm, 18*mm, 40*mm, 40*mm]))
    story.append(rich("Table 2. Paired comparison by task. Positive deltas mean the first mode outperformed the second.", CAP))
    story.append(chart_flow(charts[7], "Smart costs more and runs slower while under-performing no-context in aggregate."))
    story.append(PageBreak())


def whitepaper_crossref(story):
    story.append(rich("White Paper Predictions vs v1.3", H1))
    story.append(rich("<b>Section 11 - Multi-Resolution Context Packaging:</b> The paper says the key optimisation is not merely selecting chunks but selecting resolution: manifest, glossary, summary, targeted chunks, section, or full source. v1.3 confirms this. Injecting many full skill bodies causes attention dilution; the model follows meta-style and process text instead of the user's concrete request.", BODY))
    story.append(rich("<b>Section 19 - Future Evaluation Framework:</b> The paper specifically named Precision@K, Recall@K, MRR, token utility, and compile reduction as future metrics. v1.3 is the first run to instantiate that scaffold. Retrieval quality is low: Precision@8 mean <b>0.23</b>, Recall@8 mean <b>0.56</b>, MRR mean <b>0.31</b>, with <b>5/15 complete misses</b>.", BODY))
    story.append(rich("<b>Section 32 - Hypothesis 1:</b> 'Smart Compile reduces token load without reducing task quality' is not supported by v0.3.x. The token-load half is true; the quality half is false on this corpus. Hypothesis 2 - multi-resolution packaging improves retrieval efficiency - becomes the more important next test.", BODY))
    story.append(rich("<b>Section 34 - Build Roadmap:</b> Phase 2 Dedup and Rank is the first major improvement to retrieval quality. The benchmark makes that phase urgent. Phase 4 Multi-Resolution Skill Compiler is not optional if Smart Compile is to become quality-preserving.", BODY))
    story.append(PageBreak())


def failure_mode(story):
    story.append(rich("Failure Mode Case Study", H1))
    story.append(rich("The clearest failure is <b>comfy-prompt-fantasy</b>. The user asked for a ComfyUI prompt. No-context produced a practical prompt with positive/negative sections and settings. Smart, after receiving 36k tokens of skill context, produced a philosophical essay titled <i>Mystral Dusk</i> and failed the task.", BODY))
    no_ctx = responses["comfy-prompt-fantasy"]["no_context"]["text"][:780]
    smart = responses["comfy-prompt-fantasy"]["smart"]["text"][:780]
    story.append(rich("<b>No-context response excerpt</b>", H3))
    story.append(para(no_ctx, QUOTE))
    story.append(rich("<b>Smart response excerpt</b>", H3))
    story.append(para(smart, QUOTE))
    story.append(rich("This is the attention-dilution failure mode in concrete form: the model absorbed aesthetic and meta-discussion from context and produced more meta-discussion instead of an executable prompt.", BODY))
    story.append(PageBreak())


def hallucination_retrieval(story, charts):
    story.append(rich("Hallucinations and Retrieval Quality", H1))
    story.append(chart_flow(charts[3], "Loading more context increases fabricated facts: Smart mean hallucinations 1.49 vs no-context 0.98."))
    story.append(chart_flow(charts[4], "Search quality depends on retrieval quality. Complete misses predict degraded output."))
    story.append(PageBreak())
    rows = []
    for row in search_retrieval_rows():
        rq = row["retrieval_quality"]
        rows.append([row["task_id"], f"{rq['precision_at_k']:.2f}", f"{rq['recall_at_k']:.2f}", f"{rq['mrr']:.2f}", ", ".join(rq.get("hits") or []) or "-", ", ".join(rq.get("expected") or [])])
    story.append(table(["Task", "P@K", "R@K", "MRR", "Hits", "Expected"], rows, [38*mm, 13*mm, 13*mm, 13*mm, 42*mm, 55*mm], small=True))
    story.append(rich("Table 4. Retrieval quality per task for search mode. Complete misses are the strongest warning signal for quality loss.", CAP))
    story.append(PageBreak())


def validated_retracted(story, charts):
    story.append(rich("Validated, Retracted, Pending", H1))
    story.append(rich("<b>Validated:</b> token reduction is real; the benchmark harness now exists; Section 11's architecture is validated; retrieval quality predicts failure; Search is much more efficient than Smart per positive lift point.", BODY))
    story.append(rich("<b>Retracted:</b> the v1.1 claim that Smart held at 9.0/10 quality; the v1.2 framing that Smart improves quality over no-context; the product claim that v0.3.x Smart Compile preserves quality.", BODY))
    story.append(rich("<b>Pending:</b> cross-family judges beyond Haiku; alternative task models; a larger task corpus; user correction-rate measurement; and a post-Phase-2 rerun after ranking/dedup changes.", BODY))
    story.append(chart_flow(charts[5], "Search is dramatically more token-efficient when it helps, but both modes show negative lift on most tasks."))
    story.append(PageBreak())


def roadmap(story):
    story.append(rich("Build Roadmap Implications", H1))
    rows = [
        ["Phase 2: Dedup + Rank", "Highest", "P@8 is 0.23 and 5/15 searches miss completely. Ranking quality is the bottleneck."],
        ["Phase 3: Smart Compile", "Re-scope", "Do not ship as quality-improving until it chooses resolution, not whole skills."],
        ["Phase 4: Multi-Resolution Compiler", "Load-bearing", "Needed to avoid flooding the task model with full SKILL.md bodies."],
        ["Retrieval dashboard", "High", "Expose P@K/R@K/MRR style signals and expected-source misses before user-facing claims."],
        ["Benchmark gate", "High", "Any ranking change should rerun this report before release notes claim quality preservation."],
    ]
    story.append(table(["Roadmap item", "Priority", "Why v1.3 changes the decision"], rows, [42*mm, 24*mm, 104*mm]))
    story.append(Spacer(1, 8))
    story.append(rich("The product framing should change immediately: current CE saves tokens and provides the plumbing for brokered context. It does not yet prove that brokered context improves output quality. That distinction protects the roadmap from overselling v0.3.x.", BODY))
    story.append(PageBreak())


def limitations(story):
    story.append(rich("Limitations Still Standing", H1))
    for item in [
        "Judge family is still Anthropic-only: Sonnet task model, Haiku judge. This avoids same-model self-judging but not family-level bias.",
        "The corpus has only 15 tasks. It is representative of this project, not a universal benchmark.",
        "Gold facts and expected sources are manually authored, so they encode human judgement.",
        "No user correction-rate or real workflow completion metric is included yet.",
        "v1.3 measures the current implementation, not the intended Section 11 multi-resolution implementation.",
    ]:
        story.append(rich("- " + esc(item), BODY))
    story.append(PageBreak())


def reproducibility(story):
    story.append(rich("Reproducibility and Source Lineage", H1))
    story.append(rich("The report is generated from immutable benchmark artifacts already present under app/bench. Historical white papers remain read-only records; this report cross-references them rather than rebuilding them.", BODY))
    rows = [
        ["Task corpus", "app/bench/tasks.json", "15 representative tasks"],
        ["Gold answers", "app/bench/gold-answers.json", "Must/may/forbidden facts and expected sources"],
        ["v1.1 token-only", "app/bench/data/v1.1/results-latest.json", "15-task token run, no quality grading"],
        ["v1.1 graded sample", "app/bench/data/v1.1/results-graded-sample.json", "5-task session-as-judge quality sample"],
        ["v1.2 final", "app/bench/data/v1.2/results-v12-final.json", "Gold scoring and decomposed rubric on 5-task subset"],
        ["v1.3 final", "app/bench/data/v1.3/results-v13-final.json", "15-task aggregate, paired comparisons, lift efficiency"],
        ["v1.3 raw rows", "app/bench/data/v1.3/results-v13.json", "45 task/mode rows with retrieval-quality detail"],
        ["v1.3 responses", "app/bench/data/v1.3/responses-v13.json", "All task-model outputs used for case studies"],
        ["Build script", "app/bench/build_report.py", "Single-command PDF and chart generation"],
    ]
    story.append(table(["Input", "Path", "Use"], rows, [36*mm, 66*mm, 68*mm], small=True))
    story.append(Spacer(1, 8))
    story.append(rich("Rebuild command: <b>python app/bench/build_report.py</b>. The script writes eight PNG charts to <b>app/bench/artifacts/charts/</b> and the final PDF to <b>app/bench/artifacts/reports/</b>.", BODY))
    story.append(rich("No historical result JSON, benchmark runner, grading script, or white-paper PDF is modified by the build.", BODY))
    story.append(PageBreak())


def detail_tables(story):
    story.append(rich("Appendix A: Full Per-Task Detail", H1))
    rows = []
    for tid in task_order:
        detail = next(r for r in v13["detail"] if r["task_id"] == tid)
        for mode in MODES:
            m = detail[mode]
            rows.append([tid, MODE_LABEL[mode], num(m["input_tokens"]), pct(m["coverage"], 0), pct(m["bonus"], 0), f"{m['factual']:.1f}", f"{m['specific']:.1f}", f"{m['complete']:.1f}", f"{m['halluc']:.2f}", f"{m['composite_15']:.1f}"])
    story.append(table(["Task", "Mode", "Tokens", "Cov", "Bonus", "Fact", "Spec", "Comp", "Halluc", "Comp/15"], rows, [38*mm, 20*mm, 17*mm, 13*mm, 14*mm, 12*mm, 12*mm, 12*mm, 15*mm, 15*mm], small=True))
    story.append(PageBreak())


def build_pdf():
    charts = build_charts()
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=16*mm)
    story = []
    cover(story)
    executive_summary(story)
    methodology(story, charts)
    headline_results(story, charts)
    whitepaper_crossref(story)
    failure_mode(story)
    hallucination_retrieval(story, charts)
    validated_retracted(story, charts)
    roadmap(story)
    limitations(story)
    reproducibility(story)
    detail_tables(story)
    doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)


def page_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(IVORY))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor(GRID))
    canvas.line(18*mm, 13*mm, A4[0]-18*mm, 13*mm)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(18*mm, 8*mm, "Context Engine Benchmark Report v1.0")
    canvas.drawRightString(A4[0]-18*mm, 8*mm, str(doc.page))
    canvas.restoreState()


if __name__ == "__main__":
    build_pdf()
    size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUT} ({size_mb:.2f} MB)")
