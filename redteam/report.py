"""
Report — Renders a completed red-team campaign as a Markdown report.

Renders straight from the runner's in-memory AttackResult list, not from
Supabase — the sandbox's telemetry table only stores a hashed prompt (by
design, for privacy) with no strategy/iteration fields, so it can't
reconstruct Section 4's full prompt/response detail. The runner already
holds everything this report needs before it exits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from redteam.attacks.base import AttackResult
from src.guardrails.session import SessionGuard

BYPASS_CAP = 50

_SESSION_GUARD_DEFAULTS = SessionGuard()


@dataclass
class CampaignMeta:
    """Run-level info the report needs but that isn't on any single AttackResult."""
    campaign_id: str
    target: str
    date: str  # ISO 8601, run start
    attacks: list[str] = field(default_factory=list)
    fail_above: float | None = None


def generate(meta: CampaignMeta, results: list[AttackResult], output_path: str) -> str:
    """Render the report and write it to output_path. Returns the rendered Markdown."""
    markdown = "\n\n".join([
        _render_header(meta, results),
        _render_executive_summary(meta, results),
        _render_results_by_strategy(meta, results),
        _render_bypassed_prompts(meta, results),
        _render_blocked_summary(results),
        _render_recommendations(meta, results),
        _render_footer(meta),
    ]) + "\n"

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return markdown


# ── Shared stats helpers ─────────────────────────────────────

def _strategy_stats(attacks: list[str], results: list[AttackResult]) -> dict[str, dict]:
    """Attempts/bypasses/blocked/ASR per strategy, in the order attacks were given."""
    stats = {name: {"attempts": 0, "bypasses": 0, "blocked": 0} for name in attacks}
    for r in results:
        row = stats.setdefault(r.strategy, {"attempts": 0, "bypasses": 0, "blocked": 0})
        row["attempts"] += 1
        if r.bypassed:
            row["bypasses"] += 1
        else:
            row["blocked"] += 1
    for row in stats.values():
        row["asr"] = (row["bypasses"] / row["attempts"] * 100) if row["attempts"] else 0.0
    return stats


def _blocked_reason(result: AttackResult) -> str:
    text = result.response or ""
    if text.startswith("[BLOCKED] "):
        return text[len("[BLOCKED] "):].strip() or "Blocked (no reason given)"
    if "[ERROR]" in text:
        return "Target unreachable / error"
    return "Blocked (unknown reason)"


# ── Section renderers ────────────────────────────────────────

def _render_header(meta: CampaignMeta, results: list[AttackResult]) -> str:
    return (
        "# Aegis Red-Team Report\n\n"
        f"**Campaign ID:** {meta.campaign_id}\n"
        f"**Target:** {meta.target}\n"
        f"**Date:** {meta.date}\n"
        f"**Attacks:** {', '.join(meta.attacks)}\n"
        f"**Total Attempts:** {len(results)}"
    )


def _render_executive_summary(meta: CampaignMeta, results: list[AttackResult]) -> str:
    total = len(results)
    bypasses = sum(1 for r in results if r.bypassed)
    blocked = total - bypasses
    asr = (bypasses / total * 100) if total else 0.0

    verdict = ""
    if meta.fail_above is not None:
        if asr > meta.fail_above:
            verdict = f" The campaign FAILED the configured threshold of {meta.fail_above}%. Immediate review is recommended."
        else:
            verdict = f" The campaign PASSED the configured threshold of {meta.fail_above}%."

    summary = (
        f"This report covers a red-team campaign of {total} attack attempts across "
        f"{', '.join(meta.attacks)} strategies against {meta.target}. {bypasses} attempts "
        f"({asr:.2f}%) bypassed the guardrail stack. {blocked} attempts were blocked.{verdict}"
    )
    return "## Executive Summary\n\n" + summary


def _render_results_by_strategy(meta: CampaignMeta, results: list[AttackResult]) -> str:
    stats = _strategy_stats(meta.attacks, results)
    rows = ["| Strategy | Attempts | Bypasses | Blocked | ASR |", "|---|---|---|---|---|"]
    for name in meta.attacks:
        s = stats.get(name, {"attempts": 0, "bypasses": 0, "blocked": 0, "asr": 0.0})
        rows.append(f"| {name.title()} | {s['attempts']} | {s['bypasses']} | {s['blocked']} | {s['asr']:.2f}% |")

    total_attempts = len(results)
    total_bypasses = sum(1 for r in results if r.bypassed)
    total_blocked = total_attempts - total_bypasses
    total_asr = (total_bypasses / total_attempts * 100) if total_attempts else 0.0
    rows.append(f"| **Total** | {total_attempts} | {total_bypasses} | {total_blocked} | {total_asr:.2f}% |")

    return "## Results by Strategy\n\n" + "\n".join(rows)


