#!/usr/bin/env python3
"""
run_continuity.py — Continuity benchmark for Context Engine.

Tests whether session 2 of a paused workflow inherits state established in
session 1, across three modes:

  no_context_cold  — S2 has no memory of S1. Baseline of pain.
                     System prompt empty; only the S2 user prompt is given.
  ce_full          — S2 gets the full session_1_state object as a memory
                     snapshot. Simulates CE persisting and replaying the
                     entire state.
  ce_compact       — S2 gets the compact handoff note (1-2 sentences)
                     CE emits. Simulates the realistic delivery — what CE
                     would inject as a memory entry, not the raw state dump.

For each (task, mode) pair we measure:
  • input/output tokens, latency, dollar cost
  • inherited-fact coverage   (deterministic; must_inherit keyword hits)
  • reset-question count       (deterministic; regex matches on response)
  • forbidden-drift count      (deterministic; alternative-choice hits)
  • decomposed rubric          (Haiku judge x N runs: factual / specific / complete / hallucinations)

Headline metric: time/tokens/turns to productive output in S2 with CE-backed
state vs cold start. The lower the ce_continue numbers (vs no_context_cold),
the stronger the continuity claim.

Requires ANTHROPIC_API_KEY in env.

Usage:
    export ANTHROPIC_API_KEY=...
    python bench/run_continuity.py                          # all 7 tasks, 3 modes, 3 judge runs
    python bench/run_continuity.py --tasks-subset 2         # smoke test
    python bench/run_continuity.py --modes no_context_cold,ce_compact   # just two modes
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grade_v2 import (  # noqa: E402
    keyword_hits, parse_decomposed, DECOMPOSED_RUBRIC, cost_usd,
    aggregate_grades, DecomposedGrade,
)

HERE = Path(__file__).parent
DATA = HERE / "data" / "continuity"


def system_for_mode(mode: str, task: dict) -> str:
    """Build the system prompt that simulates each delivery mode of CE state."""
    if mode == "no_context_cold":
        return ""
    if mode == "ce_full":
        state = task["session_1_state"]
        return (
            "You are an AI assistant continuing a paused workflow. The user's "
            "previous session established the following state, which you "
            "should respect and build on without re-asking:\n\n"
            f"PREVIOUS SESSION CONTEXT:\n{json.dumps(state, indent=2)}\n\n"
            "Do not re-ask the user for facts that are already in the state above. "
            "Continue from where the previous session left off."
        )
    if mode == "ce_compact":
        handoff = task["session_1_compact_handoff"]
        return (
            "You are an AI assistant continuing a paused workflow. The user's "
            "previous session left this handoff note:\n\n"
            f"HANDOFF FROM PREVIOUS SESSION:\n{handoff}\n\n"
            "Do not re-ask the user for facts that are already covered in the "
            "handoff above. Continue from where the previous session left off."
        )
    return ""


def score_inheritance(response: str, gold: dict) -> dict:
    """Deterministic scoring of state inheritance."""
    must = gold.get("must_inherit", [])
    reset_qs = gold.get("reset_questions", [])
    forbidden = gold.get("forbidden_drift", [])

    must_hit = 0
    must_results = []
    for f in must:
        hits = keyword_hits(response, f.get("keywords", []))
        ok = bool(hits)
        if ok:
            must_hit += 1
        must_results.append({"name": f["name"], "hit": ok, "matched": hits})

    reset_hits = 0
    reset_results = []
    norm = response.lower()
    for q in reset_qs:
        matched = False
        matches = []
        for pat in q.get("patterns", []):
            if re.search(pat.lower(), norm):
                matched = True
                matches.append(pat)
        if matched:
            reset_hits += 1
        reset_results.append({"name": q["name"], "hit": matched, "patterns_matched": matches})

    forbidden_hit = 0
    forbidden_results = []
    for f in forbidden:
        hits = keyword_hits(response, f.get("keywords", []))
        ok = bool(hits)
        if ok:
            forbidden_hit += 1
        forbidden_results.append({"name": f["name"], "hit": ok, "matched": hits})

    return {
        "must_total": len(must), "must_hit": must_hit,
        "inheritance_pct": round(100 * must_hit / len(must), 1) if must else 0,
        "reset_questions_total": len(reset_qs), "reset_questions_hit": reset_hits,
        "forbidden_drift_hit": forbidden_hit,
        "must_results": must_results,
        "reset_results": reset_results,
        "forbidden_results": forbidden_results,
    }


def call_anthropic(client, model: str, system: str, user: str, max_tokens: int = 600) -> dict:
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
    p.add_argument("--tasks", default=str(HERE / "continuity-tasks.json"))
    p.add_argument("--gold", default=str(HERE / "continuity-gold.json"))
    p.add_argument("--out", default=str(DATA / "results-continuity.json"))
    p.add_argument("--responses-out", default=str(DATA / "responses-continuity.json"))
    p.add_argument("--task-model", default="claude-sonnet-4-5")
    p.add_argument("--judge-model", default="claude-haiku-4-5")
    p.add_argument("--judge-runs", type=int, default=3)
    p.add_argument("--modes", default="no_context_cold,ce_compact,ce_full")
    p.add_argument("--tasks-subset", type=int, default=0)
    p.add_argument("--max-out", type=int, default=600)
    args = p.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.stderr.write("[!] ANTHROPIC_API_KEY not set\n")
        return 1
    try:
        import anthropic
    except ImportError:
        sys.stderr.write("[!] pip install anthropic\n")
        return 1
    client = anthropic.Anthropic(api_key=api_key)

    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))["tasks"]
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))["tasks"]
    if args.tasks_subset:
        tasks = tasks[: args.tasks_subset]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    print(f"Continuity benchmark — task={args.task_model}  judge={args.judge_model} x {args.judge_runs}")
    print(f"Tasks: {len(tasks)}  Modes: {modes}\n")

    responses = {}
    rows = []

    for ti, task in enumerate(tasks, 1):
        tid = task["id"]
        s2_prompt = task["session_2_prompt"]
        print(f"  [{ti}/{len(tasks)}] {tid}")
        responses[tid] = {}
        gold_t = gold.get(tid, {})

        for mode in modes:
            system = system_for_mode(mode, task)
            try:
                r = call_anthropic(client, args.task_model, system, s2_prompt, args.max_out)
            except Exception as e:
                print(f"      {mode:<18}  FAIL  {e}")
                continue
            r["model"] = args.task_model
            r["system_chars"] = len(system)
            responses[tid][mode] = r

            inh = score_inheritance(r["text"], gold_t)

            # Judge runs
            judge_grades = []
            user_judge = (
                f"TASK (session 2 of a paused workflow):\n{s2_prompt}\n\n"
                f"SESSION 1 SUMMARY (what the user had already done):\n{task['session_1_summary']}\n\n"
                f"RESPONSE TO GRADE:\n{r['text']}"
            )
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

            print(f"      {mode:<18}  "
                  f"in={r['input_tokens']:>5,} out={r['output_tokens']:>4}  "
                  f"inh={inh['inheritance_pct']:>5.1f}%  "
                  f"resets={inh['reset_questions_hit']}  "
                  f"drift={inh['forbidden_drift_hit']}  "
                  f"fact={judge_summary.get('factual_median', 0):.1f} "
                  f"spec={judge_summary.get('specific_median', 0):.1f} "
                  f"comp={judge_summary.get('complete_median', 0):.1f} "
                  f"halluc={judge_summary.get('hallucinations_mean', 0)}")

            rows.append({
                "task_id": tid,
                "category": task["category"],
                "mode": mode,
                "model": args.task_model,
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "latency_ms": r["latency_ms"],
                "cost_usd": round(cost_usd(args.task_model, r["input_tokens"], r["output_tokens"]), 6),
                "system_chars": r["system_chars"],
                "inheritance": inh,
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
        "modes": modes,
        "rows": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nWrote: {responses_path}\nWrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
