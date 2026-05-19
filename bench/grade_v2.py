#!/usr/bin/env python3
"""
grade_v2.py — Improved measurement layer addressing the v1.1 critique.

What's new vs the tokenomics.py --grade pass:

  1. **Gold-answer fact recall.** For each task, gold-answers.json defines a
     list of facts that MUST be covered, optional facts that MAY be covered,
     and FORBIDDEN content (hallucinations, wrong OS, etc). Scoring is
     deterministic keyword-match first, with optional LLM-confirmed soft
     matches for keywords that didn't hit. Output is a coverage % per
     response — opinion replaced with measurement.

  2. **Decomposed rubric.** Each response is scored on four axes
     separately, not one holistic 1-10:
       - factual_correctness  (1-5)
       - specificity          (1-5)
       - completeness         (1-5) — against gold must_include
       - hallucination_count  (integer; lower is better)

  3. **Multi-judge, multi-run.** Each response is graded N times by each
     configured judge. Cross-family judges (Anthropic + OpenAI) break
     self-evaluation bias. Reported metrics: median + IQR across runs.

  4. **No-context baseline.** A fourth measurement path: same task model,
     no skill context at all. Tells you whether retrieval is doing real
     work or the model already knew enough.

  5. **Precision@K / Recall@K / MRR.** When expected_sources is labeled,
     score the search results against it.

  6. **Latency + cost.** End-to-end milliseconds per task and dollar cost
     per response, computed from per-model price tables.

  7. **Failure-mode labels.** Each low-scoring response gets one or more
     failure-mode tags from a fixed enum (per task in gold-answers.json).
     Lets us count "what kind of failures" not just "how many."

Usage:
    python bench/grade_v2.py --responses bench/data/v1.2/responses-v12.json --gold bench/gold-answers.json
    python bench/grade_v2.py --responses ... --judges anthropic,openai --runs 3

This module is importable; run_v12.py orchestrates the full pipeline.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable

HERE = Path(__file__).parent

# ---------- Pricing table (USD per 1M tokens, input/output) ----------
# Update as published prices change. Used for the cost column only.
PRICING = {
    "claude-haiku-4-5":      {"in": 1.00,  "out":  5.00},
    "claude-sonnet-4-5":     {"in": 3.00,  "out": 15.00},
    "claude-sonnet-4-6":     {"in": 3.00,  "out": 15.00},
    "claude-opus-4-7":       {"in": 15.00, "out": 75.00},
    "gpt-4o":                {"in": 2.50,  "out": 10.00},
    "gpt-4o-mini":           {"in": 0.15,  "out":  0.60},
    "gpt-5":                 {"in": 5.00,  "out": 25.00},  # placeholder; update on release
    "gemini-1.5-pro":        {"in": 1.25,  "out":  5.00},
    "gemini-2.0-flash":      {"in": 0.10,  "out":  0.40},
    "local":                 {"in": 0.00,  "out":  0.00},
}


def cost_usd(model: str, in_tok: int, out_tok: int) -> float:
    p = PRICING.get(model, PRICING["claude-haiku-4-5"])
    return (in_tok * p["in"] + out_tok * p["out"]) / 1_000_000


# ---------- Gold-answer fact recall (deterministic) ----------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


_NEGATION_PREFIXES = ("no ", "not ", "without ", "avoid ", "avoids ", "avoiding ",
                      "don't ", "do not ", "never ", "skip ", "skipping ",
                      "no gradients", "no glow")


def keyword_hits(text: str, keywords: list[str], guard_negation: bool = False) -> list[str]:
    """Return the subset of keywords that appear in text (case-insensitive,
    whitespace-tolerant). A keyword may be a multi-word phrase. When
    guard_negation is True, suppress hits where the keyword is immediately
    preceded by a negation token — used for forbidden checks so 'no gradients'
    doesn't count as the response asserting gradients."""
    if not keywords:
        return []
    norm = _normalize(text)
    hits = []
    for k in keywords:
        nk = _normalize(k)
        if nk not in norm:
            continue
        if guard_negation:
            # Find every occurrence; only count if at least one is NOT negated.
            counted = False
            start = 0
            while True:
                idx = norm.find(nk, start)
                if idx < 0:
                    break
                window = norm[max(0, idx - 30):idx]
                if not any(window.rstrip().endswith(neg.rstrip()) for neg in _NEGATION_PREFIXES):
                    counted = True
                    break
                start = idx + len(nk)
            if counted:
                hits.append(k)
        else:
            hits.append(k)
    return hits


@dataclass
class FactResult:
    name: str
    required: bool          # True = must_include, False = may_include
    hit: bool
    matched_keywords: list[str]


@dataclass
class FactRecallResult:
    must_total: int
    must_hit: int
    may_total: int
    may_hit: int
    forbidden_hits: list[str]    # names of forbidden patterns that fired
    facts: list[FactResult]
    coverage_pct: float          # must_hit / must_total
    bonus_pct: float             # may_hit / may_total
    failure_modes: list[str]     # inferred from misses


