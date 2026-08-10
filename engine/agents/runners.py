"""Model call wrappers over OpenAI-compatible NIM endpoints (stdlib only).

Every call is paced (RateLimiter), budgeted (BudgetTracker), and error-classified:
network/429/malformed => InferenceCallError; rejected completion claims =>
VerificationFailureError. Never conflate the two (General Rule 11).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from engine import config as cfg, paths
from engine.agents.prompts import ROLE_PROMPTS
from engine.pacing.budget import BudgetTracker
from engine.pacing.limiter import RateLimiter


class InferenceCallError(RuntimeError):
    """Timeout / throttling / rate limit / malformed response.

    A distinct failure class: NEVER conflated with verification failure.
    """


class VerificationFailureError(RuntimeError):
    """Evidence-backed rejection of a completion claim."""


def role_model(role: str) -> dict:
    """Resolve a role to its provider/model routing entry from config."""
    models = cfg.load_models()
    if role not in models["roles"]:
        raise KeyError(f"unknown role: {role!r}")
    return models["roles"][role]


def load_secrets() -> dict:
    path = paths.config_path("secrets.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def call_model(role, prompt, context=None, limiter=None, budget=None):
    """One paced, budgeted inference call. Returns the assistant text."""
    routing = role_model(role)
    provider = cfg.load_models()["providers"][routing["provider"]]
    secrets = load_secrets()
    base_url = (os.environ.get(provider["base_url_env"])
                or secrets.get(provider["base_url_env"])
                or provider.get("default_base_url"))
    api_key = (os.environ.get(provider["api_key_env"])
               or secrets.get(provider["api_key_env"]))
    if not api_key or str(api_key).startswith("REPLACE_ME"):
        raise InferenceCallError("API key not configured (config/secrets.json)")

    inference = cfg.load_engine_config()["inference"]
    limiter = limiter or RateLimiter.from_config()
    budget = budget or BudgetTracker.from_config()
    budget.record_call()
    limiter.acquire()
    try:
        messages = [{"role": "system", "content": ROLE_PROMPTS.get(role, "")}]
        if context is not None:
            messages.append({"role": "system",
                             "content": context if isinstance(context, str)
                             else json.dumps(context)})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": routing["model"],
            "messages": messages,
            "max_tokens": int(inference["max_output_tokens"]),
        }).encode("utf-8")
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=int(inference["timeout_seconds"])) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        raise InferenceCallError(f"HTTP {exc.code} from {routing['model']}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise InferenceCallError(f"network failure: {exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise InferenceCallError(f"malformed response: {exc}") from exc
    finally:
        limiter.release()


def call_json(role, prompt, context=None, limiter=None, budget=None):
    """call_model + strict JSON parse. Malformed JSON = inference failure."""
    text = call_model(role, prompt + "\nRespond with ONLY a valid JSON object.",
                      context, limiter, budget)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InferenceCallError(f"malformed JSON from {role}: {exc}") from exc


def classify_error(exc):
    """Distinct handling paths for the two failure classes (General Rule 11)."""
    if isinstance(exc, InferenceCallError):
        return "inference"
    if isinstance(exc, VerificationFailureError):
        return "verification"
    return "unknown"
