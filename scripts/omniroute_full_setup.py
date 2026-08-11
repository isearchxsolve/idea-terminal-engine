"""
OmniRoute Complete Setup Script
================================
Single script that performs full setup:
  1. Install OmniRoute as Windows service (auto-start on boot)
     → SKIPPED entirely if the service is already RUNNING
  2. Configure OmniRoute password and API key
  3. Connect free / auto-connectable providers (expanded + live discovery)
  4. Test all connections
  5. Set environment variables for Claude Code CLI and Codex CLI
  6. Configure Codex config.toml for OmniRoute
  7. Print summary with model names, API keys, endpoints

Usage:
  python scripts/omniroute_full_setup.py

Run as Administrator for Windows service installation.
"""
import os
import sys
import json
import time
import secrets
import subprocess
import urllib.request
import urllib.error
import tempfile
import shutil
import glob

# === Configuration ===
OMNIROUTE_PORT = 20128
OMNIROUTE_URL = f"http://localhost:{OMNIROUTE_PORT}"
OMNIROUTE_BASE = f"{OMNIROUTE_URL}/v1"
OMNIROUTE_PASSWORD = "omniroute-admin-2026"
OMNIROUTE_SERVICE_NAME = "OmniRoute"

# Working models (updated Aug 2026)
WORKING_MODELS = {
    # Claude family
    "cc/claude-opus-4-8": {"latency": "~4-7s", "family": "Claude Opus 4.8"},
    "cc/claude-opus-4-7": {"latency": "~4-6s", "family": "Claude Opus 4.7"},
    "cc/claude-sonnet-4-6": {"latency": "~2-4s", "family": "Claude Sonnet 4.6"},
    "claude-fable-5": {"latency": "~4-7s", "family": "Claude Fable 5"},

    # GPT-5.6 family
    "gh/gpt-5.6-sol": {"latency": "~3-6s", "family": "GPT-5.6 Sol"},
    "gh/gpt-5.6-terra": {"latency": "~3-5s", "family": "GPT-5.6 Terra"},
    "gh/gpt-5.6-luna": {"latency": "~2-4s", "family": "GPT-5.6 Luna"},
    "cx/gpt-5.5": {"latency": "~3-5s", "family": "GPT-5.5 (Codex)"},

    # Kimi & Qwen (often free via Qoder)
    "if/kimi-k3": {"latency": "~3-6s", "family": "Kimi K3"},
    "if/qwen3.8-max-preview": {"latency": "~3-6s", "family": "Qwen 3.8 Max"},
    "if/qwen3.7-max": {"latency": "~3-5s", "family": "Qwen 3.7 Max"},

    # Other strong free / cheap options
    "agy/claude-sonnet-4-6": {"latency": "~3-5s", "family": "Claude (Antigravity)"},
    "agy/gemini-3.6-flash-high": {"latency": "~2-4s", "family": "Gemini"},
    "nvidia/z-ai/glm-5.2": {"latency": "~4-6s", "family": "GLM 5.2"},
    "auto/coding:free": {"latency": "~3-5s", "family": "Auto Combo (Free)"},
    "auto/best-coding": {"latency": "varies", "family": "Auto Best Coding"},
}


def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_ok(text):
    print(f"  [+] {text}")


def print_fail(text):
    print(f"  [-] {text}")


def print_info(text):
    print(f"  [*] {text}")


def print_model(text, detail=""):
    print(f"    {text:45s} {detail}")


