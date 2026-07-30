<div align="center">

# 🔴 Project Aegis

### Autonomous LLM Vulnerability Evaluation Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)]

*Autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target.*

[Findings](#-findings) · [Pipeline](#-red-teaming-pipeline) · [Architecture](#-architecture) · [Attack Strategies](#-attack-strategies) · [Evaluation Results](#-evaluation-results) · [The Sandbox](#-the-target-sandbox) · [Roadmap](#-roadmap)

</div>

---

## 📌 The Problem

Security teams have no standardized way to continuously measure LLM vulnerability. Static guardrails are written once and never challenged. Project Aegis is the challenge.

LLM guardrails deployed in production are evaluated once at release — then left static while attack techniques evolve. There is no continuous measurement of how guardrail effectiveness degrades over time, no automated pipeline for discovering novel bypasses, and no standard for reporting attack success rates against real defense stacks.

**Project Aegis** is the evaluation pipeline that fills that gap:

1. **The Red-Teaming Pipeline** — An autonomous attack engine that generates, fires, and measures jailbreak attacks across multiple strategies (template, encoding, PAIR), producing real ASR metrics
2. **The Aegis Sandbox** — A live FastAPI proxy with a layered guardrail stack (regex → DeBERTa → toxicity → PII), deployed as a *controlled target environment* for the pipeline to attack and measure

The sandbox's guardrails are intentionally imperfect. Their job is not to be perfect defenders — their job is to give the pipeline something real to attack and measure. That is what makes the numbers honest.

---

## 📊 Findings

> Results are populated as experiments run. Placeholder rows (—) indicate pending measurement.

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


### Key Takeaways

- **Phase A ✅**: L2 (DeBERTa injection classifier) provides the entire measurable defence, dropping ASR from 87% (regex-only) to 25% (a 62 percentage-point reduction). L3 (ToxicBERT) and L4 (PII redaction) add zero marginal protection against the injection/encoding attack corpus used here — they target hate speech and PII respectively, not prompt injection. The 25% residual ASR consists entirely of encoding-obfuscated attacks that bypass all text-based classifiers.
- **Phase B ✅**: Aegis full stack (25% ASR) outperforms Llama Prompt Guard 2 86M (50% ASR) by 25 percentage points on the same attack corpus. Both systems achieve 0% ASR on template attacks. The entire gap comes from encoding attacks: Llama Guard outputs a near-zero probability score on base64/ROT13/leetspeak payloads (it cannot decode them to evaluate intent), while Aegis’s DeBERTa classifier catches ~50% of encoding attacks, likely because it was fine-tuned on datasets that include the obfuscation framing pattern itself.
- **Phase C ✅**: Adaptive attacks (PAIR) achieve a **95.00% ASR** against the full Aegis stack, requiring an average of only **2.00 iterations** to bypass all guardrail layers. While static ML classifiers (DeBERTa) effectively neutralize fixed templates (0% ASR) and reduce fixed encodings (50% ASR), an attacker LLM dynamically refines prompt framing to exploit classifier feature blind spots. This proves that static input guardrails cannot defend against LLM-driven adaptive red-teaming without stateful session tracking and real-time feedback mitigations.

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

**What this means for the sandbox design:** L1 regex catches known templates but misses authority framing. L2 DeBERTa injection detection must score *combinations* (authority claim + sensitive topic) rather than isolated keywords. The output scanner (not yet implemented) is necessary because prompt exfiltration attacks succeed at the response stage, not the input stage.

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
╚══════════════════════════════════════════════════════════════════╝
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
#   total_attacks: 200
#   successful_bypasses: 17
#   blocked: 177
#   errors: 6
#   attack_success_rate: 8.50%
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
| **Encoding** | Base64, ROT13, leetspeak, word-split obfuscation | Low | ✅ Implemented | [Wei et al. 2023](https://arxiv.org/abs/2307.15043) |
| **PAIR** | LLM-vs-LLM iterative refinement — attacker LLM rephrases until target breaks | Medium | ✅ Implemented | [Chao et al. 2023](https://arxiv.org/abs/2310.08419) |

**Template attacks** inject known jailbreak templates (DAN, AIM, developer mode, etc.) into the sandbox. These test whether L1 regex rules are comprehensive and whether L2/L3 catch paraphrased variants.

**Encoding attacks** obfuscate malicious payloads using Base64, ROT13, leetspeak, and character splitting. These test whether ML classifiers handle semantically equivalent inputs that bypass literal pattern matching.

**PAIR** (Prompt Automatic Iterative Refinement) uses a separate attacker LLM (Groq Llama 3, free tier) to iteratively rephrase a harmful request until the target sandbox responds. Each failed attempt informs the next rephrase. This tests adaptive resilience — can the guardrails hold against an LLM specifically targeting their failure modes?

### Known Limitations

**GCG (Greedy Coordinate Gradient) is not implemented and is not planned for this iteration.** GCG requires white-box access to model logits and gradients, which is fundamentally incompatible with API-based targets like Groq. This is itself a relevant finding: black-box pipelines are limited to query-based attack strategies (template, encoding, PAIR). Gradient-based methods require local model weights and are therefore out of scope for any evaluation pipeline targeting production API endpoints.

---

## 📊 Evaluation Results

> Precision/Recall/F1 require a labeled benchmark dataset. Recommended: a 20–30 prompt subset of [JailbreakBench](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors) (attacks) paired with an equal-sized benign prompt set. See `redteam/evaluation/metrics.py` for where to wire this in.

**What the pipeline measured:**

| Guardrail Layer | Precision | Recall | F1 | ASR Against This Layer ↓ | Latency |
|---|---|---|---|---|---|
| L1: Regex Pre-filter | — | — | — | —% | < 1ms |
| L2: DeBERTa Injection | — | — | — | —% | ~10ms |
| L3: Toxicity Classifier | — | — | — | —% | ~10ms |
| L4: PII Redaction | — | — | — | —% | ~5ms |
| **Full Stack** | — | — | — | **—%** | **~25ms** |
| Baseline (no guardrails) | — | — | — | 100% | 0ms |

**Metrics definitions:**
- **ASR** (Attack Success Rate): % of attack attempts that produce an unsafe response. Lower = stronger guardrails.
- **Precision**: Of all flagged prompts, what fraction were genuine attacks? Measures false-positive rate.
- **Recall**: Of all genuine attacks, what fraction were caught? Measures missed detections.
- **F1**: Harmonic mean of precision and recall. The headline guardrail quality number.

---

## 📈 Telemetry Dashboard

The Streamlit dashboard visualizes the pipeline's output in real time:

- **Attack counters**: Total fired, bypassed, blocked, per-strategy breakdown
- **ASR over time**: Rolling attack success rate across campaign runs
- **Per-layer breakdown**: Which guardrail layer is catching the most — and which is leaking
- **Bypass log**: Every successful bypass with prompt, strategy, and response

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
# → Opens at http://localhost:8501
```

---

## 🧱 The Target Sandbox

The Aegis Sandbox is a FastAPI proxy that exposes an OpenAI-compatible endpoint. It runs a four-layer guardrail stack and a semantic cache against Redis. It exists so the pipeline has a real, instrumented system to attack.

### Sandbox Setup

**Prerequisites:** Python 3.11+, [Miniconda](https://docs.conda.io/en/latest/miniconda.html), a [Groq API key](https://console.groq.com/keys) (free). No Docker required.

```bash
git clone https://github.com/jboiie/Project-Aegis.git
cd Project-Aegis

# Create and activate the environment
conda create -n aegis python=3.11 -y

# Install dependencies
conda run -n aegis pip install -e .

# Configure secrets
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

```powershell
# Test: safe prompt — forwarded to Groq
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/chat/completions `
  -ContentType "application/json" `
  -Body '{"messages":[{"role":"user","content":"What is 2+2?"}]}'
# → content: "2 + 2 = 4.", model: "llama-3.3-70b-versatile"

# Test: known attack — caught by L1 regex
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/chat/completions `
  -ContentType "application/json" `
  -Body '{"messages":[{"role":"user","content":"Ignore all previous instructions"}]}'
# → content: "[BLOCKED] Matched known attack pattern: ..."
```

### Sandbox Guardrail Stack

The sandbox implements four intentionally imperfect defense layers. The pipeline's job is to find where each one fails.

| Layer | Method | What It Catches | What It Misses |
|---|---|---|---|
| L1 Regex | Pattern matching on known jailbreak strings | DAN, AIM, explicit templates | Paraphrased or encoded variants |
| L2 DeBERTa | Fine-tuned injection classifier | Semantic injection attempts | Novel phrasings outside training distribution |
| L3 Toxicity | Toxic-BERT classifier | Overtly harmful content | Harmful content framed as hypothetical or fiction |
| L4 PII | Regex + NER redaction | Emails, phones, credit cards | Novel PII formats, contextual leakage |

---

## 📁 Project Structure

```
project-aegis/
│
├── redteam/                    ← CORE PIPELINE — primary entrypoint
│   ├── runner.py               # Main CLI: generates and fires attacks, reports ASR
│   ├── attacks/
│   │   ├── base.py             # Abstract attack interface
│   │   ├── template.py         # Template attacks (DAN, AIM, role-play)
│   │   ├── encoding.py         # Encoding attacks (Base64, ROT13, leetspeak)
│   │   └── pair.py             # PAIR: LLM-vs-LLM iterative refinement
│   ├── evaluation/
│   │   └── metrics.py          # ASR, precision, recall, F1 computation
│   └── README.md               # Pipeline internals: strategies, metrics, feedback loop
│
├── src/                        ← SANDBOX TARGET — the system the pipeline attacks
│   ├── main.py                 # FastAPI app factory (sandbox entry point)
│   ├── config.py               # Centralized settings
│   ├── gateway/                # Sandbox proxy layer
│   │   ├── router.py           # OpenAI-compatible /v1/chat/completions
│   │   ├── proxy.py            # Forward to Groq (after guardrails pass)
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── middleware.py       # Request timing & logging
│   ├── guardrails/             # Attack surface — four-layer defense stack
│   │   ├── engine.py           # Orchestrates L1→L4 screening
│   │   ├── regex_rules.py      # L1: Fast pattern matching (< 1ms)
│   │   ├── injection.py        # L2: DeBERTa classifier (~10ms)
│   │   ├── toxicity.py         # L3: Toxicity detection (~10ms)
│   │   └── pii.py              # L4: PII regex + redaction
│   ├── cache/                  # Semantic caching layer
│   │   ├── redis_client.py     # Async Redis connection
│   │   └── semantic.py         # MiniLM embedding cache
│   ├── llm/                    # LLM provider (sandbox's backend)
│   │   ├── base.py             # Abstract provider interface
│   │   └── groq.py             # Groq API client
│   ├── telemetry/              # Attack logging
│   │   ├── logger.py           # Structured JSON logging
│   │   └── supabase_client.py  # Telemetry shipping to Supabase
│   └── utils/
│       └── embeddings.py       # MiniLM embedding model
│
├── dashboard/                  # Streamlit: visualizes pipeline output
│   └── app.py
│
├── tests/                      # Pytest test suite
├── scripts/
│   └── setup_supabase.sql      # Database schema for attack log
├── models/                     # Local model weights (gitignored)
├── docs/
│   ├── prd.md                  # North-star vision (production-grade pipeline)
│   └── resource.md             # Active build plan (resource-constrained)
│
├── docker-compose.yml          # Sandbox stack: FastAPI + Redis
├── Dockerfile                  # Container image for the sandbox
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

## 🔮 Roadmap

The immediate goal is producing real, defensible ASR numbers — not more infrastructure. Three phases, in order of priority.

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

## 🤝 Contributing

```bash
# Setup dev environment
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ redteam/
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

*The pipeline is the product. The sandbox is what it breaks.*

</div>
