import json
r = json.loads(open("data/cmp_gptoss120b_template.jsonl", encoding="utf-8").readline())
print(json.dumps(r, indent=2)[:2000])
