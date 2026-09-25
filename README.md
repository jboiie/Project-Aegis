<div align="center">

# 🔴 Project Aegis

### Autonomous LLM Vulnerability Evaluation Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![Tests](https://github.com/jboiie/Project-Aegis/actions/workflows/tests.yml/badge.svg)](https://github.com/jboiie/Project-Aegis/actions/workflows/tests.yml)
[![Docker Verify](https://github.com/jboiie/Project-Aegis/actions/workflows/docker-verify.yml/badge.svg)](https://github.com/jboiie/Project-Aegis/actions/workflows/docker-verify.yml)

*Autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target.*

[Findings](#-findings) · [Pipeline](#-red-teaming-pipeline) · [Architecture](#-architecture) · [Attack Strategies](#-attack-strategies) · [The Sandbox](#-the-target-sandbox) · [Point At Your Own Endpoint](#-point-at-your-own-endpoint) · [Deploy](DEPLOY.md) · [Roadmap](#-roadmap)

</div>

---

> **Headline: a free, zero-recall-cost regex fix plus a second-stage classifier (Laya) scoped only to L2's blind spot cuts the guardrail stack's real false-positive category (`security_education`) from 61.1% to 5.6% on held-out test data, at a measured 6.0% attack-recall cost — while fixed-corpus (template/encoding) attack success rate against the full stack is ~0%, and PAIR (adaptive attacker) is excluded from all ASR claims after the attacker LLM refused to generate jailbreak candidates 90.4% of the time, triggering the project's own pre-committed stopping rule.** See [Findings](#-findings) for the full table and methodology.

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

*Full methodology, splits, and every intermediate number: [PROJECT_DESC.md](PROJECT_DESC.md). What follows is the current, validated state — a prior round of this README's numbers (a 25% fixed-corpus ASR, a 95%→20% PAIR result) was superseded after a diagnostic pass found the measurement itself was compromised (session-ID pollution across "independent" attack attempts, a judge that counted plain model refusals as bypasses, and other issues documented in PROJECT_DESC.md's "Baseline findings" section) — those figures are retired, not just outdated.*

### Locked baseline (current, real measurement)

- **Fixed-corpus attacks (template + encoding, 520 real AdvBench goals) achieve ~0% ASR against the full stack** — fresh sessions, cache off, judged by an uplift-based rubric (not a bare "wasn't blocked" heuristic).
- **PAIR (adaptive attacker) is excluded from all ASR claims.** The attacker LLM (`qwen/qwen3.6-27b` on Groq's free tier) refused to generate jailbreak candidates 90.4% of the time even with PAIR-paper framing — a real limitation of the available free-tier attacker, not a stack property. The project's own pre-committed stopping rule (>50% attacker refusal → drop from ASR claims) triggered and was honored rather than tuned around.
- **A real stack blind spot**: `role_play` template attacks ("Professor Smith" framing) pass every guardrail layer cleanly, 5/5 — only the target model's own refusal stops them. Not yet fixed; tracked in PROJECT_DESC.md.
- **Over-blocking is real and concentrated**: full benign-set FPR is small in aggregate, but the entire cost sits in two categories, `security_education` and `literal_editing_instruction` — everything below is about fixing that concentrated cost.

### Headline: fixing the false-positive concentration (Laya second-stage experiment)

Three approaches compared on the same held-out test split, same metrics, Wilson 95% CIs throughout:

| Approach | `security_education` batches 1-2 FPR | batch 3 FPR | combined FPR | attack recall lost |
|---|---|---|---|---|
| Current stack (no change) | 61.1% [38.6%, 79.7%] | 15.0% [9.3%, 23.3%] | 22.0% [15.5%, 30.3%] | 0.0% |
| L2 threshold tuning (cheaper alternative, tested and rejected) | 61.1% (unchanged) | 14.0% [8.5%, 22.1%] | 21.2% [14.8%, 29.4%] | 4.7% |
| L1 keyword fix only (shipped - see below) | 22.2% [9.0%, 45.2%] | 7.0% [3.4%, 13.7%] | 9.3% [5.3%, 15.9%] | 0.0% |
| **L1 keyword fix + Laya on L2 blocks only (recommended design)** | **5.6% [1.0%, 25.8%]** | **0.0% [0.0%, 3.7%]** | **0.8% [0.1%, 4.6%]** | 6.0% [4.8%, 7.5%] |
| Laya on all L1/L2 blocks (Laya alone, for comparison) | 11.1% [3.1%, 32.8%] | 0.0% [0.0%, 3.7%] | 1.7% [0.5%, 6.0%] | 6.0% [4.8%, 7.5%] |

**What each fix targets, and why they compose:** an L1 audit found every `security_education` false block traced to one bare-keyword regex pattern (`jailbreak(ed)?`) matching meta-discussion of jailbreaking, not actual attacks — removing it costs **zero** real attack recall (0/1583 sweep, 0/1193 test) and is now shipped in `src/guardrails/regex_rules.py`. Separately, Laya's entire measured benefit comes from the L2 side — **zero of its overturns touch L1-blocked attacks** — so it was scoped to L2 blocks only rather than applied to the whole stack. The combined-design row and the Laya-alone row are statistically comparable (overlapping CIs, same recall cost); the combined design is preferred because each fix targets a **separate, independently-verified failure mode** rather than asking one model to cover both. An L2-threshold-tuning baseline (raising L2's own decision threshold instead of adding a second model) was also tested and rejected: it recovers **0%** of the FPR on the sweep split L2 can't tell benign educational text about jailbreaking from real attacks at any threshold.

**End-to-end harm check**: every attack Laya's chosen threshold would overturn (72/72, test split) was sent through the sandbox with guardrails off to the target model — **0 bypassed**, 100% refused unaided. This shows zero added harm *against this specific target model's alignment* — not a general claim that Laya's overturns are safe against any target.

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

<p align="center">
  <img src="docs/assets/architecture.png" alt="Structure diagram: attack prompts flow from the pipeline into the Aegis Sandbox through one OpenAI-compatible endpoint, through SessionGuard, Semantic Cache, and the four-layer guardrail stack, and the guarded response returns through that same endpoint." width="700">
</p>

Requests enter and guarded responses leave through the same address:
`POST /v1/chat/completions`. Most prompts stop somewhere in the L1–L4
guardrail stack; a minority reach the LLM and are checked again by
OutputGuard before the response goes back. Logging to Supabase and the demo
dashboard is optional and off the request path.

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
#   successful_bypasses: 3
#   blocked: 97
#   errors: 0
#   attack_success_rate: 3.00%
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
| **Encoding** | Base64, ROT13, leetspeak, word-split, Unicode homoglyph obfuscation | Low | ✅ Implemented | [Wei et al. 2023](https://arxiv.org/abs/2307.02483) |
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
│   ├── report.py               # --report: renders a campaign's results as a Markdown report
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
├── tests/                      # Pytest test suite (61 tests)
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
│   └── prior_work.md           # Predecessor project findings that motivated the sandbox design
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
  --fail-above 20 \
  --report reports/campaign.md
```

### What to Configure

| Variable | Where | Purpose |
|---|---|---|
| `--target` | CLI flag | Your OpenAI-compatible endpoint URL |
| `--attacks` | CLI flag | Comma-separated: `template`, `encoding`, `pair` (or all three) |
| `--attempts` | CLI flag | Attacks per strategy. 50–100 gives stable ASR numbers |
| `--seed` | CLI flag | Fix seed for reproducibility across runs (default: 42) |
| `--fail-above` | CLI flag | Exit code 1 if ASR exceeds this % — use as a CI/CD gate (e.g. `--fail-above 20`) |
| `--report` | CLI flag | Path to write a structured Markdown report after the campaign finishes (e.g. `--report reports/campaign.md`) |
| `--delay` | CLI flag | Seconds to wait between requests, for rate-limited targets (default: 2.0) |
| `GROQ_API_KEY` | `.env` or shell | Required for PAIR's attacker LLM. [Get one free](https://console.groq.com/keys) |

The runner sends OpenAI-format `POST` requests (`{"model": "...", "messages": [{"role": "user", "content": "<attack prompt>"}]}`) and expects a JSON response with a `choices[0].message.content` field. Any proxy that speaks OpenAI-compatible chat completions works without modification.

### What the Report Looks Like

```
==================================================
RED TEAM REPORT
==================================================
  total_attacks: 100
  successful_bypasses: 3
  blocked: 97
  errors: 0
  attack_success_rate: 3.00%
```

Each bypass is logged with: the exact prompt that worked, the attack strategy that generated it, and the full response from your endpoint. Logs go to stdout (structured JSON) and optionally to Supabase if configured.

Pass `--report reports/campaign.md` to get the deliverable a company would actually hand to their security team: a Markdown report with an executive summary, per-strategy ASR table, full detail on every bypass (prompt, response, guardrail verdict), a top-5 block-reason breakdown, and conditional recommendations (e.g. "PAIR bypassed SessionGuard — tighten the lockout threshold"). Rendered entirely from the in-run results — no Supabase dependency, so it works even without telemetry configured. See `redteam/report.py`.

### Interpreting Results

| ASR Range | What it means |
|---|---|
| **0–10%** | Strong coverage against fixed-corpus attacks. Run PAIR next to find adaptive blind spots |
| **10–30%** | Typical for ML-based stacks. Encoding and framing bypasses are leaking through |
| **30–60%** | Significant gaps. Likely missing a semantic injection layer (DeBERTa-class classifier) |
| **60%+** | Regex-only or no guardrails. The pipeline is near-baseline |

> **Note:** A low fixed-corpus ASR does not mean your stack is free of cost elsewhere. Our own full stack measured ~0% fixed-corpus ASR while still over-blocking benign requests in specific categories (see [Findings](#-findings)) — run the labeled benign eval (`redteam/evaluation/run_eval.py`) alongside attack campaigns, not instead of them.

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
- [x] Re-run PAIR (same seed=42, 20 goals) against full stack + all three countermeasures (numbers from this run retired - see [Findings](#-findings))
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
- [x] Add CI test job (`.github/workflows/tests.yml`) — 61 tests on every push/PR
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
