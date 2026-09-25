"""Runs the Argus reference agent live (Gemini) over its real drift-sampler
question set to get REAL agent answer text for token-length analysis.
Supabase is unreachable (project hostname does not resolve - flagged
separately), so this replaces the originally-planned "pull from
session_turns" approach with a live run against the same question set
drift/sampler.py uses in production. No Supabase write, read-only use of
the reference agent.
"""
import asyncio
import json
import sys

sys.path.insert(0, r"C:/Programming/Projects/argus")

from agent.reference_agent import ask_async, load_ground_truth
from drift.sampler import UNCOVERED_QUESTIONS

OUT_PATH = r"C:/Programming/Projects/aegis/scripts/laya_bench_agent_answers.json"


def _load_done() -> list[dict]:
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _save(answers: list[dict]) -> None:
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2)


async def _ask_with_retry(q: str, attempts: int = 12) -> str:
    """Gemini free tier throws transient 503s ("high demand") under load -
    observed as a sustained multi-minute outage during this benchmark run,
    not a single blip, so this backs off longer than the SDK's own tenacity
    retry and outlasts a real outage window instead of just a rate-limit."""
    for i in range(attempts):
        try:
            return await ask_async(q)
        except Exception as exc:
            if i == attempts - 1:
                raise
            wait = min(20 * (i + 1), 120)
            print(f"    (attempt {i+1} failed: {type(exc).__name__}, retrying in {wait}s)")
            await asyncio.sleep(wait)


async def main():
    products, policies = load_ground_truth()
    answers = _load_done()
    done_questions = {a["question"] for a in answers}
    print(f"  resuming with {len(answers)} already-collected answers")

    for product in products:
        q = f"What does the {product['name']} cost?"
        if q in done_questions:
            continue
        a = await _ask_with_retry(q)
        answers.append({"question": q, "answer": a, "kind": "numeric"})
        _save(answers)
        print(f"  [numeric] {q!r} -> {len(a)} chars")

    topics = {}
    for policy in policies:
        topics.setdefault(policy["topic"], []).append(policy)
    for topic in topics:
        q = f"What is your {topic} policy?"
        if q in done_questions:
            continue
        a = await _ask_with_retry(q)
        answers.append({"question": q, "answer": a, "kind": "faithfulness"})
        _save(answers)
        print(f"  [faithfulness] {q!r} -> {len(a)} chars")

    for q, ref in UNCOVERED_QUESTIONS:
        if q in done_questions:
            continue
        a = await _ask_with_retry(q)
        answers.append({"question": q, "answer": a, "kind": "self_consistency", "ref": ref})
        _save(answers)
        print(f"  [uncovered] {q!r} -> {len(a)} chars")

    print(f"\nWrote {len(answers)} real agent answers.")


if __name__ == "__main__":
    asyncio.run(main())
