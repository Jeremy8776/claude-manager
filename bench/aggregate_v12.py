#!/usr/bin/env python3
"""
aggregate_v12.py — Combine deterministic scoring + session grades into the
final v1.2 results file. Produces a per-task table and summary stats.
"""
from __future__ import annotations
import json, statistics
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data" / "v1.2"

det = json.loads((DATA / "results-v12.json").read_text(encoding="utf-8"))
sg = json.loads((DATA / "session_grades.json").read_text(encoding="utf-8"))
resp = json.loads((DATA / "responses-v12.json").read_text(encoding="utf-8"))

# Index session grades
sgrades = {(g["task_id"], g["mode"]): g for g in sg["grades"]}

rows = []
for t in det["results"]:
    tid = t["task_id"]
    for mode in ("no_context", "smart", "search"):
        m = t["modes"].get(mode)
        if not m:
            continue
        g = sgrades.get((tid, mode))
        fr = m["fact_recall"]
        rq = m.get("retrieval_quality")
        in_tok = m["input_tokens"]
        out_tok = m["output_tokens"]
        composite = (g["factual"] + g["specific"] + g["complete"]) / 3 if g else 0
        rows.append({
            "task_id": tid,
            "mode": mode,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": m["cost_usd"],
            "latency_ms": m["latency_ms"],
            "fact_coverage_pct": fr["coverage_pct"],
            "fact_bonus_pct": fr["bonus_pct"],
            "forbidden_hits": fr["forbidden_hits"],
            "failure_modes": fr["failure_modes"],
            "factual": g["factual"] if g else 0,
            "specific": g["specific"] if g else 0,
            "complete": g["complete"] if g else 0,
            "hallucinations": g["hallucinations"] if g else 0,
            "composite_15": round(composite, 2),                  # composite on 0-5 scale (per-axis mean)
            "composite_pct": round(composite / 5 * 100, 1),       # composite as a %
            "retrieval": rq,
            "judge_notes": g["notes"] if g else "",
        })

# Per-mode aggregates
def by_mode(field):
    out = {}
    for mode in ("no_context", "smart", "search"):
        vs = [r[field] for r in rows if r["mode"] == mode and r[field] is not None]
        if not vs: continue
        out[mode] = {
            "median": round(statistics.median(vs), 2),
            "mean": round(statistics.mean(vs), 2),
            "min": min(vs),
            "max": max(vs),
        }
    return out

def tokens_per_quality_point(mode):
    rs = [r for r in rows if r["mode"] == mode and r["composite_15"] > 0]
    if not rs: return None
    # Use composite on a 0-15 scale (sum of 3 axes, each 0-5) for tk/pt
    tk = [r["input_tokens"] for r in rs]
    pts = [(r["factual"] + r["specific"] + r["complete"]) for r in rs]
    return round(statistics.median(tk) / statistics.median(pts), 1)

retr = {}
for r in rows:
    if r["mode"] == "search" and r["retrieval"]:
        for k in ("precision_at_k", "recall_at_k", "mrr"):
            retr.setdefault(k, []).append(r["retrieval"][k])
retr_summary = {k: round(statistics.mean(v), 3) for k, v in retr.items()}

summary = {
    "ran_at": det["ran_at"],
    "task_count": len([r for r in rows if r["mode"] == "smart"]),
    "task_model": "claude-sonnet-4-5 (session)",
    "judges": "session:claude-sonnet-4-5 (single judge, single run; cross-family multi-run pending API keys)",
    "tokens": {
        "raw_all_baseline": 186654,
        "by_mode_input_tokens": by_mode("input_tokens"),
        "by_mode_output_tokens": by_mode("output_tokens"),
        "by_mode_cost_usd": by_mode("cost_usd"),
        "by_mode_latency_ms": by_mode("latency_ms"),
    },
    "fact_recall": {
        "coverage_must_include_pct": by_mode("fact_coverage_pct"),
        "bonus_may_include_pct":     by_mode("fact_bonus_pct"),
    },
    "decomposed_rubric": {
        "factual_1to5":         by_mode("factual"),
        "specific_1to5":        by_mode("specific"),
        "complete_1to5":        by_mode("complete"),
        "hallucinations_count": by_mode("hallucinations"),
        "composite_pct":        by_mode("composite_pct"),
    },
    "retrieval_quality_mean": retr_summary,
    "tokens_per_quality_point": {
        "no_context": tokens_per_quality_point("no_context"),
        "smart":      tokens_per_quality_point("smart"),
        "search":     tokens_per_quality_point("search"),
    },
}

