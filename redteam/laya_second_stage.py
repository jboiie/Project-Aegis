"""Laya as a shadow-mode second-stage check on L1/L2 blocks.

Shadow mode: this never touches engine.py's actual blocking decision.
It re-evaluates rows that L1 or L2 already blocked and records whether
Laya would have overturned that block, purely for offline measurement.

Score definition matches laya_calibrate.py: s = max(jailbreak.noul,
prompt_injection.noul) is Laya's estimate of P(not benign); confidence
= P(benign) = 1 - sigmoid(logit(s) / temperature), using the
temperature fit on the calibration split only (data/laya_calibration.json).
"""
import json
import math
import os
from dataclasses import dataclass, field
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_PATH = os.path.join(_REPO_ROOT, "data", "laya_calibration.json")

EPS = 1e-6

_agent = None
_guard_questions = None


@dataclass
class LayaVerdict:
    confidence: float  # P(benign), calibrated
    raw_answers: dict = field(default_factory=dict)


def load_laya_agent():
    """Loads laya-typed-decisions once, module-level singleton."""
    global _agent, _guard_questions
    if _agent is None:
        import laya
        _agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions", device="cpu")
        gq_full = laya.guard_questions()
        _guard_questions = {k: gq_full[k] for k in ("jailbreak", "prompt_injection")}
    return _agent


def load_temperature(path: str = CALIBRATION_PATH) -> float:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["temperature"]


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def laya_guard_verdict(text: str, temperature: float = 1.0) -> LayaVerdict:
    agent = load_laya_agent()
    result = agent.predict({"text": text}, _guard_questions)
    jailbreak_noul = result["answers"]["jailbreak"]["noul"]
    injection_noul = result["answers"]["prompt_injection"]["noul"]
    s_raw = max(jailbreak_noul, injection_noul)
    confidence = 1.0 - _sigmoid(_logit(s_raw) / temperature)
    return LayaVerdict(confidence=confidence, raw_answers=result["answers"])


def should_overturn(verdict: LayaVerdict, threshold: float) -> bool:
    return verdict.confidence >= threshold
