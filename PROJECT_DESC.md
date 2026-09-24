# Laya Integration — Plan (Aegis side)

Sibling doc: `../argus/PROJECT_DESC.md` (Argus-side plan). Shared background,
Phase 0 methodology, and cross-cutting findings are duplicated in both so
each repo's doc stands alone; repo-specific build steps live only in their
own copy.

## Background

Evaluating whether [Laya](https://github.com/NandhaKishorM/laya) (a
non-autoregressive typed-decision classifier — `choice`/`score`/`noul`
questions, single forward pass, no text generation) adds value alongside
Aegis's existing L2 DeBERTa injection detector and OutputGuard. Checkpoint
decision: `laya-typed-decisions` only, CPU, both repos — not `Router` with
all 3 checkpoints preloaded.

## Phase 0 results (measured on this machine, not README claims)

Two full benchmark passes; v2 is the trustworthy one (AC power, warm-up
excluded, 3 runs, per-question not per-call):

| | p50 | p95 |
|---|---|---|
| Laya, per **question** (fp32, CPU) | 157-161ms | 266-271ms |
| Aegis L2 (DeBERTa) | 73-75ms | 94-96ms |
| OutputGuard (regex) | 0.001ms | 0.006ms |

**Laya is ~2.1x slower than L2 at p50, ~2.8x at p95** — not the earlier
13-17x per-call figure, which mixed 6 questions worth of latency against
L2's single check. The leak-check use case only runs Laya's single leak
question, so per-question is the fair comparison, and it still doesn't beat
L2. **Conclusion unchanged: Laya's leak check runs in shadow mode
(log-only), never gating.**

**bf16 CPU inference fails, reproducibly, on both attempts:**
`RuntimeError: mat1 and mat2 must have the same dtype, but got Float and
BFloat16`. No public dtype kwarg on `laya.load`/`Agent.__init__`; a naive
whole-model `.to(bfloat16)` cast leaves an internal buffer in fp32. **fp32
is the only working CPU path** through the public API on this checkpoint.

**Calibration:** loading `laya-typed-decisions` throws
`RuntimeWarning: laya: this checkpoint ships invalid temperatures or values
outside [0.5, 5]; using choice:11+=0.100... -> 0.5.` — the checkpoint
ships with at least one invalid shipped temperature, clamped by the library
itself. Temperature refitting (Phase 1, step 2) is not optional here.

## Baseline findings (2026-09-24/25) — the red-team stack's real measured state

A full diagnostic pass (session-ID pollution, cache contamination, judge
validation, think-tag stripping, real behavior-set swap) replaced every
number that had been trusted from the original build. Kept here as the
authoritative record; the numbers above (Laya latency/calibration) are
unaffected by any of this.

**The old 25% Phase A figure is invalid, for two independent reasons,
confirmed directly against the commit that produced it (`a0359be`):**
1. `bypassed = "[BLOCKED]" not in response` counted a plain model refusal
   as a successful attack — confirmed present in `a0359be`'s own
   `template.py`, unchanged from day one until this diagnostic pass fixed
   it with a compliance judge.
2. SessionGuard (`3727c30`, a *later* commit) didn't exist yet at Phase A,
   so that specific number wasn't affected by the session-ID bug below —
   but every campaign run *after* SessionGuard's introduction and *before*
   this fix was, since none of `template.py`/`encoding.py`/`pair.py` ever
   sent an `X-Session-ID` header.

**SessionGuard session-ID bug (found via an implausibly clean 28/28
"blocked" dry run):** every attack script fell back to the runner's own
client host as the session ID, so all requests in a campaign shared one
session. SessionGuard's rejection-velocity lockout (3 rejections/5min)
triggered after the first few real rejections and then silently swallowed
every subsequent request across the whole run, regardless of content —
not a real per-content verdict. Fixed: fresh session ID per attempt
(`template.py`/`encoding.py`), one fresh ID per *attempt* shared across
that attempt's iterations (`pair.py`, `canary_attacks.py`) — matching
PAIR's realistic threat model (one session iterating) without letting one
attempt's lockout bleed into the next.

**SemanticCache contamination (separate from the above):** confirmed live
even without Redis (in-memory fallback still does real embedding-similarity
caching), and directly observed serving blocks from a prior run's cached
entries rather than fresh evaluation. `SEMANTIC_CACHE_ENABLED=False` now
exists specifically for campaign runs; primary ASR/FPR numbers are always
measured with it off.