def score_facts(response: str, gold: dict) -> FactRecallResult:
    must = gold.get("must_include", [])
    may = gold.get("may_include", [])
    forbidden = gold.get("forbidden", [])

    def _hit(f: dict) -> tuple[bool, list[str]]:
        kws = f.get("keywords") or []
        if not kws:
            return True, []  # empty keyword list = manual-review pass
        hits = keyword_hits(response, kws)
        mode = f.get("match_mode", "any")
        if mode == "all":
            ok = len(hits) == len(kws)
        else:  # default "any"
            ok = bool(hits)
        return ok, hits

    facts: list[FactResult] = []
    must_hit = 0
    for f in must:
        ok, hits = _hit(f)
        if ok:
            must_hit += 1
        facts.append(FactResult(f["name"], True, ok, hits))

    may_hit = 0
    for f in may:
        ok, hits = _hit(f)
        if ok:
            may_hit += 1
        facts.append(FactResult(f["name"], False, ok, hits))

    forbidden_fired = []
    for f in forbidden:
        kws = f.get("keywords") or []
        hits = keyword_hits(response, kws, guard_negation=True)
        if hits:
            forbidden_fired.append(f["name"])

    coverage = (must_hit / len(must)) * 100 if must else 100.0
    bonus = (may_hit / len(may)) * 100 if may else 0.0

    # Infer failure modes from misses
    failure_modes = []
    enumerated = gold.get("failure_modes", [])
    if coverage < 60 and "vague_advice" in enumerated:
        failure_modes.append("vague_advice")
    for f in facts:
        if f.required and not f.hit:
            # Map common patterns to failure-mode tags. Names in gold-answers.json
            # are designed so this mapping is mostly identity.
            tag_map = {
                "windows_command": "wrong_os",
                "linux_cron": "wrong_os",
                "negative_prompt": "missing_negative",
                "agent_loop": "no_loop",
                "tool_result_id": "missing_tool_id",
                "anthropic_sdk": "wrong_sdk",
                "backup_first": "no_backup",
                "safety_step": "no_safety_step",
                "version_named": "missing_version",
                "vulnerability_named": "missing_vulnerability_name",
            }
            tag = tag_map.get(f.name, f"missing_{f.name}")
            if tag in enumerated:
                failure_modes.append(tag)
    failure_modes.extend([f"forbidden:{n}" for n in forbidden_fired])

    return FactRecallResult(
        must_total=len(must), must_hit=must_hit,
        may_total=len(may), may_hit=may_hit,
        forbidden_hits=forbidden_fired,
        facts=facts,
        coverage_pct=round(coverage, 1),
        bonus_pct=round(bonus, 1),
        failure_modes=sorted(set(failure_modes)),
    )


# ---------- Retrieval quality (Precision@K / Recall@K / MRR) ----------

@dataclass
class RetrievalQuality:
    k: int
    precision_at_k: float
    recall_at_k: float
    mrr: float
    expected: list[str]
    retrieved: list[str]
    hits: list[str]


def score_retrieval(retrieved_skill_ids: list[str], expected_sources: list[str], k: int = None) -> RetrievalQuality:
    """retrieved_skill_ids: the ordered list of skill_ids returned by /api/search.
    expected_sources: the labeled gold list for the task."""
    if k is None:
        k = len(retrieved_skill_ids)
    top_k = retrieved_skill_ids[:k]
    expected_set = set(expected_sources)
    hits = [s for s in top_k if s in expected_set]
    precision = (len(hits) / len(top_k)) if top_k else 0.0
    recall = (len(hits) / len(expected_set)) if expected_set else 0.0
    # MRR: 1 / rank of first relevant result
    mrr = 0.0
    for i, s in enumerate(top_k, 1):
        if s in expected_set:
            mrr = 1.0 / i
            break
    return RetrievalQuality(
        k=k,
        precision_at_k=round(precision, 3),
        recall_at_k=round(recall, 3),
        mrr=round(mrr, 3),
        expected=expected_sources,
        retrieved=top_k,
        hits=hits,
    )


# ---------- Decomposed rubric (LLM-judged) ----------

DECOMPOSED_RUBRIC = """You are grading an AI assistant's response to a user task. Score on FOUR independent axes.

Axes:
- factual_correctness (1-5): Do the named APIs, commands, paths, syntax actually exist as stated? Score 1 if there are clear factual errors; 5 if everything checkable looks correct.
- specificity (1-5): Is the response concrete? 1 = generic platitudes; 5 = task-specific with exact names, values, paths, code.
- completeness (1-5): Does it cover what a user would need to actually finish the task? 1 = misses critical steps; 5 = covers everything required.
- hallucination_count (integer >= 0): Count distinct fabricated facts — things the response asserts as true that are likely wrong or invented. 0 if none spotted.

Output EXACTLY five lines in this format, nothing else:
FACTUAL: <1-5>
SPECIFIC: <1-5>
COMPLETE: <1-5>
HALLUCINATIONS: <integer>
NOTES: <one short sentence on the most notable strength or weakness>"""


