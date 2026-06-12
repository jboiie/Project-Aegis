PRD: Project Aegis — Autonomous LLM Vulnerability Evaluation Pipeline

> **⚠️ This is a NORTH-STAR design document.** It describes the ideal production-grade pipeline
> assuming significant compute (GPU cluster, Kafka). The current implementation
> is a resource-constrained proof-of-concept using FastAPI, Redis, Supabase, and Groq's free tier,
> running on a student laptop with a ~₹3,500 budget. See the README and resource.md for actual build status.

---

## 1. Executive Summary & Vision

Security teams have no standardized way to continuously measure LLM vulnerability. Static guardrails
are written once and never challenged. Project Aegis is the challenge.

The core product is an **autonomous red-teaming evaluation pipeline** that continuously generates,
executes, and measures jailbreak attacks against LLM endpoints. It produces real, reproducible metrics:
attack success rates (ASR) broken down by attack strategy and guardrail layer, precision/recall on
safety classifiers, and discovery rates for novel bypasses.

The pipeline operates against the **Aegis Sandbox** — a FastAPI proxy with a four-layer guardrail
stack (regex → DeBERTa injection classifier → toxicity classifier → PII redaction). The sandbox is a
*controlled target*, not the product. Its guardrails are intentionally imperfect; the pipeline's job is
to find where they fail and quantify the failure rate.

The customers for this system are **security researchers and ML safety teams** who need continuous,
automated measurement of their LLM defense posture — not enterprise teams deploying chatbots.

---

## 2. Product Vision: The Evaluation Pipeline

### 2.1 What the Pipeline Does

1. **Attack Generation** — Loads a corpus of attack strategies (template, encoding, PAIR) and generates concrete attack payloads targeting a given harmful behavior category
2. **Execution** — Fires attacks asynchronously at the target endpoint, collecting raw HTTP responses
3. **Measurement** — Classifies each response as a bypass or a block using an automated judge (string matching + LLM-as-judge for ambiguous cases)
4. **Reporting** — Computes ASR, precision, recall, and F1 per attack strategy, per guardrail layer, and for the full pipeline
5. **Feedback** — Successful bypass prompts are logged with metadata (strategy, target layer, response) and fed back as seed corpus for PAIR refinement

### 2.2 Success Metrics

The pipeline is successful when it can report the following with reproducible accuracy:

| Metric | Definition | Target |
|---|---|---|
| **Attack Success Rate (ASR)** | % of attack attempts producing an unsafe response | Accurate within ±2% vs. human eval |
| **Novel bypass discovery rate** | Unique bypass prompt patterns discovered per campaign | Increasing trend over iterations |
| **Pipeline automation level** | % of campaign stages requiring no human intervention | > 95% fully automated |
| **Judge accuracy** | Automated bypass classification vs. human labels | F1 > 0.90 on HarmBench standard |
| **Evaluation throughput** | Attacks evaluated per hour on student hardware | > 200/hr baseline |

These are the measures of a working red-teaming tool. Proxy latency and throughput are sandbox
implementation details, not pipeline success metrics.

---

## 3. Core Pipeline Components

### 3.1 Attack Engine

Implements three query-based strategies from the academic literature:

**Template Attacks** (Implemented)
Known jailbreak templates: DAN, AIM, developer mode, role-play framing, hypothetical scenarios.
Source corpus: JailbreakChat + HarmBench behavior dataset.
Tests whether pattern-matching defenses (L1 regex) are comprehensive.

**Encoding Attacks** (Implemented)
Obfuscation via Base64, ROT13, leetspeak, character splitting, Unicode substitution.
Tests whether semantic classifiers (L2/L3) can handle input transformations.
Reference: Wei et al. 2023.

**PAIR — Prompt Automatic Iterative Refinement** (In Progress)
An attacker LLM (Llama 3 via Groq free tier) receives a target behavior and iteratively rephrases
attack prompts based on feedback from the sandbox's response. The loop continues until a bypass is
produced or max iterations reached.
Core insight: the attacker LLM specifically targets the defender's failure modes.
Reference: Chao et al. 2023.

**Note on GCG**: Gradient-based adversarial suffix generation (Zou et al. 2023) requires white-box
access to model logits, which is incompatible with API-based targets. This is a fundamental
constraint of black-box evaluation pipelines, not a gap to be closed in this iteration.