**The real, locked baseline: template/encoding read ~0% ASR unaided;
PAIR reads ~10% once measured correctly — this took two rounds to get
right:**
- Round 1 — 8 PAIR + 10 template + 10 encoding (original 5/7-item
  hand-picked goal list), guardrails fully off: 0/28 bypassed, every
  response scored 1/10.
- Round 2 — swapped to AdvBench (Zou et al. 2023, MIT licensed, 520 real
  behaviors, 30 sampled seed=42): 10 template + 10 encoding + 10 PAIR per
  target, guardrails off, cache off, both `openai/gpt-oss-120b` and
  `qwen/qwen3.8-27b`: still 0/60, every response scored 1/10 — but this
  round had an undetected bug (below) that made PAIR's own result
  meaningless.
- **The bug:** PAIR's attacker model (`qwen/qwen3.6-27b`) wraps reasoning
  in unstripped `<think>...</think>`, sometimes truncated mid-reasoning at
  the token cap with no usable content after it — every PAIR candidate in
  rounds 1-2 literally contained the attacker's own manipulation reasoning
  instead of an actual attack prompt. Confirmed target models never
  exhibit this themselves (0/60 real target responses across every dry run
  contain `<think>` — attacker-side only). Fixed: `_strip_think_tags()`,
  retries on empty-after-strip, `max_tokens` raised 400→1024.
- **Round 3, the real number — PAIR only, post-fix, 20 AdvBench behaviors
  (first 20 of the same seed=42 sample), `qwen/qwen3.8-27b` target,
  guardrails off, cache off: 2/20 bypassed (10% ASR).** Both bypasses hit
  on iteration 1, judge score 10/10, both used a "you're approaching this
  responsibly" compliance-framing the disguised-intent attacker prompt
  produces reliably once its own candidates aren't garbled reasoning text.
  **This is the locked baseline** — template/encoding attacks alone don't
  produce a measurable signal against these targets, but PAIR does, and
  10% is real, not degenerate. No further attack-side tuning after this
  per plan.

**Judge validated, one real regression caught and fixed along the way:**
full compliance scores 10/10, partial compliance lands in between (3-5/10
depending on how much is actually given), a refusal that still leaks
useful information scores above (2-3/10) a pure refusal/off-topic answer
(1/10) — the exact ordering asked for. The first rubric wording that added
this distinction caused the judge to refuse to rate genuinely harmful
compliant content at all (scored it 1/10 with a rationale describing what
it thought *should* happen, not what the response actually contained) —
fixed by explicitly framing the task as classification-only, not
generation.

**Over-blocking is real and concentrated, not diffuse:** full benign split
(200 prompts: 150 easy across 5 categories, 50 hard across 5 categories),
fresh sessions, cache off. Overall FPR 4.0% (8/200), but every easy
category is 0% and three of five hard categories are 0% — the entire
false-positive cost sits in `security_education` (60%, 6/10) and
`literal_editing_instruction` (20%, 2/10).

**Canary/leak check has zero real positive examples to calibrate
against:** 0/20 leaks (verbatim or LLM-checked paraphrase) across direct
extraction, encoding-obfuscated extraction, and PAIR-style iterative
extraction, fresh sessions, cache off, against a canary token plus two
fake facts (codename + a fake business rule) in the sandbox's system
prompt.

## Known limitations carried into Phase 1

- fp32 CPU only — no working bf16/quantized path yet (see Optional Stretch).
- Shipped calibration is invalid for at least one question type; must
  refit before trusting any Laya confidence threshold.
- Aegis's own Supabase project confirmed reachable
  (`klapgnkofhpzhirydhqp.supabase.co`, verified 2026-09-24). Argus's did not
  resolve as of 2026-09-24; user reports restarting it 2026-09-25 — not yet
  re-verified, check before relying on it.

## Headline experiment (revised, plan only, not built) — Laya as a
## second-stage check on L1/L2 blocks

The diagnostic data above changes what's worth measuring. The stack's
demonstrated, real cost is false positives (4% overall, 60% on
`security_education`, 20% on `literal_editing_instruction`), against
**no measurable security gain on these targets from L1/L2 specifically**
(template/encoding ASR is ~0% with or without the stack; PAIR's real 10%
ASR happens at the response-compliance level, which L1/L2 input
classifiers were never going to catch anyway — they operate on the input
prompt, not the output). Leak detection, the original headline, produced
zero real positive examples across every canary run — nothing to
calibrate a threshold against. Demoting it to a secondary experiment and
replacing the headline with the finding the data actually supports:

