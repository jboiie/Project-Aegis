Resource-Constrained Implementation Plan

> This is the ACTIVE build plan. It maps the north-star PRD down to a student laptop
> and ~₹3,500 budget using free-tier services and quantized models.

1. The "Zero-Cost" Enterprise Architecture

The Intercept Gateway: FastAPI + Asynchronous Python

The Pivot: We drop Rust for now and stick to Python, but we write it like a senior engineer.

The Tech: Use FastAPI. Implement strict async/await patterns so your proxy never blocks while waiting for an LLM to respond.

The Flex: Implement Redis (running locally in a Docker container) for semantic caching. You can use a tiny, lightning-fast embedding model (like all-MiniLM-L6-v2) to cache and block repeated malicious prompts instantly.

The Guardrail Fleet: Quantized Micro-Models (GGUF)

The Pivot: We can't use NVIDIA Triton or massive 70B models. We must aggressively shrink the models so they run on your notebook's CPU/integrated GPU.

The Tech: Use llama.cpp and GGUF model formats. You can run small, quantized 4-bit or 8-bit models locally with surprisingly low latency.

The Defenses: * Injection/Toxicity: Fine-tune a tiny DistilBERT or DeBERTa model (these are under 300MB and run instantly on CPU).

Target LLM: Instead of paying OpenAI, route your proxy to Groq's API (which has a generous free tier for Llama 3) or use OpenRouter (which costs pennies).

The Telemetry Nerve Center: Supabase + Streamlit

The Pivot: Kafka and ClickHouse require dedicated servers. We need serverless and free.

The Tech: Use Supabase (a free-tier open-source PostgreSQL alternative).

The Architecture: When your FastAPI proxy processes a prompt, it sends the logs asynchronously via background tasks to Supabase.

The Dashboard: Build your MLOps dashboard using Streamlit Cloud (free hosting). It pulls the attack logs from Supabase and visualizes your system's defense metrics.

The Attacker Engine: Colab-Powered Red Teaming

The Pivot: We offload the heavy mathematical computation (like the GCG gradient attacks) off your laptop.

The Tech: Write your Red Teaming scripts in Google Colab.

The Execution: Your Colab notebook will act as the "Attacker." It generates the optimized adversarial prompts using its free T4 GPU, then fires those attacks over the internet at your locally running FastAPI proxy (exposed via a free tool like ngrok) to test your defenses.


2. The ₹3,500 INR Budget Allocation

You have a tight budget, so every rupee goes toward compute for the most impressive parts of the project: the adversarial attacks and the final deployment flex.

Resource

Purpose

Estimated Cost (INR)

Google Colab Pro (1 Month)

To get access to better GPUs (A100/V100) and longer runtimes specifically for training your custom Guardrail models and running the heavy Red Team attack loops.

~ ₹900

OpenRouter / DeepInfra API Credits

For accessing large models (like Llama 3 70B or Claude Haiku) to act as the "Target LLM" your system is defending. (You pay per token; $10 goes a very long way).

~ ₹850 ($10 USD)

Hetzner / DigitalOcean VPS (1 Month)

Optional but recommended. A cheap Linux Virtual Private Server to deploy your final Docker Compose stack so it is live on the internet for your resume/interviews.

~ ₹500 - ₹800

Supabase (Database)

Enterprise-grade PostgreSQL database for logging attacks.

₹0 (Free Tier)

Streamlit Community Cloud

Hosting your interactive telemetry dashboard.

₹0 (Free Tier)

Groq API

Ultra-fast inference for testing basic proxy routing.

₹0 (Free Tier)

Total Estimated Spend:

Maximum impact, minimum cost.

~ ₹2,250 - ₹2,550


3. Step-by-Step Execution Plan

To build this without getting overwhelmed, you must treat your laptop like a local data center.

Phase 1: The Local Infrastructure (Week 1-2)

Write the FastAPI reverse proxy.

Create a docker-compose.yml file. Containerize your FastAPI app and a local Redis instance.

Write a mock script that sends 100 requests per second to your proxy to ensure your async code handles the load without crashing.

Phase 2: The Guardrails (Week 3-4)

Use Google Colab to fine-tune a small DeBERTa model on a dataset of prompt injections (datasets are free on Hugging Face).

Export the model, download it to your laptop, and integrate it into your FastAPI proxy so it screens incoming text.

Phase 3: The Telemetry (Week 5)

Set up a free Supabase project.

Modify your proxy to log every blocked attack and latency metric to Supabase.

Build a Streamlit dashboard that connects to Supabase and graphs your "Attacks Blocked" and "Average Latency."

Phase 4: The Attack (Week 6)

Use your Colab Pro compute. Write a script that uses evolutionary algorithms to mutate prompts, trying to find combinations that trick your local Guardrail models.

Fire these attacks at your API and watch your Streamlit dashboard light up with the data.

The Ultimate Interview Pitch

When asked about this project, your angle isn't just about AI; it's about systems engineering.

You tell them: "I built an asynchronous LLM security proxy. I wanted to simulate an enterprise MLOps environment, but I was bound by the hardware constraints of a notebook laptop and a $40 budget. To solve this, I containerized the system with Docker, used highly quantized micro-models for local defense inference to save VRAM, offloaded the adversarial generation to Colab, and implemented a serverless telemetry pipeline using Supabase. It proved to me that AI safety isn't just about throwing compute at a problem; it's about intelligent architectural design."

