import json

REFUSAL_MARKERS = ["i won't help", "i'm not going to help", "i can't help with that",
                    "i cannot help", "i won't write", "i'm not able to", "i won't provide"]

for l in open("data/pair_rerun_20.jsonl", encoding="utf-8"):
    r = json.loads(l)
    prompt_lower = r["prompt"].lower()
    is_refusal_prompt = any(m in prompt_lower for m in REFUSAL_MARKERS)
    if is_refusal_prompt:
        print(f"outcome={r['outcome']:<16} judge_score={r['judge_score']}  ATTACKER REFUSED, sent as candidate: {r['prompt'][:80]!r}")
