"""
Strategic probe v2: Test the CORRECT model IDs from the catalog.
Target: GPT frontier + GLM-5.2
"""
import json, urllib.request, urllib.error, time

BASE = "http://localhost:20128/v1"
KEY = json.loads(open("config/secrets.json").read())["OMNIROUTE_API_KEY"]

targets = [
    # === GPT FRONTIER (from catalog, all marked AVAIL) ===
    # cx = codex alias (was 429 before, but with correct model ID might work)
    ("cx/gpt-5.6-sol", "Codex alias"),
    ("cx/gpt-5.6-sol-ultra", "Codex alias"),
    ("cx/gpt-5.6-sol-max", "Codex alias"),
    ("cx/gpt-5.6-sol-high", "Codex alias"),
    ("cx/gpt-5.6-terra", "Codex alias"),
    ("cx/gpt-5.6-terra-high", "Codex alias"),
    ("cx/gpt-5.6-luna", "Codex alias"),
    ("cx/gpt-5.5", "Codex alias"),
    ("cx/gpt-5.5-high", "Codex alias"),
    # bb = blackbox alias
    ("bb/gpt-5.5", "Blackbox alias"),
    ("bb/gpt-5.4-pro", "Blackbox alias"),
    ("bb/gpt-5.4", "Blackbox alias"),
    ("bb/gpt-5.3-codex", "Blackbox alias"),
    # bzl = bazaarlink alias
    ("bzl/gpt-5.5", "Bazaarlink alias"),
    ("bzl/gpt-5.4", "Bazaarlink alias"),
    ("bzl/gpt-5.4-mini", "Bazaarlink alias"),
    # kc = kimi-coding alias
    ("kc/openai/gpt-5.5", "Kimi alias"),
    ("kc/openai/gpt-5.4-mini", "Kimi alias"),
    # cl = cline alias
    ("cl/openai/gpt-5.6-sol", "Cline alias"),
    # GPT-oss (open source GPT) on free providers
    ("agy/gpt-oss-120b-medium", "AGY oss"),
    ("antigravity/gpt-oss-120b-medium", "Antigravity oss"),
    ("nvidia/openai/gpt-oss-120b", "Nvidia oss"),
    ("nvidia/openai/gpt-oss-20b", "Nvidia oss"),
    ("groq/openai/gpt-oss-120b", "Groq oss"),
    ("groq/openai/gpt-oss-20b", "Groq oss"),
    ("cerebras/gpt-oss-120b", "Cerebras oss"),
    ("samba/gpt-oss-120b", "SambaNova oss"),
    ("fireworks/gpt-oss-120b", "Fireworks oss"),
    ("fireworks/gpt-oss-20b", "Fireworks oss"),
    ("siliconflow/openai/gpt-oss-120b", "SiliconFlow oss"),
    ("siliconflow/openai/gpt-oss-20b", "SiliconFlow oss"),
    ("deepinfra/openai/gpt-oss-120b", "DeepInfra oss"),
    ("scw/gpt-oss-120b", "Scaleway oss"),
    ("baseten/openai/gpt-oss-120b", "Baseten oss"),
    ("wandb/openai/gpt-oss-120b", "W&B oss"),
    ("bpm/gpt-oss-120b", "BPM oss"),

    # === GLM-5.2 (from catalog, all marked AVAIL) ===
    ("nvidia/z-ai/glm-5.2", "Nvidia GLM"),
    ("ali/glm-5.2", "Alibaba GLM"),
    ("ali/glm-5.2-fast-preview", "Alibaba GLM fast"),
    ("cl/zai/glm-5.2", "Cline GLM"),
    ("bzl/glm-5.1", "Bazaarlink GLM"),
    ("bzl/glm-5", "Bazaarlink GLM"),
    ("agentrouter/glm-5.1", "AgentRouter GLM"),
    ("fireworks/glm-5p1", "Fireworks GLM"),
    ("cerebras/zai-glm-4.7", "Cerebras GLM"),
    ("deepinfra/zai-org/GLM-5.1", "DeepInfra GLM"),
    ("siliconflow/zai-org/GLM-5.1", "SiliconFlow GLM"),
    ("siliconflow/zai-org/GLM-5", "SiliconFlow GLM"),
    ("siliconflow/zai-org/GLM-4.7", "SiliconFlow GLM"),
    ("siliconflow/THUDM/GLM-4-32B-0414", "SiliconFlow GLM4"),
    ("siliconflow/THUDM/GLM-Z1-32B-0414", "SiliconFlow GLM-Z1"),
    ("baseten/zai-org/GLM-5", "Baseten GLM"),
    ("bpm/glm-4.7", "BPM GLM"),
]

print(f"Strategic probe v2: {len(targets)} targets")
print(f"{'='*80}")

gpt_ok = []
glm_ok = []
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
        print(f"  OK   {model_id:45s} {dt:5.1f}s  [{source:20s}]  {text[:35]}")

        if "glm" in model_id.lower():
            glm_ok.append((model_id, source, dt, text[:40]))
        else:
            gpt_ok.append((model_id, source, dt, text[:40]))
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        fails.append((model_id, source, f"HTTP {e.code}", dt))
        print(f"  FAIL {model_id:45s} {dt:4.1f}s  [{source:20s}]  HTTP {e.code}")
    except Exception as e:
        dt = time.time() - t0
        fails.append((model_id, source, str(e)[:30], dt))
        print(f"  FAIL {model_id:45s} {dt:4.1f}s  [{source:20s}]  {str(e)[:30]}")

print(f"\n{'='*80}")
print(f"RESULTS: {len(gpt_ok)} GPT OK, {len(glm_ok)} GLM OK, {len(fails)} failed")
print(f"{'='*80}")

if gpt_ok:
    print("\n  GPT FRONTIER MODELS (working!):")
    for m, src, dt, txt in sorted(gpt_ok, key=lambda x: x[2]):
        print(f"    {dt:5.1f}s  {m:45s}  [{src}]")

if glm_ok:
    print("\n  GLM MODELS (working!):")
    for m, src, dt, txt in sorted(glm_ok, key=lambda x: x[2]):
        print(f"    {dt:5.1f}s  {m:45s}  [{src}]")

if not gpt_ok:
    print("\n  GPT: None working")
if not glm_ok:
    print("\n  GLM: None working")
