"""
Strategic probe: Find working paths to GPT frontier models and GLM-5.2.
Tests every possible provider/route for these specific models.
"""
import json, urllib.request, urllib.error, time

BASE = "http://localhost:20128/v1"
KEY = json.loads(open("config/secrets.json").read())["OMNIROUTE_API_KEY"]

# Every possible model name for GPT and GLM across all providers
targets = [
    # === GPT-5.6 / GPT-5 / GPT-4o variants ===
    # Codex (OAuth, was 429)
    ("codex/gpt-5.6-sol", "Codex OAuth"),
    ("codex/gpt-5", "Codex OAuth"),
    ("codex/gpt-5-turbo", "Codex OAuth"),
    ("codex/gpt-4o", "Codex OAuth"),
    ("codex/o3", "Codex o3"),
    ("codex/o4-mini", "Codex o4-mini"),
    # Amazon-Q (OAuth, was 500)
    ("amazon-q/gpt-5.6-sol", "Amazon-Q OAuth"),
    ("amazon-q/gpt-5", "Amazon-Q OAuth"),
    ("amazon-q/gpt-4o", "Amazon-Q OAuth"),
    # Kilocode (OAuth, was 401/timeout)
    ("kilocode/gpt-5.6-sol", "Kilocode OAuth"),
    ("kilocode/gpt-5", "Kilocode OAuth"),
    ("kilocode/gpt-4o", "Kilocode OAuth"),
    # OpenCode (API key, was 403)
    ("opencode/gpt-5.6-sol", "OpenCode apikey"),
    ("opencode/gpt-5", "OpenCode apikey"),
    ("opencode/gpt-4o", "OpenCode apikey"),
    # OpenRouter (free, was 401 on some)
    ("openrouter/free", "OpenRouter free"),
    ("openrouter/openrouter/free", "OpenRouter free alt"),
    # Auto/combo routing
    ("auto/coding:free", "Auto combo"),
    ("auto/best-coding", "Auto combo"),
    # XAI (was 400)
    ("xai/gpt-5.6-sol", "XAI"),
    # Blackbox (was 400)
    ("blackbox/gpt-5.6-sol", "Blackbox"),
    ("blackbox/gpt-4o", "Blackbox"),
    # Other providers that might route GPT
    ("agy/gpt-5.6-sol", "AGY"),
    ("agy/gpt-4o", "AGY"),
    ("antigravity/gpt-5.6-sol", "Antigravity"),
    ("antigravity/gpt-4o", "Antigravity"),
    ("nvidia/gpt-5.6-sol", "Nvidia"),
    ("nvidia/gpt-4o", "Nvidia"),
    ("sambanova/gpt-5.6-sol", "SambaNova"),
    ("novita/gpt-5.6-sol", "Novita"),
    ("novita/gpt-4o", "Novita"),
    ("deepinfra/gpt-5.6-sol", "DeepInfra"),
    ("together/gpt-5.6-sol", "Together"),
    ("groq/gpt-5.6-sol", "Groq"),
    ("fireworks/gpt-5.6-sol", "Fireworks"),
    ("mistral/gpt-5.6-sol", "Mistral"),
    ("cohere/gpt-5.6-sol", "Cohere"),

    # === GLM-5.2 / GLM-4 variants ===
    ("opencode/glm-5.2", "OpenCode apikey"),
    ("opencode/glm-4", "OpenCode apikey"),
    ("agy/glm-5.2", "AGY"),
    ("agy/glm-4", "AGY"),
    ("antigravity/glm-5.2", "Antigravity"),
    ("antigravity/glm-4", "Antigravity"),
    ("kilocode/glm-5.2", "Kilocode"),
    ("amazon-q/glm-5.2", "Amazon-Q"),
    ("codex/glm-5.2", "Codex"),
    ("nvidia/glm-5.2", "Nvidia"),
    ("nvidia/glm-4", "Nvidia"),
    ("sambanova/glm-5.2", "SambaNova"),
    ("novita/glm-5.2", "Novita"),
    ("deepinfra/glm-5.2", "DeepInfra"),
    ("together/glm-5.2", "Together"),
    ("openrouter/glm-5.2", "OpenRouter"),
    ("blackbox/glm-5.2", "Blackbox"),
    ("auto/glm-5.2", "Auto combo"),
    # Zhipu-specific
    ("zhipu/glm-5.2", "Zhipu direct"),
    ("zhipu/glm-4", "Zhipu direct"),
    ("alibaba/glm-5.2", "Alibaba"),
    ("baidu/glm-5.2", "Baidu"),
    ("siliconflow/glm-5.2", "SiliconFlow"),
    ("siliconflow/glm-4", "SiliconFlow"),
    ("kimi-coding/glm-5.2", "Kimi"),
    ("minimax/glm-5.2", "MiniMax"),
    ("moonshot/glm-5.2", "Moonshot"),
]

print(f"Strategic probe: {len(targets)} model/provider combinations")
print("Targeting: GPT frontier + GLM-5.2")
print(f"{'='*80}")

gpt_hits = []
glm_hits = []
fails = []

for model_id, source in targets:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=25)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        dt = time.time() - t0
        print(f"  OK   {model_id:40s} {dt:5.1f}s  [{source}]  {text[:40]}")

        if "glm" in model_id.lower():
            glm_hits.append((model_id, source, dt, text[:40]))
        else:
            gpt_hits.append((model_id, source, dt, text[:40]))
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        fails.append((model_id, source, f"HTTP {e.code}", dt))
    except Exception as e:
        dt = time.time() - t0
        fails.append((model_id, source, str(e)[:40], dt))

print(f"\n{'='*80}")
print(f"RESULTS: {len(gpt_hits)} GPT models working, {len(glm_hits)} GLM models working")
print(f"{'='*80}")

if gpt_hits:
    print("\n  GPT MODELS (working):")
    for m, src, dt, txt in sorted(gpt_hits, key=lambda x: x[2]):
        print(f"    {dt:5.1f}s  {m:40s}  [{src}]")
else:
    print("\n  GPT MODELS: NONE working")

if glm_hits:
    print("\n  GLM MODELS (working):")
    for m, src, dt, txt in sorted(glm_hits, key=lambda x: x[2]):
        print(f"    {dt:5.1f}s  {m:40s}  [{src}]")
else:
    print("\n  GLM MODELS: NONE working")

# Show closest failures
print("\n  Closest failures (not timeout/auth):")
for m, src, err, dt in fails:
    if "400" not in err and "timeout" not in err.lower():
        print(f"    {dt:5.1f}s  {m:40s}  [{src}]  {err}")
