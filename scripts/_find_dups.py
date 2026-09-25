import json
from collections import Counter
rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
c = Counter(r["prompt"] for r in rows)
for p, n in c.items():
    if n > 1:
        print(n, repr(p))
