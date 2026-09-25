import os
from dotenv import load_dotenv
load_dotenv("C:/Programming/Projects/aegis/.env")
import httpx

headers = {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": "application/json"}

for model in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]:
    payload = {"model": model, "messages": [{"role": "user", "content": "What is 2+2?"}], "max_tokens": 20}
    r = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
    print(f"\n=== {model} ===")
    print("status:", r.status_code)
    for k, v in r.headers.items():
        if "ratelimit" in k.lower():
            print(f"  {k}: {v}")
    if r.status_code != 200:
        print("  body:", r.text[:300])
