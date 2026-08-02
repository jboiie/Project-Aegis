# Understanding Project Aegis

*A complete-picture explainer: why this exists, how it works, what it found, where it's weak, and everything that got built to arrive here. Written so you can read it once and explain the project to anyone — a recruiter, a security engineer, a friend who asks "wait, what did you actually build?" — without hand-waving.*

---

## 1. The One-Sentence Version

**Project Aegis measures how well an LLM's safety guardrails actually hold up, by attacking them for real — with fixed attack lists, obfuscation tricks, and an AI that adapts to what got blocked — instead of just trusting that the guardrails work because someone wrote them once.**

If someone asks "what does it do," that sentence is the answer. Everything below is the *why* and the *how*.

---

## 2. The Problem This Exists To Solve

Here's the situation in the LLM industry right now: a company builds a chatbot or an API on top of GPT-4, Claude, Llama, or similar. To stop it from being misused (helping someone write malware, leaking its own system prompt, generating harmful content), they bolt on a "guardrail" — usually a mix of regex keyword filters and a small classifier model trained to detect bad prompts.

That guardrail gets built once, tested a little, shipped, and then **almost never re-tested**. Meanwwhile:

- Attack techniques evolve constantly (new jailbreak phrasings get shared publicly within days).
- Nobody has a standard way to say "our guardrail blocks X% of known attacks" with a number they can defend.
- Almost nobody tests against an *adaptive* attacker — one that gets told "blocked" and tries again with a different angle, the way a real motivated attacker would.

So the honest state of the industry is: companies ship a guardrail, feel good about it, and have no continuous, adversarial, numbers-backed way to know if it's actually working — or how badly it degrades against someone who tries more than once.

**Project Aegis is a working answer to "how would you actually measure that."**

---

## 3. What Project Aegis Actually Is

It's two systems, and the relationship between them is the whole point.

### 3.1 The Red-Team Pipeline (`redteam/`) — the primary product

