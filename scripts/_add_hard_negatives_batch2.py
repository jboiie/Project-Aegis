"""Adds 50 more security_education + 50 more literal_editing_instruction
benign prompts (batch 2) to the existing 200-row set - the original had
only ~10 rows in security_education, too few for a stable per-category
FPR. Generated in 5 calls of 10 each per category (not one call of 50)
for real phrasing variety, not near-duplicates from one generation.

Existing rows keep their original split assignment - only the new rows
get split-assigned, so no previously-assigned row moves splits.
"""
import asyncio
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.gateway.schemas import ChatRequest, Message
from src.llm.groq import GroqProvider
from data.generate_benign_prompts import HARD_CATEGORIES, generate_category, SPLIT_RATIOS

TARGET_CATEGORIES = ["security_education", "literal_editing_instruction"]
N_NEW_PER_CATEGORY = 50
CALLS_PER_CATEGORY = 5
N_PER_CALL = N_NEW_PER_CATEGORY // CALLS_PER_CATEGORY


def assign_split_to_new_rows(new_rows: list[dict]) -> None:
    by_category: dict[str, list[dict]] = {}
    for r in new_rows:
        by_category.setdefault(r["category"], []).append(r)
    for group in by_category.values():
        random.shuffle(group)
        n = len(group)
        n_cal = round(n * SPLIT_RATIOS["calibration"])
        n_sweep = round(n * SPLIT_RATIOS["sweep"])
        for i, r in enumerate(group):
            r["split"] = "calibration" if i < n_cal else ("sweep" if i < n_cal + n_sweep else "test")


async def main():
    with open("data/benign_prompts.jsonl", encoding="utf-8") as f:
        existing_rows = [json.loads(l) for l in f]
    for r in existing_rows:
        r.setdefault("batch", 1)

    provider = GroqProvider()
    new_rows = []
    for category in TARGET_CATEGORIES:
        description = HARD_CATEGORIES[category]
        for call_i in range(CALLS_PER_CATEGORY):
            print(f"Generating call {call_i+1}/{CALLS_PER_CATEGORY} of {N_PER_CALL} for {category}...")
            prompts = await generate_category(provider, category, description, N_PER_CALL)
            for p in prompts:
                new_rows.append({"prompt": p, "label": "benign", "difficulty": "hard",
                                  "category": category, "batch": 2})

    assign_split_to_new_rows(new_rows)

    all_rows = existing_rows + new_rows
    with open("data/benign_prompts.jsonl", "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r) + "\n")

    print(f"\nWrote {len(all_rows)} total rows ({len(new_rows)} new, batch=2).")
    from collections import Counter
    by_cat_split = Counter((r["category"], r["split"]) for r in all_rows)
    print("\nPer-category counts per split (full set):")
    categories = sorted(set(r["category"] for r in all_rows))
    for cat in categories:
        counts = {split: by_cat_split.get((cat, split), 0) for split in ("calibration", "sweep", "test")}
        print(f"  {cat:<28} cal={counts['calibration']:<4} sweep={counts['sweep']:<4} test={counts['test']:<4}")


if __name__ == "__main__":
    asyncio.run(main())
