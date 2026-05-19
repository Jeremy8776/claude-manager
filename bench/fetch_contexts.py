#!/usr/bin/env python3
"""
fetch_contexts.py — Pre-fetch CE smart + search contexts for each task and
dump them to disk. Used when the grading pass needs an LLM that isn't
reachable via API key (e.g. running through Claude Code session auth).

Output: bench/artifacts/contexts/<task_id>.smart.md and
bench/artifacts/contexts/<task_id>.search.md plus
bench/artifacts/contexts/manifest.json with token counts + skill counts per task.

Run AFTER `python bench/tokenomics.py` (or alongside; only depends on CE).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Re-use the helpers we already built in tokenomics.py.
sys.path.insert(0, str(Path(__file__).parent))
from tokenomics import (  # noqa: E402
    DEFAULT_CE_URL,
    build_context_text,
    build_search_context_text,
    count_tokens,
    fetch_active_skill_bodies,
    fetch_compiled_baseline,
    post_json,
    reachable,
)

HERE = Path(__file__).parent
OUT_DIR = HERE / "artifacts" / "contexts"
TASKS_PATH = HERE / "tasks.json"

CE_URL = os.environ.get("CE_URL", DEFAULT_CE_URL)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "16000"))
SEARCH_LIMIT = int(os.environ.get("SEARCH_LIMIT", "8"))


def main() -> int:
    if not reachable(CE_URL):
        sys.stderr.write(f"[!] CE not reachable at {CE_URL}\n")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with TASKS_PATH.open(encoding="utf-8") as f:
        tasks = json.load(f)

    print(f"Fetching active skill bodies...")
    active_bodies = fetch_active_skill_bodies(CE_URL)
    print(f"  {len(active_bodies)} active skills loaded")

    manifest = {
        "ce_url": CE_URL,
        "max_tokens": MAX_TOKENS,
        "search_limit": SEARCH_LIMIT,
        "active_skill_count": len(active_bodies),
        "tasks": [],
    }

    for i, task in enumerate(tasks, 1):
        tid = task["id"]
        print(f"  [{i:>2}/{len(tasks)}] {tid:<28}", end=" ", flush=True)

        smart = post_json(CE_URL, "/api/compile/smart",
                          {"task": task["prompt"], "maxTokens": MAX_TOKENS})
        selected = smart.get("selectedSkillIds") or []
        smart_ctx = build_context_text(selected, active_bodies)
        smart_tokens = count_tokens(smart_ctx)

        search = post_json(CE_URL, "/api/search",
                           {"query": task["prompt"], "limit": SEARCH_LIMIT})
        chunks = search.get("results") or []
        search_ctx = build_search_context_text(chunks)
        search_tokens = count_tokens(search_ctx)

        (OUT_DIR / f"{tid}.smart.md").write_text(smart_ctx, encoding="utf-8")
        (OUT_DIR / f"{tid}.search.md").write_text(search_ctx, encoding="utf-8")

        manifest["tasks"].append({
            "id": tid,
            "category": task.get("category", ""),
            "prompt": task["prompt"],
            "selected_skill_count": len(selected),
            "smart_tokens": smart_tokens,
            "search_tokens": search_tokens,
            "search_chunk_count": len(chunks),
            "smart_path": str((OUT_DIR / f"{tid}.smart.md").relative_to(HERE.parent)),
            "search_path": str((OUT_DIR / f"{tid}.search.md").relative_to(HERE.parent)),
        })
        print(f"smart {smart_tokens:>6,}tk / search {search_tokens:>5,}tk")

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {len(tasks)} task contexts to {OUT_DIR.relative_to(HERE.parent)}/")
    print(f"Manifest: {(OUT_DIR / 'manifest.json').relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
