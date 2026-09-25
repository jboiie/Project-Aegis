import os
from dotenv import load_dotenv
load_dotenv("C:/Programming/Projects/aegis/.env")
import httpx
r = httpx.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
print(r.status_code)
for m in r.json().get("data", []):
    print(m["id"])
