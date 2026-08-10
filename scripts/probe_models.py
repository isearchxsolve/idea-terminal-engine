"""Quick probe: which models actually respond?"""
import json, urllib.request, urllib.error

secrets = json.loads(open("config/secrets.json").read())
base = secrets.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
key = secrets.get("OMNIROUTE_API_KEY", "omni")

test_models = [
    # aug models (premium?)
    "aug/opus4.8", "aug/sonnet5-high", "aug/gpt5.6-sol", "aug/gpt5.4",
    # auto models (free routing?)
    "auto/best-coding", "auto/best-reasoning", "auto/claude-opus", "auto/claude-sonnet",
    # oc models (free)
    "oc/nemotron-3-ultra-free", "oc/deepseek-v4-flash-free", "oc/big-pickle",
    # tllm/agy (gateway)
    "tllm/GPT_5_4", "agy/claude-opus-4-6-thinking",
    # openrouter free
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    # current nvidia
    "nvidia/z-ai/glm-5.2",
]

for model_id in test_models:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16, "stream": False,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=45)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        print(f"  OK   {model_id:50s} -> {text[:50]!r}")
    except urllib.error.HTTPError as e:
        print(f"  FAIL {model_id:50s} -> HTTP {e.code} {e.reason}")
    except Exception as e:
        print(f"  FAIL {model_id:50s} -> {e}")
