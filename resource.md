Resource-Constrained Implementation Plan

> This is the ACTIVE build plan. It maps the north-star PRD down to a student laptop
> and ~₹3,500 budget using free-tier services and quantized models.
> Priority order: red-team runner → attack modules → metrics → PAIR → sandbox wiring → dashboard.

---

## 1. Project Identity

**Project Aegis** is an autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target.

The pipeline (`redteam/`) is the primary system. Build it first.
The sandbox (`src/`) is the attack target. Build it second, to the minimum viable state needed to measure against.

---

## 2. The "Zero-Cost" Stack

### 2.1 Red-Teaming Pipeline (Primary — Build First)

**Runner**: `redteam/runner.py` — async HTTP client (httpx) that fires attack payloads at the target
endpoint and collects responses. Already scaffolded. Integration work remaining.

**Attack Modules**:
- `redteam/attacks/template.py` — DAN, AIM, role-play templates. Load from a corpus JSON; inject into the target endpoint.
- `redteam/attacks/encoding.py` — Base64, ROT13, leetspeak transforms. Apply to a harmful payload and fire at the sandbox.
- `redteam/attacks/pair.py` — PAIR loop: use Groq's free Llama 3 as the attacker LLM. Iterate until bypass or max iterations. This is the most important attack module to complete.

**Evaluation**:
- `redteam/evaluation/metrics.py` — ASR, precision, recall, F1. Already scaffolded. Add per-layer breakdown once sandbox telemetry is wired.
- Automated judge: string-match for refusals first (free). LLM-as-judge via Groq free tier for ambiguous cases.

### 2.2 Aegis Sandbox (Target — Minimal Viable Implementation)

The sandbox exists to be attacked, not to be perfect. Build the minimum needed for the pipeline to measure against it.

**Required for measurement:**
- FastAPI endpoint at `/v1/chat/completions` that accepts prompts and returns responses
- L1 regex guardrail running (already scaffolded)
- L2 DeBERTa injection classifier loaded and running (model loading not yet wired)
- L3 toxicity classifier loaded and running (model loading not yet wired)
- Basic telemetry: log each request, verdict (blocked/passed), and which layer triggered

**Not required for first measurement pass:**
- L4 PII redaction (add in Phase 2)
- Redis semantic cache (add in Phase 2)
- Full Supabase telemetry (local file logging sufficient for Phase 1)

**The sandbox tech stack:**
- FastAPI + async Python (no Rust needed — sandbox throughput is not the constraint)
- Quantized DeBERTa and toxicity models running on CPU (< 300MB each, fine on a student laptop)
- Groq free tier as the backend LLM (Llama 3 70B, fast inference, zero cost)
- Local Redis in Docker for semantic cache

### 2.3 Telemetry: Supabase + Streamlit

**Pivot**: Kafka and ClickHouse require dedicated servers. Use Supabase (free-tier PostgreSQL) instead.

Every attack attempt, verdict, and bypass is logged asynchronously from the sandbox to Supabase.
The Streamlit dashboard pulls from Supabase and visualizes:
- ASR over time (rolling window)
- Per-strategy bypass counts
- Per-layer block breakdown
- Raw bypass log (prompt + response)

---

## 3. Budget Allocation

Every rupee goes toward compute for the pipeline's most demanding components.

| Resource | Purpose | Estimated Cost |
|---|---|---|
| Google Colab Pro (1 month) | PAIR attacker LLM longer runtimes; GCG gradient attacks on T4/A100 GPU | ~₹900 |
| OpenRouter / DeepInfra credits | Larger attacker LLM for PAIR (Llama 3 70B or Claude Haiku) | ~₹850 ($10 USD) |
| Hetzner / DigitalOcean VPS (1 month) | Optional: deploy final stack publicly for demo/portfolio | ~₹500–₹800 |
| Supabase | Attack log database | ₹0 (free tier) |
| Streamlit Community Cloud | Dashboard hosting | ₹0 (free tier) |
| Groq API | Sandbox backend LLM + PAIR attacker LLM | ₹0 (free tier) |
| **Total** | | **~₹2,250–₹2,550** |

