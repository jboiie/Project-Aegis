"""
Red Team Runner — Orchestrates automated attacks against the Aegis proxy.

Loads attack strategies, fires them at the target endpoint, collects
results, and computes evaluation metrics.

Usage:
    python -m redteam.runner --target http://localhost:8000 --attacks pair,encoding,template
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
) -> RunReport:
    """
    Execute a red-team campaign against the target proxy.

    Args:
        target_url: The Aegis proxy endpoint.
        attack_names: List of attack strategy names to use.
        num_attempts: Number of attack attempts per strategy.

    Returns:
        RunReport with aggregated results.
    """
    report = RunReport()

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

            except Exception as e:
                report.errors += 1
                logger.error("attack_error", strategy=name, attempt=i, error=str(e))

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Red Team Runner")
    parser.add_argument("--target", default="http://localhost:8000/v1/chat/completions")
    parser.add_argument("--attacks", default="template,encoding")
    parser.add_argument("--attempts", type=int, default=50)
    args = parser.parse_args()

    attack_list = [a.strip() for a in args.attacks.split(",")]
    report = asyncio.run(run_attacks(args.target, attack_list, args.attempts))

    print("\n" + "=" * 50)
    print("RED TEAM REPORT")
    print("=" * 50)
    for key, val in report.summary().items():
        print(f"  {key}: {val}")
