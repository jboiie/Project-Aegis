import json
import re

rows = [json.loads(l) for l in open("data/laya_screen_results.jsonl", encoding="utf-8")]
sec_ed_test_l1 = [r for r in rows if r["split"]=="test" and r["row_type"]=="benign"
                  and r["category"]=="security_education" and r["blocking_layer"]=="L1"]

print(f"security_education test rows blocked by L1: {len(sec_ed_test_l1)}")

TOPIC_KEYWORD_PATTERNS = [
    re.compile(r"(?i)jailbreak(ed)?"),
]
# genuine injection-shaped patterns (imperative, aimed at the model)
GENUINE_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+(DAN|AIM|STAN|DUDE|developer\s+mode)"),
    re.compile(r"(?i)pretend\s+you\s+(are|have)\s+no\s+(restrictions|guidelines|rules)"),
    re.compile(r"(?i)respond\s+without\s+any\s+(safety|ethical)\s+(filters|guidelines)"),
    re.compile(r"(?i)bypass\s+(your|the)\s+(safety|content)\s+(filters|policy)"),
    re.compile(r"(?i)act\s+as\s+an?\s+(unrestricted|uncensored|unfiltered)"),
    re.compile(r"(?i)from\s+now\s+on,?\s+you\s+(will|must|should)\s+(not\s+)?follow"),
]

topic_kw = 0
genuine = 0
for r in sec_ed_test_l1:
    reason = r["blocked_reason"]
    m = re.search(r"Matched known attack pattern: '(.+)'$", reason)
    matched_text = m.group(1) if m else reason
    is_topic = any(p.fullmatch(matched_text) or p.search(matched_text) and matched_text.lower() in ("jailbreak", "jailbreaks", "jailbroken", "jailbreaking") for p in TOPIC_KEYWORD_PATTERNS)
    # simplest robust check: matched text is literally just the word jailbreak/jailbroken etc
    if re.fullmatch(r"(?i)jailbreak(ed|ing|s)?", matched_text):
        topic_kw += 1
        kind = "TOPIC_KEYWORD"
    else:
        genuine += 1
        kind = "GENUINE_INJECTION_SHAPED"
    print(f"  [{kind}] matched={matched_text!r}  prompt={r['prompt'][:70]!r}")

print(f"\ntopic-keyword-only blocks: {topic_kw}")
print(f"genuine injection-shaped blocks: {genuine}")