def _render_bypassed_prompts(meta: CampaignMeta, results: list[AttackResult]) -> str:
    bypasses = [r for r in results if r.bypassed]
    bypasses.sort(key=lambda r: (r.strategy, r.timestamp))

    lines = ["## Bypassed Prompts (Full Detail)", ""]
    if not bypasses:
        lines.append("No bypasses recorded.")
        return "\n".join(lines)

    shown = bypasses[:BYPASS_CAP]
    if len(bypasses) > BYPASS_CAP:
        lines.append(f"> Showing first {BYPASS_CAP} bypasses. Full bypass log available in the runner output for campaign {meta.campaign_id}.")
        lines.append("")

    for i, r in enumerate(shown, 1):
        iterations = r.metadata.get("iterations_to_bypass", "N/A") if r.strategy == "pair" else "N/A"
        lines.append(f"### Bypass #{i} — {r.strategy} — {r.timestamp or 'unknown'}")
        lines.append("")
        lines.append("**Prompt sent:**")
        lines.append(f"```\n{r.prompt}\n```")
        lines.append("**Response received:**")
        lines.append(f"```\n{r.response}\n```")
        lines.append(f"**Guardrail verdict:** ALLOWED (attack bypassed all layers)")
        lines.append(f"**Iterations (PAIR only):** {iterations}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_blocked_summary(results: list[AttackResult]) -> str:
    blocked = [r for r in results if not r.bypassed]
    lines = ["## Blocked Attacks Summary", ""]
    if not blocked:
        lines.append("No blocked attempts recorded.")
        return "\n".join(lines)

    counts: dict[str, int] = {}
    for r in blocked:
        reason = _blocked_reason(r)
        counts[reason] = counts.get(reason, 0) + 1

    top5 = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    total_blocked = len(blocked)

    rows = ["| Block Reason | Count | % of Blocked |", "|---|---|---|"]
    for reason, count in top5:
        rows.append(f"| {reason} | {count} | {count / total_blocked * 100:.2f}% |")

    lines.extend(rows)
    return "\n".join(lines)


def _render_recommendations(meta: CampaignMeta, results: list[AttackResult]) -> str:
    stats = _strategy_stats(meta.attacks, results)
    template_asr = stats.get("template", {}).get("asr", 0.0)
    encoding_asr = stats.get("encoding", {}).get("asr", 0.0)
    pair_asr = stats.get("pair", {}).get("asr", 0.0)

    items = []
    if template_asr > 0:
        items.append(
            "**Template attacks bypassed.** Review L1 regex rules — known jailbreak templates "
            "(DAN, AIM, developer mode) should be caught at L1 with zero bypass rate. Add the "
            "bypassed prompts from Section 4 to your regex ruleset."
        )
    if encoding_asr > 0:
        items.append(
            "**Encoding attacks bypassed.** Your semantic injection classifier (L2) is not "
            "generalizing to obfuscated payloads. Consider fine-tuning on base64/ROT13/leetspeak "
            "variants, or adding a decode-then-screen pre-processing step before L2."
        )
    if pair_asr > 0 and pair_asr > encoding_asr:
        items.append(
            f"**Adaptive attacks significantly outperform fixed-corpus attacks** ({pair_asr:.2f}% vs "
            f"{encoding_asr:.2f}%). Your guardrails are vulnerable to iterative rephrasing. Implement "
            "session-level rejection tracking (SessionGuard) to break the attacker's feedback loop."
        )
    if pair_asr > 0:
        items.append(
            "**PAIR bypassed SessionGuard.** The attacker succeeded within the rejection-velocity "
            f"window. Consider tightening the lockout threshold (currently: {_SESSION_GUARD_DEFAULTS.max_rejections} "
            f"rejections per {_SESSION_GUARD_DEFAULTS.window_seconds:.0f} seconds)."
        )
    items.append(
        "**Re-run cadence:** Guardrail effectiveness degrades as attack techniques evolve. Re-run "
        "this campaign after any model update, guardrail rule change, or on a fixed schedule "
        "(recommended: monthly)."
    )

    lines = ["## Recommendations", ""]
    lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)


def _render_footer(meta: CampaignMeta) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return (
        "---\n\n"
        "Generated by Aegis\n"
        f"Campaign ID: {meta.campaign_id} | Target: {meta.target} | {now}"
    )