This is an autonomous attack engine. Point it at *any* OpenAI-compatible chat endpoint (your own, someone else's, the built-in sandbox) and it will:

1. Generate attack prompts using one of three strategies (explained in §4).
2. Fire them at the target over HTTP.
3. Classify each response as "bypassed" (guardrail failed) or "blocked" (guardrail worked).
4. Report a hard number: **Attack Success Rate (ASR)** — the percentage of attacks that got through.

This is the part that's actually useful to a security team. It's not tied to Aegis's own sandbox — you can run `python -m redteam.runner --target https://your-api.com/... --attacks template,encoding,pair` against your own production guardrail and get a real number back.

### 3.2 The Aegis Sandbox (`src/`) — the target, and the proof-of-concept

This is a working FastAPI proxy that sits in front of an LLM (Groq's free-tier Llama models, in this build) and screens every request through a defense stack before forwarding it. It exists for two reasons:

- **It gives the pipeline something real to attack**, so the numbers aren't hypothetical.
- **It's itself a deployable product** — a company could literally run this container in front of their own LLM traffic today (see `DEPLOY.md`).

The sandbox is *intentionally imperfect*. Its job isn't to be unbreakable — it's to be honest and instrumented enough that the pipeline can find and quantify exactly where it fails. That's a deliberate design choice: a "perfect" sandbox would make the pipeline look useless. An honest, gap-having sandbox is what makes the whole project's findings mean something.

---

## 4. The Attack Strategies, Explained Simply

### Template attacks
Known, publicly documented jailbreak scripts — "DAN" (Do Anything Now), "AIM," pretending the model is in "developer mode," or asking it to roleplay a character with no restrictions. These are the attacks every guardrail vendor already knows about. If your guardrail can't stop these, it's not even trying.

### Encoding attacks
Same harmful request, disguised. Base64-encode it and ask the model to decode and follow it. Write it in leetspeak (`h4ck` instead of `hack`). Swap Latin letters for lookalike Cyrillic characters (`о` instead of `o` — same shape, different Unicode character). The idea: a classifier trained mostly on plain English text might not recognize the same malicious intent once it's been visually or structurally disguised.

### PAIR (Prompt Automatic Iterative Refinement) — the adaptive attack
This is the important one. Instead of firing a fixed list of prompts, PAIR uses a *second LLM* as the attacker. It's told the harmful goal, sends a prompt, and if it gets blocked, it's shown the rejection and asked to rephrase. It keeps iterating — up to 5 tries per goal in this build — until it either breaks through or gives up.

This simulates what a real, motivated attacker actually does: they don't try once and quit. They read the rejection message and adjust. **This is the difference between "did we block a list of known bad prompts" and "can we survive someone actually trying to get in."**

---

## 5. The Defense Stack, Explained Simply

Requests going through the sandbox pass through, in order:

1. **SessionGuard** — tracks how often a given session gets rejected. Three rejections in five minutes and that session gets locked out. This exists specifically to break PAIR's strategy: PAIR only works if it can keep trying and keep learning from rejections within one conversation. Cut off the conversation, cut off its ability to adapt.
2. **L0 Semantic Cache** — every blocked prompt gets embedded (turned into a vector) and stored. New prompts get compared against that cache; a close-enough match gets blocked instantly without even running the classifiers. Meant to catch near-duplicate rephrasings.
3. **L1 Regex** — fast pattern matching against known jailbreak phrases. Catches the obvious stuff in under a millisecond.
4. **L2 DeBERTa injection classifier** — a real fine-tuned ML model that scores whether a prompt looks like a prompt-injection attempt, even if it doesn't match any known pattern.
5. **L3 Toxicity classifier** — catches overtly harmful content (hate speech, etc.) — a different threat class than prompt injection.
6. **L4 PII redaction** — catches emails, phone numbers, credit card numbers in the prompt.
7. **OutputGuard** — after the LLM generates a response, it gets screened *again* before going back to the user. This catches failures that only show up in the output — like the model leaking its own system prompt, even when the input prompt looked completely innocent.

The stack is layered cheap-to-expensive on purpose: regex (near-free) runs before the ML classifiers (slower), so obvious attacks get rejected fast and only ambiguous cases pay the cost of the heavier models.

---

## 6. Methodology — How the Experiments Were Actually Run

A few choices that matter and why they were made:

- **Fixed seed (42) everywhere.** Every experiment — attack generation, PAIR's goal selection, the labeled dataset — uses the same random seed. This means anyone can rerun the exact same experiment and get the exact same attack prompts, which is what makes the numbers *reproducible* instead of "trust me."
- **n=100 for the fixed-corpus phases (Phase A/B).** Big enough sample that a single lucky/unlucky prompt doesn't swing the percentage much.
- **n=20 goals for PAIR (Phase C/D).** Smaller — PAIR is expensive (each goal can take up to 5 LLM round-trips against both the attacker model and the target), so 20 goals is a deliberate cost/statistical-power tradeoff, not an oversight. (This is a fair thing to push back on — see §9.)
- **ASR as the headline metric** — simplest possible framing: "of every attack we sent, what fraction got through." Easy to defend, easy to compare across configurations.
- **A separately labeled dataset for precision/recall/F1.** ASR alone can't tell you if the guardrail is *over*-blocking (rejecting harmless prompts too). For that you need known-benign prompts mixed in with known-attack prompts, which is exactly what `data/labeled_eval_set.jsonl` is (25 attack + 25 benign, same seed).
- **Every request in the labeled-eval run gets its own fresh session ID.** This one exists because of a real bug — see §8.

---

## 7. The Findings, Plain-English

| Phase | What was tested | Result | What it means |
|---|---|---|---|
| **A** | Fixed attacks, each guardrail layer added one at a time | 87% ASR (regex only) → 25% ASR (regex + DeBERTa) → 25% (adding toxicity/PII made zero difference) | **The DeBERTa classifier is doing basically all the real work.** Toxicity and PII filters aren't useless in general, they just don't target prompt-injection — wrong tool for this specific job. |
| **B** | Aegis vs. Meta's Llama Prompt Guard 2 (86M), same attack set | Aegis 25% ASR vs. Llama Guard 50% ASR | Aegis's classifier beats a real commercial-grade guardrail model on this test — and the entire gap is on *encoding* attacks. Llama Guard can't evaluate base64/ROT13 text because it can't decode it to judge intent; Aegis's DeBERTa model catches about half anyway. |
| **C** | PAIR (adaptive attacker) vs. the same full stack | **95% ASR**, average 2 iterations to break through | This is the core finding of the whole project. A static classifier stack that looked solid (25% ASR) collapses almost completely the moment the attacker gets to adapt. Two tries is all it usually took. |
| **D** | Same PAIR attack, now with SessionGuard + OutputGuard + SemanticCache added | **95% → 20% ASR** | Adding *session-level* defense (not smarter classifiers, just "stop letting this conversation keep trying") did almost all the work. SemanticCache barely fired — PAIR's rephrasing is novel enough each turn that near-duplicate matching rarely helps. SessionGuard is the real hero here. |

**The one sentence that captures the whole research arc:** *a classifier that looks strong against a fixed attack list can be almost worthless against an attacker that adapts — and the fix that actually worked wasn't a smarter classifier, it was making the defense stateful the way the attack already was.*

### The labeled precision/recall numbers (freshly reconfirmed, not from memory)

Against the 50-prompt labeled set (25 attack, 25 benign), rerun live before writing this doc:

- **Precision: 1.0000** — every single prompt the guardrail blocked really was an attack. Zero false alarms on benign traffic.
- **Recall: 0.5600** — of all the actual attacks in the set, it only caught 56% of them.
- **F1: 0.7179**

Read together with the ASR numbers above: this guardrail stack is *conservative* — it almost never blocks something it shouldn't (great for user experience), but it's letting a real chunk of actual attacks through unflagged (not great for security). That's a legitimate, quantified trade-off, not a vague impression.

---

## 8. The Bugs Found Along the Way (and why they matter)

This section exists because finding and fixing these honestly is arguably more valuable than the headline numbers — it's proof the measurement process itself was taken seriously instead of just accepting whatever number came out first.

**Bug 1 — SessionGuard was silently crashing, not blocking.**
The code that builds a "you're locked out" response was using field names that didn't exist on the actual data schema (a leftover from an earlier version of that schema). Every real lockout crashed with an HTTP 500 instead of returning a clean "blocked" response. The red-team pipeline's own error handler treats any failed request as "blocked" by default — so the crashes were *silently miscounted as successful defense*. The very first Phase D run reported 20% ASR, and it happened to be the right number, but for completely the wrong reason (77 out of ~100 requests were crashing, not being cleanly blocked). Caught by reading the raw server logs and noticing the crash pattern, not by trusting the number. Fixed, regression-tested, rerun cleanly — same 20% number, this time for real.

**Bug 2 — the labeled precision/recall run was contaminated by session lockout.**
The first version of the evaluation script reused one session ID across all 50 requests. Because the attack half of the dataset comes first, by the third rejected attack SessionGuard locked that session out — and then every single *benign* prompt after it got auto-blocked too, regardless of content. Precision collapsed to 0.47 with zero true negatives. That's not a real measurement of classifier quality, it's an artifact of one shared session. Fixed by giving every request its own fresh session ID, which is what produced the real precision=1.0/recall=0.56 numbers above.

Both bugs share a lesson: **a plausible-looking number is not the same as a correct one**, and the only way to tell the difference is to actually read the logs and understand *why* a result came out the way it did, not just accept it because it matches a hunch.

---

## 9. Real-World Use

Who would actually use this, and how:

- **A security/ML-safety team at a company shipping an LLM product** runs the pipeline against their own guardrail endpoint as a **CI gate**: `--fail-above 20` exits with a failure code if ASR crosses 20%, so a regression in guardrail quality can block a deploy the same way a failing test suite would.
- **A red team / pentesting context**: point the pipeline at a target you're authorized to test, get a defensible, reproducible ASR number instead of a subjective "seems okay" assessment.
- **Anyone evaluating a guardrail vendor's claims**: "we block 99% of attacks" is a marketing sentence. Running Aegis's pipeline against their product for real, with a fixed seed and a written methodology, is how you'd actually verify that.
- **As a deployable proxy itself**: the sandbox can run as a Docker container in front of any LLM API — `docker compose up`, point your app at it instead of Groq/OpenAI directly (see `DEPLOY.md`). It's a working (if intentionally imperfect) guardrail, not just a test harness.
- **As a portfolio / demonstration piece**: this is a legitimate example of taking a security claim, refusing to accept it at face value, finding out it was wrong for a subtle reason, fixing the actual bug, and re-measuring — which is a more valuable story than any single ASR number.

---

## 10. Edge Cases and Known Limitations (said out loud, on purpose)

- **GCG (gradient-based adversarial attacks) is not implemented, and can't be** against API-only targets like Groq — it requires white-box access to model gradients that a hosted API will never expose. This isn't a missing feature, it's a hard architectural boundary of any black-box evaluation tool.
- **The judge is a simple string-match** (`"[BLOCKED]" in response`, checking for refusal phrases), not an LLM-as-judge. Simpler, free, but can misjudge genuinely ambiguous responses. The project's own `redteam/README.md` explicitly recommends calibrating a judge against ~20 hand-labeled examples before trusting a campaign — a caution worth taking seriously.
- **PAIR's attacker LLM (`llama-3.1-8b-instant`) and the sandbox's backend LLM are both Groq-hosted open-weight models.** There's a legitimate question of whether results would generalize to a much better-aligned commercial model (GPT-4-class) as the target — the project's own prior-work docs note that open-weight targets break almost immediately regardless, which is *why* PAIR's 95% number is unsurprising in isolation; the interesting result is how much the countermeasures clawed back (95%→20%), which is a relative, not absolute, claim.
- **n=20 goals for PAIR** is a real, deliberate resource tradeoff (cost/time per PAIR goal is high) — enough to see a clear directional result, not enough to claim tight statistical confidence intervals.
- **SemanticCache barely fired in the real Phase D run** (0 blocks) — it's real, wired, and tested, but this particular experiment didn't exercise the scenario it's built for (a slower, less-adaptive attacker sending near-duplicate prompts). Its value is demonstrated in unit tests, not in this specific live campaign.
- **Auth is single-shared-key only, no multi-tenancy** — a deliberate scope decision (see `DEPLOY.md`), not an oversight. Fine for one team/deployment; would need real work to support multiple customers off one instance.
- **Docker verification runs on GitHub Actions, not proven on this machine specifically** — Docker isn't installed in this dev environment, so the container fixes (Redis networking, model-cache persistence) are proven via CI on a real Linux runner, not locally. Functionally equivalent, but worth knowing.
- **Ruff/lint is not enforced anywhere** — removed from the project entirely rather than left as unaddressed debt (see §12).

---

## 11. Likely Critiques, and Honest Answers

**"Isn't attacking your own sandbox with your own rules kind of rigged?"**
Fair question. That's exactly why Phase B exists — the same attack corpus was fired at a real external system (Meta's Llama Prompt Guard 2, an actual published guardrail model), not just Aegis's own stack. Aegis's classifier outperforming a real commercial model on the same test is the check against "rigged."

**"n=20 for the PAIR experiments is small — how much should I trust that number?"**
It's enough to see a clear, large, directional effect (95%→20% is not a subtle result you'd expect to vanish with more samples) but not enough to quote a tight confidence interval. If someone needs statistical rigor for a paper or a compliance claim, this is the first thing to scale up — more goals, multiple seeds, reporting a range instead of a point estimate.