### 3.2 Evaluation Engine

Automated bypass classification using a two-stage judge:

1. **String-match judge**: Checks for known refusal phrases ("I cannot", "I'm unable to", "As an AI..."). Fast, zero-cost, handles clear-cut cases.
2. **LLM-as-judge**: For ambiguous responses, uses a secondary LLM to classify the response as compliant (bypass) or non-compliant (block). Calibrated against HarmBench human labels.

Outputs per attack run:
- `attack_success_rate`: Primary metric
- `precision`, `recall`, `F1`: Classifier quality across the full guardrail stack (requires labeled dataset)
- `per_layer_asr`: Which guardrail layer was bypassed (requires instrumented sandbox)
- `bypass_log`: Full record of every successful bypass with prompt + response

### 3.3 The Aegis Sandbox (Target Environment)

The sandbox is the pipeline's attack target. It implements a four-layer guardrail stack:

- **L1 Regex**: Pattern matching on ~30 known jailbreak signatures. Catches explicit templates. Misses paraphrases and encoded variants — by design. The pipeline measures how much it misses.
- **L2 DeBERTa Injection Classifier**: Semantic injection detection (~10ms, CPU). Catches injection attempts that evade regex. Misses novel phrasings outside training distribution — the pipeline finds those.
- **L3 Toxicity Classifier** (toxic-BERT): Catches overtly harmful content. Misses harmful content wrapped in fictional or hypothetical framing.
- **L4 PII Redaction**: Regex + NER. Catches standard PII formats. Misses contextual or indirect leakage.
- **Semantic Cache** (Redis + MiniLM): Blocks known-bad embeddings in < 5ms. Misses attacks with high edit distance from cached vectors.

Each layer is instrumented to log whether it was the deciding factor in a block. This produces per-layer ASR — the pipeline's key diagnostic output.

---

## 4. North-Star Architecture (Production Grade)

For continuous autonomous operation at scale, the production pipeline requires:

- **Attack runner**: Rust/Tokio for zero-GC async HTTP, firing thousands of attacks/second
- **Model serving**: NVIDIA Triton Inference Server with TensorRT-LLM for guardrail models
- **Telemetry**: Kafka → ClickHouse for million-event-per-second attack log ingestion
- **Orchestration**: Kubernetes with auto-scaling Triton pods under attack load spikes
- **IaC**: Terraform for reproducible cloud deployment (AWS/GCP)

---

## 5. Benchmark Standards

The pipeline is calibrated against two established evaluation standards:

**JailbreakBench** — Provides a standardized behavior dataset and evaluation protocol. Pipeline ASR
numbers are reported against the JBB-Behaviors dataset to enable comparison with other red-teaming tools.

**HarmBench** — Provides human-labeled bypass/non-bypass classifications for calibrating the automated
judge. Pipeline judge F1 is measured against HarmBench labels before any ASR numbers are published.

---

## 6. Required Engineering Competencies

Building the full pipeline requires:

- **ML research**: Understanding of adversarial attack literature (PAIR and query-based methods), ability to implement and adapt research code
- **Systems**: Async Python for the current implementation; Rust/Tokio for production attack throughput
- **MLOps**: Experiment tracking, reproducible evaluation, model versioning for the guardrail stack
- **Distributed systems**: Kafka, Kubernetes, and streaming infrastructure for the north-star architecture

---

## 7. Compute Requirements

**Current (resource-constrained):**
- Student laptop, 8GB+ RAM, CPU-only
- Groq free tier for sandbox backend and PAIR attacker LLM
- Total cost: ₹0–₹850/month

**North-Star (production):**
- GPU cluster for continuous training of specialized attack models
- Triton Inference Server nodes for guardrail fleet
- Kafka + ClickHouse cluster for telemetry at scale
- Estimated cloud cost: $500–$1,500+/month depending on campaign frequency

---

## 8. Future Directions

A reinforcement-learning-based attacker (e.g., a PPO-trained policy maximizing ASR while preserving
semantic similarity to benign prompts) is a natural extension of the PAIR approach but out of scope
for this iteration. The current pipeline provides the measurement infrastructure that such a system
would require as its evaluation loop.