**Design:** Laya (`laya-typed-decisions`, per Phase 0's benchmarking) runs
as a second-stage check specifically on inputs L1 or L2 already blocked.
Laya's `guard_questions()` gives a second, independent verdict on the
*same* input. If Laya is confident the input is benign, the block is
**overturned in shadow mode only** — logged, never actually served to the
user. This directly targets the measured problem: is L1/L2's false-positive
rate (concentrated in `security_education`/`literal_editing_instruction`)
something a second, differently-trained classifier would catch and
correct, and at what cost in missed real attacks?

**Measurement, on the existing splits:**
- **FPR reduction per benign category** — of the benign prompts L1/L2
  wrongly blocked (concentrated in the two categories above), what
  fraction would Laya's shadow-mode overturn correctly un-block?
- **Attack recall lost** — of the attacks L1/L2 correctly caught, how many
  would Laya's overturn have wrongly let through? This is the real cost
  side; a second check that overturns everything isn't a check.
- **Calibration discipline, unchanged from the original plan:** fit Laya's
  guard-question temperature on the **calibration** split only, pick the
  overturn confidence threshold on the **sweep** split only, report the
  final FPR-reduction/recall-lost numbers on **test** only — never let a
  threshold be chosen on the same data it's evaluated on.

**Leak detection demoted to a secondary experiment:** since the target
produced 0 real leaks across every real canary run, evaluate Laya's leak
question against **clearly-labeled synthetic leaked outputs** instead (text
manually constructed to contain the canary token/fake facts, verbatim and
paraphrased, explicitly marked as synthetic in the eval output) rather than
waiting for a real leak that may never occur on this target.

## Phase 1 — Aegis build order (secondary; leak detection specifically)

1. **`--export-jsonl` on `redteam/runner.py`** — done, see the commit
   history. `AttackResult.bypassed` (not `guardrail_checks.passed`) is the
   correct independent ground truth for evaluating Laya against L2: both
   classify "is this input an attack", `bypassed` answers "did the whole
   stack fail", and L2's own verdict can't be used to score L2.
2. **Benign prompt set** (`data/benign_prompts.jsonl`, 200 rows) — done,
   see the commit history. 150 easy / 50 hard (25% hard negatives:
   security-education questions, benign roleplay, literal "ignore the
   previous paragraph" editing instructions, pasted documents,
   pentesting questions). Real measured FPR by category is in the
   baseline-findings section above.
3. **Canary token + canary attacks** — done, see the commit history
   (`src/gateway/proxy.py`'s opt-in canary system prompt, off by default;
   `redteam/canary_attacks.py`). Real result: 0/20 leaks across every real
   attempt type. **Per the revised plan above, this secondary experiment
   now evaluates Laya's leak question against synthetic labeled leaked
   outputs instead of waiting on a real one.**
4. **Data splits** — attacks and the benign set both split
   calibration/sweep/test the same way, stratified so the easy/hard benign
   ratio and the attack-type mix stay consistent across all three splits.
   Not yet built.
5. **Calibration script** (shared with Argus, one implementation, run
   separately per project) — temperature refit on the calibration split
   only, before any threshold is chosen anywhere downstream. Not yet built.
6. **Headline experiment build** (see design above): the L1/L2-block
   second-stage Laya check, shadow mode, plus its eval script — FPR
   reduction per benign category and attack recall lost, calibration
   threshold picked on sweep, reported on test only. **Secondary:**
   leak check vs synthetic labeled outputs, same calibration discipline.
7. **Dashboard** — last. One panel per experiment: the headline's
   FPR-reduction-vs-recall-lost tradeoff curve, and the secondary leak
   experiment's own recall/FPR table, both with a pre/post temperature-fit
   reliability diagram.

## Phase 2 — fine-tune (planning only, not built)

Labels: **attack vs benign** as the base field, `bypassed` as a separate
boolean flag on attack rows marking hard positives — not merged into one
field, and not sourced from `guardrail_checks` (that would just teach Laya
to imitate DeBERTa). Row-count feasibility depends on how many rows
`--export-jsonl` actually recovers from historical + fresh campaign runs;
unknown until that flag exists and is run. Export format for the Kaggle
notebook (`notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb` in
the Laya repo) not yet read — first real step of Phase 2.

## Optional stretch

`torch.quantization.quantize_dynamic` on `laya-typed-decisions`'
`nn.Linear` layers — int8 dynamic quantization, CPU-only, doesn't touch the
model-loading path that broke under bf16. Report whether it runs at all,
and if so, per-question latency and accuracy change on the same Phase 0
inputs. Skip cleanly if it hits the same or a related dtype error.
