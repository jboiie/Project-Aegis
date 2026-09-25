import json
from collections import Counter
for fname in ["dryrun_guardrails_off.jsonl","dryrun_template.jsonl","dryrun_encoding.jsonl","dryrun_pair.jsonl",
              "dryrun2_template.jsonl","dryrun2_encoding.jsonl","dryrun2_pair.jsonl"]:
    try:
        rows = [json.loads(l) for l in open(f"data/{fname}", encoding="utf-8")]
    except FileNotFoundError:
        print(fname, "NOT FOUND"); continue
    print(f"\n=== {fname} === n={len(rows)}")
    if rows:
        c = Counter(r.get("outcome") for r in rows)
        print("outcome counts:", dict(c))
        print("sample keys:", list(rows[0].keys()))
        print("sample response snippet:", rows[0].get("response","")[:100])
