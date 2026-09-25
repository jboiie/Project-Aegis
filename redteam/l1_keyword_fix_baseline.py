"""Baseline: remove the bare topic-keyword pattern (`jailbreak(ed)?`)
from L1's JAILBREAK_PATTERNS, keeping every genuine injection-phrasing
pattern (`ignore previous instructions`, `you are now DAN`, `pretend
you have no restrictions`, `respond without safety filters`, `bypass
safety filters`, `act as unrestricted`, `from now on you will/must`)
and all ENCODING_PATTERNS unchanged.

This does NOT edit src/guardrails/regex_rules.py - it's a simulation
against already-saved screen results, re-applying the (unchanged)
regex definitions imported directly from that module so the two never
drift out of sync. For rows that fall through the fixed L1, we don't
have L2's decision (L1 short-circuited before L2 ever ran on them in
the original screen) - the only new computation is a targeted,
already-precedented InjectionDetector().check() (local, no Groq) on
those rows, mirroring the L2-threshold-baseline deviation.

Recall cost is defined as: rows whose current
blocked_reason is a bare match of the removed pattern, AND that do not
match any remaining L1 pattern, AND that L2 (at its current 0.85
threshold) would also let through - i.e. actually reaches an unblocked
state under the fix, not just "no longer stopped by this one pattern."
"""
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guardrails.regex_rules import JAILBREAK_PATTERNS, ENCODING_PATTERNS

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOVED_PATTERN = r"(?i)jailbreak(ed)?"
FIXED_PATTERNS = [re.compile(p) for p in JAILBREAK_PATTERNS if p != REMOVED_PATTERN] + \
                 [re.compile(p) for p in ENCODING_PATTERNS]

assert any(p == REMOVED_PATTERN for p in JAILBREAK_PATTERNS), \
    "REMOVED_PATTERN must match a real entry in regex_rules.py - guards against silent drift"


def matches_remaining_l1(text: str) -> bool:
    return any(p.search(text) for p in FIXED_PATTERNS)


def load_l1_blocked(split: str) -> list[dict]:
    rows = [json.loads(l) for l in open(os.path.join(_REPO_ROOT, "data", "laya_screen_results.jsonl"), encoding="utf-8")]
    return [r for r in rows if r["split"] == split and r["blocking_layer"] == "L1"]


def bare_keyword_rows(l1_rows: list[dict]) -> list[dict]:
    out = []
    for r in l1_rows:
        m = re.search(r"Matched known attack pattern: '(.+)'$", r["blocked_reason"])
        matched = m.group(1) if m else ""
        if re.fullmatch(REMOVED_PATTERN, matched):
            out.append(r)
    return out


async def check_l2_for_fallthrough(rows: list[dict]) -> dict:
    """Rows that no longer match L1 under the fix - does L2 catch them?
    New, targeted InjectionDetector().check() calls (no Groq) since L1
    short-circuited before L2 ever ran on these in the original screen."""
    from src.guardrails.injection import InjectionDetector
    detector = InjectionDetector()
    await detector.load()
    result = {}
    for r in rows:
        check = await detector.check(r["prompt"])
        result[r["prompt"]] = check.passed  # True = L2 does NOT block it either
    return result


async def main():
    print(f"Removed pattern: {REMOVED_PATTERN!r}")
    print(f"Remaining L1 patterns: {len(FIXED_PATTERNS)} (was {len(JAILBREAK_PATTERNS) + len(ENCODING_PATTERNS)})\n")

    for split in ("sweep", "test"):
        l1_rows = load_l1_blocked(split)
        bare = bare_keyword_rows(l1_rows)
        n_attack_bare = sum(1 for r in bare if r["label"] == "attack")
        n_benign_bare = sum(1 for r in bare if r["label"] == "benign")
        print(f"--- {split} --- L1-blocked total={len(l1_rows)}, bare-keyword-only candidates={len(bare)} "
              f"(attack={n_attack_bare}, benign={n_benign_bare})")

        still_l1 = [r for r in bare if matches_remaining_l1(r["prompt"])]
        fallthrough = [r for r in bare if r not in still_l1]
        print(f"  still caught by another L1 pattern: {len(still_l1)}")
        print(f"  fall through to L2: {len(fallthrough)}")

        if fallthrough:
            l2_pass = await check_l2_for_fallthrough(fallthrough)
            truly_unblocked = [r for r in fallthrough if l2_pass[r["prompt"]]]
        else:
            truly_unblocked = []
        n_attack_unblocked = sum(1 for r in truly_unblocked if r["label"] == "attack")
        n_benign_unblocked = sum(1 for r in truly_unblocked if r["label"] == "benign")
        print(f"  truly unblocked under the fix (L1 fixed AND L2 lets through): "
              f"{len(truly_unblocked)} (attack={n_attack_unblocked}, benign={n_benign_unblocked})")

        out_path = os.path.join(_REPO_ROOT, "data", f"l1_keyword_fix_{split}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "split": split,
                "bare_keyword_candidates": len(bare),
                "still_caught_by_other_l1": len(still_l1),
                "fallthrough_to_l2": len(fallthrough),
                "truly_unblocked": len(truly_unblocked),
                "truly_unblocked_attack": n_attack_unblocked,
                "truly_unblocked_benign": n_benign_unblocked,
                "unblocked_prompts": [r["prompt"] for r in truly_unblocked],
            }, f, indent=2)
        print(f"  written to {out_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
