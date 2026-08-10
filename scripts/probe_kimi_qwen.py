"""
Strategic probe: Kimi and Qwen frontier models.
Tests all available paths to find working ones.
"""
import json, urllib.request, urllib.error, time

BASE = "http://localhost:20128/v1"
KEY = json.loads(open("config/secrets.json").read())["OMNIROUTE_API_KEY"]

targets = [
    # === KIMI FRONTIER ===
    # kimi-coding provider (OAuth, was healthy)
    ("kimi-coding/kimi-k2", "kimi-coding OAuth"),
    ("kc/moonshotai/kimi-k2.6", "kc alias"),
    ("kc/k1.5", "kc alias"),
    # kmc provider (connected)
    ("kmc/k3", "kmc"),
    ("kmc/kimi-for-coding", "kmc"),
    ("kmc/kimi-for-coding-highspeed", "kmc"),
    # nvidia provider (API key, healthy)
    ("nvidia/moonshotai/kimi-k2.6", "nvidia"),
    # moonshot direct
    ("moonshot/kimi-k3", "moonshot direct"),
    ("moonshot/kimi-k2.6", "moonshot direct"),
    ("moonshot/kimi-k2.7-code", "moonshot direct"),
    # cl alias
    ("cl/moonshotai/kimi-k3", "cl alias"),
    # other providers
    ("af/moonshot/kimi-k2.6", "af"),
    ("bzl/kimi-k2.6", "bzl"),
    ("bzl/kimi-k2.5", "bzl"),
    ("bpm/kimi-k2-thinking", "bpm"),
    ("ali/kimi-k2.7-code", "ali"),

    # === QWEN FRONTIER ===
    # kimi-coding provider
    ("kc/qwen/qwen3.6-plus", "kc alias"),
    ("kc/qwen/qwen3.5-397b-a17b", "kc alias"),
    # nvidia provider
    ("nvidia/qwen/qwen3.5-397b-a17b", "nvidia"),
    ("nvidia/qwen/qwen3.5-122b-a10b", "nvidia"),
    # groq provider (connected)
    ("groq/qwen/qwen3-32b", "groq"),
    ("groq/qwen/qwen3.6-27b", "groq"),
    # ali provider
    ("ali/qwen3.7-max", "ali"),
    ("ali/qwen3.7-plus", "ali"),
    ("ali/qwen3.6-plus", "ali"),
    ("ali/qwen3.5-plus", "ali"),
    ("ali/qwen3.5-397b-a17b", "ali"),
    # together provider (connected)
    ("together/Qwen/Qwen3-235B-A22B", "together"),
    # hyp provider
    ("hyp/Qwen/QwQ-32B", "hyp"),
    ("hyp/Qwen/Qwen2.5-72B-Instruct", "hyp"),
    # siliconflow
    ("siliconflow/Qwen/Qwen3-Coder-480B-A35B-Instruct", "siliconflow"),
    ("siliconflow/Qwen/Qwen3.5-397B-A17B", "siliconflow"),
    ("siliconflow/Qwen/Qwen3-235B-A22B", "siliconflow"),
    # ainative
    ("ainative/qwen3-235b-cerebras", "ainative"),
    ("ainative/qwen3-32b", "ainative"),
    # af
    ("af/qwen/qwen3-32b", "af"),
    # bzl
    ("bzl/qwen3.6-plus", "bzl"),
    # ovh
    ("ovh/Qwen2.5-Coder-32B-Instruct", "ovh"),
    # scw
    ("scw/qwen3-235b-a22b-instruct-2507", "scw"),
]

print(f"Testing {len(targets)} Kimi + Qwen models...\n")
print(f"{'Model':55s} {'Provider':15s} {'Time':>6s} {'Status':10s} {'Response'}")
print("=" * 120)

working = []

for model_id, label in targets:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "What is your exact model name and version? Reply in one sentence."}],
        "max_tokens": 80,
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
        resp = urllib.request.urlopen(req, timeout=30)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()[:60]
        model_used = payload.get("model", "?")
        dt = time.time() - t0
        print(f"{model_id:55s} {label:15s} {dt:5.1f}s {'OK':10s} {text}")
        working.append((model_id, label, dt, text))
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        err_body = ""
        try:
            err_body = e.read().decode()[:80]
        except:
            pass
        print(f"{model_id:55s} {label:15s} {dt:5.1f}s HTTP {e.code:3d}  {err_body}")
    except urllib.error.URLError as e:
        dt = time.time() - t0
        print(f"{model_id:55s} {label:15s} {dt:5.1f}s FAIL   {e.reason}")
    except Exception as e:
        dt = time.time() - t0
        print(f"{model_id:55s} {label:15s} {dt:5.1f}s ERR    {str(e)[:60]}")

print(f"\n{'='*80}")
print(f"WORKING: {len(working)} / {len(targets)}")
print("=" * 80)
for model_id, label, dt, text in working:
    print(f"  {model_id:55s} {dt:5.1f}s  [{label}]")
    print(f"    -> {text}")
