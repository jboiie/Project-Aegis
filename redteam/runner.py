"""
Red Team Runner — Primary Entrypoint of Project Aegis

This is the core of the project. The Aegis Sandbox (src/) exists so that this
runner has a real, instrumented system to attack and measure.

The runner orchestrates automated attack campaigns against any OpenAI-compatible
endpoint. It loads attack strategies, fires them asynchronously at the target,
collects raw HTTP responses, classifies each response as a bypass or a block,
and computes evaluation metrics (ASR, precision, recall, F1).

Usage:
    python -m redteam.runner --target http://localhost:8000/v1/chat/completions \\
        --attacks template,encoding,pair --attempts 100

See redteam/README.md for full pipeline documentation: attack strategies, metric
definitions, feedback loop design, and Phase A/B/C experiment roadmap.
"""

import asyncio
import argparse
import time
from dataclasses import dataclass, field

import httpx
import structlog

from redteam.attacks.base import BaseAttack, AttackResult
from redteam.attacks.pair import PAIRAttack
from redteam.attacks.encoding import EncodingAttack
from redteam.attacks.template import TemplateAttack

logger = structlog.get_logger()


@dataclass
class RunReport:
    """Summary of a red-team run."""
    total_attacks: int = 0
    successful_bypasses: int = 0
    blocked: int = 0
    errors: int = 0
    results: list[AttackResult] = field(default_factory=list)

    @property
    def attack_success_rate(self) -> float:
        """ASR — the key metric. Lower is better (for the defender)."""
        if self.total_attacks == 0:
            return 0.0
        return self.successful_bypasses / self.total_attacks

    def summary(self) -> dict:
        return {
            "total_attacks": self.total_attacks,
            "successful_bypasses": self.successful_bypasses,
            "blocked": self.blocked,
            "errors": self.errors,
            "attack_success_rate": f"{self.attack_success_rate:.2%}",
        }


# ── Attack registry ──────────────────────────────────────────
ATTACK_REGISTRY: dict[str, type[BaseAttack]] = {
    "pair": PAIRAttack,
    "encoding": EncodingAttack,
    "template": TemplateAttack,
}


async def run_attacks(
    target_url: str,
    attack_names: list[str],
    num_attempts: int = 50,
    seed: int | None = None,
    delay: float = 0.3,
) -> RunReport:
    """
    Execute a red-team campaign against the target proxy.

    Args:
        target_url: The Aegis proxy endpoint.
        attack_names: List of attack strategy names to use.
        num_attempts: Number of attack attempts per strategy.
        seed: Random seed — fixes the prompt corpus so configs are comparable.
        delay: Seconds to wait between requests (avoids Groq rate limits).

    Returns:
        RunReport with aggregated results.
    """
    report = RunReport()

    if seed is not None:
        import random
        random.seed(seed)
        logger.info("random_seed_set", seed=seed)

    for name in attack_names:
        attack_cls = ATTACK_REGISTRY.get(name)
        if not attack_cls:
            logger.warning("unknown_attack", name=name)
            continue

        attack = attack_cls()
        logger.info("starting_attack", strategy=name, attempts=num_attempts)

        for i in range(num_attempts):
            try:
                result = await attack.execute(target_url)
                report.total_attacks += 1
                report.results.append(result)

                if result.bypassed:
                    report.successful_bypasses += 1
                else:
                    report.blocked += 1

                await asyncio.sleep(delay)  # avoid Groq rate limits

            except Exception as e:
                report.errors += 1
                logger.error("attack_error", strategy=name, attempt=i, error=str(e))

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Red Team Runner")
    parser.add_argument("--target", default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--attacks", default="template,encoding")
    parser.add_argument("--attempts", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible attack corpus (default: 42)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between requests to avoid rate limits (default: 2.0)")
    args = parser.parse_args()

    attack_list = [a.strip() for a in args.attacks.split(",")]
    report = asyncio.run(run_attacks(args.target, attack_list, args.attempts,
                                     seed=args.seed, delay=args.delay))

    print("\n" + "=" * 50)
    print("RED TEAM REPORT")
    print("=" * 50)
    for key, val in report.summary().items():
        print(f"  {key}: {val}")
