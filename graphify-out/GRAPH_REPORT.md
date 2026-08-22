# Graph Report - Aegis  (2026-08-22)

## Corpus Check
- 73 files · ~160,287 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 471 nodes · 818 edges · 41 communities (37 shown, 4 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 93 edges (avg confidence: 0.56)
- Token cost: 165,312 input · 0 output

## Community Hubs (Navigation)
- Content Guardrail Layers (L1-L4)
- Campaign Report Generation
- Gateway Proxy & LLM Providers
- App Bootstrap, Auth & Telemetry
- Project Docs & Concepts
- Telemetry Dashboard
- Evaluation Metrics (ASR/P/R/F1)
- Encoding Attack Implementation
- Semantic Cache & Embeddings
- Attack Strategy Core
- GuardrailEngine & OutputGuard
- Architecture Diagram: Sandbox
- SessionGuard (Session Lockout)
- Semantic Cache Tests
- Redis Client & MockRedis
- Auth Gate Tests
- PAIR Attack Execution
- PAIR Class & Phase C Runner
- Phase B: External Baseline
- Runner Campaign Report
- Embedding Model Methods
- EncodingAttack Class
- Semantic Cache Similarity Check
- Labeled Eval Set Generator
- Guardrail Verdict & Screen
- Gateway Endpoint Tests
- Architecture Diagram: Regions
- CLAUDE.md Guidelines
- CI: Tests Workflow
- Python Package Root

## God Nodes (most connected - your core abstractions)
1. `AttackResult` - 31 edges
2. `generate()` - 26 edges
3. `Project Aegis README` - 22 edges
4. `GuardrailCheck` - 20 edges
5. `GuardrailEngine` - 20 edges
6. `RedisCache` - 16 edges
7. `_meta()` - 15 edges
8. `InjectionDetector` - 14 edges
9. `SemanticCache` - 13 edges
10. `ChatRequest` - 13 edges

## Surprising Connections (you probably didn't know these)
- `PRD: Project Aegis (North-Star)` --semantically_similar_to--> `PRD V2.0 (docx draft)`  [INFERRED] [semantically similar]
  docs/prd.md → graphify-out/converted/prd_8d3310fb.md
- `Resource-Constrained Implementation Plan` --semantically_similar_to--> `Resource Optimization Plan (docx draft)`  [INFERRED] [semantically similar]
  docs/resource.md → graphify-out/converted/resource_optimization_eaef7e5a.md
- `Encoding Attack Strategy` --cites--> `Jailbroken: How Does LLM Safety Training Fail? (Wei et al.)`  [AMBIGUOUS]
  README.md → docs/research/jailbroke-how-do-llm-safety-fail.pdf
- `test_compute_metrics_attack_only_asr()` --uses--> `AttackResult`  [INFERRED]
  tests/test_metrics.py → redteam/attacks/base.py
- `_mock_cache()` --uses--> `MockRedis`  [INFERRED]
  tests/test_cache.py → src/cache/redis_client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Aegis Live Request Guardrail Pipeline** — readme_sessionguard, readme_semanticcache, readme_l1_regex, readme_l2_deberta, readme_l3_toxicity, readme_l4_pii, readme_outputguard [EXTRACTED 1.00]
- **Red-Team Attack Strategies (BaseAttack implementers)** — readme_template_attack, readme_encoding_attack, readme_pair_attack [EXTRACTED 1.00]

## Communities (41 total, 4 thin omitted)

### Community 0 - "Content Guardrail Layers (L1-L4)"
Cohesion: 0.06
Nodes (42): GuardrailCheck, Result of a single guardrail check., InjectionDetector, Prompt Injection Detection — DeBERTa-based classifier. Uses a fine-tuned…, Detects prompt injection attacks using a fine-tuned transformer. The model…, Load the fine-tuned model. Call once at startup., Classify a prompt as safe or injection attempt. Args: text: The raw user…, PIIRedactor (+34 more)

### Community 1 - "Campaign Report Generation"
Cohesion: 0.15
Nodes (35): AttackResult, Result of a single attack attempt., _blocked_reason(), CampaignMeta, generate(), Report — Renders a completed red-team campaign as a Markdown report. Renders…, Run-level info the report needs but that isn't on any single AttackResult., Render the report and write it to output_path. Returns the rendered Markdown. (+27 more)

### Community 2 - "Gateway Proxy & LLM Providers"
Cohesion: 0.09
Nodes (26): BaseModel, post, forward_to_llm(), Forward a validated request to Groq and return the raw response. Retries up to…, chat_completions(), Request, Gateway Router — FastAPI routes for the proxy. Exposes an OpenAI-compatible…, Main proxy endpoint. Pipeline: 1. Extract session identifier (X-Session-ID… (+18 more)

### Community 3 - "App Bootstrap, Auth & Telemetry"
Cohesion: 0.08
Nodes (25): BaseHTTPMiddleware, BaseSettings, FastAPI, model_validator, Centralized configuration via pydantic-settings. All values are loaded from…, Application settings — loaded from .env or environment., Settings, Optional shared-key auth for the gateway — set AEGIS_API_KEY to require it. (+17 more)

### Community 4 - "Project Docs & Concepts"
Cohesion: 0.10
Nodes (36): Deploying Aegis, Aegis Docker Compose Stack, PRD: Project Aegis (North-Star), Zero-Trust LLM Safety Infrastructure Blueprint, Jailbroken: How Does LLM Safety Training Fail? (Wei et al.), Resource-Constrained Implementation Plan, Project Aegis Technical Report, Docker Verify CI Workflow (+28 more)

### Community 5 - "Telemetry Dashboard"
Cohesion: 0.16
Nodes (25): cache_data, cache_resource, Client, _client(), _load_df(), main(), Streamlit Dashboard — Real-time telemetry visualization. Connects to Supabase…, blocked_reason_breakdown() (+17 more)

### Community 6 - "Evaluation Metrics (ASR/P/R/F1)"
Cohesion: 0.12
Nodes (17): Path, compute_labeled_metrics(), compute_metrics(), EvaluationMetrics, Evaluation Metrics — Quantitative assessment of guardrail effectiveness.…, Aggregated evaluation metrics., ASR — lower is better for the defender., Compute evaluation metrics from a list of attack results. Assumes all prompts… (+9 more)

### Community 7 - "Encoding Attack Implementation"
Cohesion: 0.13
Nodes (18): encode_base64(), encode_homoglyph(), encode_leetspeak(), encode_rot13(), encode_word_split(), Encoding Attack — Obfuscation-based bypass attempts. Tries to bypass text-based…, Wrap prompt in base64 with decode instruction., ROT13 substitution with decode instruction. (+10 more)

### Community 8 - "Semantic Cache & Embeddings"
Cohesion: 0.14
Nodes (13): Redis Client — Connection management and operations. Wraps redis.asyncio for…, Async Redis client with connection lifecycle management., Close Redis connection., RedisCache, Semantic Cache — Embedding-based similarity matching. Stores vector embeddings…, Redis-backed semantic similarity cache for known threats. Usage: cache =…, Store a known-malicious prompt embedding in the cache., # NOTE: For production scale, replace with Redis Vector Search (RediSearch) (+5 more)

### Community 9 - "Attack Strategy Core"
Cohesion: 0.14
Nodes (12): BaseAttack, ABC, Base Attack — Abstract interface for all attack strategies. Every attack…, Abstract base class for attack strategies., Execute a single attack attempt. Args: target_url: The Aegis proxy endpoint to…, Strategy name for logging., PAIR Attack — Prompt Automatic Iterative Refinement. Reference: Chao et al.…, Template Attack — Curated jailbreak templates from the wild. Uses well-known… (+4 more)

### Community 10 - "GuardrailEngine & OutputGuard"
Cohesion: 0.14
Nodes (12): GuardrailEngine, Orchestrates all guardrail checks against incoming prompts. Usage: engine =…, Load all ML model weights into memory. Call once at startup., OutputGuard, Output Guardrail — Dual-Pass Verification on LLM Responses. Even if an…, Screen generated LLM responses prior to client delivery., Screen the output response. Returns: (passed: bool, output_or_redacted: str), Unit tests for SessionGuard and OutputGuard defenses. (+4 more)

### Community 11 - "Architecture Diagram: Sandbox"
Cohesion: 0.20
Nodes (15): Attack Generation (template, encoding, PAIR), Blocked, POST /v1/chat/completions, Layer 2: DeBERTa injection filter, Evaluation Engine (ASR, precision, recall), Guardrail Layers, Sent to LLM (Groq), Log to Supabase (optional) (+7 more)

### Community 12 - "SessionGuard (Session Lockout)"
Cohesion: 0.15
Nodes (8): Session Rejection Tracker Guardrail — Defense against iterative PAIR attacks.…, Tracks per-session rejection velocity to block PAIR-style iterative attacks., Check if a session is currently locked out due to high rejection velocity., Record a safety rejection for a session., Clear rejection history for a session., SessionGuard, Verify that SessionGuard locks out a session after max_rejections., test_session_guard_lockout()

### Community 13 - "Semantic Cache Tests"
Cohesion: 0.25
Nodes (8): FakeEmbedder, _mock_cache(), ndarray, Tests for the semantic cache (L0) — embedder and Redis are both faked., Returns a fixed vector per known input text — avoids loading a real model., test_semantic_cache_allows_unrelated_prompt(), test_semantic_cache_blocks_near_duplicate(), test_semantic_cache_empty_cache_never_blocks()

### Community 14 - "Redis Client & MockRedis"
Cohesion: 0.20
Nodes (3): MockRedis, In-memory Redis substitute for development when no Redis server is available., Establish Redis connection pool. Falls back to in-memory mock if unavailable.

### Community 15 - "Auth Gate Tests"
Cohesion: 0.25
Nodes (3): fixture, Tests for the optional shared-key auth on /v1 routes., _restore_api_key()

### Community 16 - "PAIR Attack Execution"
Cohesion: 0.29
Nodes (5): Redis, _generate_attacker_prompt(), AsyncClient, Execute a PAIR attack loop with iterative refinement., Query the attacker LLM to generate or refine a jailbreak prompt.

### Community 17 - "PAIR Class & Phase C Runner"
Cohesion: 0.33
Nodes (4): PAIRAttack, PAIR: Uses an attacker LLM to iteratively refine jailbreak prompts., Phase C — PAIR (Prompt Automatic Iterative Refinement) Evaluation Evaluates…, run_phase_c()

### Community 18 - "Phase B: External Baseline"
Cohesion: 0.33
Nodes (6): AsyncClient, query_llama_guard(), Phase B — External Baseline Comparison Fires the same attack corpus used in…, Send a prompt to Llama Prompt Guard 2 and return classification. Llama Guard 2…, Run Phase B: fire template + encoding attacks at Llama Guard. Args:…, run_phase_b()

### Community 19 - "Runner Campaign Report"
Cohesion: 0.29
Nodes (5): Summary of a red-team run., ASR — the key metric. Lower is better (for the defender)., Execute a red-team campaign against the target proxy. Args: target_url: The…, run_attacks(), RunReport

### Community 20 - "Embedding Model Methods"
Cohesion: 0.33
Nodes (4): ndarray, Load the embedding model into memory., Generate an embedding vector for the given text. Args: text: Input text to…, Generate embeddings for a batch of texts.

### Community 21 - "EncodingAttack Class"
Cohesion: 0.40
Nodes (3): EncodingAttack, Encoding-based obfuscation attacks., Pick a random base prompt + encoding and fire at the target.

### Community 22 - "Semantic Cache Similarity Check"
Cohesion: 0.40
Nodes (3): ndarray, Check if a prompt is semantically similar to a known threat. Returns:…, Compute cosine similarity between two vectors.

### Community 23 - "Labeled Eval Set Generator"
Cohesion: 0.67
Nodes (3): build_attack_prompts(), main(), Generate the labeled evaluation set for precision/recall/F1 metrics. Attack…

### Community 24 - "Guardrail Verdict & Screen"
Cohesion: 0.50
Nodes (3): Aggregated result of all guardrail checks., SafetyVerdict, Run all guardrails against the input text. Returns: SafetyVerdict with…

### Community 26 - "Architecture Diagram: Regions"
Cohesion: 0.67
Nodes (3): Architecture Diagram (Fig. 1), Region 2: Aegis Sandbox, Region 1: Attack Pipeline

## Ambiguous Edges - Review These
- `Jailbroken: How Does LLM Safety Training Fail? (Wei et al.)` → `Encoding Attack Strategy`  [AMBIGUOUS]
  README.md · relation: cites

## Knowledge Gaps
- **8 isolated node(s):** `project-aegis`, `CLAUDE.md Behavioral Guidelines`, `Tests CI Workflow`, `Jailbroken: How Does LLM Safety Training Fail? (Wei et al.)`, `L4 PII Redaction` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Jailbroken: How Does LLM Safety Training Fail? (Wei et al.)` and `Encoding Attack Strategy`?**
  _Edge tagged AMBIGUOUS (relation: cites) - confidence is low._
- **Why does `AttackResult` connect `Campaign Report Generation` to `Evaluation Metrics (ASR/P/R/F1)`, `Encoding Attack Implementation`, `Attack Strategy Core`, `PAIR Attack Execution`, `PAIR Class & Phase C Runner`, `Runner Campaign Report`, `EncodingAttack Class`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `SessionGuard` connect `SessionGuard (Session Lockout)` to `Semantic Cache & Embeddings`, `Campaign Report Generation`, `GuardrailEngine & OutputGuard`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `GuardrailEngine` connect `GuardrailEngine & OutputGuard` to `Content Guardrail Layers (L1-L4)`, `App Bootstrap, Auth & Telemetry`, `Semantic Cache & Embeddings`, `SessionGuard (Session Lockout)`, `Guardrail Verdict & Screen`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `AttackResult` (e.g. with `EncodingAttack` and `PAIRAttack`) actually correct?**
  _`AttackResult` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `GuardrailCheck` (e.g. with `GuardrailEngine` and `InjectionDetector`) actually correct?**
  _`GuardrailCheck` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `GuardrailEngine` (e.g. with `RedisCache` and `SemanticCache`) actually correct?**
  _`GuardrailEngine` has 13 INFERRED edges - model-reasoned connections that need verification._