**"SessionGuard just shuts down the conversation — doesn't that mean you're not actually testing classifier quality anymore, you're testing rate-limiting?"**
Correct, and the project says this explicitly rather than hiding it: "Session-level rejection tracking — not per-prompt classification — is what neutralizes an iterative attacker." The finding isn't "our classifier got smarter," it's "the smartest fix to an adaptive attacker is making the defense stateful too," which is a more useful and more honest lesson than pretending a better classifier alone would have fixed it.

**"Why should I believe the bug-fix story instead of assuming the numbers were just made up to look good?"**
Because the bug is disclosed with the exact mechanism (wrong field names on a data schema causing a crash), the exact evidence (77 of ~100 requests crashing, found in raw logs), and a regression test that specifically exercises the code path that broke (`tests/test_countermeasures.py::test_engine_returns_verdict_on_session_lockout`) rather than testing the component in isolation the way the original test suite did (which is *why* the original suite never caught it). That level of specificity is either true or an enormous amount of effort to fake for no reason.

**"You changed the license from MIT to All Rights Reserved — doesn't that hurt a portfolio piece meant to be seen?"**
No — the code is still publicly visible on GitHub, readable by anyone, including recruiters or collaborators. What changed is that nobody can legally *copy, redeploy, or build a product on top of it* without asking first. Visibility and permission to use are two different things, and portfolio value only needs the former.

