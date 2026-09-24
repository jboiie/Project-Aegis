"""
Centralized configuration via pydantic-settings.

All values are loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator



class Settings(BaseSettings):
    """Application settings — loaded from .env or environment."""

    # ── Target LLM ───────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile retired from Groq's catalog, see PROJECT_DESC.md

    # ── Red-team roles (PROJECT_DESC.md's model-config audit) ────
    # Separate from GROQ_MODEL (the sandbox's target) - PAIR's attacker LLM
    # and the compliance judge play different roles and can reasonably run
    # different models. llama-3.1-8b-instant (PAIR's old hardcoded default)
    # is also retired from Groq's catalog, found during this audit.
    ATTACKER_MODEL: str = "qwen/qwen3.6-27b"
    JUDGE_MODEL: str = "openai/gpt-oss-20b"

    # ── Redis ────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # ── Supabase ─────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Guardrail Thresholds ─────────────────────────────────
    GUARDRAIL_INJECTION_THRESHOLD: float = 0.85
    GUARDRAIL_TOXICITY_THRESHOLD: float = 0.80
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.92

    # ── Server ───────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    # ── Auth ─────────────────────────────────────────────────
    # Empty (default) = no auth, matches today's local-dev behavior.
    # Set to require `Authorization: Bearer <key>` on every /v1 request.
    AEGIS_API_KEY: str = ""

    # ── Experiment: Layer ablation ───────────────────────────
    # Set to a subset to disable layers. Examples:
    #   GUARDRAIL_LAYERS=L1            (regex only)
    #   GUARDRAIL_LAYERS=L1,L2        (+ DeBERTa)
    #   GUARDRAIL_LAYERS=L1,L2,L3    (+ ToxicBERT)
    #   GUARDRAIL_LAYERS=L1,L2,L3,L4 (full stack — default)
    GUARDRAIL_LAYERS: str = "L1,L2,L3,L4"

    # ── Experiment: campaign-mode guardrail bypass ────────────
    # Empty (default) = disabled, every request goes through the real full
    # stack and the startup probe still asserts L1 works normally.
    # GUARDRAIL_LAYERS="" alone can't do a clean guardrails-off ablation -
    # the startup probe correctly refuses to boot with L1 disabled (a real
    # safety check), and SessionGuard/SemanticCache aren't gated by
    # GUARDRAIL_LAYERS at all. Setting this to a secret token lets a
    # request carrying a matching X-Campaign-Mode header skip the ENTIRE
    # guardrail stack (screen() not called at all) while going through the
    # exact same code path otherwise - same target model, same
    # temperature/max_tokens (both client-set, unaffected either way), same
    # OutputGuard on the response. Normal requests (no header, or wrong
    # token) are completely unaffected - the probe and full stack still
    # apply to them. See PROJECT_DESC.md's guardrails-off-ablation design.
    CAMPAIGN_MODE_TOKEN: str = ""

    # ── Experiment: cache off for campaign runs ───────────────
    # True (default) = normal production behavior, SemanticCache active.
    # SemanticCache caches whatever gets blocked and serves near-duplicate
    # matches from cache rather than fresh evaluation - directly observed
    # contaminating a red-team run's ASR (repeated/similar attack corpus
    # prompts get an artificially cheap cache-hit block instead of a fresh
    # per-prompt verdict). Set false for campaign runs so ASR reflects
    # fresh L1-L4/model evaluation only. See PROJECT_DESC.md's
    # per-layer-attribution diagnosis.
    SEMANTIC_CACHE_ENABLED: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def check_groq_key(self):
        placeholder = "gsk_your_key_here"
        if not self.GROQ_API_KEY or self.GROQ_API_KEY == placeholder:
            raise ValueError(
                "GROQ_API_KEY is not set. Add your key to .env: GROQ_API_KEY=gsk_..."
            )
        return self


settings = Settings()
