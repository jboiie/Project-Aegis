import json
rows = [json.loads(l) for l in open("data/benign_prompts.jsonl", encoding="utf-8")]
dups = {'Can you explain the basic mechanisms behind prompt injection attacks in large language models?',
        'What role does tokenization play in enabling or preventing prompt injection attacks?'}
for r in rows:
    if r["prompt"] in dups:
        print(r["batch"], r["prompt"][:50])