@dataclass
class DecomposedGrade:
    factual: int = 0
    specific: int = 0
    complete: int = 0
    hallucinations: int = 0
    notes: str = ""
    judge: str = ""
    run_idx: int = 0


def parse_decomposed(text: str) -> DecomposedGrade:
    g = DecomposedGrade()
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("FACTUAL:"):
            digits = re.findall(r"\d+", line)
            if digits:
                g.factual = max(1, min(5, int(digits[0])))
        elif line.upper().startswith("SPECIFIC:"):
            digits = re.findall(r"\d+", line)
            if digits:
                g.specific = max(1, min(5, int(digits[0])))
        elif line.upper().startswith("COMPLETE:"):
            digits = re.findall(r"\d+", line)
            if digits:
                g.complete = max(1, min(5, int(digits[0])))
        elif line.upper().startswith("HALLUCINATIONS:"):
            digits = re.findall(r"\d+", line)
            if digits:
                g.hallucinations = max(0, int(digits[0]))
        elif line.upper().startswith("NOTES:"):
            g.notes = line.split(":", 1)[1].strip()
    return g


# ---------- Multi-judge orchestration ----------

@dataclass
class JudgeConfig:
    name: str            # e.g. "anthropic:haiku" or "openai:gpt-4o-mini"
    family: str          # "anthropic" | "openai" | "gemini" | "session"
    model: str
    api_key_env: str     # which env var to read


def call_anthropic_judge(model: str, system: str, user: str, api_key: str) -> tuple[str, int, int]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model, max_tokens=300,
        system=system, messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return text, int(resp.usage.input_tokens), int(resp.usage.output_tokens)


def call_openai_judge(model: str, system: str, user: str, api_key: str) -> tuple[str, int, int]:
    import openai
    client = openai.OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model, max_tokens=300,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    text = resp.choices[0].message.content or ""
    u = resp.usage
    return text, int(u.prompt_tokens), int(u.completion_tokens)


JUDGE_DISPATCH = {
    "anthropic": call_anthropic_judge,
    "openai": call_openai_judge,
}


def grade_response_decomposed(
    task_prompt: str, response: str,
    judges: list[JudgeConfig], runs: int = 3,
    session_grader: Optional[Callable[[str, str], DecomposedGrade]] = None,
) -> list[DecomposedGrade]:
    """Returns a list of DecomposedGrade — one per (judge, run). The session_grader
    callable, if provided, is used for judges of family 'session' (the current
    Claude Code conversation acting as judge, useful when API keys aren't available)."""
    user = f"TASK:\n{task_prompt}\n\nRESPONSE TO GRADE:\n{response}"
    grades = []
    for j in judges:
        for run_idx in range(runs):
            if j.family == "session" and session_grader is not None:
                g = session_grader(task_prompt, response)
            else:
                api_key = os.environ.get(j.api_key_env, "")
                if not api_key:
                    g = DecomposedGrade(notes=f"(no {j.api_key_env})")
                else:
                    try:
                        fn = JUDGE_DISPATCH[j.family]
                        text, _, _ = fn(j.model, DECOMPOSED_RUBRIC, user, api_key)
                        g = parse_decomposed(text)
                    except Exception as e:
                        g = DecomposedGrade(notes=f"(judge error: {e})")
            g.judge = j.name
            g.run_idx = run_idx
            grades.append(g)
    return grades


def aggregate_grades(grades: list[DecomposedGrade]) -> dict:
    """Median + IQR + per-judge breakdown across multi-judge multi-run grading."""
    valid = [g for g in grades if g.factual > 0]
    if not valid:
        return {"n": 0}
    def med(xs): return statistics.median(xs)
    def iqr(xs):
        if len(xs) < 4:
            return 0.0
        q = statistics.quantiles(xs, n=4)
        return round(q[2] - q[0], 2)
    return {
        "n": len(valid),
        "factual_median": med([g.factual for g in valid]),
        "factual_iqr": iqr([g.factual for g in valid]),
        "specific_median": med([g.specific for g in valid]),
        "specific_iqr": iqr([g.specific for g in valid]),
        "complete_median": med([g.complete for g in valid]),
        "complete_iqr": iqr([g.complete for g in valid]),
        "hallucinations_mean": round(statistics.mean([g.hallucinations for g in valid]), 2),
        "hallucinations_max": max([g.hallucinations for g in valid]),
        "composite_median": round(med([(g.factual + g.specific + g.complete) / 3 for g in valid]), 2),
        "per_judge": {
            j: {
                "factual_median": med([g.factual for g in valid if g.judge == j]),
                "specific_median": med([g.specific for g in valid if g.judge == j]),
                "complete_median": med([g.complete for g in valid if g.judge == j]),
            }
            for j in sorted({g.judge for g in valid})
        },
    }
