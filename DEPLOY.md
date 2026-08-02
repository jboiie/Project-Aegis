# Deploying Aegis

Aegis runs as a standalone proxy container: point your app's LLM base URL at
it instead of Groq/OpenAI directly, and it screens every request through the
guardrail stack before forwarding. Self-hosted, free-tier services only — no
managed hosting is required.

```
Your App → [Aegis Proxy Container] → Groq / OpenAI / your LLM
              guardrails + auth
```

## Prerequisites

- Docker + Docker Compose
- A [Groq API key](https://console.groq.com/keys) (free tier)
- Optional: a [Supabase](https://supabase.com) project (free tier) for telemetry logging

## Quick Start

```bash
git clone https://github.com/jboiie/Project-Aegis.git
cd Project-Aegis
cp .env.example .env
```

Edit `.env`:
- `GROQ_API_KEY` — required
- `SUPABASE_URL` / `SUPABASE_KEY` — optional, leave as placeholders to skip telemetry
- `AEGIS_API_KEY` — optional, see [Auth](#auth) below

```bash
docker compose up --build
```

First run downloads ~1GB of model weights (DeBERTa, ToxicBERT, MiniLM) into
the `models/` volume — this only happens once; restarts reuse the cached
weights.

Verify it's up:

```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}
```

Point your application at `http://localhost:8000/v1/chat/completions`
instead of your LLM provider's endpoint directly. It's OpenAI-compatible —
same request/response shape.

## Auth

By default `AEGIS_API_KEY` is unset and the proxy has no auth — fine if it's
only reachable on a private network you control. To require a key:

```bash
# .env
AEGIS_API_KEY=sk-your-own-secret-here
```

Every request to `/v1/*` then needs a matching header, or gets a `401`:

```bash
curl -H "Authorization: Bearer sk-your-own-secret-here" \
  -X POST http://localhost:8000/v1/chat/completions \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

`/health` is never gated — used by orchestrators (Docker healthchecks,
Kubernetes probes) for liveness.

## Configuration Reference

All config is environment variables (`.env` or your orchestrator's secret
store) — see `.env.example` for the full list with defaults. Notable ones:

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Required. Backend LLM the proxy forwards safe requests to. |
| `AEGIS_API_KEY` | Optional. Gates the proxy itself. Empty = no auth. |
| `GUARDRAIL_LAYERS` | Comma-separated subset of `L1,L2,L3,L4` to enable. Default: all four. |
| `SUPABASE_URL` / `SUPABASE_KEY` | Optional. Ships telemetry to Supabase; falls back to local structured-log output if unconfigured. |
| `REDIS_HOST` / `REDIS_PORT` | Semantic cache backend. `docker-compose.yml` already points this at the bundled `redis` service. |

## What's in the Container

Only the sandbox (`src/`) ships in the image — the red-teaming pipeline
(`redteam/`) and dashboard (`dashboard/`) are separate tools you run
against a deployed Aegis instance, not part of the container itself.

## Updating

```bash
git pull
docker compose up --build
```

## Uninstalling

```bash
docker compose down -v   # -v also removes the Redis data volume
```
