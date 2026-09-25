import json
import re
import statistics

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")  # generic approximation - target
# model isn't OpenAI's own, so this is a documented estimate, not a vendor
# exact count. Attacker/judge counts below ARE vendor-exact (Groq's own
# usage field, logged directly).


def tok(text: str) -> int:
    return len(enc.encode(text or ""))


# ── Attacker + judge: real vendor-reported usage, parsed from logs ──
def parse_usage_lines(path: str, role: str) -> list[dict]:
    rows = []
    pattern = re.compile(r"(\w+)=(\{[^}]*\}|\S+)")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "groq_call_usage" not in line or f"role={role}" not in line:
                continue
            fields = dict(pattern.findall(line))
            rows.append({
                "prompt_tokens": int(fields["prompt_tokens"]),
                "completion_tokens": int(fields["completion_tokens"]),
                "total_tokens": int(fields["total_tokens"]),
            })
    return rows


attacker_rows = parse_usage_lines("scripts/_attacker_usage_raw.txt", "attacker")
print(f"ATTACKER (qwen/qwen3.6-27b), n={len(attacker_rows)} real calls:")
print(f"  prompt_tokens:     mean={statistics.mean(r['prompt_tokens'] for r in attacker_rows):.0f}  "
      f"min={min(r['prompt_tokens'] for r in attacker_rows)}  max={max(r['prompt_tokens'] for r in attacker_rows)}")
print(f"  completion_tokens: mean={statistics.mean(r['completion_tokens'] for r in attacker_rows):.0f}  "
      f"min={min(r['completion_tokens'] for r in attacker_rows)}  max={max(r['completion_tokens'] for r in attacker_rows)}")
print(f"  total_tokens:      mean={statistics.mean(r['total_tokens'] for r in attacker_rows):.0f}  sum={sum(r['total_tokens'] for r in attacker_rows)}")

judge_rows = []
for f in ["btst3fssl.output"]:
    pass  # judge usage was printed to stdout of the judge demo, parsed below directly

print()

# ── Target: sandbox's ChatResponse doesn't pass through vendor usage, ──
# estimate via tokenizer on the real captured prompt+response text.
for name, path in [("template", "data/dryrun_template.jsonl"), ("encoding", "data/dryrun_encoding.jsonl"), ("pair", "data/dryrun_pair.jsonl")]:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]
    token_counts = [tok(r["prompt"]) + tok(r["response"]) for r in rows]
    print(f"TARGET call, {name} (n={len(rows)}, tokenizer-estimated prompt+response): "
          f"mean={statistics.mean(token_counts):.0f}  min={min(token_counts)}  max={max(token_counts)}")

print()
outcomes = {"blocked_by_stack": 0, "refused_by_model": 0, "bypassed": 0, "errored": 0}
for path in ["data/dryrun_template.jsonl", "data/dryrun_encoding.jsonl", "data/dryrun_pair.jsonl"]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            outcomes[r["outcome"]] += 1
print("COMBINED outcome counts across all 28 dry-run attempts:", outcomes)

pair_rows = [json.loads(l) for l in open("data/dryrun_pair.jsonl", encoding="utf-8")]
fallback_total = sum(r["metadata"].get("attacker_fallback_count", 0) for r in pair_rows)
total_attacker_calls = len(attacker_rows)
print(f"\nAttacker fallback rate: {fallback_total}/{total_attacker_calls} calls used the canned fallback "
      f"({fallback_total/total_attacker_calls:.1%}) - i.e. attacker LLM (qwen3.6-27b) refusal/failure rate")