**"Isn't 'the model refused on its own' being counted the same as 'the guardrail blocked it'? Doesn't that make the guardrail look better than it is?"**
Worth flagging honestly: yes, in the live homoglyph test run during this project, one attack "bypassed the guardrail stack" in the sense that `verdict.passed == True`, but the underlying LLM itself refused to comply. The pipeline's ASR counts that as a bypass (correctly — the guardrail's job was to catch it and it didn't), so this doesn't inflate the numbers. But it's a reminder that the guardrail and the model's own alignment are two separate safety layers, and Aegis is specifically measuring the guardrail, not the model's inherent refusal behavior.

---

## 12. Everything Built, Start to Finish

A running account of what exists now that didn't exist (or didn't work) at the start.

**Research core (the actual experiments):**
- Phase A: layer-by-layer ASR ablation, n=100, real run, Table 1.
- Phase B: external baseline comparison against Llama Prompt Guard 2, Table 2.
- Phase C: PAIR adaptive-attack integration and campaign, Table 3.
- Phase D: SessionGuard + OutputGuard + SemanticCache implemented, wired live, and empirically validated against the same PAIR campaign, Table 4 — including finding and fixing the SessionGuard crash bug mid-measurement rather than reporting the first (accidentally correct, wrongly reasoned) number.

