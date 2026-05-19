#!/usr/bin/env python3
"""
aggregate_v13.py — Aggregate the full 15-task × 3-mode × 3-judge-run benchmark.

Reports median + IQR per axis, paired comparisons across modes, and the
honest finding that contradicts v1.2's framing.

Usage:
    python bench/aggregate_v13.py                    # aggregate + print
    python bench/aggregate_v13.py --gate             # aggregate + gate check (exit 1 on fail)
    python bench/aggregate_v13.py --gate --json      # aggregate + gate + JSON output
"""
from __future__ import annotations
import argparse, json, statistics, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--gate", action="store_true", help="Exit 1 if quality or retrieval gates fail")
p.add_argument("--json", action="store_true", help="Output final result as JSON to stdout")
args = p.parse_args()

HERE = Path(__file__).parent
DATA = HERE / "data" / "v1.3"
data = json.loads((DATA / "results-v13.json").read_text(encoding="utf-8"))
rows = data["rows"]


def med(xs): return statistics.median(xs) if xs else 0
def mean(xs): return statistics.mean(xs) if xs else 0
def iqr(xs):
    if len(xs) < 4: return 0.0
    q = statistics.quantiles(xs, n=4)
    return q[2] - q[0]


# Per-mode aggregates
modes = ("no_context", "smart", "search")
def mode_rows(m): return [r for r in rows if r["mode"] == m]

agg = {}
for m in modes:
    rs = mode_rows(m)
    agg[m] = {
        "n": len(rs),
        "input_tokens_median": int(med([r["input_tokens"] for r in rs])),
        "output_tokens_median": int(med([r["output_tokens"] for r in rs])),
        "latency_ms_median": int(med([r["latency_ms"] for r in rs])),
        "cost_usd_median": round(med([r["cost_usd"] for r in rs]), 5),
        "cost_usd_total": round(sum(r["cost_usd"] for r in rs), 4),
        "coverage_pct_mean": round(mean([r["fact_recall"]["coverage_pct"] for r in rs]), 1),
        "bonus_pct_mean": round(mean([r["fact_recall"]["bonus_pct"] for r in rs]), 1),
        "factual_median": med([r["judge_summary"].get("factual_median", 0) for r in rs]),
        "factual_iqr": round(iqr([r["judge_summary"].get("factual_median", 0) for r in rs]), 2),
        "specific_median": med([r["judge_summary"].get("specific_median", 0) for r in rs]),
        "specific_iqr": round(iqr([r["judge_summary"].get("specific_median", 0) for r in rs]), 2),
        "complete_median": med([r["judge_summary"].get("complete_median", 0) for r in rs]),
        "complete_iqr": round(iqr([r["judge_summary"].get("complete_median", 0) for r in rs]), 2),
        "hallucinations_mean": round(mean([r["judge_summary"].get("hallucinations_mean", 0) for r in rs]), 2),
        "hallucinations_max": max([r["judge_summary"].get("hallucinations_max", 0) for r in rs]),
        "composite_15_median": round(med([
            (r["judge_summary"].get("factual_median", 0)
             + r["judge_summary"].get("specific_median", 0)
             + r["judge_summary"].get("complete_median", 0))
            for r in rs
        ]), 2),
    }

# Paired comparisons: per-task, mode A vs mode B
by_task = {}
for r in rows:
    by_task.setdefault(r["task_id"], {})[r["mode"]] = r

def composite(r):
    js = r["judge_summary"]
    return js.get("factual_median", 0) + js.get("specific_median", 0) + js.get("complete_median", 0)

pairs = {"smart_vs_no_context": [], "search_vs_no_context": [], "smart_vs_search": []}
for tid, modes_d in by_task.items():
    if "no_context" in modes_d:
        if "smart" in modes_d:
            pairs["smart_vs_no_context"].append((tid, composite(modes_d["smart"]) - composite(modes_d["no_context"])))
        if "search" in modes_d:
            pairs["search_vs_no_context"].append((tid, composite(modes_d["search"]) - composite(modes_d["no_context"])))
    if "smart" in modes_d and "search" in modes_d:
        pairs["smart_vs_search"].append((tid, composite(modes_d["smart"]) - composite(modes_d["search"])))

