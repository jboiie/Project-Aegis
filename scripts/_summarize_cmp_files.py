import json
from collections import Counter

for fname in ["cmp_gptoss120b_template.jsonl","cmp_gptoss120b_encoding.jsonl","cmp_gptoss120b_pair.jsonl",
              "cmp_qwen_template.jsonl","cmp_qwen_encoding.jsonl","cmp_qwen_pair.jsonl"]:
    try:
        rows = [json.loads(l) for l in open(f"data/{fname}", encoding="utf-8")]
    except FileNotFoundError:
        print(fname, "NOT FOUND")
        continue
    print(f"\n=== {fname} === n={len(rows)}")
    if rows:
        print("keys:", list(rows[0].keys()))
        c = Counter(r.get("outcome", r.get("bypassed")) for r in rows)
        print("outcome/bypassed counts:", dict(c))
