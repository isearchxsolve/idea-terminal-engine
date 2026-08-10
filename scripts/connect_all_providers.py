"""
Connect ALL providers to OmniRoute via the API.
Uses discovered provider names from model prefixes and dashboard JS.
"""
import requests, json, time

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
token = r.cookies.get("auth_token")
h = {"Content-Type": "application/json"}
c = {"auth_token": token}

# Get currently connected providers
data = s.get(f"{BASE}/api/providers", headers=h, cookies=c, timeout=5).json()
connected = {conn["provider"] for conn in data.get("connections", [])}
print(f"Currently connected: {len(connected)} - {sorted(connected)}")

# All known provider IDs from /v1/models prefixes + dashboard JS discovery
# These are the provider identifiers OmniRoute recognizes
all_providers = {
    # Already connected (will skip)
    # "amazon-q", "antigravity", "agy", "cline", "codex", "kimi-coding",
    # "kilocode", "nvidia", "openrouter", "opencode", "xai-oauth",

    # From /v1/models prefixes (not yet connected)
    "kc", "oc", "cx", "tllm", "aug", "cl", "ddgw", "xao", "felo", "kmc",
    "veoaifree-web", "veo-free", "pepper", "mcode", "aq",

    # From dashboard JS discovery (display names mapped to IDs)
    "openrouter", "opencode", "nvidia", "antigravity", "agy", "cline",
    "codex", "kimi-coding", "kilocode", "amazon-q", "xai-oauth",
    "augment", "blackbox", "cerebras", "together", "fireworks",
    "deepinfra", "groq", "mistral", "cohere", "ai21", "replicate",
    "huggingface", "perplexity", "anyscale", "deepseek", "qwen",
    "alibaba", "baidu", "zhipu", "moonshot", "minimax", "lingyiwanwu",
    "openai", "anthropic", "google", "meta", "xai",
    "azure-openai", "azure-ai", "aws-bedrock", "gcp-vertex",
    "github", "gitlab", "cloudflare", "vercel", "modal",
    "replicate", "baseten", "octoai", "lepton", "banana",
    "stability", "midjourney", "runway", "kling",
    "elevenlabs", "cartesia", "assemblyai", "whisper",
    "openrouter-free", "openrouter-auto",
    "lmstudio", "ollama", "jan", "text-generation-webui",
    "klab", "fal", "siliconflow", "novita", "windmill",
    "agentrouter", "arenafree", "chutes", "fetchit",
    "featherless", "friendliai", "hyperbolic", "infermatic",
    "inflection", "kilab", "lambda", "nanobanana",
    "nebius", "nim", "northeastern", "openpipe", "ovhcloud",
    "parasail", "paperplane", "piapi", "pinokio",
    "recraft", "sambanova", "scaleway", "segmind",
    "together-ai", "unifuncs", "vast", "vercel-ai",
    "wizardlm", "xai-grok", "zapier", "zhipu-ai",
}

# Remove already connected
to_connect = all_providers - connected
print(f"\nTrying to connect {len(to_connect)} new providers...")
print(f"Skipping {len(connected)} already connected\n")

results = {"connected": [], "already": [], "failed": [], "needs_apikey": []}

for pid in sorted(to_connect):
    # Try with a placeholder API key
    body = {"name": pid, "provider": pid, "apiKey": "free"}
    try:
        r = s.post(f"{BASE}/api/providers", json=body, headers=h, cookies=c, timeout=8)
        status = r.status_code
        resp = r.text[:200]

        if status in (200, 201):
            print(f"  OK   {pid:30s} connected!")
            results["connected"].append(pid)
        elif "already exists" in resp.lower() or "duplicate" in resp.lower():
            print(f"  DUP  {pid:30s} already exists")
            results["already"].append(pid)
        elif "api key" in resp.lower() and "required" in resp.lower():
            # Try without apiKey or with different format
            body2 = {"name": pid, "provider": pid, "apiKey": "sk-free"}
            r2 = s.post(f"{BASE}/api/providers", json=body2, headers=h, cookies=c, timeout=8)
            if r2.status_code in (200, 201):
                print(f"  OK   {pid:30s} connected with sk-free!")
                results["connected"].append(pid)
            else:
                print(f"  KEY  {pid:30s} needs real API key")
                results["needs_apikey"].append(pid)
        else:
            print(f"  FAIL {pid:30s} {status} {resp[:80]}")
            results["failed"].append((pid, f"{status}: {resp[:60]}"))
    except Exception as e:
        print(f"  ERR  {pid:30s} {str(e)[:60]}")
        results["failed"].append((pid, str(e)[:60]))

# Summary
print(f"\n{'='*60}")
print("CONNECTION RESULTS")
print(f"{'='*60}")
print(f"  Newly connected: {len(results['connected'])}")
for p in results["connected"]:
    print(f"    + {p}")
print(f"  Already existed: {len(results['already'])}")
print(f"  Needs API key:   {len(results['needs_apikey'])}")
for p in results["needs_apikey"]:
    print(f"    ! {p}")
print(f"  Failed:          {len(results['failed'])}")
for p, reason in results["failed"][:20]:
    print(f"    x {p}: {reason}")

# Now get updated connections list
data = s.get(f"{BASE}/api/providers", headers=h, cookies=c, timeout=5).json()
conns = data.get("connections", [])
print(f"\nTotal connections now: {len(conns)}")

# Save results
with open("scripts/connection_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved results to scripts/connection_results.json")
