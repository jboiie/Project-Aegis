Resource-Constrained Implementation Plan

> **This build plan is COMPLETE** — Phases A-D all shipped (see README Roadmap for final results
> and Tables 1-4). Kept as a historical record of the original plan; some details below
> (e.g. "not yet wired", "pending") describe the pre-implementation state, not current status.
> It mapped the north-star PRD down to a student laptop and ~₹3,500 budget using free-tier
> services and quantized models.

---

## 1. Project Identity

**Project Aegis** is an autonomous LLM red-teaming pipeline with a live guardrail sandbox as its attack target.

The pipeline (`redteam/`) is the primary system. The sandbox (`src/`) is the attack target.
The immediate goal is not more features — it is **real, defensible ASR numbers**.

---

## 2. The "Zero-Cost" Stack

### 2.1 Red-Teaming Pipeline (Primary — Build First)

**Runner**: `redteam/runner.py` — async HTTP client (httpx) that fires attack payloads at the target
endpoint and collects responses. Already scaffolded. Integration work remaining.

**Attack Modules**:
- `redteam/attacks/template.py` — DAN, AIM, role-play templates. Load from corpus; inject into target endpoint.
- `redteam/attacks/encoding.py` — Base64, ROT13, leetspeak transforms. Apply to a harmful payload and fire.
- `redteam/attacks/pair.py` — PAIR loop: Groq Llama 3 as attacker LLM. Iterate until bypass or max iterations. Implemented in Phase C.

**Evaluation**:
- `redteam/evaluation/metrics.py` — ASR, precision, recall, F1. Already scaffolded. Add per-layer breakdown once sandbox telemetry is wired.
- Automated judge: string-match for refusals first (free). LLM-as-judge via Groq for ambiguous cases.

### 2.2 Aegis Sandbox (Target — Minimal Viable Implementation)

The sandbox exists to be attacked, not to be perfect. Build the minimum needed for the pipeline to measure against it.

**Required for Phase A measurement:**
- FastAPI endpoint at `/v1/chat/completions` that accepts prompts and returns responses
- L1 regex guardrail running (already scaffolded)
- L2 DeBERTa injection classifier loaded and running (model loading not yet wired)
- L3 toxicity classifier loaded and running (model loading not yet wired)
- Basic telemetry: log each request, verdict (blocked/passed), and which layer triggered

**Not required for Phase A:**
- L4 PII redaction (enable in Phase A final run)
- Redis semantic cache (add in Phase B)
- Full Supabase telemetry (local file logging sufficient for Phase A)

**Tech stack:**
- FastAPI + async Python (no Rust — sandbox throughput is not the constraint)
- Quantized DeBERTa and toxicity models on CPU (< 300MB each)
- Groq free tier as backend LLM (Llama 3 70B)
- Local Redis in Docker for semantic cache

### 2.3 Telemetry: Supabase + Streamlit

**Pivot**: Kafka and ClickHouse require dedicated servers. Use Supabase (free-tier PostgreSQL) instead.

Every attack attempt, verdict, and bypass is logged asynchronously from the sandbox to Supabase.
The Streamlit dashboard visualizes:
- ASR over time (rolling window)
- Per-strategy bypass counts
- Per-layer block breakdown
- Raw bypass log (prompt + response)

---

## 3. Budget Allocation

| Resource | Purpose | Estimated Cost |
|---|---|---|
| Groq API | Sandbox backend LLM + PAIR attacker LLM (Llama 3) | ₹0 (free tier) |
| OpenRouter / DeepInfra credits | Llama Guard for Phase B external comparison (optional) | ~₹850 ($10 USD) |
| Hetzner / DigitalOcean VPS (1 month) | Optional: deploy stack publicly for demo/portfolio | ~₹500–₹800 |
| Supabase | Attack log database | ₹0 (free tier) |
| Streamlit Community Cloud | Dashboard hosting | ₹0 (free tier) |
| **Total** | | **₹0–₹1,650** |

---

## 4. Step-by-Step Execution Plan

### Phase A — Baseline ASR (Weeks 1–3)