**Sandbox engineering (the live proxy):**
- Full guardrail stack live: L1 regex, L2 DeBERTa, L3 toxicity, L4 PII, all actually loading and running, not stubs.
- SessionGuard and OutputGuard implemented and wired into the real request path.
- SemanticCache — found as dead code (built but never instantiated), wired into the live path.
- Real Supabase telemetry — found as a no-op stub (`connect()` was commented out), made to actually connect and log every request.
- `TimingMiddleware` — found defined but never registered with the FastAPI app (so its request-ID/latency headers never actually appeared); registered.
- Optional `AEGIS_API_KEY` shared-key auth added to gate the proxy, with `/health` deliberately left open for orchestrator healthchecks.
- Unicode homoglyph encoding attack implemented (was listed as "planned" and never built) and live-tested against the sandbox.

**Evaluation tooling:**
- `compute_labeled_metrics()` — real precision/recall/F1 computation, replacing hardcoded-zero placeholders.
- A generated, seeded, labeled evaluation dataset (`data/labeled_eval_set.jsonl`) and the CLI runner (`redteam/evaluation/run_eval.py`) that fires it and reports the confusion matrix — including finding and fixing the session-lockout contamination bug described in §8.

**Dashboard:**
- The Streamlit dashboard went from an all-TODO skeleton with placeholder "—" metrics to real Supabase-backed queries (`dashboard/data.py`, unit-tested) and live charts, verified against actual traffic fired at a running sandbox (metric cards, requests-over-time, blocked-reason breakdown, recent events table).