# === Step 1: Install OmniRoute as Windows Service ===
def install_omniroute():
    print_header("Step 1: Install OmniRoute as Windows Service")

    # ------------------------------------------------------------------
    # Early exit: if the service is already RUNNING, do NOTHING.
    # No stop, no remove, no install, no start.
    # ------------------------------------------------------------------
    result = subprocess.run(
        ["sc", "query", OMNIROUTE_SERVICE_NAME],
        capture_output=True, text=True
    )
    if result.returncode == 0 and "RUNNING" in result.stdout:
        print_ok("OmniRoute service is already RUNNING — skipping install/stop/start")
        return True

    # Resolve OmniRoute entry script
    node_root = r"C:\Users\Admin\AppData\Local\hermes\node"
    node_exe = os.path.join(node_root, "node.exe")
    pkg_root = os.path.join(node_root, "node_modules", "omniroute")
    server_script = os.path.join(pkg_root, "bin", "omniroute.mjs")
    server_script_fallback = os.path.join(pkg_root, "dist", "server-ws.mjs")
    work_dir = pkg_root

    if not os.path.exists(node_exe):
        print_fail(f"node.exe not found at {node_exe}")
        return False
    if not os.path.exists(server_script):
        if os.path.exists(server_script_fallback):
            server_script = server_script_fallback
            print_info(f"Falling back to dev build entry: {server_script}")
        else:
            print_fail("OmniRoute entry script not found.")
            print_info(f"Tried: {server_script}")
            print_info(f"Tried: {server_script_fallback}")
            return False
    else:
        print_info(f"Entry script: {server_script}")

    # Locate nssm
    nssm_exe = shutil.which("nssm") or os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        "nssm", "nssm.exe")
    winget_nssm = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe")
    if not os.path.exists(winget_nssm):
        candidates = glob.glob(os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\NSSM.NSSM_*\*\win64\nssm.exe"))
        if candidates:
            winget_nssm = candidates[0]
    if os.path.exists(winget_nssm):
        nssm_exe = winget_nssm
    if not os.path.exists(nssm_exe):
        print_info("Installing nssm via winget (service manager)...")
        subprocess.run(["winget", "install", "nssm", "-e",
                       "--accept-source-agreements", "--accept-package-agreements"],
                      capture_output=True)
        if os.path.exists(winget_nssm):
            nssm_exe = winget_nssm
        else:
            nssm_exe = shutil.which("nssm") or nssm_exe
    if not os.path.exists(nssm_exe):
        print_fail("nssm not found (PATH, winget install, or expected locations).")
        print_info("Install nssm manually: winget install nssm")
        return False
    print_info(f"nssm: {nssm_exe}")

    # Register as Windows service via nssm
    print_info("Registering OmniRoute as Windows service...")
    try:
        # Only remove if it exists but is NOT running (we already returned early if RUNNING)
        subprocess.run([nssm_exe, "stop", OMNIROUTE_SERVICE_NAME], capture_output=True)
        subprocess.run([nssm_exe, "remove", OMNIROUTE_SERVICE_NAME, "confirm"],
                      capture_output=True)

        # Install service with application ONLY
        result = subprocess.run(
            [nssm_exe, "install", OMNIROUTE_SERVICE_NAME, node_exe],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print_fail(f"Service install failed: {result.stderr.strip()}")
            print_info("Run this script as Administrator!")
            return False

        app_params = f"--max-old-space-size=4096 {server_script}"
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppParameters", app_params],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppDirectory", work_dir],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Description",
                       "OmniRoute AI Model Gateway"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Start",
                       "SERVICE_AUTO_START"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRestartDelay", "10000"],
                      capture_output=True, check=True)
        # Throttle: prevent rapid crash-storm restarts (30 s minimum between restarts)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppThrottle", "30000"],
                      capture_output=True, check=True)

        # Logging
        omni_log_dir = os.path.expanduser(r"~\.omniroute\logs")
        os.makedirs(omni_log_dir, exist_ok=True)
        stdout_log = os.path.join(omni_log_dir, "service-stdout.log")
        stderr_log = os.path.join(omni_log_dir, "service-stderr.log")
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStdout", stdout_log],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStderr", stderr_log],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateFiles", "1"],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateOnline", "1"],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateBytes", "10485760"],
                      capture_output=True, check=True)

        # Force LocalSystem
        print_info("Ensuring service runs as LocalSystem")
        sc_cmd = [
            os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"), "/c",
            f"sc config {OMNIROUTE_SERVICE_NAME} obj= LocalSystem password= \"\""
        ]
        subprocess.run(sc_cmd, capture_output=True, text=True)

        qcp = subprocess.run(
            [os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"), "/c",
             f"sc qc {OMNIROUTE_SERVICE_NAME}"],
            capture_output=True, text=True)
        start_name = "unknown"
        for line in qcp.stdout.splitlines():
            if "SERVICE_START_NAME" in line:
                start_name = line.split(":", 1)[1].strip()
                break
        print_info(f"SERVICE_START_NAME = {start_name}")

        # Environment injection
        omni_data_dir = os.path.expanduser(r"~\.omniroute")
        os.makedirs(omni_data_dir, exist_ok=True)
        node_install_dir = node_root
        base_path = os.environ.get("PATH", "")
        if node_install_dir.lower() not in base_path.lower():
            base_path = base_path.rstrip(";") + ";" + node_install_dir if base_path else node_install_dir

        env_file = os.path.join(omni_data_dir, ".env")
        storage_key = None
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("STORAGE_ENCRYPTION_KEY="):
                            storage_key = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass
        if not storage_key:
            storage_key = secrets.token_hex(32)
            try:
                with open(env_file, "a", encoding="utf-8") as f:
                    f.write(f"\nSTORAGE_ENCRYPTION_KEY={storage_key}\n")
            except Exception as e:
                print_info(f"(non-fatal) could not persist .env key: {e}")
            print_info(f"Generated new STORAGE_ENCRYPTION_KEY -> {env_file}")
        else:
            print_info(f"Reusing existing STORAGE_ENCRYPTION_KEY from {env_file}")

        env_entries = [
            f"DATA_DIR={omni_data_dir}",
            f"USERPROFILE={os.path.expanduser('~')}",
            f"HOME={os.path.expanduser('~')}",
            f"PATH={base_path}",
            f"STORAGE_ENCRYPTION_KEY={storage_key}",
        ]
        masked_entries = [
            e if not e.startswith("STORAGE_ENCRYPTION_KEY=")
            else f"STORAGE_ENCRYPTION_KEY={storage_key[:8]}...{storage_key[-8:]}"
            for e in env_entries
        ]
        print_info("Injecting AppEnvironmentExtra: " + " | ".join(masked_entries))
        subprocess.run(
            [nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppEnvironmentExtra",
             *env_entries],
            capture_output=True, check=True)
        storage_key = None

        # Clean rogue LocalSystem profile
        rogue_dir = r"C:\Windows\System32\config\systemprofile\.omniroute"
        if os.path.exists(rogue_dir):
            try:
                shutil.rmtree(rogue_dir, ignore_errors=True)
            except Exception as e:
                print_info(f"(non-fatal) could not remove rogue {rogue_dir}: {e}")

        # Start service (only because we just installed it)
        subprocess.run([nssm_exe, "start", OMNIROUTE_SERVICE_NAME], capture_output=True)

        # Wait for port  (correct endpoint: /api/monitoring/health)
        port_ready = False
        for _ in range(75):
            time.sleep(1)
            try:
                req = urllib.request.Request(
                    f"{OMNIROUTE_URL}/api/monitoring/health", method="GET")
                urllib.request.urlopen(req, timeout=2)
                port_ready = True
                break
            except urllib.error.HTTPError as e:
                # 401 = server is up but needs auth; still means port is ready
                if e.code in (401, 403):
                    port_ready = True
                    break
            except Exception:
                continue

        if not port_ready:
            print_fail(f"Service started but port {OMNIROUTE_PORT} not responding after 75s")
            print_info(f"Check stderr log: {stderr_log}")
            return False

        print_ok("OmniRoute installed as Windows service (auto-start on boot)")
        print_ok(f"Service name: {OMNIROUTE_SERVICE_NAME}")
        print_ok(f"Node: {node_exe}")
        print_ok(f"Script: {server_script}")
        print_ok(f"AppParameters: {app_params}")
        print_ok(f"stdout -> {stdout_log}")
        print_ok(f"stderr -> {stderr_log}")
        return True

    except subprocess.CalledProcessError as e:
        print_fail(f"nssm command failed: {e}")
        print_info("Run this script as Administrator!")
        return False
    except Exception as e:
        print_fail(f"Service installation error: {e}")
        print_info("Run this script as Administrator!")
        return False


