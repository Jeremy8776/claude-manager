#!/usr/bin/env python3
"""
run_v13.py — End-to-end v1.3 benchmark.

Generates responses for every task × every mode using a real task model, then
grades each response N times with the configured judges, then writes the
final aggregated results.

Pipeline:
  1. Load tasks + gold answers + pre-fetched contexts (from fetch_contexts.py).
  2. For each task, for each mode (no_context, smart, search):
       a. Build the system prompt (empty / smart skill bodies / search chunks).
       b. Call the task model. Record text, in/out tokens, latency.
  3. Score every response with the deterministic grade_v2 scorers:
       fact-recall + retrieval-quality.
  4. Grade every response N times per judge with the decomposed rubric.
  5. Aggregate (median + IQR) and write bench/data/v1.3/results-v13.json.

Requires ANTHROPIC_API_KEY in the env. Reads it once at startup; never
written to disk.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python bench/run_v13.py
    python bench/run_v13.py --tasks-subset 5 --judge-runs 3
    python bench/run_v13.py --task-model claude-sonnet-4-5 --judge-model claude-haiku-4-5
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
    score_facts, score_retrieval, parse_decomposed,
    DECOMPOSED_RUBRIC, cost_usd, aggregate_grades, DecomposedGrade,
)

HERE = Path(__file__).parent
DATA = HERE / "data" / "v1.3"
CONTEXTS = HERE / "artifacts" / "contexts"


def system_for_mode(mode: str, tid: str) -> tuple[str, list[str]]:
    """Return (system_prompt_body, retrieved_skill_ids).
    retrieved_skill_ids is non-empty only for mode='search'."""
    if mode == "no_context":
        return "", []
    if mode == "smart":
        path = CONTEXTS / f"{tid}.smart.md"
        if not path.exists():
            return "", []
        body = path.read_text(encoding="utf-8")
        return f"You are an AI assistant. Use the following retrieved knowledge where relevant.\n\n{body}", []
    if mode == "search":
        path = CONTEXTS / f"{tid}.search.md"
        if not path.exists():
            return "", []
        body = path.read_text(encoding="utf-8")
        # Extract retrieved skill IDs from chunk headers
        import re
        ids = []
        seen = set()
        for m in re.finditer(r"skill=(\S+)", body):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                ids.append(m.group(1))
        return f"You are an AI assistant. Use the following retrieved chunks where relevant.\n\n{body}", ids
    return "", []


def call_anthropic(client, model: str, system: str, user: str, max_tokens: int = 700) -> dict:
    t0 = time.time()
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": user}]}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return {
        "text": text.strip(),
        "input_tokens": int(resp.usage.input_tokens),
        "output_tokens": int(resp.usage.output_tokens),
        "latency_ms": int((time.time() - t0) * 1000),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", default=str(HERE / "gold-answers.json"))
    p.add_argument("--tasks", default=str(HERE / "tasks.json"))
    p.add_argument("--out", default=str(DATA / "results-v13.json"))
    p.add_argument("--responses-out", default=str(DATA / "responses-v13.json"))
    p.add_argument("--task-model", default="claude-sonnet-4-5")
    p.add_argument("--judge-model", default="claude-haiku-4-5")
    p.add_argument("--judge-runs", type=int, default=3)
    p.add_argument("--tasks-subset", type=int, default=0, help="Run only the first N tasks.")
    p.add_argument("--modes", default="no_context,smart,search")
    p.add_argument("--task-max-out", type=int, default=700)
    args = p.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.stderr.write("[!] ANTHROPIC_API_KEY not set. Aborting.\n")
        return 1

    try:
        import anthropic
    except ImportError:
        sys.stderr.write("[!] pip install anthropic\n")
        return 1
    client = anthropic.Anthropic(api_key=api_key)

    gold_root = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    gold = gold_root["tasks"]
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    if args.tasks_subset:
        tasks = tasks[: args.tasks_subset]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    print(f"Task model:  {args.task_model}")
    print(f"Judge model: {args.judge_model}  x {args.judge_runs} runs per response")
    print(f"Tasks:       {len(tasks)}  | modes: {modes}")
    print()

    responses = {}
    rows = []

    for ti, task in enumerate(tasks, 1):
        tid = task["id"]
        prompt = task["prompt"]
        print(f"  [{ti:>2}/{len(tasks)}] {tid}")
        responses[tid] = {}
        gold_t = gold.get(tid, {})
        for mode in modes:
            system, retrieved_ids = system_for_mode(mode, tid)
            if mode != "no_context" and not system:
                print(f"      {mode:<11}  (no context on disk; skipping)")
                continue
            try:
                r = call_anthropic(client, args.task_model, system, prompt, args.task_max_out)
            except Exception as e:
                print(f"      {mode:<11}  FAIL  {e}")
                continue
            r["model"] = args.task_model
            if retrieved_ids:
                r["retrieved_skill_ids"] = retrieved_ids
            responses[tid][mode] = r

            # Score deterministically
            recall = score_facts(r["text"], gold_t)
            retrieval = None
            if mode == "search":
                expected = gold_t.get("expected_sources", [])
                if expected and retrieved_ids:
                    retrieval = asdict(score_retrieval(retrieved_ids, expected))

            # Judge N times
            judge_grades = []
            user_judge = f"TASK:\n{prompt}\n\nRESPONSE TO GRADE:\n{r['text']}"
            for run_idx in range(args.judge_runs):
                try:
                    jr = call_anthropic(client, args.judge_model, DECOMPOSED_RUBRIC,
                                        user_judge, max_tokens=200)
                    g = parse_decomposed(jr["text"])
                    g.judge = f"anthropic:{args.judge_model}"
                    g.run_idx = run_idx
                    judge_grades.append(g)
                except Exception as e:
                    judge_grades.append(DecomposedGrade(notes=f"(judge err: {e})",
                                                       judge=f"anthropic:{args.judge_model}",
                                                       run_idx=run_idx))
            judge_summary = aggregate_grades(judge_grades)

            print(f"      {mode:<11}  in={r['input_tokens']:>6,}  out={r['output_tokens']:>4}  "
                  f"cov={recall.coverage_pct:>5.1f}%  bonus={recall.bonus_pct:>5.1f}%  "
                  f"fact={judge_summary.get('factual_median', 0):.1f} "
                  f"spec={judge_summary.get('specific_median', 0):.1f} "
                  f"comp={judge_summary.get('complete_median', 0):.1f} "
                  f"halluc={judge_summary.get('hallucinations_mean', 0)} ")

            rows.append({
                "task_id": tid,
                "category": task.get("category", ""),
                "mode": mode,
                "model": args.task_model,
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "latency_ms": r["latency_ms"],
                "cost_usd": round(cost_usd(args.task_model, r["input_tokens"], r["output_tokens"]), 6),
                "fact_recall": asdict(recall),
                "retrieval_quality": retrieval,
                "judge_runs": [asdict(g) for g in judge_grades],
                "judge_summary": judge_summary,
            })

    responses_path = Path(args.responses_out)
    out_path = Path(args.out)
    responses_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    responses_path.write_text(json.dumps(responses, indent=2), encoding="utf-8")
    out_path.write_text(json.dumps({
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task_model": args.task_model,
        "judge_model": args.judge_model,
        "judge_runs": args.judge_runs,
        "task_count": len(tasks),
        "rows": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nWrote responses: {responses_path}")
    print(f"Wrote results:   {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
