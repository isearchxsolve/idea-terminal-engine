"""
Restore Zed settings with all 51 verified working models from our probe.
Data source: frontier_model_status.json (live-tested 2026-08-11)
"""
import json, os

SETTINGS = os.path.expandvars(r"%APPDATA%\Zed\settings.json")
STATUS   = "scripts/frontier_model_status.json"

# Load the probe results
with open(STATUS) as f:
    status = json.load(f)

# Load current Zed settings
with open(SETTINGS, encoding="utf-8") as f:
    settings = json.load(f)

# Build display names from model IDs
def display_name(model_id):
    provider, *rest = model_id.split("/", 1)
    name = rest[0] if rest else model_id
    labels = {
        "kc":          "KC",
        "kmc":         "KMC",
        "nvidia":      "NVIDIA",
        "agy":         "AGY",
        "antigravity": "Antigravity",
        "openrouter":  "OpenRouter",
        "oc":          "OpenCode",
        "cl":          "Cline",
        "cx":          "Codex",
        "xao":         "xAI",
    }
    prefix = labels.get(provider, provider.upper())
    # humanise the model slug
    slug = name.replace("-", " ").replace("/", " / ").replace("_", " ")
    return f"{slug} [{prefix}]"

# Standard capabilities block
def caps(tools=True, images=False):
    return {
        "tools": tools,
        "images": images,
        "parallel_tool_calls": False,
        "prompt_cache_key": False,
        "chat_completions": True,
        "interleaved_reasoning": False,
        "max_tokens_parameter": False,
    }

# Models with vision capability
VISION_MODELS = {
    "nvidia/meta/llama-3.2-11b-vision-instruct",
    "nvidia/nvidia/nemotron-nano-12b-v2-vl",
    "nvidia/nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
}

# Build the model list sorted fastest first
model_entries = []
for model_id, dt, _ in sorted(status["ok"], key=lambda x: x[1]):
    entry = {
        "name": model_id,
        "display_name": display_name(model_id),
        "max_tokens": 128000,
        "max_output_tokens": 32000,
        "capabilities": caps(images=(model_id in VISION_MODELS)),
    }
    model_entries.append(entry)

# Inject into settings
settings["language_models"]["openai_compatible"]["OmniRoute"]["available_models"] = model_entries

# Write back
with open(SETTINGS, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

print(f"Restored {len(model_entries)} verified models into Zed settings.")
print(f"Fastest: {model_entries[0]['name']}  ({model_entries[0]['display_name']})")
print(f"Slowest: {model_entries[-1]['name']}  ({model_entries[-1]['display_name']})")
