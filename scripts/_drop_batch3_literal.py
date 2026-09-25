import json

benign_rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
before = len(benign_rows)
kept = [r for r in benign_rows if not (r.get("batch") == 3 and r["category"] == "literal_editing_instruction")]
dropped = before - len(kept)
with open("data/benign_prompts.jsonl", "w", encoding="utf-8") as f:
    for r in kept:
        f.write(json.dumps(r) + "\n")
print(f"benign_prompts.jsonl: {before} -> {len(kept)} ({dropped} dropped)")

screen_rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
before2 = len(screen_rows)
kept2 = [r for r in screen_rows if not (r.get("batch") == 3 and r.get("category") == "literal_editing_instruction")]
dropped2 = before2 - len(kept2)
with open("data/laya_screen_results.jsonl", "w", encoding="utf-8") as f:
    for r in kept2:
        f.write(json.dumps(r) + "\n")
print(f"laya_screen_results.jsonl: {before2} -> {len(kept2)} ({dropped2} dropped)")
