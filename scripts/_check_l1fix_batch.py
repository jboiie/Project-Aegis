import json
data = json.load(open("data/l1_keyword_fix_test.json", encoding="utf-8"))
unblocked_prompts = set(data["unblocked_prompts"])
rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
test_benign = [r for r in rows if r["row_type"]=="benign" and r["split"]=="test"]
by_batch = {}
for r in test_benign:
    if r["prompt"] in unblocked_prompts:
        by_batch[r.get("batch")] = by_batch.get(r.get("batch"),0)+1
print("unblocked-by-L1-fix rows, by batch:", by_batch)