# Headline derived numbers
sm_tk = summary["tokens"]["by_mode_input_tokens"]["smart"]["median"]
se_tk = summary["tokens"]["by_mode_input_tokens"]["search"]["median"]
nc_tk = summary["tokens"]["by_mode_input_tokens"]["no_context"]["median"]
summary["headline"] = {
    "smart_saving_vs_raw_all_pct":  round(100 * (1 - sm_tk / 186654), 1),
    "search_saving_vs_raw_all_pct": round(100 * (1 - se_tk / 186654), 1),
    "smart_quality_lift_vs_no_context_pct": round(
        summary["decomposed_rubric"]["composite_pct"]["smart"]["median"]
        - summary["decomposed_rubric"]["composite_pct"]["no_context"]["median"], 1),
    "search_quality_lift_vs_no_context_pct": round(
        summary["decomposed_rubric"]["composite_pct"]["search"]["median"]
        - summary["decomposed_rubric"]["composite_pct"]["no_context"]["median"], 1),
    "search_failure_at_release_note": "Precision@8=0.00 Recall@8=0.00 — retrieval missed internal-comms + slack-gif-creator entirely; predicts the observed quality drop.",
}

out = {"summary": summary, "rows": rows}
DATA.mkdir(parents=True, exist_ok=True)
(DATA / "results-v12-final.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

# Print table
print(f"\n{'task':<25} {'mode':<11} {'tokens':>7} {'cov':>5} {'bonus':>6} {'fact':>4} {'spec':>4} {'comp':>4} {'comp%':>6}")
print("-" * 80)
for r in rows:
    print(f"{r['task_id']:<25} {r['mode']:<11} {r['input_tokens']:>7,} "
          f"{r['fact_coverage_pct']:>4.0f}% {r['fact_bonus_pct']:>5.0f}% "
          f"{r['factual']:>4} {r['specific']:>4} {r['complete']:>4} "
          f"{r['composite_pct']:>5.0f}%")
print()
print("=" * 80)
print(f"SUMMARY  (5 tasks; baseline raw_all = 186,654 tokens)")
print("=" * 80)
for k in ("no_context", "smart", "search"):
    tk = summary["tokens"]["by_mode_input_tokens"][k]["median"]
    saving = round(100 * (1 - tk / 186654), 1) if k != "no_context" else None
    cov = summary["fact_recall"]["coverage_must_include_pct"][k]["mean"]
    bonus = summary["fact_recall"]["bonus_may_include_pct"][k]["mean"]
    comp = summary["decomposed_rubric"]["composite_pct"][k]["median"]
    tpqp = summary["tokens_per_quality_point"][k]
    print(f"  {k:<11}  med tk={tk:>7,}  save={f'{saving}%' if saving is not None else ' n/a':>6}  "
          f"cov={cov:>5.1f}%  bonus={bonus:>5.1f}%  composite={comp:>5.1f}%  tk/pt={tpqp}")
print()
print(f"Retrieval quality (mean, search mode):")
for k, v in retr_summary.items():
    print(f"  {k:<16} {v:.3f}")
print()
print(f"Headline:")
for k, v in summary["headline"].items():
    print(f"  {k}: {v}")

print(f"\nWrote {DATA / 'results-v12-final.json'}")
