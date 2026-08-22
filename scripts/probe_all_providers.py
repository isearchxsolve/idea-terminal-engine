"""Comprehensive model probe: tests one representative model per provider family."""
import json, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor, as_completed

secrets = json.loads(open("config/secrets.json").read())
base = secrets.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
key = secrets.get("OMNIROUTE_API_KEY", "omni")

# One representative model per provider family, prioritizing models useful for the engine
probe_targets = [
    # --- Currently used by engine (models.json) ---
    ("ENGINE-CURRENT", "agy/claude-opus-4-6-thinking"),
    ("ENGINE-CURRENT", "cl/openai/gpt-5.6-sol"),
    ("ENGINE-CURRENT", "agy/gemini-3.6-flash-high"),

    # --- Antigravity (agy) family ---
    ("agy", "agy/claude-sonnet-4-6"),
    ("agy", "agy/gemini-3-flash-agent"),
    ("agy", "agy/gemini-2.5-flash-thinking"),

    # --- Aug (premium?) ---
    ("aug", "aug/opus4.8"),
    ("aug", "aug/sonnet5-high"),
    ("aug", "aug/gpt5.6-sol"),
    ("aug", "aug/glm-5.2"),

    # --- Auto-routing ---
    ("auto", "auto/best-coding"),
    ("auto", "auto/best-reasoning"),
    ("auto", "auto/best-free"),
    ("auto", "auto/coding:free"),

    # --- CLI route (cl) ---
    ("cl", "cl/anthropic/claude-opus-4.8"),
    ("cl", "cl/x-ai/grok-4.5"),
    ("cl", "cl/zai/glm-5.2"),
    ("cl", "cl/nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("cl", "cl/moonshotai/kimi-k3"),

    # --- Cline route ---
    ("cline", "cline/anthropic/claude-opus-4.8"),
    ("cline", "cline/openai/gpt-5.6-sol"),

    # --- Codex ---
    ("codex", "codex/gpt-5.6-sol"),
    ("codex", "codex/gpt-5.6-terra"),
    ("codex", "codex/gpt-5.5"),

    # --- OpenCode (oc) ---
    ("oc", "oc/claude-opus-4-8"),
    ("oc", "oc/claude-sonnet-5"),
    ("oc", "oc/gpt-5.6-sol"),
    ("oc", "oc/gpt-5.5-pro"),
    ("oc", "oc/deepseek-v4-flash-free"),
    ("oc", "oc/nemotron-3-ultra-free"),
    ("oc", "oc/big-pickle"),
    ("oc", "oc/glm-5.2"),
    ("oc", "oc/grok-4.5"),
    ("oc", "oc/kimi-k3"),
    ("oc", "oc/gemini-3.6-flash"),

    # --- OpenRouter free ---
    ("openrouter", "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("openrouter", "openrouter/openai/gpt-oss-20b:free"),
    ("openrouter", "openrouter/google/gemma-4-31b-it:free"),
    ("openrouter", "openrouter/cohere/north-mini-code:free"),

    # --- NVIDIA NIM direct ---
    ("nvidia-direct", "nvidia/z-ai/glm-5.2"),

    # --- tllm gateway ---
    ("tllm", "tllm/CLAUDE_4_6_OPUS"),
    ("tllm", "tllm/GPT_5_4"),
    ("tllm", "tllm/gemini_3_pro"),
    ("tllm", "tllm/deepseek_v4"),

    # --- Kimi coding ---
    ("kimi-coding", "kimi-coding/k3"),
    ("kimi-coding", "kimi-coding/kimi-for-coding"),

    # --- DDGW ---
    ("ddgw", "ddgw/claude-haiku-4-5"),
    ("ddgw", "ddgw/gpt-5.4-mini"),

    # --- Pepper ---
    ("pepper", "pepper/pepper-1"),

    # --- No-think variants (currently used model) ---
    ("no-think", "no-think/agy/claude-opus-4-6-thinking"),
    ("no-think", "no-think/oc/claude-opus-4-8"),
]


def ping(model_id: str, timeout: int = 45) -> dict:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16, "stream": False,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        elapsed = time.time() - t0
        return {"model": model_id, "status": "OK", "reply": text[:60], "time": elapsed}
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        return {"model": model_id, "status": f"HTTP {e.code}", "reply": e.reason, "time": elapsed}
    except Exception as e:
        elapsed = time.time() - t0
        return {"model": model_id, "status": "FAIL", "reply": str(e)[:80], "time": elapsed}


print(f"Probing {len(probe_targets)} models via {base} ...\n")
results = {}
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(ping, m): (fam, m) for fam, m in probe_targets}
    for fut in as_completed(futures):
        fam, m = futures[fut]
        r = fut.result()
        results.setdefault(fam, []).append(r)
        icon = "OK  " if r["status"] == "OK" else "FAIL"
        print(f"  [{icon}] {r['model']:55s} {r['status']:10s} {r['time']:.1f}s  {r['reply'][:40]}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY BY PROVIDER FAMILY")
print("=" * 80)
total_ok = 0
total_fail = 0
for fam in sorted(results.keys()):
    entries = results[fam]
    ok = [e for e in entries if e["status"] == "OK"]
    fail = [e for e in entries if e["status"] != "OK"]
    total_ok += len(ok)
    total_fail += len(fail)
    print(f"\n  {fam} ({len(ok)}/{len(entries)} working)")
    for e in sorted(ok, key=lambda x: x["time"]):
        print(f"    OK   {e['model']:50s} {e['time']:.1f}s")
    for e in fail:
        print(f"    FAIL {e['model']:50s} {e['status']} {e['reply'][:40]}")

print(f"\n{'=' * 80}")
print(f"TOTAL: {total_ok} OK, {total_fail} FAIL out of {total_ok + total_fail} probed")
