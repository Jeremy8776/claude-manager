#!/usr/bin/env python3
"""
run_v12.py — v1.2 benchmark orchestrator.

Replaces tokenomics.py --grade with the full critique-addressing measurement
pipeline. Reads gold-answers.json + tasks.json, runs every task through up to
four context paths (no-context, smart, search, raw_all-skipped-for-cost),
grades each response by:
  - deterministic gold-fact recall  (always run; no API key needed)
  - retrieval Precision@K / Recall@K / MRR  (always run if expected_sources labeled)
  - decomposed LLM rubric  (factual / specific / complete / hallucinations)
    via multiple judges across families (anthropic, openai), N runs each.
  - failure-mode taxonomy  (inferred from gold misses)

Captures latency + cost per call. Writes bench/data/v1.2/results-v12.json.

When API keys aren't available, the script still produces meaningful results
via the deterministic scorers (gold recall + retrieval metrics). Use
--responses path/to/file.json to score pre-generated responses without
calling the task model.

Usage:
    # Full pipeline with API keys:
    export ANTHROPIC_API_KEY=...
    export OPENAI_API_KEY=...
    python bench/run_v12.py --judges anthropic:haiku,openai:gpt-4o-mini --runs 3

    # Deterministic-only scoring of pre-generated responses:
    python bench/run_v12.py --responses bench/data/v1.2/responses-v12.json --no-llm-grade

    # Single judge, low cost smoke test:
    python bench/run_v12.py --judges anthropic:haiku --runs 1 --tasks-subset 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grade_v2 import (  # noqa: E402
    JudgeConfig, score_facts, score_retrieval,
    grade_response_decomposed, aggregate_grades, cost_usd,
)

# Hard-coded judge presets so the CLI stays short.
JUDGE_PRESETS = {
    "anthropic:haiku":      JudgeConfig("anthropic:haiku",  "anthropic", "claude-haiku-4-5",   "ANTHROPIC_API_KEY"),
    "anthropic:sonnet":     JudgeConfig("anthropic:sonnet", "anthropic", "claude-sonnet-4-5",  "ANTHROPIC_API_KEY"),
    "openai:gpt-4o-mini":   JudgeConfig("openai:gpt-4o-mini", "openai",  "gpt-4o-mini",        "OPENAI_API_KEY"),
    "openai:gpt-4o":        JudgeConfig("openai:gpt-4o",      "openai",  "gpt-4o",             "OPENAI_API_KEY"),
}

HERE = Path(__file__).parent
DATA = HERE / "data" / "v1.2"


def load_responses(path: Path) -> dict:
    """Pre-generated responses from disk. Schema:
       { task_id: { context_mode: { "text": ..., "input_tokens": ..., "output_tokens": ...,
                                    "latency_ms": ..., "model": ..., "retrieved_skill_ids": [...] }}}"""
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", default=str(HERE / "gold-answers.json"))
    p.add_argument("--tasks", default=str(HERE / "tasks.json"))
    p.add_argument("--responses", default=str(DATA / "responses-v12.json"),
                   help="Pre-generated responses to score. Required when --no-task-run.")
    p.add_argument("--out", default=str(DATA / "results-v12.json"))
    p.add_argument("--judges", default="anthropic:haiku",
                   help="Comma-separated judge presets, e.g. 'anthropic:haiku,openai:gpt-4o-mini'")
    p.add_argument("--runs", type=int, default=3, help="Judge runs per response.")
    p.add_argument("--no-llm-grade", action="store_true",
                   help="Skip the LLM decomposed-rubric pass. Deterministic scorers still run.")
    p.add_argument("--tasks-subset", type=int, default=0,
                   help="Score only the first N tasks (for fast iteration).")
    args = p.parse_args()

    gold_root = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    gold = gold_root["tasks"]
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    if args.tasks_subset:
        tasks = tasks[: args.tasks_subset]

    responses_path = Path(args.responses)
    responses = load_responses(responses_path) if responses_path.exists() else {}

    judges = [JUDGE_PRESETS[j.strip()] for j in args.judges.split(",") if j.strip() in JUDGE_PRESETS]
    if not args.no_llm_grade and judges:
        print(f"Judges: {', '.join(j.name for j in judges)} x {args.runs} runs each")
    else:
        print("LLM grading: skipped (deterministic scorers only)")

    out = {
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "judges": [j.name for j in judges] if not args.no_llm_grade else [],
        "runs_per_judge": args.runs if not args.no_llm_grade else 0,
        "task_count": len(tasks),
        "results": [],
    }

    for task in tasks:
        tid = task["id"]
        if tid not in gold:
            print(f"  [skip] {tid}: no gold entry")
            continue
        if tid not in responses:
            print(f"  [skip] {tid}: no responses on disk")
            continue
        per_task = {
            "task_id": tid,
            "category": task.get("category", ""),
            "prompt": task["prompt"],
            "modes": {},
        }
        for mode, resp in responses[tid].items():
            text = resp.get("text", "")
            recall = score_facts(text, gold[tid])
            retrieval = None
            if mode == "search":
                retrieved = resp.get("retrieved_skill_ids", [])
                expected = gold[tid].get("expected_sources", [])
                if expected and retrieved:
                    retrieval = asdict(score_retrieval(retrieved, expected))
            llm_grades = []
            if not args.no_llm_grade and judges and text.strip():
                llm_grades = grade_response_decomposed(
                    task["prompt"], text, judges, runs=args.runs,
                )
            llm_summary = aggregate_grades(llm_grades) if llm_grades else {"n": 0}

            model = resp.get("model", "unknown")
            in_tok = int(resp.get("input_tokens", 0))
            out_tok = int(resp.get("output_tokens", 0))
            per_task["modes"][mode] = {
                "model": model,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "latency_ms": int(resp.get("latency_ms", 0)),
                "cost_usd": round(cost_usd(model, in_tok, out_tok), 6),
                "fact_recall": asdict(recall),
                "retrieval_quality": retrieval,
                "llm_grades": [asdict(g) for g in llm_grades],
                "llm_summary": llm_summary,
            }
        out["results"].append(per_task)
        rs = per_task["modes"]
        recall_line = " | ".join(
            f"{m}={rs[m]['fact_recall']['coverage_pct']:.0f}%" for m in rs if "fact_recall" in rs[m]
        )
        print(f"  {tid:<28} {recall_line}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
