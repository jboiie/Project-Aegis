<div align="center">

# 🔴 Project Aegis

### Autonomous LLM Vulnerability Evaluation Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![Tests](https://github.com/jboiie/Project-Aegis/actions/workflows/tests.yml/badge.svg)](https://github.com/jboiie/Project-Aegis/actions/workflows/tests.yml)
[![Docker Verify](https://github.com/jboiie/Project-Aegis/actions/workflows/docker-verify.yml/badge.svg)](https://github.com/jboiie/Project-Aegis/actions/workflows/docker-verify.yml)

*Autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target.*

[Findings](#-findings) · [Pipeline](#-red-teaming-pipeline) · [Architecture](#-architecture) · [Attack Strategies](#-attack-strategies) · [The Sandbox](#-the-target-sandbox) · [Point At Your Own Endpoint](#-point-at-your-own-endpoint) · [Deploy](DEPLOY.md) · [Roadmap](#-roadmap)

</div>

---

> **PAIR (adaptive LLM attacker) achieved a 95% bypass rate against our full guardrail stack — in an average of 2 iterations per goal.** Static ML classifiers that cut a fixed-corpus attack rate from 87% to 25% are nearly useless against an attacker that receives rejection feedback and rephrases. That gap is the core finding. Adding session-level rejection tracking (breaking the feedback loop PAIR depends on) cut that back down to 20% — see [Table 4](#-findings). Everything else in this repo is measuring where and why it happens.

---

## 📌 The Problem

Security teams have no standardized way to continuously measure LLM vulnerability. Static guardrails are written once and never challenged. Project Aegis is the challenge.

LLM guardrails deployed in production are evaluated once at release — then left static while attack techniques evolve. There is no continuous measurement of how guardrail effectiveness degrades over time, no automated pipeline for discovering novel bypasses, and no standard for reporting attack success rates against real defense stacks.

**Project Aegis** is the evaluation pipeline that fills that gap:

1. **The Red-Teaming Pipeline** — An autonomous attack engine that generates, fires, and measures jailbreak attacks across multiple strategies (template, encoding, PAIR), producing real ASR metrics
2. **The Aegis Sandbox** — A live FastAPI proxy with a layered guardrail stack (SessionGuard → SemanticCache → regex → DeBERTa → toxicity → PII → OutputGuard), deployed as a *controlled target environment* for the pipeline to attack and measure

The sandbox has known coverage gaps — the same gaps present in real production guardrail stacks. Its job is to give the pipeline something real to attack and measure.

---

## 📊 Findings

### Table 1 — ASR by Cumulative Guardrail Layer (Phase A)

*Attack set: template + encoding attacks, n=100 total (50 per strategy), seed=42, 0 errors.*

| Guardrail Configuration | Total Attacks | Bypasses | Blocked | ASR ↓ | Δ vs prev |
|---|---|---|---|---|---|
| No guardrails (baseline) | — | — | — | ~100% | — |
| L1 only (Regex) | 100 | 87 | 13 | **87.00%** | — |
| L1 + L2 (+ DeBERTa injection) | 100 | 25 | 75 | **25.00%** | ↓ 62pp |
| L1 + L2 + L3 (+ ToxicBERT) | 100 | 25 | 75 | **25.00%** | 0pp |
| Full stack (L1–L4 + PII) | 100 | 25 | 75 | **25.00%** | 0pp |

### Table 2 — Aegis vs. External Baseline (Phase B)

*Same attack corpus (seed=42, n=100) fired at Aegis full stack and Llama Prompt Guard 2 (86M) via Groq.*

| Target | Template ASR | Encoding ASR | Overall ASR | n |
|---|---|---|---|---|
| **Aegis full stack** | ~0% | ~50% | **25.00%** | 100 |
| **Llama Prompt Guard 2 (86M)** | 0% | 100% | **50.00%** | 100 |
| **Delta (Aegis − Llama Guard)** | ±0% | −50pp | **−25pp** | — |

> Positive delta = Llama Guard stronger. Negative delta = Aegis stronger.
> Both systems block 100% of template attacks. The gap is entirely on encoding-obfuscated attacks.

### Table 3 — PAIR vs. Template/Encoding (Phase C)

*Adaptive attack (PAIR with llama-3.1-8b-instant attacker, max_iterations=5) compared to fixed-corpus attacks against full Aegis stack.*

| Strategy | Attacks Fired | Bypasses | ASR ↓ | Avg. Iterations to Bypass |
|---|---|---|---|---|
| Template (Fixed) | 50 | 0 | **0.00%** | N/A |
| Encoding (Fixed) | 50 | 25 | **50.00%** | N/A |
| **PAIR (Adaptive)** | 20 | 19 | **95.00%** | **2.00** |

### Table 4 — PAIR vs. Aegis + Countermeasures (Phase D)

*Same PAIR setup as Table 3 (seed=42, 20 goals, max_iterations=5), rerun against the full stack plus three countermeasures: SessionGuard (session lockout after 3 rejections/5min), OutputGuard (dual-pass output screening), SemanticCache (L0 embedding-similarity block on known-blocked prompts).*

| Configuration | Attacks Fired | Bypasses | ASR ↓ | Avg. Iterations to Bypass |
|---|---|---|---|---|
| Full stack, no countermeasures | 20 | 19 | **95.00%** | 2.00 |
| **Full stack + SessionGuard + OutputGuard + SemanticCache** | 20 | 4 | **20.00%** | 2.25 |

> SemanticCache recorded 0 blocks in this run — PAIR's rephrasing is novel enough each turn that L0 rarely gets a near-duplicate match before SessionGuard's rejection-velocity lockout already ends the session. SessionGuard is doing essentially all of the work here.
>
> **Note on measurement integrity:** the first rerun of this experiment showed the same 20.00% ASR, but for the wrong reason — a schema bug in SessionGuard's lockout path (`GuardrailCheck` built with fields that don't match the model) caused every lockout to crash with a 500 instead of returning a clean block, and PAIR's error handler misclassified those crashes as "blocked." Fixed in `src/guardrails/engine.py`; the number above is from the post-fix run with zero server errors. A regression test (`tests/test_countermeasures.py::test_engine_returns_verdict_on_session_lockout`) now covers this path.

### Key Takeaways

- **Phase A ✅**: L2 (DeBERTa injection classifier) provides the entire measurable defence, dropping ASR from 87% (regex-only) to 25% (a 62 percentage-point reduction). L3 (ToxicBERT) and L4 (PII redaction) add zero marginal protection against the injection/encoding attack corpus used here — they target hate speech and PII respectively, not prompt injection. The 25% residual ASR consists entirely of encoding-obfuscated attacks that bypass all text-based classifiers.
- **Phase B ✅**: Aegis full stack (25% ASR) outperforms Llama Prompt Guard 2 86M (50% ASR) by 25 percentage points on the same attack corpus. Both systems achieve 0% ASR on template attacks. The entire gap comes from encoding attacks: Llama Guard outputs a near-zero probability score on base64/ROT13/leetspeak payloads (it cannot decode them to evaluate intent), while Aegis’s DeBERTa classifier catches ~50% of encoding attacks, likely because it was fine-tuned on datasets that include the obfuscation framing pattern itself.
- **Phase C ✅**: Adaptive attacks (PAIR) achieve a **95.00% ASR** against the full Aegis stack, requiring an average of only **2.00 iterations** to bypass all guardrail layers. While static ML classifiers (DeBERTa) effectively neutralize fixed templates (0% ASR) and reduce fixed encodings (50% ASR), an attacker LLM dynamically refines prompt framing to exploit classifier feature blind spots. This proves that static input guardrails cannot defend against LLM-driven adaptive red-teaming without stateful session tracking and real-time feedback mitigations.
- **Phase D ✅**: Adding SessionGuard + OutputGuard + SemanticCache cuts PAIR's ASR from 95.00% to **20.00%** (75pp reduction), landing back in the same range as the fixed-corpus full-stack ASR (25%). Session-level rejection tracking — not per-prompt classification — is what neutralizes an iterative attacker: PAIR's entire strategy depends on a sustained feedback loop with one session, and breaking that loop matters more than catching any individual rephrase.

### Qualitative Findings (Prior Work)

> These findings are empirical results from pair-lab and prompt-autopsy experiments — predecessor projects to Aegis. They directly motivate the sandbox's layer design and the pipeline's attack strategy selection. Full writeup: [docs/prior_work.md](docs/prior_work.md).

**The overarching finding: alignment in open-weight models is surface-level pattern matching, not deep intent understanding. Parameter count is irrelevant to safety — a 70B model fails as fast as an 8B model when framing bypasses its training patterns.**

| Attack Vector | Tactic | Empirical Result |
|---|---|---|
| **Role-play & Authority** | Academic researcher / teacher framing mixed with sensitive requests | Highly effective. Known personas (DAN) get blocked; professional authority claims with sensitive topics bypass rapidly |
| **Educational Bypass** | "For educational purposes only" framing | Shifts model into "helpful teacher" mode. Generated working, commented keylogger code in tests |
| **Inline Injection** | Injecting `###SYSTEM`, `[INST]` structural tokens into user prompt | Models process injected structure and make judgment calls based on it. Filters are behavioral, not structural |
| **Prompt Exfiltration** | Asking the model to output its internal instructions | Model either leaks actual system prompt or hallucinates a plausible one — both are failures |
| **Obfuscation (Base64/Leetspeak)** | Encoding malicious payload before sending | Unpredictable: model may decode and comply, decode and hallucinate, or refuse. L2/L3 classifiers trained on plaintext may not generalize |

**What this means for the sandbox design:** L1 regex catches known templates but misses authority framing. L2 DeBERTa injection detection must score *combinations* (authority claim + sensitive topic) rather than isolated keywords. The output scanner is necessary because prompt exfiltration attacks succeed at the response stage, not the input stage — implemented as OutputGuard (`src/guardrails/output.py`) in Phase D.

---

## 🏗️ Architecture

The pipeline is the primary system. The sandbox is what it attacks.

```
╔══════════════════════════════════════════════════════════════════╗
║               RED-TEAM PIPELINE (Primary System)                 ║
║                                                                  ║
║   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐   ║
║   │ Attack       │──▶│ Runner       │──▶│ Evaluation        │   ║
║   │ Generation   │   │ (Async HTTP) │   │ Engine            │   ║
║   │              │   │              │   │                   │   ║
║   │ • Template   │   │ Fires N      │   │ • ASR             │   ║
║   │ • Encoding   │   │ attacks at   │   │ • Precision       │   ║
║   │ • PAIR       │   │ target URL   │   │ • Recall / F1     │   ║
║   └──────────────┘   └──────┬───────┘   │ • Per-layer       │   ║
║                             │           └───────────────────┘   ║
║                             │ attacks                           ║
╚═════════════════════════════╪════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║              AEGIS SANDBOX (Attack Target)                       ║
║                                                                  ║
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │  POST /v1/chat/completions (OpenAI-compatible endpoint)    │  ║
║  │  optional: Authorization: Bearer <AEGIS_API_KEY>            │  ║
║  └────────────────────┬───────────────────────────────────────┘  ║
║                       │                                          ║
║  ┌────────────────────▼───────────────────────────────────────┐  ║
║  │  SessionGuard — rejection-velocity lockout                 │  ║
║  │  (breaks PAIR's adaptive feedback loop)                    │  ║
║  └────────────────────┬───────────────────────────────────────┘  ║
║                       │                                          ║
║  ┌────────────────────▼───────────────────────────────────────┐  ║
║  │  Semantic Cache (Redis + MiniLM — < 5ms block)            │  ║
║  └────────────────────┬───────────────────────────────────────┘  ║
║                       │                                          ║
║  ┌────────────────────▼───────────────────────────────────────┐  ║
║  │  Guardrail Stack (Live Attack Surface)                     │  ║
║  │  L1: Regex pre-filter    (< 1ms)                          │  ║
║  │  L2: DeBERTa injection   (~10ms)                          │  ║
║  │  L3: Toxicity classifier (~10ms)                          │  ║
║  │  L4: PII redaction       (~5ms)                           │  ║
║  └────────────────────┬───────────────────────────────────────┘  ║
║                       │                                          ║
║           Blocked ◀───┴───▶ Forwarded to Groq LLM               ║
║                                     │                             ║
║                       ┌─────────────▼──────────────┐             ║
║                       │  OutputGuard — dual-pass     │             ║
║                       │  response screening          │             ║
║                       └─────────────┬──────────────┘             ║
╚═════════════════════════════════════╪══════════════════════════════╝
                                      │
                                      ▼
              ┌───────────────────────────────┐
              │  Supabase (PostgreSQL)         │
              │  Attack logs, verdicts, ASR   │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Streamlit Dashboard           │
              │  Real-time metrics, attack log │
              └───────────────┬───────────────┘
```

### Design Decisions

| Decision | Rationale |
|---|---|
| **Pipeline-first architecture** | The red-team runner is the primary entrypoint. The sandbox is a dependency, not the product |
| **Layered guardrails as attack surface** | Sequential L1→L4 layers create measurable per-layer bypass rates — the pipeline reports which layer failed |
| **OpenAI-compatible sandbox API** | Any attack targeting an OpenAI-compatible endpoint can be redirected to the sandbox by changing one URL |
| **FastAPI sandbox** (not Rust) | Rapid iteration on the target. The sandbox needs to be easy to modify, not fast to serve |
| **Supabase for telemetry** | Free-tier PostgreSQL. Every attack attempt, verdict, and bypass is logged for post-hoc analysis |

---

## 🔴 Red-Teaming Pipeline

The pipeline is the core of this project. It implements automated attack strategies from the academic literature and measures guardrail effectiveness with real metrics.

### Running the Pipeline

```bash
# Install dependencies
pip install -e ".[redteam]"

# Fire a red-team campaign against the sandbox
python -m redteam.runner \
  --target http://localhost:8000/v1/chat/completions \
  --attacks template,encoding \
  --attempts 100

# Output:
# ==================================================
# RED TEAM REPORT
# ==================================================
#   total_attacks: 100
#   successful_bypasses: 25
#   blocked: 75
#   errors: 0
#   attack_success_rate: 25.00%
```

### Feedback Loop

```
Attack Generation → Execution → Measurement → Analysis → Refined Attacks
        ↑                                                        │
        └────────────────────────────────────────────────────────┘
```

Bypasses discovered in one campaign inform the next. The pipeline logs every successful bypass with the exact prompt, the attack strategy, and the guardrail layer that failed. This log is the seed corpus for PAIR refinement in Phase C.

---

## ⚔️ Attack Strategies

| Strategy | Technique | Complexity | Status | Reference |
|---|---|---|---|---|
| **Template** | Known jailbreaks (DAN, AIM, role-play, hypothetical framing) | Low | ✅ Implemented | [JailbreakChat](https://jailbreakchat.com) |
| **Encoding** | Base64, ROT13, leetspeak, word-split, Unicode homoglyph obfuscation | Low | ✅ Implemented | [Wei et al. 2023](https://arxiv.org/abs/2307.15043) |
| **PAIR** | LLM-vs-LLM iterative refinement — attacker LLM rephrases until target breaks | Medium | ✅ Implemented | [Chao et al. 2023](https://arxiv.org/abs/2310.08419) |

**Template attacks** inject known jailbreak templates (DAN, AIM, developer mode, etc.) into the sandbox. These test whether L1 regex rules are comprehensive and whether L2/L3 catch paraphrased variants.

**Encoding attacks** obfuscate malicious payloads using Base64, ROT13, leetspeak, character splitting, and Unicode homoglyph substitution. These test whether ML classifiers handle semantically equivalent inputs that bypass literal pattern matching.

**PAIR** (Prompt Automatic Iterative Refinement) uses a separate attacker LLM (Groq Llama 3, free tier) to iteratively rephrase a harmful request until the target sandbox responds. Each failed attempt informs the next rephrase. This tests adaptive resilience — can the guardrails hold against an LLM specifically targeting their failure modes?

### Known Limitations

**GCG (Greedy Coordinate Gradient) is not implemented and is not planned for this iteration.** GCG requires white-box access to model logits and gradients, which is fundamentally incompatible with API-based targets like Groq. This is itself a relevant finding: black-box pipelines are limited to query-based attack strategies (template, encoding, PAIR). Gradient-based methods require local model weights and are therefore out of scope for any evaluation pipeline targeting production API endpoints.

---

## 📈 Telemetry Dashboard

A Streamlit dashboard reads live telemetry from Supabase (`aegis_events`, logged by every sandbox request via `src/telemetry/supabase_client.py`):

- **Metric cards**: total requests, blocked count, block rate, avg latency
- **Requests over time**: hourly-bucketed total vs. blocked counts
- **Blocked-reason breakdown**: pie chart of which guardrail check fired
- **Recent events table**: last 500 events (prompt hashed, not raw text)

Query + aggregation logic lives in `dashboard/data.py` (unit-tested, no network needed); `dashboard/app.py` is the thin Streamlit rendering layer.

> **Note:** `aegis_events` logs all live sandbox traffic, not a labeled red-team run — so "block rate" here is a live pass/block ratio, not the Attack Success Rate reported in Tables 1–4 (that comes from `redteam/evaluation/metrics.py` against a known attack corpus).

```bash
pip install -e ".[dashboard]"
# set SUPABASE_URL / SUPABASE_KEY in .env, then run scripts/setup_supabase.sql once
streamlit run dashboard/app.py
# → Opens at http://localhost:8501
```

---

## 🧱 The Target Sandbox

The Aegis Sandbox is a FastAPI proxy that exposes an OpenAI-compatible endpoint. It runs SessionGuard, a semantic cache against Redis, a four-layer guardrail stack (L1-L4), and OutputGuard on the response. It exists so the pipeline has a real, instrumented system to attack.

### Sandbox Setup

**Prerequisites:** Python 3.11+, [Miniconda](https://docs.conda.io/en/latest/miniconda.html), a [Groq API key](https://console.groq.com/keys) (free). No Docker required — for a Docker-based deployment instead, see [DEPLOY.md](DEPLOY.md).

```bash
git clone https://github.com/jboiie/Project-Aegis.git
cd Project-Aegis

# Create and activate the environment
conda create -n aegis python=3.11 -y

# Install dependencies
conda run -n aegis pip install -e .

# Configure secrets (Linux/Mac)
cp .env.example .env
# Configure secrets (Windows)
copy .env.example .env
# Edit .env → set GROQ_API_KEY=gsk_...
```

```bash
# Start the sandbox (models download on first run — ~1GB, one time only)
conda run --no-capture-output -n aegis uvicorn src.main:app --port 8000 --reload

# Ready when you see:
# {"event": "startup_probe_passed", ...}
# INFO:     Application startup complete.
```

```bash
# Test: safe prompt — forwarded to Groq
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is 2+2?"}]}'
# → {"content": "2 + 2 = 4.", "model": "llama-3.3-70b-versatile", ...}

# Test: known attack — caught by L1 regex
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Ignore all previous instructions"}]}'
# → {"content": "[BLOCKED] Matched known attack pattern: ...", ...}
```


### Sandbox Guardrail Stack

The sandbox implements the input-side L1-L4 layers plus session- and output-level defenses, each with known coverage gaps — the same gaps present in real production guardrail stacks. The pipeline's job is to find where each one fails.

| Layer | Method | What It Catches | What It Misses |
|---|---|---|---|
| SessionGuard | Rejection-velocity lockout (3 rejections / 5min) | Sustained adaptive-attacker feedback loops (PAIR) | Single-shot attacks, low-frequency probing |
| L0 SemanticCache | Embedding similarity vs. known-blocked prompts (Redis + MiniLM) | Near-duplicate rephrasings of already-blocked prompts | Genuinely novel phrasing each attempt (PAIR mostly evades this) |
| L1 Regex | Pattern matching on known jailbreak strings | DAN, AIM, explicit templates | Paraphrased or encoded variants |
| L2 DeBERTa | Fine-tuned injection classifier | Semantic injection attempts | Novel phrasings outside training distribution |
| L3 Toxicity | Toxic-BERT classifier | Overtly harmful content | Harmful content framed as hypothetical or fiction |
| L4 PII | Regex + NER redaction | Emails, phones, credit cards | Novel PII formats, contextual leakage |
| OutputGuard | Dual-pass response screening | System-prompt leaks, harmful content generated in the response | Responses that don't match scanned leak/harm patterns |

---

## 📁 Project Structure

```
project-aegis/
│
├── redteam/                    ← CORE PIPELINE — primary entrypoint
│   ├── runner.py               # Main CLI: generates and fires attacks, reports ASR
│   ├── phase_b.py              # Phase B: external baseline comparison (Llama Guard)
│   ├── phase_c.py              # Phase C: PAIR campaign runner
│   ├── attacks/
│   │   ├── base.py             # Abstract attack interface
│   │   ├── template.py         # Template attacks (DAN, AIM, role-play)
│   │   ├── encoding.py         # Encoding: Base64, ROT13, leetspeak, homoglyph
│   │   └── pair.py             # PAIR: LLM-vs-LLM iterative refinement
│   ├── evaluation/
│   │   ├── metrics.py          # ASR, precision, recall, F1 computation
│   │   └── run_eval.py         # Labeled-set CLI runner (real precision/recall/F1)
│   └── README.md               # Pipeline internals: strategies, metrics, feedback loop
│
├── src/                        ← SANDBOX TARGET — the system the pipeline attacks
│   ├── main.py                 # FastAPI app factory (sandbox entry point)
│   ├── config.py               # Centralized settings
│   ├── gateway/                # Sandbox proxy layer
│   │   ├── router.py           # OpenAI-compatible /v1/chat/completions
│   │   ├── proxy.py            # Forward to Groq (after guardrails pass)
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── middleware.py       # Request timing & logging
│   │   └── auth.py             # Optional AEGIS_API_KEY shared-key auth
│   ├── guardrails/             # Attack surface — defense stack
│   │   ├── engine.py           # Orchestrates SessionGuard → L1→L4 → OutputGuard
│   │   ├── regex_rules.py      # L1: Fast pattern matching (< 1ms)
│   │   ├── injection.py        # L2: DeBERTa classifier (~10ms)
│   │   ├── toxicity.py         # L3: Toxicity detection (~10ms)
│   │   ├── pii.py              # L4: PII regex + redaction
│   │   ├── session.py          # SessionGuard: rejection-velocity lockout
│   │   └── output.py           # OutputGuard: dual-pass response screening
│   ├── cache/                  # Semantic caching layer
│   │   ├── redis_client.py     # Async Redis connection
│   │   └── semantic.py         # MiniLM embedding cache (L0)
│   ├── llm/                    # LLM provider (sandbox's backend)
│   │   ├── base.py             # Abstract provider interface
│   │   └── groq.py             # Groq API client
│   ├── telemetry/              # Attack logging
│   │   ├── logger.py           # Structured JSON logging
│   │   └── supabase_client.py  # Telemetry shipping to Supabase
│   └── utils/
│       └── embeddings.py       # MiniLM embedding model
│
├── dashboard/                  # Streamlit: visualizes live sandbox telemetry
│   ├── app.py                  # Streamlit rendering layer
│   └── data.py                 # Supabase query + pandas aggregation (unit-tested)
│
├── tests/                      # Pytest test suite (48 tests)
├── scripts/
│   ├── setup_supabase.sql              # Database schema for attack log
│   └── generate_labeled_eval_set.py    # Builds data/labeled_eval_set.jsonl (seed=42)
├── data/
│   └── labeled_eval_set.jsonl  # 25 attack + 25 benign prompts, ground-truth labeled
├── models/                     # Local model weights (gitignored)
├── docs/
│   ├── prd.md                  # North-star vision (production-grade pipeline)
│   ├── resource.md             # Historical build plan (resource-constrained) — phases complete
│   ├── technical_report.md     # Full write-up: methodology, findings, empirical validation
│   ├── prior_work.md           # Predecessor project findings that motivated the sandbox design
│   └── understanding_aegis.md  # Plain-English explainer: motivation, methodology, critiques, full build history
├── .github/workflows/
│   ├── tests.yml                # Runs the pytest suite on push/PR
│   └── docker-verify.yml        # Builds + smoke-tests the Docker container on push/PR
│
├── docker-compose.yml          # Sandbox stack: FastAPI + Redis
├── Dockerfile                  # Container image for the sandbox
├── DEPLOY.md                   # Docker deployment guide: quick start, auth, config
├── pyproject.toml              # Python project config & dependencies
└── .env.example                # Environment variable template
```

---

## 💰 Cost & Compute

Designed to run on a student budget.

| Resource | Purpose | Cost |
|---|---|---|
| Laptop (8GB+ RAM) | Pipeline runner, sandbox, Redis, DeBERTa on CPU | ₹0 |
| Groq API (free tier) | Sandbox backend LLM + PAIR attacker LLM (Llama 3) | ₹0 |
| Supabase (free tier) | Attack log database | ₹0 |
| Streamlit Cloud (free) | Dashboard hosting | ₹0 |
| OpenRouter credits | External baseline LLM (Llama Guard, Phase B) — optional | ~₹850 |
| **Total** | | **₹0 – ₹850** (~$0–$10) |

---

## 🎯 Point at Your Own Endpoint

The pipeline is not just for the Aegis sandbox. Any OpenAI-compatible endpoint can be the target — point it at your own LLM proxy, your internal API gateway, or any guardrail stack you're evaluating.

### Quick Start

```bash
# Install the red-team pipeline only (no sandbox needed)
pip install -e ".[redteam]"

# Set your Groq API key (used by PAIR's attacker LLM — free tier is fine)
export GROQ_API_KEY=gsk_...

# Fire a 100-attack campaign; fail CI if ASR exceeds 20%
python -m redteam.runner \
  --target https://your-api.example.com/v1/chat/completions \
  --attacks template,encoding,pair \
  --attempts 100 \
  --seed 42 \
  --fail-above 20
```

### What to Configure

| Variable | Where | Purpose |
|---|---|---|
| `--target` | CLI flag | Your OpenAI-compatible endpoint URL |
| `--attacks` | CLI flag | Comma-separated: `template`, `encoding`, `pair` (or all three) |
| `--attempts` | CLI flag | Attacks per strategy. 50–100 gives stable ASR numbers |
| `--seed` | CLI flag | Fix seed for reproducibility across runs (default: 42) |
| `--fail-above` | CLI flag | Exit code 1 if ASR exceeds this % — use as a CI/CD gate (e.g. `--fail-above 20`) |
| `GROQ_API_KEY` | `.env` or shell | Required for PAIR's attacker LLM. [Get one free](https://console.groq.com/keys) |

The runner sends OpenAI-format `POST` requests (`{"model": "...", "messages": [{"role": "user", "content": "<attack prompt>"}]}`) and expects a JSON response with a `choices[0].message.content` field. Any proxy that speaks OpenAI-compatible chat completions works without modification.

### What the Report Looks Like

```
==================================================
RED TEAM REPORT
==================================================
  total_attacks: 100
  successful_bypasses: 25
  blocked: 75
  errors: 0
  attack_success_rate: 25.00%
```

Each bypass is logged with: the exact prompt that worked, the attack strategy that generated it, and the full response from your endpoint. Logs go to stdout (structured JSON) and optionally to Supabase if configured.

### Interpreting Results

| ASR Range | What it means |
|---|---|
| **0–10%** | Strong coverage against fixed-corpus attacks. Run PAIR next to find adaptive blind spots |
| **10–30%** | Typical for ML-based stacks. Encoding and framing bypasses are leaking through |
| **30–60%** | Significant gaps. Likely missing a semantic injection layer (DeBERTa-class classifier) |
| **60%+** | Regex-only or no guardrails. The pipeline is near-baseline |

> **Note:** A low fixed-corpus ASR does not mean you are safe against PAIR. Our own stack scored 25% on fixed attacks and 95% against the adaptive attacker. Run all three strategies.

## 🔮 Roadmap

All four research phases are complete. The pipeline was built around one constraint: produce real, defensible ASR numbers against a live target — not synthetic benchmarks, not self-reported estimates. Everything below tracks how that was executed.

### Phase A — Baseline ASR ✅
Run the pipeline against the sandbox with layers enabled incrementally. Each configuration uses the same attack set, same prompt corpus.

- [x] Wire full sandbox pipeline: cache → guardrails → LLM → response
- [x] Load DeBERTa injection and toxicity models at startup (CPU, no GPU needed)
- [x] Full stack confirmed live: 20% ASR on pilot run (n=40)
- [x] Layer toggle implemented (`GUARDRAIL_LAYERS` env var, server hot-reloads on change)
- [x] Re-run Phase A with n=100 per strategy for statistically reliable layer-by-layer ASR
- [x] Fill in Table 1 (Findings section)

### Phase B — External Baseline Comparison ✅
Run the same attack corpus against one external reference guardrail to make the numbers meaningful beyond self-reference.

- [x] Wire Llama Guard via Groq inference API as the comparison target
- [x] Run same template + encoding attack set against external baseline
- [x] Compute delta: Aegis full-stack ASR vs. external baseline ASR
- [x] Fill in Table 2 (Findings section)

### Phase C — PAIR Integration ✅
Wire the adaptive attack strategy and measure whether it achieves higher ASR than fixed-corpus attacks.

- [x] Implement PAIR loop in `redteam/attacks/pair.py`: Groq Llama 3 as attacker LLM, iterate until bypass or max iterations (default: 5)
- [x] Run PAIR against full sandbox stack; record ASR and average iterations-to-bypass
- [x] Run PAIR against external baseline from Phase B for cross-target comparison
- [x] Fill in Table 3 (Findings section)

### Phase D — Countermeasures ✅
Implement and empirically validate defenses against the PAIR bypass rate found in Phase C.

- [x] Implement SessionGuard (`src/guardrails/session.py`): rejection-velocity lockout, breaks PAIR's feedback loop
- [x] Implement OutputGuard (`src/guardrails/output.py`): dual-pass response screening
- [x] Wire SemanticCache (`src/cache/semantic.py`) into the live request path (was previously dead code — implemented but never instantiated)
- [x] Fix schema bug in SessionGuard's lockout path that crashed requests with a 500 instead of returning a clean block
- [x] Re-run PAIR (same seed=42, 20 goals) against full stack + all three countermeasures: 95.00% → 20.00% ASR
- [x] Fill in Table 4 (Findings section)

### Phase E — Deployment & Hardening ✅
Turn the validated research stack into something a company can actually run.

- [x] Wire live Supabase telemetry into the request path (`app.state.telemetry`, `TelemetryClient.log_event`)
- [x] Build a real Streamlit dashboard against `aegis_events` (`dashboard/data.py` + `dashboard/app.py`) — verified live against real sandbox traffic
- [x] Register `TimingMiddleware` (was defined but never activated) — `X-Request-ID` / `X-Process-Time-Ms` headers now real
- [x] Add optional `AEGIS_API_KEY` shared-key auth on `/v1/*` (`/health` stays open for healthchecks)
- [x] Fix Docker: `HF_HOME` model-cache persistence, `REDIS_HOST` compose-network bug, `.dockerignore`
- [x] Verify Docker for real via CI (`.github/workflows/docker-verify.yml`) — no local Docker/WSL install required
- [x] Add `DEPLOY.md`: drop-in proxy-container quick start, auth, config reference
- [x] Add CI test job (`.github/workflows/tests.yml`) — 48 tests on every push/PR
- [x] Implement the previously-planned Unicode homoglyph encoding attack

### Future Directions

A reinforcement-learning-based attacker (e.g., a PPO-trained policy maximizing ASR while preserving semantic similarity to benign prompts) is a natural extension but out of scope for this iteration.

---

## 📚 References

- [PAIR: Jailbreaking Black-Box LLMs](https://arxiv.org/abs/2310.08419) — Chao et al. 2023
- [Universal Adversarial Attacks on Aligned LLMs](https://arxiv.org/abs/2307.15043) — Zou et al. 2023 (GCG — white-box only, not implemented)
- [JailbreakBench](https://jailbreakbench.github.io/) — Standardized jailbreak evaluation framework
- [HarmBench](https://github.com/centerforaisafety/HarmBench) — Automated red-teaming benchmark
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — LLM attack taxonomy

---

## 📄 License

All Rights Reserved — publicly viewable, not licensed for use, copying, modification, or redistribution without permission. See [LICENSE](LICENSE).

---

<div align="center">

*The pipeline is the product. The sandbox is what it breaks.*

</div>
