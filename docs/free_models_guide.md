# OmniRoute Free Models Guide (Independently Verified)

The landscape of "free" AI models is full of traps, trial credits, and rate limits. This guide classifies models and providers into exact tiers based on their **actual billing mechanics**.

---

## 1. Zero-Setup "Truly Free" Models (Recommended)

These require **no API keys** and **no credit cards**. They are managed via OAuth or auto-tokens and provide the most seamless free experience in tools like Zed.

| Priority | Model ID                        | Provider    | Notes |
|----------|---------------------------------|-------------|-------|
| 1        | `auto/coding:free`              | OmniRoute   | Automatically pools all healthy free models to bypass rate limits. |
| 2        | `auto/best-coding`              | OmniRoute   | Broader routing pool. |
| 3        | `agy/gemini-2.5-flash`          | Antigravity | Extremely fast, reliable fallback (when healthy). |
| 4        | `agy/gemini-3.6-flash-high`     | Antigravity | Another solid free fallback. |

---

## 2. "Bring Your Own Key" (BYOK) Perpetual Free APIs

These providers require you to sign up for an API key, but they offer **generous, permanent daily/minute free tiers** without requiring a payment method. Highly recommended to add to your OmniRoute setup for maximum resilience.

| Provider | Model Families | Free Tier Limits (Approx) | Signup URL |
|----------|----------------|---------------------------|------------|
| **Groq** | Llama 3, Mixtral | 30 RPM, 30,000 TPM (Resets every minute) | console.groq.com |
| **Cerebras** | Llama 3 | 5 RPM, 30,000 TPM, 1M Tokens/Day (Resets daily) | cloud.cerebras.ai |
| **Mistral** | Mistral Nemo, 8x7B | 1 RPS, ~500k TPM ("Experiment Tier") | console.mistral.ai |

*How to use:* Get your key, then set `OMNIROUTE_GROQ_KEY=your_key` and run the `omniroute_full_setup.py` script.

---

## 3. The "Free Trial" Credit Traps

These providers are heavily marketed as free, but they operate on a **limited credit system**. You will get a generous initial burst, but once exhausted, you will hit a hard paywall or be severely restricted.

| Provider / Model ID | Notes on Limitations |
|---------------------|----------------------|
| **Qoder** (`if/kimi-k3`, `qwen3.x`) | 14-day trial with 300 credits. Premium models burn 1.0x-1.6x credits per call. Once exhausted, you drop to highly restricted "Lite" mode unless you pay $20/mo. |
| **DeepSeek** | Initial free API credits upon signup, then strictly pay-as-you-go. |
| **Together AI** | ~$5 in initial free credits, then pay-as-you-go. |
| **SiliconFlow** | Initial free trial credits, then pay-as-you-go. |

---

## 4. Strictly Paid (Avoid if looking for free)

These IDs often show up in client configs but require active paid subscriptions.

| Model ID | Required Subscription |
|----------|-----------------------|
| `cc/claude-opus-4-8` | Claude Pro / Team ($20+/mo) |
| `claude-fable-5` | Claude Pro / Team ($20+/mo) |
| `gh/gpt-5.6-sol` | GitHub Copilot ($10/mo) |
| `cx/gpt-5.5` | OpenAI / Codex paid tier |
| `nvidia/z-ai/glm-5.2` | Currently severely rate-limited on free NIM endpoints (often times out). |