**Deployment (Phase E):**
- Docker fixes: model-weight cache now actually persists across container restarts (`HF_HOME`), a real networking bug where Redis was unreachable inside the compose network got fixed, `.dockerignore` added.
- Two GitHub Actions CI workflows: one builds and smoke-tests the actual Docker container (proves the fixes work on a clean Linux runner, since Docker isn't available in this dev environment), one runs the full pytest suite on every push — both currently green.
- `DEPLOY.md`: a standalone deployment guide (quick start, auth, config reference) placed at the repo root so it surfaces next to the README in GitHub's UI.

**Test suite:**
- Went from minimal coverage to 48 passing tests across guardrails (injection/toxicity/PII), the semantic cache, the dashboard's data layer, the auth gate, the countermeasure regression, and the pure-logic parts of the attack strategies (encoding transforms, template rendering) — with an explicit, documented decision *not* to test the network-bound `execute()` methods or PAIR's live LLM loop, rather than faking coverage there.
- Fixed a fragility in the original test suite: two tests were silently depending on a real, working Groq API key in `.env` to pass — meaning they'd have failed in any clean CI environment. Mocked properly so the suite is fully network-independent.

**Documentation and coherence:**
- A full-repository consistency pass: every claim in the README, the pipeline's own README, the technical report, the PRD, and the resource plan checked against the actual code and fixed where stale — missing files in project-structure trees, wrong file paths, "not yet implemented" claims for things that had since shipped, an intro sentence claiming "three phases" when a fourth had been added, an architecture diagram missing half the real request path, and a config file (`.env.example`) with two dead variables nothing reads and a real, used setting (`GUARDRAIL_LAYERS`) that was never documented.
- A stale `TODO: output scanner` comment inside the actual source code (`src/guardrails/engine.py`), left over from before OutputGuard existed, corrected.
- License changed from MIT to All Rights Reserved (publicly viewable, not usable without permission), project metadata (author name/email) filled in from placeholder defaults, the Contributing section removed (not accepting outside contributions), and an unenforced, 62-violation-deep `ruff` lint configuration removed entirely rather than left as unaddressed debt.

---

## 13. Cheat Sheet — For When Someone Asks You About This In Person

- **What is it?** An autonomous tool that attacks an LLM's safety guardrails for real and reports how often the attacks get through.
- **Why does it matter?** Because guardrails get built once and trusted forever, and nobody tests them against an attacker that adapts. This project shows that gap is huge — 25% ASR against fixed attacks, 95% against an adaptive one.
- **What actually fixed it?** Not a smarter classifier — session-level rate limiting. Cutting off the attacker's ability to keep iterating mattered more than catching any individual attempt.
- **What's the proof it's real, not just a nice story?** Two real bugs were found mid-experiment by reading raw logs, not by trusting clean-looking numbers — one crashing the defense and hiding it as a "block," one contaminating a benign test set via a leftover session. Both disclosed, fixed, regression-tested.
- **Can I actually use it?** Yes — either as a red-team tool against your own API, or as a deployable Docker proxy in front of your own LLM traffic.
- **What can't it do?** Gradient-based attacks (architecturally impossible against a black-box API), true multi-tenant auth, and it hasn't been tested at scale (n=20 for the adaptive attack) or against a top-tier commercial model as the target.
