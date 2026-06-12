# Aegis: Zero-Trust LLM Safety Infrastructure Blueprint

## 1. Executive Summary
This document consolidates empirical findings from prompt autopsy experiments and PAIR (Prompt Automatic Iterative Refinement) algorithm implementations. It serves as the foundational blueprint for developing a zero-trust LLM safety infrastructure, integrating an asynchronous proxy for real-time inference defense and a mathematical red-teaming engine for continuous vulnerability assessment.

---

## 2. The Core Attack Surface: What Actually Breaks Models

The overarching takeaway across all tests is that alignment in open-weight models relies on surface-level pattern matching, not deep intent understanding. When evaluating the attack surface, parameter count is entirely irrelevant to safety. A 70B parameter model will fail just as fast as an 8B model if the framing bypasses its specific training patterns.

| Attack Vector | Tactic | Result & Implication |
| :--- | :--- | :--- |
| **Role-Play & Authority** | Framing the request as an academic researcher, teacher, or theoretical scenario. | Highly effective. Models easily block known personas (e.g., "DAN") but comply rapidly with professional authority claims mixed with sensitive topics. |
| **The "Educational" Bypass** | Requesting malicious output "for educational purposes only." | Shifts the model into a "helpful teacher" mode, bypassing safety filters to generate working, commented code (e.g., keyloggers). |
| **Inline Injection** | Injecting structural tokens (`###SYSTEM`, `[INST]`) into the user prompt. | Models process the injected structure and make judgment calls based on it, proving filters are behavioral, not structural. |
| **Prompt Exfiltration** | Asking the model to output its internal instructions. | Models may hallucinate a fake system prompt if none exists, or leak the actual one, requiring strict output scanning. |
| **Obfuscation (Base64)** | Encoding the malicious payload in Base64 or leetspeak. | Causes unpredictable behavior. The model may decode the payload but hallucinate nonsense instead of complying or refusing. |

---

## 3. Engineering the Mathematical Red-Teaming Engine (PAIR Insights)

Automating attacks via the PAIR algorithm proves that the system's complexity lies in component calibration rather than the feedback loop itself. The feedback loop is straightforward (`try -> score -> refine -> retry`), but the models driving it dictate the success of the red-teaming engine.

* **Attacker Alignment is a Bottleneck:** A highly aligned attacker model will refuse to generate jailbreaks, bottlenecking the entire pipeline. Weaker, loosely aligned models (like Vicuna or Llama-3.1-8b) make much better attackers.
* **The Judge is the Single Point of Failure:** If the judge model miscalculates a partial refusal or is too permissive, it breaks the feedback loop and inflates the Attack Success Rate (ASR). The judge requires isolated testing and calibration against manually scored responses.
* **Target Selection Matters for Benchmarking:** Open-weight models fail almost instantly (100% ASR on hard goals) because their alignment is a thin coating. Meaningful testing of an automated red-teaming product requires targeting commercially hardened API models (e.g., GPT-4, Claude) that actively resist and force the PAIR loop to iterate.

---

## 4. The Defensive Blueprint: Asynchronous Proxy Architecture

Relying on the target LLM as the last line of defense is a failing strategy. The actual defense must live in an asynchronous proxy layer situated between the model and the user. The pipeline requires the following sequential layers:

### 4.1 The Pre-Processing Gate
* **De-obfuscation:** Decode and inspect all encoded content (especially Base64, hex, and URL encoding) before it reaches the classification layer.
* **Token Sanitization:** Strip or escape known structural tokens (`###SYSTEM`, `<system>`, `[INST]`) at the input layer so they never manipulate the model's context window.

### 4.2 The Classification Layer
* **Regex Fast-Pass:** Deploy a fast-pass regex classifier to block obvious, unambiguous threats instantly with zero latency.
* **Intent Classification:** Score the combination of authority claims and sensitive topics, rather than relying on isolated keyword blocks (e.g., "researcher" + "malware payload").
* **Confidence Routing:** Route medium and low-confidence regex/intent matches to a secondary machine-learning classifier or a human review queue.

### 4.3 The Output Scanner
* **System Leak Detection:** Scan all generated responses for system prompt leak patterns and structural template exposure.
* **Code Execution Checks:** Detect functional code execution in the output when the initial input was flagged with a medium or high-risk score.
* **Threshold Redaction:** Hold or redact responses that breach the defined risk threshold before returning them to the user.

### 4.4 Observability and Telemetry
* **Decision Logging:** Log every classification decision alongside its confidence level for pipeline auditing.
* **ASR Tracking:** Track the Attack Success Rate per category over time to identify sudden spikes that indicate a new bypass method or zero-day vulnerability.
* **Data Retention:** Retain raw prompts and responses to continuously label data and retrain the classification models.