**Goal**: Real ASR numbers showing the marginal effect of each guardrail layer. This is the core empirical output of the project.

**Week 1 — Wire the pipeline end-to-end:**
1. Complete `redteam/runner.py`: fire attacks → collect responses → compute ASR
2. Complete `redteam/attacks/template.py`: load corpus, fire, classify response
3. Complete `redteam/attacks/encoding.py`: apply transforms, fire, classify response
4. Complete `redteam/evaluation/metrics.py`: string-match judge for refusals

**Week 2 — Wire the sandbox:**
1. `main.py` startup → load guardrail models → `router.py` → `engine.py` → Groq
2. Load DeBERTa injection model and toxicity model at startup (quantized, CPU)
3. Add per-request telemetry: which layer triggered, verdict, latency

**Week 3 — Run the layer-by-layer experiment:**
1. Disable all guardrails → run attack set → record ASR (should be ~100%)
2. Enable L1 regex only → run same attack set → record ASR
3. Enable L1 + L2 → re-run → record ASR
4. Enable L1 + L2 + L3 → re-run → record ASR
5. Enable full stack (L1–L4) → re-run → record ASR
6. Fill in Table 1 in README Findings section

**Deliverable**: Table 1 completed. Headline finding: how much each layer reduces ASR on the template + encoding attack set.

---

### Phase B — External Baseline Comparison (Week 4)

**Goal**: Make the ASR numbers meaningful by comparing against an external reference.

**Recommended comparison target**: Llama Guard via Groq inference API. If setup is too costly, use a strong system-prompt refusal baseline (Groq Llama 3 + "never comply with harmful requests" system prompt) as a cheap proxy.

**Steps:**
1. Wire the comparison target as a second `--target` URL in the runner (no code changes needed — just point it at the external endpoint)
2. Run the same template + encoding attack set (same prompts, same N) against the external baseline
3. Compute delta: Aegis full-stack ASR vs. external baseline ASR
4. Fill in Table 2 in README Findings section

**Deliverable**: Table 2 completed. The number answers: "Is Aegis's layered stack more or less permissive than Llama Guard on the same corpus of attacks?"

---

### Phase C — PAIR Integration (Weeks 5–6)

**Goal**: Add the adaptive attack strategy and measure whether it achieves higher ASR than fixed-corpus attacks.

1. Implement PAIR loop in `redteam/attacks/pair.py`:
   - Attacker LLM: Groq Llama 3 (free tier)
   - Seed: a base harmful behavior description
   - Loop: rephrase → fire at sandbox → if blocked, feed rejection back → rephrase again
   - Terminate: bypass found, or max 20 iterations reached
2. Run PAIR against full Aegis sandbox; record ASR and average iterations-to-bypass
3. Optionally run PAIR against the external baseline from Phase B
4. Fill in Table 3 in README Findings section

**Deliverable**: Table 3 completed. The number answers: "Does an adaptive attacker (PAIR) break the guardrails at a higher rate than a fixed corpus of jailbreaks?"

---

## 5. The Interview Pitch

"I built an autonomous LLM red-teaming pipeline. The problem is that most teams deploy guardrails
once and never measure whether they still hold as attack techniques evolve. Aegis is the continuous
measurement tool — it generates jailbreak attacks using template, encoding, and PAIR strategies,
fires them at a live guardrail sandbox, and produces real ASR metrics broken down by attack type
and defense layer.

The core experiment is a layer-by-layer ablation: I ran the same attack set against the sandbox with
only L1 regex active, then incrementally enabled L2 DeBERTa, L3 toxicity, and L4 PII, measuring
how ASR dropped at each step. That tells you which layer is doing the actual work. Then I ran the
same attack set against Llama Guard as an external baseline, so the numbers aren't self-referential.

The sandbox is intentionally imperfect — it's not supposed to be a perfect defender, it's supposed
to be an honest target. I was constrained to a student laptop and a ₹3,500 budget, so I quantized
the classifier models for CPU inference, used Groq's free tier as both the sandbox backend and the
PAIR attacker LLM. The result is a reproducible measurement pipeline: run the same attack set,
get the same ASR number, compare across configurations."
