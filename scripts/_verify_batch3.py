import json
from collections import Counter

rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
print("total rows:", len(rows))
b3 = [r for r in rows if r.get("batch") == 3]
print("batch3 total:", len(b3))
print(Counter((r["category"], r["split"]) for r in b3))
print("any batch3 not split=test:", any(r["split"] != "test" for r in b3))
prompts = [r["prompt"] for r in rows]
print("exact dup prompts overall:", len(prompts) - len(set(prompts)))
