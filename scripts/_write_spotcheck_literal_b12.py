import json

screen_rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
by_prompt = {}
for r in screen_rows:
    if r["row_type"] == "benign" and r["category"] == "literal_editing_instruction":
        by_prompt[r["prompt"]] = r

benign_rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
b12 = [r for r in benign_rows if r["category"] == "literal_editing_instruction" and r["batch"] in (1, 2)]

lines = ["# Batches 1-2 literal_editing_instruction Audit", "",
         f"All {len(b12)} batches 1-2 literal_editing_instruction rows, blocked and unblocked.", ""]
for i, r in enumerate(b12, 1):
    sr = by_prompt.get(r["prompt"])
    blocked_by = sr["blocking_layer"] if sr and sr["blocking_layer"] else "none"
    lines.append(f"{i}. **row_id**: b{r['batch']}-{i}  **split**: {r['split']}  **blocked_by**: {blocked_by}")
    lines.append(f"   {r['prompt']}")
    lines.append("")

with open("data/spotcheck_literal_b12.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"total b1+b2 literal_editing rows: {len(b12)}")
n_missing = sum(1 for r in b12 if r["prompt"] not in by_prompt)
print(f"rows not found in screen results: {n_missing}")
