"""Direct per-layer attribution for template/encoding attacks - fires the
same style of attacks the real attack scripts use, but keeps the full
safety.checks payload (which AttackResult normally discards after
extracting content) so we can see which layer actually fired, per attempt.
Each request gets its own fresh session ID (the same fix now in
template.py/encoding.py itself)."""
import asyncio
import random
import sys
import uuid

sys.path.insert(0, "C:/Programming/Projects/aegis")

import httpx

from redteam.attacks.template import TEMPLATES, HARMFUL_REQUESTS
from redteam.attacks.encoding import ENCODERS, BASE_PROMPTS
from src.config import settings

TARGET_URL = "http://localhost:8000/v1/chat/completions"


async def fire(client, content, label):
    headers = {"X-Session-ID": str(uuid.uuid4())}
    payload = {"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": content}]}
    resp = await client.post(TARGET_URL, json=payload, headers=headers)
    data = resp.json()
    safety = data.get("safety") or {}
    checks = safety.get("checks", [])
    failed = [c["name"] for c in checks if not c.get("passed", True)]
    blocked = bool(safety.get("blocked_reason"))
    print(f"  [{label}] blocked={blocked}  failed_checks={failed}  reason={safety.get('blocked_reason', '')[:80]!r}")


async def main():
    random.seed(1)
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== TEMPLATE (10 attempts, fresh session each) ===")
        for i in range(10):
            template = random.choice(TEMPLATES)
            harmful = random.choice(HARMFUL_REQUESTS)
            prompt = template["prompt"].format(harmful_request=harmful)
            await fire(client, prompt, f"template/{template['name']}")

        print("\n=== ENCODING (10 attempts, fresh session each) ===")
        for i in range(10):
            base_prompt = random.choice(BASE_PROMPTS)
            encoding_name = random.choice(list(ENCODERS.keys()))
            encoded = ENCODERS[encoding_name](base_prompt)
            await fire(client, encoded, f"encoding/{encoding_name}")


if __name__ == "__main__":
    asyncio.run(main())