---

## 4. Step-by-Step Execution Plan

### Phase 1 — Pipeline Core (Week 1–2)

**Goal**: A working red-team runner that can fire template and encoding attacks at any OpenAI-compatible endpoint and report ASR.

1. Complete `redteam/runner.py` integration: fire attacks → collect responses → compute metrics
2. Complete `redteam/attacks/template.py`: load corpus, inject, parse response
3. Complete `redteam/attacks/encoding.py`: apply transforms, fire, parse response
4. Complete `redteam/evaluation/metrics.py`: string-match judge for refusals
5. Validate against Groq API directly (no sandbox yet) to confirm the pipeline works end-to-end

**Deliverable**: `python -m redteam.runner --target https://api.groq.com/... --attacks template,encoding --attempts 50` produces a real ASR report.

### Phase 2 — Sandbox Wiring (Week 3–4)

**Goal**: Minimal sandbox running, pipeline attacking it, per-layer telemetry working.

1. Wire sandbox pipeline: `main.py` startup → load guardrail models → `router.py` → `engine.py` → Groq
2. Load DeBERTa injection model and toxicity model at startup (quantized, CPU)
3. Add per-request telemetry: which layer triggered, latency, verdict
4. Redirect pipeline runner at sandbox: `--target http://localhost:8000/v1/chat/completions`
5. Run first benchmark campaign: template + encoding, 100 attempts each

**Deliverable**: First real ASR numbers per layer. Fill in the evaluation table in README.

### Phase 3 — PAIR + Telemetry Dashboard (Week 5–6)

**Goal**: PAIR attack running; dashboard visualizing live pipeline output.

1. Implement PAIR loop in `redteam/attacks/pair.py`: attacker LLM (Groq Llama 3) iterates until bypass or max iterations
2. Set up Supabase project; wire sandbox telemetry to log to Supabase
3. Build Streamlit dashboard: ASR over time, per-strategy breakdown, bypass log
4. Run PAIR campaign against sandbox; compare ASR to template/encoding baseline

**Deliverable**: Dashboard live at localhost:8501 showing real metrics. PAIR ASR measured and compared to simpler attacks.

### Phase 4 — GCG + Benchmarking (Colab GPU)

**Goal**: GCG attacks running via Colab; pipeline benchmarked against JailbreakBench.

1. Implement GCG in Colab notebook: generate adversarial suffixes using sandbox's model as proxy gradient signal
2. Expose local sandbox via ngrok; fire Colab-generated attacks at it
3. Run pipeline against [JailbreakBench](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors) behavior dataset
4. Calibrate automated judge against HarmBench human labels
5. Report final ASR numbers per strategy vs. JailbreakBench standard

---

## 5. The Interview Pitch (Reframed)

The old pitch was: "I built a security proxy."
The new pitch is: "I built a red-teaming evaluation pipeline."

When asked about this project:

"I built an autonomous LLM red-teaming pipeline. The problem I was solving is that most teams deploy
guardrails once and never measure whether they still hold as attack techniques evolve. Aegis is the
continuous measurement tool — it generates jailbreak attacks using template, encoding, and PAIR
strategies, fires them at a live guardrail sandbox, and produces real ASR metrics broken down by
attack type and defense layer. The sandbox is a FastAPI proxy with four layers of defense — regex,
DeBERTa injection classifier, toxicity classifier, and PII redaction — and it's intentionally
imperfect because that's what makes the metrics honest. I was constrained to a student laptop and
a ₹3,500 budget, so I quantized the classifier models for CPU inference, used Groq's free tier
as both the sandbox backend and the PAIR attacker LLM, and offloaded gradient-based attacks to
Colab. The result is a full evaluation loop: generate attacks, measure bypass rate, log bypasses,
refine attacks — running at zero compute cost."
