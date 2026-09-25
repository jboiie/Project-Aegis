import sys
sys.path.insert(0, "C:/Programming/Projects/aegis")

from src.guardrails.regex_rules import RegexGuardrail
from redteam.attacks.template import TEMPLATES, HARMFUL_REQUESTS
from redteam.attacks.encoding import ENCODERS, BASE_PROMPTS

guard = RegexGuardrail()

print("=== TEMPLATES (wrapper text, rendered with a real harmful_request) ===")
for t in TEMPLATES:
    rendered = t["prompt"].format(harmful_request=HARMFUL_REQUESTS[0])
    result = guard.check(rendered)
    print(f"  {t['name']:<16} L1 matched={not result.passed}  detail={result.detail!r}")

print("\n=== ENCODING (base prompt run through each encoder) ===")
for name, encoder in ENCODERS.items():
    encoded = encoder(BASE_PROMPTS[0])
    result = guard.check(encoded)
    print(f"  {name:<12} L1 matched={not result.passed}  detail={result.detail!r}")
