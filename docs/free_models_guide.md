# OmniRoute Free Models Guide

### Truly Free Models (Unlimited or generous free tier)

| Priority | Model ID                        | Provider   | Notes                          |
|----------|---------------------------------|------------|--------------------------------|
| 1        | `auto/coding:free`              | OmniRoute  | Auto-picks healthy free models |
| 2        | `auto/best-coding`              | OmniRoute  | Broader free pool              |
| 3        | `agy/gemini-2.5-flash`          | Antigravity| Fast free fallback (if healthy)|
| 4        | `agy/gemini-3.6-flash-high`     | Antigravity| Another fast free option       |

---

### Trial / Credit-Based Models

These models are free to start, but **run on a limited credit system**. Once your initial credits are exhausted, you will drop to a heavily restricted daily allowance unless you subscribe.

| Model ID                        | Provider   | Notes                          |
|---------------------------------|------------|--------------------------------|
| `if/kimi-k3`                    | Qoder      | Premium coding model (consumes credits fast) |
| `if/qwen3.8-max-preview`        | Qoder      | Premium general + coding (consumes credits)  |
| `if/qwen3.7-max`                | Qoder      | Solid alternative (consumes credits)         |

---

### Models to Avoid (for free use)

| Model ID                  | Why to avoid                      |
|---------------------------|-----------------------------------|
| `cc/claude-opus-4-8`      | Requires paid Claude Code         |
| `claude-fable-5`          | Requires paid Claude Code         |
| `gh/gpt-5.6-sol`          | Requires paid Codex / Copilot     |
| `cx/gpt-5.5`              | Requires paid Codex               |
| `nvidia/z-ai/glm-5.2`     | Currently rate-limited / queueing |
| Heavy `agy/claude-*`      | Often throttled on free tier      |

---

### Quick Setup Reminder

1. Connect **Qoder** in the dashboard (most important free provider).
2. In Zed, select `if/kimi-k3` or `if/qwen3.8-max-preview`.
3. Keep `auto/coding:free` as a reliable fallback.
