# Project Aegis: Empirical Evaluation of Static vs. Adaptive LLM Red-Teaming Against Multi-Layer Input Guardrails

**Author:** Jai / Project Aegis  
**Repository:** [github.com/jboiie/Project-Aegis](https://github.com/jboiie/Project-Aegis)  
**Date:** July 2026  

---

## Executive Summary

As Large Language Models (LLMs) are deployed into production environments, multi-layer guardrail systems (combining heuristics, ML classifiers, and domain filters) are increasingly relied upon to filter malicious inputs. **Project Aegis** is an autonomous LLM vulnerability evaluation pipeline designed to empirically test and benchmark guardrail efficacy under both static and adaptive attack conditions.

Through three rigorous experimental phases (n=100 per strategy, fixed seed=42), we evaluated the Aegis multi-layer sandbox against fixed-corpus attacks, external commercial baselines (Meta's Llama Prompt Guard 2), and LLM-driven adaptive red-teaming (PAIR).

### Core Findings

1. **DeBERTa Drives the Primary Defense (Phase A):**
   - Heuristic L1 Regex rules alone exhibit an **87.00% Attack Success Rate (ASR)**.
   - Adding L2 DeBERTa (`deberta-v3-base-prompt-injection-v2`) reduces ASR by **62 percentage points** down to **25.00%**.
   - Specialized layers L3 (ToxicBERT) and L4 (PII redaction) offer **0 percentage points** of marginal protection against prompt injection and obfuscated attacks, confirming that domain-specific classifiers fail on out-of-domain injection payloads.

2. **Aegis Outperforms Meta's Llama Prompt Guard 2 (Phase B):**
   - On an identical attack corpus, Aegis full stack achieved **25.00% ASR** compared to Llama Prompt Guard 2 86M's **50.00% ASR** (a **25 percentage point advantage** for Aegis).
   - While both systems achieved 0% ASR on standard template jailbreaks, Llama Guard failed completely against encoding obfuscation (100% ASR), whereas Aegis caught ~50% of obfuscated attacks due to DeBERTa's fine-tuning on framing patterns.

3. **Adaptive Red-Teaming (PAIR) Collapses Static Defenses (Phase C):**
   - When exposed to an adaptive Attacker LLM (`llama-3.1-8b-instant`) operating in an iterative feedback loop (PAIR), Aegis's full-stack ASR soared from **25.00% to 95.00%**.
   - The Attacker LLM required an average of **only 2.00 iterations** to mutate prompt framing and bypass all guardrail layers.

4. **Session-Level Countermeasures Neutralize PAIR (Phase D):**
   - Wiring SessionGuard, OutputGuard, and SemanticCache into the live request path and re-running the identical PAIR campaign (seed=42, 20 goals) cut ASR from **95.00% to 20.00%** — a 75 percentage-point reduction.
   - Rejection-velocity session lockout (SessionGuard), not per-prompt classification, accounts for nearly all of the reduction: PAIR's attack model depends on a sustained feedback loop within one session, and breaking that loop is more effective than trying to classify each individual rephrase.

---

## 1. System Architecture & Methodology

The Aegis sandbox implements an instrumented OpenAI-compatible gateway (`/v1/chat/completions`) backed by a four-layer input defense stack:

```
[ Incoming Request ]
         │
         ▼
 ┌───────────────┐
 │ L1: Regex     │ ── (Exact phrase matching: DAN, ignore instructions)
 └───────┬───────┘
         │ Passed
         ▼
 ┌───────────────┐
 │ L2: DeBERTa   │ ── (ML classifier: protectai/deberta-v3-base-prompt-injection-v2)
 └───────┬───────┘
         │ Passed
         ▼
 ┌───────────────┐
 │ L3: ToxicBERT │ ── (Toxicity & hate-speech classifier)
 └───────┬───────┘
         │ Passed
         ▼
 ┌───────────────┐
 │ L4: PII       │ ── (Regex & NER redaction for sensitive entities)
 └───────┬───────┘
         │ Passed
         ▼
[ Target LLM (Groq / Llama 3.3 70B) ]
```

---

## 2. Experimental Results

### Phase A — Layer-by-Layer Guardrail Ablation Study
*Evaluated against 100 fixed-corpus attacks (50 Template, 50 Encoding), seed=42.*

| Guardrail Configuration | Total Attacks | Bypasses | Blocked | ASR ↓ | Δ Marginal Reduction |
|---|---|---|---|---|---|
| No Guardrails (Baseline) | 100 | 100 | 0 | 100.00% | — |
| L1 Only (Regex Heuristics) | 100 | 87 | 13 | **87.00%** | Baseline |
| L1 + L2 (+ DeBERTa Injection) | 100 | 25 | 75 | **25.00%** | **↓ 62.00pp** |
| L1 + L2 + L3 (+ ToxicBERT) | 100 | 25 | 75 | **25.00%** | **0.00pp** |
| Full Stack (L1–L4 + PII) | 100 | 25 | 75 | **25.00%** | **0.00pp** |

*Takeaway:* Regex handles obvious canned phrases, but DeBERTa provides virtually all actual protection. Obfuscated encodings account for 100% of the 25% residual bypasses.

---

### Phase B — Benchmark Comparison: Aegis vs. Meta Llama Prompt Guard 2
*Identical attack set (n=100, seed=42) evaluated against `meta-llama/llama-prompt-guard-2-86m`.*

| Target System | Template ASR | Encoding ASR | Overall ASR ↓ | Performance Delta |
|---|---|---|---|---|
| **Aegis Full Stack** | 0.00% | 50.00% | **25.00%** | **Baseline** |
| **Llama Prompt Guard 2 (86M)** | 0.00% | 100.00% | **50.00%** | **+25.00pp (Weaker)** |

*Takeaway:* Standalone prompt guard models fail on obfuscation vectors (Base64, ROT13, Leetspeak) because they attempt to evaluate text semantics without decoding the payload.

---

### Phase C — Static vs. Adaptive Red-Teaming (PAIR Attack)
*Adaptive LLM-driven refinement loop (PAIR) evaluated against Aegis full stack.*

| Strategy Type | Strategy Name | Total Goals | Bypasses | ASR ↓ | Avg. Iterations to Bypass |
|---|---|---|---|---|---|
| **Fixed Corpus** | Template | 50 | 0 | **0.00%** | N/A |
| **Fixed Corpus** | Encoding | 50 | 25 | **50.00%** | N/A |
| **Adaptive Loop** | **PAIR (Attacker LLM)** | 20 | 19 | **95.00%** | **2.00** |

*Takeaway:* Static guardrails are highly vulnerable to active feedback. In just **2 iterations**, an attacker LLM learns the classifier's decision boundaries and rephrases the prompt to achieve a 95% bypass rate.

---

## 3. Defense & Countermeasure Architecture (Phase D)

To mitigate the **95% PAIR bypass rate**, we implement three stateful countermeasure mechanisms in Aegis:

### 1. Semantic Intent Caching (`src/cache/semantic.py`)
Previously blocked prompts are embedded via `sentence-transformers/all-MiniLM-L6-v2` and stored in Redis. Incoming prompts with cosine similarity $\ge 0.92$ to known malicious intents are blocked instantly at L0.

### 2. Stateful Session & Rejection Tracking (`src/guardrails/session.py`)
Attacker LLMs rely on iterative feedback (`[BLOCKED]` responses). By tracking client session identifiers and monitoring rejection velocity ($\ge 3$ blocked attempts within 5 minutes), the gateway issues a temporary session ban, breaking the PAIR feedback loop.

### 3. Dual-Pass Output Guardrails (`src/gateway/router.py`)
When input classifiers fail against heavily obfuscated prompts, output verification screens the target LLM's response prior to client delivery. If the LLM generates actionable harmful instructions or refusal failures, the output is redacted.

### Empirical Validation

The three countermeasures above were wired into the live request path and the identical PAIR campaign from Phase C (seed=42, 20 goals, max_iterations=5) was re-run against the full stack.

| Configuration | Attacks Fired | Bypasses | ASR ↓ | Avg. Iterations to Bypass |
|---|---|---|---|---|
| Full stack, no countermeasures (Phase C) | 20 | 19 | **95.00%** | 2.00 |
| **Full stack + SessionGuard + OutputGuard + SemanticCache** | 20 | 4 | **20.00%** | 2.25 |

SemanticCache recorded zero blocks during this run: PAIR's per-iteration rephrasing is novel enough that L0 rarely finds a near-duplicate before SessionGuard's rejection-velocity lockout ends the session first. SessionGuard is doing effectively all of the observed work; OutputGuard and SemanticCache did not fire in this campaign but remain defense-in-depth for attack patterns this corpus didn't exercise (e.g. a slower attacker staying under the rejection-velocity threshold, or an attack that reaches the output stage).

**Measurement integrity note:** the first validation run also measured 20.00% ASR, but for the wrong reason. `GuardrailEngine`'s session-lockout path constructed a `GuardrailCheck` with fields that don't exist on that schema (`layer=`, `score=`, `threshold=` instead of `name=`, `confidence=`), which raised a `pydantic.ValidationError` and returned an HTTP 500 on every lockout instead of a clean blocked verdict. The red-team runner's error handler treats any request exception as a block, so these crashes were silently miscounted as successful defenses (77 of ~100 requests crashed during that run). The bug was fixed and the campaign re-run cleanly with zero server errors before the number above was accepted. A regression test (`tests/test_countermeasures.py::test_engine_returns_verdict_on_session_lockout`) now exercises the lockout path through `GuardrailEngine.screen()` rather than testing `SessionGuard` in isolation, which is the coverage gap that let this ship originally.

---

## 4. Conclusion

The empirical findings of Project Aegis demonstrate that **alignment and safety in open-weight models and static guardrails are fragile pattern-matching surfaces**. While multi-layer ML stacks like DeBERTa significantly outperform commercial baselines like Llama Guard against fixed attacks, they remain fundamentally vulnerable to adaptive LLM red-teaming (PAIR).

Defending next-generation AI systems requires transitioning from static, single-turn input filtering to **stateful, session-aware defensive pipelines**. This is not just a theoretical prescription: wiring session-level rejection tracking, dual-pass output screening, and semantic intent caching into Aegis's live request path cut PAIR's ASR from 95.00% to 20.00% against the identical attack campaign. The dominant contributor was session-level state, not per-prompt classification — the same lesson as Phase A/B/C in reverse: the attacker's advantage came from being stateful (iterating with feedback) while the defense was stateless, and the fix was to make the defense stateful too.