paired_summary = {}
for k, vs in pairs.items():
    diffs = [d for _, d in vs]
    paired_summary[k] = {
        "n": len(diffs),
        "mean_delta": round(mean(diffs), 2),
        "median_delta": round(med(diffs), 2),
        "wins": sum(1 for d in diffs if d > 0),
        "ties": sum(1 for d in diffs if d == 0),
        "losses": sum(1 for d in diffs if d < 0),
        "worst_task": min(vs, key=lambda x: x[1]) if vs else None,
        "best_task": max(vs, key=lambda x: x[1]) if vs else None,
    }

# Retrieval-quality aggregates (search mode only)
retr = [r["retrieval_quality"] for r in rows if r["mode"] == "search" and r["retrieval_quality"]]
retr_summary = {
    "n": len(retr),
    "precision_at_k_mean": round(mean([r["precision_at_k"] for r in retr]), 3),
    "recall_at_k_mean": round(mean([r["recall_at_k"] for r in retr]), 3),
    "mrr_mean": round(mean([r["mrr"] for r in retr]), 3),
    "complete_misses": [r["expected"] for r in retr if r["precision_at_k"] == 0],
}

# Token-per-quality-point of LIFT over no_context
def lift_efficiency(mode):
    rs = []
    for tid, ms in by_task.items():
        if mode not in ms or "no_context" not in ms:
            continue
        delta_q = composite(ms[mode]) - composite(ms["no_context"])
        delta_tk = ms[mode]["input_tokens"] - ms["no_context"]["input_tokens"]
        rs.append((tid, delta_tk, delta_q))
    if not rs:
        return None
    # only count rows where lift > 0 (the rest are negative-value)
    pos = [(tk, q) for _, tk, q in rs if q > 0]
    if not pos:
        return {"n_positive_lift": 0, "n_total": len(rs)}
    return {
        "n_total": len(rs),
        "n_positive_lift": len(pos),
        "n_negative_lift": sum(1 for _, _, q in rs if q < 0),
        "n_zero_lift":     sum(1 for _, _, q in rs if q == 0),
        "median_tk_per_lift_pt": round(med([tk for tk, q in pos]) / med([q for tk, q in pos]), 1),
    }

lift = {m: lift_efficiency(m) for m in ("smart", "search")}

# Build per-task detail rows for the appendix table
detail = []
for tid in sorted(by_task.keys()):
    ms = by_task[tid]
    row = {"task_id": tid, "category": ms[next(iter(ms))]["category"]}
    for m in modes:
        if m not in ms: continue
        r = ms[m]
        js = r["judge_summary"]
        row[m] = {
            "input_tokens": r["input_tokens"],
            "coverage": r["fact_recall"]["coverage_pct"],
            "bonus": r["fact_recall"]["bonus_pct"],
            "factual": js.get("factual_median", 0),
            "specific": js.get("specific_median", 0),
            "complete": js.get("complete_median", 0),
            "halluc": js.get("hallucinations_mean", 0),
            "composite_15": composite(r),
        }
    detail.append(row)

final = {
    "ran_at": data["ran_at"],
    "task_model": data["task_model"],
    "judge_model": data["judge_model"],
    "judge_runs": data["judge_runs"],
    "task_count": data["task_count"],
    "raw_all_baseline_tokens": 186654,
    "by_mode": agg,
    "paired": paired_summary,
    "retrieval_quality": retr_summary,
    "lift_efficiency": lift,
    "detail": detail,
}

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "results-v13-final.json").write_text(json.dumps(final, indent=2), encoding="utf-8")

# Print summary
print("=" * 96)
print(f"v1.3 RESULTS — task={data['task_model']}  judge={data['judge_model']}×{data['judge_runs']} runs  N={data['task_count']}")
print("=" * 96)

print(f"\n{'Mode':<12} {'med tk':>8} {'cov':>5} {'bonus':>6} {'fact':>5} {'spec':>5} {'comp':>5} {'halluc':>7} {'comp/15':>8} {'$':>7}")
for m in modes:
    a = agg[m]
    print(f"{m:<12} {a['input_tokens_median']:>8,} "
          f"{a['coverage_pct_mean']:>4.0f}% {a['bonus_pct_mean']:>5.0f}% "
          f"{a['factual_median']:>5.1f} {a['specific_median']:>5.1f} {a['complete_median']:>5.1f} "
          f"{a['hallucinations_mean']:>7.2f} {a['composite_15_median']:>7.1f} ${a['cost_usd_total']:>6.2f}")