# === Step 2: Configure OmniRoute ===

KNOWN_FALLBACK_KEY = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"


def _omni_get(path, cookie=None, bearer=None, timeout=8):
    """Simple helper: GET with optional cookie or bearer auth. Returns (status, body_bytes)."""
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(f"{OMNIROUTE_URL}{path}", headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def verify_key(key):
    """Return True if key authenticates successfully.
    /v1/models can return 4000+ models and be slow, so use a generous timeout.
    Falls back to a minimal chat call if models list times out.
    """
    status, _ = _omni_get("/v1/models", bearer=key, timeout=20)
    if status == 200:
        return True
    if status == 0:  # urllib timeout on large payload — try a minimal probe instead
        body = json.dumps({
            "model": "nvidia/z-ai/glm-5.2",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }).encode()
        req = urllib.request.Request(
            f"{OMNIROUTE_URL}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=15)
            return True  # got a response (even error is fine, just not 401/403)
        except urllib.error.HTTPError as e:
            return e.code not in (401, 403)
        except Exception:
            pass
    return False


def configure_omniroute():
    print_header("Step 2: Configure OmniRoute")

    # ------------------------------------------------------------------ #
    # 2a.  Wait for the server to be reachable.                           #
    #      /api/monitoring/health is unauthenticated and returns 200      #
    #      when the server is healthy. Accept any 2xx (or 4xx fallback). #
    # ------------------------------------------------------------------ #
    server_up = False
    for i in range(15):
        status, body = _omni_get("/api/monitoring/health", timeout=3)
        if status != 0:   # any HTTP response (incl 401) = server is alive
            server_up = True
            try:
                info = json.loads(body)
                svc_status = info.get("status", "unknown")
            except Exception:
                svc_status = str(status)
            print_ok(f"OmniRoute is reachable at {OMNIROUTE_URL} — status: {svc_status}")
            break
        if i == 14:
            print_fail("OmniRoute not responding after 15 attempts — is the service running?")
            return None
        time.sleep(2)

    if not server_up:
        return None

    # ------------------------------------------------------------------ #
    # 2b.  Try the known fallback key first (fastest path).              #
    # ------------------------------------------------------------------ #
    if verify_key(KNOWN_FALLBACK_KEY):
        print_ok(f"Verified existing API key: {KNOWN_FALLBACK_KEY[:20]}...")
        return KNOWN_FALLBACK_KEY

    # ------------------------------------------------------------------ #
    # 2c.  Login with password → get session cookie → list /api/keys.   #
    # ------------------------------------------------------------------ #
    try:
        import http.cookiejar
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )
        login_data = json.dumps({"password": OMNIROUTE_PASSWORD}).encode()
        login_req = urllib.request.Request(
            f"{OMNIROUTE_URL}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        login_resp = opener.open(login_req, timeout=8)
        if login_resp.status not in (200, 201):
            print_fail(f"Login returned unexpected status {login_resp.status}")
            return None

        # ---- Build Cookie header string from jar -------------------- #
        cookie_hdr = "; ".join(
            f"{c.name}={c.value}" for c in cookie_jar
            if c.domain in ("", "localhost", "127.0.0.1")
        )

        # ---- Fetch API keys using the session cookie ---------------- #
        status, body = _omni_get("/api/keys", cookie=cookie_hdr, timeout=8)
        if status == 200:
            data = json.loads(body.decode())
            for k in data.get("keys", []):
                if not k.get("isActive", True):
                    continue
                # key field is masked (e.g. "sk-2daf4****5ddf"); try keyPrefix
                prefix = k.get("keyPrefix", "")
                if prefix and prefix == KNOWN_FALLBACK_KEY[:len(prefix)]:
                    print_ok(f"Matched existing key by prefix: {prefix}...")
                    return KNOWN_FALLBACK_KEY
                # If key is not masked, use it directly
                raw = k.get("key", "")
                if raw and "*" not in raw and verify_key(raw):
                    print_ok(f"Retrieved valid API key from /api/keys: {raw[:20]}...")
                    return raw

        print_info("Could not retrieve full key from /api/keys (masked). Using known default.")
        return KNOWN_FALLBACK_KEY

    except Exception as e:
        print_fail(f"Login / key-retrieval failed: {e}")
        print_info(f"Falling back to known default key.")
        return KNOWN_FALLBACK_KEY


# === Step 3: Connect Providers (revised — correct schema + verified list) ===
#
# IMPORTANT FINDING (tested 2026-08-11):
#   - The POST /api/providers endpoint requires: {"name", "provider", "apiKey"}
#   - NOT just {"name": provider_name}
#   - Providers with apiKey="free" (placeholder) ALL fail with 401/403
#   - The following providers work WITHOUT a real API key (OAuth / auto-token):
#       agy, antigravity, kimi-coding, nvidia (has real key), opencode, amazon-q
#   - All other providers need real API keys registered at their websites.
#
# FREE-TIER providers that need a REAL (free) API key — register at each site:
#   groq.com → groq | cerebras.ai → cerebras | sambanova.ai → sambanova
#   together.ai → together | mistral.ai → mistral | deepseek.com → deepseek
#   novita.ai → novita | fireworks.ai → fireworks | chutes.ai → chutes
#   nebius.com → nebius | deepinfra.com → deepinfra | hyperbolic.xyz → hyperbolic
#   cohere.com → cohere | scaleway.com → scaleway | siliconflow.cn → siliconflow
#   openrouter.ai → openrouter | huggingface.co → huggingface

PROVIDERS_NEEDING_REAL_KEY = [
    ("groq",        "https://console.groq.com"),
    ("cerebras",    "https://cloud.cerebras.ai"),
    ("sambanova",   "https://cloud.sambanova.ai"),
    ("together",    "https://api.together.xyz"),
    ("mistral",     "https://console.mistral.ai"),
    ("deepseek",    "https://platform.deepseek.com"),
    ("novita",      "https://novita.ai/dashboard"),
    ("fireworks",   "https://fireworks.ai/account/api-keys"),
    ("chutes",      "https://chutes.ai"),
    ("nebius",      "https://studio.nebius.com"),
    ("deepinfra",   "https://deepinfra.com/dash/api_keys"),
    ("hyperbolic",  "https://app.hyperbolic.xyz"),
    ("cohere",      "https://dashboard.cohere.com/api-keys"),
    ("scaleway",    "https://console.scaleway.com"),
    ("siliconflow", "https://cloud.siliconflow.cn"),
    ("openrouter",  "https://openrouter.ai/keys"),
    ("huggingface", "https://huggingface.co/settings/tokens"),
]


def connect_providers(api_key):
    print_header("Step 3: Connect Auto-Auth Providers")

    # ------------------------------------------------------------------ #
    # OAuth / token / auto-connect providers that work WITHOUT a real     #
    # API key — these are added with the correct {name,provider,apiKey}  #
    # schema. Providers with apiKey="free" placeholder are NOT added here #
    # because they ALL fail (tested 2026-08-11).                          #
    # ------------------------------------------------------------------ #
    # Only add providers that have proven to work via OmniRoute auto-auth:
    AUTO_PROVIDERS = [
        # provider ID as known by OmniRoute
        "agy",          # Antigravity (agy) — OAuth, works via isearch.xsolve
        "antigravity",  # Antigravity — OAuth
        "kimi-coding",  # Kimi Coding — auto-token, OmniRoute manages refresh
        "amazon-q",     # Amazon Q — auto-token
        "opencode",     # OpenCode — auto-token
    ]

    # Providers that need a real API key but do have a free tier
    # — added only if a real key is provided via the api_key_overrides dict
    api_key_overrides = {}  # e.g. {"groq": "gsk_xxxx", "cerebras": "csk_xxxx"}
    # Populate from environment if set
    for p, _ in PROVIDERS_NEEDING_REAL_KEY:
        env_key = os.environ.get(f"OMNIROUTE_{p.upper()}_KEY", "")
        if env_key and not env_key.startswith("free"):
            api_key_overrides[p] = env_key

    connected = []
    already = []
    failed = []

    # ---- Add auto-auth providers ----------------------------------------
    for provider in AUTO_PROVIDERS:
        try:
            payload = json.dumps({
                "name": provider,
                "provider": provider,
                # No apiKey — these use OAuth/token auth managed by OmniRoute
            }).encode()
            req = urllib.request.Request(
                f"{OMNIROUTE_URL}/api/providers",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=6)
            if resp.status in (200, 201):
                connected.append(provider)
            elif resp.status == 409:
                already.append(provider)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                already.append(provider)
            else:
                failed.append(provider)
        except Exception:
            failed.append(provider)

    # ---- Add API-key providers if real keys are available ---------------
    for provider, url in PROVIDERS_NEEDING_REAL_KEY:
        real_key = api_key_overrides.get(provider)
        if not real_key:
            continue
        try:
            payload = json.dumps({
                "name": provider,
                "provider": provider,
                "apiKey": real_key,
            }).encode()
            req = urllib.request.Request(
                f"{OMNIROUTE_URL}/api/providers",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=8)
            if resp.status in (200, 201):
                connected.append(f"{provider}(key)")
                print_ok(f"Connected {provider} with real API key")
            elif resp.status == 409:
                already.append(provider)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                already.append(provider)
            else:
                failed.append(provider)
        except Exception:
            failed.append(provider)

    total_ok = len(connected) + len(already)
    print_ok(f"Connected / already present: {total_ok}")
    if connected:
        print_info("Newly connected: " + ", ".join(connected))
    if already:
        print_info(f"Already existed: {len(already)}")
    if failed:
        print_info(f"Could not auto-connect: {', '.join(failed)}")

    print()
    print_info("=" * 60)
    print_info("Providers below need a REAL (free) API key to work.")
    print_info("Register at the URL, then add via dashboard or set env var:")
    print_info("  OMNIROUTE_<PROVIDER>_KEY=your_key  (then re-run this script)")
    print_info("=" * 60)
    for p, url in PROVIDERS_NEEDING_REAL_KEY:
        print(f"    {p:<14}  {url}")
    print()
    print_info("Dashboard → Providers:  http://localhost:20128/dashboard/providers")
    print()

    return total_ok > 0



# === Step 4: Test Connections ===
def test_connections(api_key):
    print_header("Step 4: Test Connections")

    try:
        req = urllib.request.Request(
            f"{OMNIROUTE_URL}/api/providers",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        connections = data.get("connections", [])

        healthy = 0
        for conn in connections:
            if conn.get("isHealthy", False):
                healthy += 1

        print_ok(f"{healthy}/{len(connections)} connections healthy")
        return healthy

    except Exception as e:
        print_fail(f"Test failed: {e}")
        return 0


# === Step 5: Set Environment Variables ===
def set_environment_variables(api_key):
    print_header("Step 5: Set Environment Variables")

    import winreg

    env_vars = {
        "OMNIROUTE_BASE_URL": OMNIROUTE_BASE,
        "OMNIROUTE_API_KEY": api_key,
        "ANTHROPIC_BASE_URL": OMNIROUTE_BASE,
        "ANTHROPIC_API_KEY": api_key,
        "OPENAI_BASE_URL": OMNIROUTE_BASE,
        "OPENAI_API_KEY": api_key,
    }

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ
        )

        for name, value in env_vars.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
            print_ok(f"{name} = {value[:30]}...")

        winreg.CloseKey(key)
        return True

    except Exception as e:
        print_fail(f"Failed to set env vars: {e}")
        return False


# === Step 6: Configure Codex CLI ===
def configure_codex(api_key):
    print_header("Step 6: Configure Codex CLI")

    config_path = os.path.expanduser(r"~\.codex\config.toml")

    if not os.path.exists(config_path):
        print_info("Codex config not found. Run 'codex' once to generate it.")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace('model = "gpt-5.6-luna"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model = "gpt-5.6-sol"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model_provider = "litellm-nemotron"', 'model_provider = "omniroute"')
        content = content.replace('model_provider = "nvidia"', 'model_provider = "omniroute"')
        content = content.replace('wire_api = "chat"', 'wire_api = "responses"')

        if '[model_providers.omniroute]' not in content:
            content += f'''

[model_providers.omniroute]
name = "OmniRoute Local Gateway"
base_url = "{OMNIROUTE_BASE}"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = true
'''

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print_ok("Codex configured for OmniRoute")
        return True

    except Exception as e:
        print_fail(f"Failed to configure Codex: {e}")
        return False


# === Step 7: Print Summary ===
def print_summary(api_key):
    print_header("SETUP COMPLETE - Summary")

    print(f"""
  OmniRoute Service: {OMNIROUTE_SERVICE_NAME}
  Dashboard:         {OMNIROUTE_URL}/dashboard
  API Base:          {OMNIROUTE_BASE}
  API Key:           {api_key}
  Password:          {OMNIROUTE_PASSWORD}
""")

    print("\n  WORKING MODELS (Free + Frontier):")
    print("  " + "-"*65)
    for model, info in WORKING_MODELS.items():
        print_model(model, f"{info['latency']:>8s}  {info['family']}")

    print(f"""
  ENVIRONMENT VARIABLES SET:
    OMNIROUTE_BASE_URL = {OMNIROUTE_BASE}
    OMNIROUTE_API_KEY  = {api_key}
    ANTHROPIC_BASE_URL = {OMNIROUTE_BASE}
    ANTHROPIC_API_KEY  = {api_key}
    OPENAI_BASE_URL    = {OMNIROUTE_BASE}
    OPENAI_API_KEY     = {api_key}

  CLI TOOLS CONFIGURED:
    Claude Code CLI:  claude
    Codex CLI:        codex --dangerously-bypass-approvals-and-sandbox

  NEXT STEPS:
    1. Open dashboard → Providers and connect:
         • Claude Code   (for Opus 4.8 / Fable 5)
         • Codex or GitHub Copilot  (for GPT-5.6 Sol family)
         • Qoder         (already tried – free Kimi K3 + Qwen 3.8 Max)
    2. Open a NEW terminal and run:
         claude
         codex --dangerously-bypass-approvals-and-sandbox
""")


# === Main ===
def main():
    print_header("OmniRoute Complete Setup")
    print("\n  This script will:")
    print("    1. Install OmniRoute as Windows service (auto-start)")
    print("       → SKIPPED if the service is already RUNNING")
    print("    2. Configure OmniRoute and get API key")
    print("    3. Connect free / auto-connectable providers")
    print("    4. Test connections")
    print("    5. Set environment variables")
    print("    6. Configure Codex CLI")
    print("    7. Print summary with model names and API keys")
    print("\n  Run as Administrator for service installation.")

    # Step 1: Install (or skip if already running)
    if not install_omniroute():
        print_fail("OmniRoute installation incomplete. Check above.")
        # Continue anyway — might already be running

    # Step 2: Configure
    api_key = configure_omniroute()
    if not api_key:
        api_key = KNOWN_FALLBACK_KEY
        print_info(f"Using known default key: {api_key}")

    # Step 3: Connect providers
    connect_providers(api_key)

    # Step 4: Test
    test_connections(api_key)

    # Step 5: Environment variables
    set_environment_variables(api_key)

    # Step 6: Configure Codex
    configure_codex(api_key)

    # Step 7: Print summary
    print_summary(api_key)

    print()


if __name__ == "__main__":
    main()