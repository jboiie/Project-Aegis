import json
import random

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
b3 = [r for r in rows if r.get("batch") == 3]

blocked = [r for r in b3 if r["blocking_layer"] in ("L1", "L2")]
unblocked = [r for r in b3 if r["blocking_layer"] is None]

random.seed(42)
sample_unblocked = random.sample(unblocked, 10)

lines = ["# Batch 3 Spot-Check", "", f"All {len(blocked)} batch-3 rows blocked by L1/L2, plus 10 random unblocked rows.", ""]
i = 1
for r in blocked:
    lines.append(f"{i}. **row_id**: b3-{i}  **category**: {r['category']}  **blocked_by**: {r['blocking_layer']}")
    lines.append(f"   {r['prompt']}")
    lines.append("")
    i += 1

lines.append("---")
lines.append("")
for r in sample_unblocked:
    lines.append(f"{i}. **row_id**: b3-{i}  **category**: {r['category']}  **blocked_by**: none")
    lines.append(f"   {r['prompt']}")
    lines.append("")
    i += 1

with open("data/spotcheck_batch3.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"blocked={len(blocked)} unblocked_sample={len(sample_unblocked)} total_entries={i-1}")
