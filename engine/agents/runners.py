"""Model call wrappers over OpenAI-compatible NIM endpoints (stdlib only).

Every call is paced (RateLimiter), budgeted (BudgetTracker), and error-classified:
network/429/malformed => InferenceCallError; rejected completion claims =>
VerificationFailureError. Never conflate the two (General Rule 11).
"""
from __future__ import annotations

import json
import os
import time
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


def _parse_chat_response(raw_text: str) -> str:
    """Extract message content or reasoning content from JSON payload or SSE stream."""
    raw_text = raw_text.strip()
    if raw_text.startswith("{") or raw_text.startswith("["):
        try:
            payload = json.loads(raw_text)
            if isinstance(payload, dict) and "choices" in payload and payload["choices"]:
                msg = payload["choices"][0].get("message", {})
                content = msg.get("content")
                if not content and msg.get("reasoning_content"):
                    content = msg.get("reasoning_content")
                if content is not None:
                    return content
        except Exception:
            pass

    content_parts = []
    reasoning_parts = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning_parts.append(delta["reasoning_content"])
                message = choices[0].get("message", {})
                if message.get("content"):
                    content_parts.append(message["content"])
        except Exception:
            continue

    if content_parts:
        return "".join(content_parts)
    if reasoning_parts:
        return "".join(reasoning_parts)
    return raw_text


def _call_once(routing, role, prompt, context, limiter, budget):
    """Single inference call with retry backoff. Raises InferenceCallError on failure."""
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
        "stream": False,
    }).encode("utf-8")
    req_url = base_url.rstrip("/") + "/chat/completions"

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        budget.record_call()
        limiter.acquire()
        try:
            req = urllib.request.Request(
                req_url, data=body,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=int(inference["timeout_seconds"])) as resp:
                raw_text = resp.read().decode("utf-8")
            result = _parse_chat_response(raw_text)
            if result:
                return result
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            return result
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            raise InferenceCallError(f"HTTP {exc.code} from {routing['model']}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            raise InferenceCallError(f"network failure: {exc}") from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise InferenceCallError(f"malformed response: {exc}") from exc
        finally:
            limiter.release()


def call_model(role, prompt, context=None, limiter=None, budget=None):
    """One paced, budgeted inference call with fallback chain support.

    Tries the primary model for the role; on failure, walks the fallback
    list from config/models.json until one succeeds.
    """
    routing = role_model(role)

    # Try primary
    try:
        return _call_once(routing, role, prompt, context, limiter, budget)
    except InferenceCallError as primary_exc:
        fallbacks = list(routing.get("fallback", []))
        
        # Direct Failover if OmniRoute returns an HTTP error or network failure
        if routing["provider"] == "omniroute":
            error_msg = str(primary_exc)
            if "network failure" in error_msg or "timed out" in error_msg or "HTTP " in error_msg:
                # Inject direct NIM fallback at the front of the fallback chain
                nim_fallback = {"provider": "nim", "model": "nvidia/nemotron-3-super-120b-a12b"}
                if nim_fallback not in fallbacks:
                    fallbacks.insert(0, nim_fallback)
                nim_fallback_2 = {"provider": "nim", "model": "meta/llama-3.3-70b-instruct"}
                if nim_fallback_2 not in fallbacks:
                    fallbacks.append(nim_fallback_2)

        # Walk fallback chain
        for i, fb in enumerate(fallbacks):
            try:
                # If we are failing over to NIM, we want to ensure we don't stall forever.
                # The timeout is handled in _call_once via inference['timeout_seconds'].
                return _call_once(fb, role, prompt, context, limiter, budget)
            except InferenceCallError:
                continue
        # All fallbacks exhausted
        raise primary_exc


def _extract_json_candidate(text: str) -> str:
    """Extract candidate JSON substring from model output."""
    import re
    if text is None:
        return ""
    stripped = text.strip()
    # 1. Try markdown code block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\s*\n?```', stripped, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        if candidate:
            return candidate
    # 2. Try finding outermost balanced braces or brackets
    start_brace = stripped.find('{')
    start_bracket = stripped.find('[')
    starts = [s for s in (start_brace, start_bracket) if s != -1]
    if starts:
        start = min(starts)
        open_char = stripped[start]
        close_char = '}' if open_char == '{' else ']'
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] == open_char:
                depth += 1
            elif stripped[i] == close_char:
                depth -= 1
                if depth == 0:
                    return stripped[start:i + 1]
        last_close = stripped.rfind(close_char)
        if last_close > start:
            return stripped[start:last_close + 1]
    return stripped


def _parse_json(text: str):
    """Parse JSON with multiple defensive recovery strategies."""
    import re
    import ast
    candidate = _extract_json_candidate(text)
    # Pass 1: standard strict json.loads
    try:
        return json.loads(candidate)
    except Exception:
        pass
    # Pass 2: non-strict json.loads (allows unescaped control chars in strings)
    try:
        return json.loads(candidate, strict=False)
    except Exception:
        pass
    # Pass 3: fix common invalid backslash escapes in code/regex strings
    fixed = re.sub(r'\\(?![/"\\bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', candidate)
    try:
        return json.loads(fixed, strict=False)
    except Exception:
        pass
    # Pass 4: python literal eval fallback
    try:
        val = ast.literal_eval(candidate)
        if isinstance(val, (dict, list)):
            return val
    except Exception:
        pass
    # Pass 5: re-evaluate on candidate to get standard JSONDecodeError
    return json.loads(candidate)


def call_json(role, prompt, context=None, limiter=None, budget=None, max_retries=2):
    """call_json + robust JSON extraction with automatic retry on malformed JSON."""
    last_exc = None
    last_text = ""
    for attempt in range(max_retries + 1):
        try:
            retry_prompt = prompt
            if attempt > 0:
                retry_prompt += f"\n\nIMPORTANT: Your previous output was invalid JSON ({last_exc}). Ensure all double quotes inside string values are properly escaped (e.g. \\\" and not raw quotes), all brackets are closed, and respond with ONLY a valid JSON object or array."
            else:
                retry_prompt += "\nRespond with ONLY a valid JSON object or array."
            text = call_model(role, retry_prompt, context, limiter, budget)
            last_text = text
            return _parse_json(text)
        except (json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            continue
    raise InferenceCallError(
        f"malformed JSON from {role} after {max_retries} retries: {last_exc}\nRaw Output:\n{last_text}") from last_exc


def classify_error(exc):
    """Distinct handling paths for the two failure classes (General Rule 11)."""
    if isinstance(exc, InferenceCallError):
        return "inference"
    if isinstance(exc, VerificationFailureError):
        return "verification"
    return "unknown"
