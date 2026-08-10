"""Probe newly discovered providers from the OmniRoute connections list."""
import json, urllib.request, urllib.error, time

secrets = json.loads(open("config/secrets.json").read())
base = secrets["OMNIROUTE_BASE_URL"]
key = secrets["OMNIROUTE_API_KEY"]

# New providers not in the original probe
models = [
    # xai-oauth (connected, active)
    "xai-oauth/grok-4.5",
    "xai-oauth/grok-build-0.1",
    # amazon-q (connected, active)
    "amazon-q/claude-opus-4-8",
    "amazon-q/claude-sonnet-5",
    "amazon-q/gpt-5.6-sol",
    "amazon-q/gemini-3.6-flash-high",
    # kilocode (connected, active)
    "kilocode/claude-opus-4-8",
    "kilocode/gpt-5.6-sol",
    "kilocode/gemini-3.6-flash-high",
    # antigravity full-name prefix (connected, active)
    "antigravity/claude-opus-4-6-thinking",
    "antigravity/gemini-3.6-flash-high",
    "antigravity/claude-sonnet-4-6",
    # opencode full-name prefix (connected, active)
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/big-pickle",
    "opencode/gpt-5.6-sol",
    "opencode/claude-sonnet-5",
    "opencode/glm-5.2",
    # openrouter auto-route
    "openrouter/openrouter/free",
    # Special meta-models
    "fusion-coder",
    "codex-auto-review",
]

for m in models:
    body = json.dumps({
        "model": m,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16, "stream": False,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=45)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        print(f"  OK   {m:50s} {time.time()-t0:.1f}s  {text[:50]}")
    except urllib.error.HTTPError as e:
        print(f"  FAIL {m:50s} HTTP {e.code} {e.reason}")
    except Exception as e:
        print(f"  FAIL {m:50s} {str(e)[:60]}")
