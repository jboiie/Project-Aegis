import json

for name, path in [("template", "data/dryrun_template.jsonl"), ("encoding", "data/dryrun_encoding.jsonl"), ("pair", "data/dryrun_pair.jsonl")]:
    print(f"=== {name} ===")
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line)
            print(f"  #{i}: {r['response'][:90]!r}")