print("\nPaired comparisons (composite/15):")
for k, p in paired_summary.items():
    print(f"  {k:<24} n={p['n']:<3} mean d={p['mean_delta']:>6.2f}  wins/ties/losses = {p['wins']}/{p['ties']}/{p['losses']}")
    if p['worst_task']:
        print(f"    worst: {p['worst_task'][0]} (d={p['worst_task'][1]:.0f})    best: {p['best_task'][0]} (d={p['best_task'][1]:.0f})")

print("\nRetrieval quality (search mode):")
r = retr_summary
print(f"  P@8 mean = {r['precision_at_k_mean']:.3f}   R@8 mean = {r['recall_at_k_mean']:.3f}   MRR mean = {r['mrr_mean']:.3f}")
print(f"  Complete retrieval misses: {len(r['complete_misses'])} of {r['n']} tasks")

print("\nLift efficiency over no_context (tokens per +1 composite point of lift):")
for m, l in lift.items():
    if l is None:
        continue
    if l.get("median_tk_per_lift_pt") is None:
        print(f"  {m}: NO POSITIVE LIFT on any task (negative={l['n_negative_lift']}, zero={l['n_zero_lift']}, positive={l['n_positive_lift']})")
    else:
        print(f"  {m}: {l['median_tk_per_lift_pt']:>10,.0f} tk/+1pt  "
              f"(positive lift {l['n_positive_lift']}/{l['n_total']}; "
              f"negative lift {l['n_negative_lift']}; zero {l['n_zero_lift']})")

print("\nHEADLINE: Smart Compile in its current form")
sv = paired_summary["smart_vs_no_context"]
if sv["mean_delta"] < 0:
    print(f"  DEGRADES composite quality by {abs(sv['mean_delta']):.2f} points on average vs no-context.")
    print(f"  Loses on {sv['losses']}/{sv['n']} tasks; wins on {sv['wins']}.")
    print(f"  Implication: full-skill-body injection at ~75k tokens hits an attention-dilution regime")
    print(f"  the no-context model doesn't experience. Hypothesis 1 (in its v1.0 form) is contradicted.")
elif sv["mean_delta"] > 0:
    print(f"  IMPROVES composite quality by {sv['mean_delta']:.2f} points on average vs no-context.")
sr = paired_summary["search_vs_no_context"]
print(f"\n  Search vs no_context: mean d = {sr['mean_delta']:+.2f}  ({sr['wins']} wins / {sr['ties']} ties / {sr['losses']} losses)")
print(f"\nWrote {DATA / 'results-v13-final.json'}")

# --gate: check quality gates, exit 1 on failure
if args.json:
    json.dump(final, sys.stdout, indent=2)
    print()

if args.gate:
    gates_failed = 0

    # Gate 1: No-context quality — Smart and Search must beat or tie no-context
    for mode_key, label in [("smart_vs_no_context", "Smart Compile vs no_context"),
                            ("search_vs_no_context", "MCP Search vs no_context")]:
        p_data = paired_summary[mode_key]
        if p_data["mean_delta"] < 0:
            print(f"\n  [GATE FAIL] {label}: mean delta = {p_data['mean_delta']:.2f} "
                  f"(losses={p_data['losses']}/{p_data['n']})")
            gates_failed += 1
        else:
            print(f"\n  [GATE PASS] {label}: mean delta = {p_data['mean_delta']:.2f} "
                  f"(wins={p_data['wins']}, ties={p_data['ties']})")

    # Gate 2: Retrieval quality — Recall@8 must be 1.00
    retr_r = retr_summary
    if retr_r["recall_at_k_mean"] < 1.0:
        print(f"  [GATE FAIL] R@8 = {retr_r['recall_at_k_mean']:.3f} (expected 1.000). "
              f"{len(retr_r['complete_misses'])} complete misses.")
        gates_failed += 1
    else:
        print(f"  [GATE PASS] R@8 = {retr_r['recall_at_k_mean']:.3f}")

    if gates_failed:
        print(f"\n  {gates_failed} gate(s) FAILED.")
        sys.exit(1)
    else:
        print(f"\n  All gates PASSED.")
