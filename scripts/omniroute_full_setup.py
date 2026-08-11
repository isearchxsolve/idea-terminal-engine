"""
OmniRoute Complete Setup Script
================================
Single script that performs full setup:
  1. Install OmniRoute as Windows service (auto-start on boot)
     → SKIPPED entirely if the service is already RUNNING
  2. Configure OmniRoute password and API key
  3. Connect free / auto-connectable providers
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

KNOWN_FALLBACK_KEY = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"

# Working models (updated Aug 2026 - Deep Scan Verified)
WORKING_MODELS = {
    # ==========================================
    # VERIFIED WORKING CLASS
    # ==========================================
    "agy/claude-sonnet-4-6": {"latency": "~5.0s", "family": "Claude Sonnet 4.6 (Antigravity)"},
    "antigravity/claude-sonnet-4-6": {"latency": "~8.4s", "family": "Claude Sonnet 4.6 (Antigravity)"},
    "agy/gemini-3.6-flash-high": {"latency": "~4.8s", "family": "Gemini 3.6 Flash (Antigravity)"},
    "nvidia/gpt-oss-20b": {"latency": "~2.6s", "family": "GPT-OSS 20B (NVIDIA)"},
    
    # ==========================================
    # AUTO-ROUTERS (Fallback clusters)
    # ==========================================
    "auto/coding:free": {"latency": "varies", "family": "Auto Combo (Free)"},
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

    result = subprocess.run(
        ["sc", "query", OMNIROUTE_SERVICE_NAME],
        capture_output=True, text=True
    )
    if result.returncode == 0 and "RUNNING" in result.stdout:
        print_ok("OmniRoute service is already RUNNING — skipping install/stop/start")
        return True

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
            return False
    else:
        print_info(f"Entry script: {server_script}")

    nssm_exe = shutil.which("nssm") or os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"), "nssm", "nssm.exe")
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
        print_info("Installing nssm via winget...")
        subprocess.run(["winget", "install", "nssm", "-e",
                       "--accept-source-agreements", "--accept-package-agreements"],
                      capture_output=True)
        nssm_exe = shutil.which("nssm") or nssm_exe
    if not os.path.exists(nssm_exe):
        print_fail("nssm not found. Install with: winget install nssm")
        return False
    print_info(f"nssm: {nssm_exe}")

    print_info("Registering OmniRoute as Windows service...")
    try:
        subprocess.run([nssm_exe, "stop", OMNIROUTE_SERVICE_NAME], capture_output=True)
        subprocess.run([nssm_exe, "remove", OMNIROUTE_SERVICE_NAME, "confirm"], capture_output=True)

        result = subprocess.run(
            [nssm_exe, "install", OMNIROUTE_SERVICE_NAME, node_exe],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print_fail(f"Service install failed: {result.stderr.strip()}")
            print_info("Run this script as Administrator!")
            return False

        app_params = f"--max-old-space-size=4096 {server_script}"
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppParameters", app_params], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppDirectory", work_dir], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Description", "OmniRoute AI Model Gateway"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Start", "SERVICE_AUTO_START"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRestartDelay", "10000"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppThrottle", "30000"], capture_output=True, check=True)

        omni_log_dir = os.path.expanduser(r"~\.omniroute\logs")
        os.makedirs(omni_log_dir, exist_ok=True)
        stdout_log = os.path.join(omni_log_dir, "service-stdout.log")
        stderr_log = os.path.join(omni_log_dir, "service-stderr.log")
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStdout", stdout_log], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStderr", stderr_log], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateFiles", "1"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateOnline", "1"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateBytes", "10485760"], capture_output=True, check=True)

        print_info("Ensuring service runs as LocalSystem")
        sc_cmd = [os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"), "/c",
                  f"sc config {OMNIROUTE_SERVICE_NAME} obj= LocalSystem password= \"\""]
        subprocess.run(sc_cmd, capture_output=True, text=True)

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
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppEnvironmentExtra", *env_entries],
                      capture_output=True, check=True)

        rogue_dir = r"C:\Windows\System32\config\systemprofile\.omniroute"
        if os.path.exists(rogue_dir):
            try:
                shutil.rmtree(rogue_dir, ignore_errors=True)
            except Exception:
                pass

        subprocess.run([nssm_exe, "start", OMNIROUTE_SERVICE_NAME], capture_output=True)

        port_ready = False
        for _ in range(75):
            time.sleep(1)
            try:
                req = urllib.request.Request(f"{OMNIROUTE_URL}/api/monitoring/health", method="GET")
                urllib.request.urlopen(req, timeout=2)
                port_ready = True
                break
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    port_ready = True
                    break
            except Exception:
                continue

        if not port_ready:
            print_fail(f"Service started but port {OMNIROUTE_PORT} not responding after 75s")
            return False

        print_ok("OmniRoute installed as Windows service (auto-start on boot)")
        return True

    except Exception as e:
        print_fail(f"Service installation error: {e}")
        print_info("Run this script as Administrator!")
        return False


def _omni_get(path, cookie=None, bearer=None, timeout=8):
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
    status, _ = _omni_get("/v1/models", bearer=key, timeout=20)
    if status == 200:
        return True
    if status == 0:
        body = json.dumps({
            "model": "if/kimi-k3",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }).encode()
        req = urllib.request.Request(
            f"{OMNIROUTE_URL}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=15)
            return True
        except urllib.error.HTTPError as e:
            return e.code not in (401, 403)
        except Exception:
            pass
    return False


def configure_omniroute():
    print_header("Step 2: Configure OmniRoute")

    server_up = False
    for i in range(15):
        status, body = _omni_get("/api/monitoring/health", timeout=3)
        if status != 0:
            server_up = True
            try:
                info = json.loads(body)
                svc_status = info.get("status", "unknown")
            except Exception:
                svc_status = str(status)
            print_ok(f"OmniRoute is reachable — status: {svc_status}")
            break
        if i == 14:
            print_fail("OmniRoute not responding after 15 attempts")
            return None
        time.sleep(2)

    if not server_up:
        return None

    if verify_key(KNOWN_FALLBACK_KEY):
        print_ok(f"Verified existing API key: {KNOWN_FALLBACK_KEY[:20]}...")
        return KNOWN_FALLBACK_KEY

    try:
        import http.cookiejar
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        login_data = json.dumps({"password": OMNIROUTE_PASSWORD}).encode()
        login_req = urllib.request.Request(
            f"{OMNIROUTE_URL}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        opener.open(login_req, timeout=8)

        cookie_hdr = "; ".join(f"{c.name}={c.value}" for c in cookie_jar
                               if c.domain in ("", "localhost", "127.0.0.1"))
        status, body = _omni_get("/api/keys", cookie=cookie_hdr, timeout=8)
        if status == 200:
            data = json.loads(body.decode())
            for k in data.get("keys", []):
                if not k.get("isActive", True):
                    continue
                prefix = k.get("keyPrefix", "")
                if prefix and prefix == KNOWN_FALLBACK_KEY[:len(prefix)]:
                    print_ok(f"Matched existing key by prefix: {prefix}...")
                    return KNOWN_FALLBACK_KEY
                raw = k.get("key", "")
                if raw and "*" not in raw and verify_key(raw):
                    print_ok(f"Retrieved valid API key: {raw[:20]}...")
                    return raw

        print_info("Using known default key")
        return KNOWN_FALLBACK_KEY
    except Exception as e:
        print_fail(f"Login / key-retrieval failed: {e}")
        return KNOWN_FALLBACK_KEY


PROVIDERS_NEEDING_REAL_KEY = [
    ("groq", "https://console.groq.com"),
    ("cerebras", "https://cloud.cerebras.ai"),
    ("sambanova", "https://cloud.sambanova.ai"),
    ("together", "https://api.together.xyz"),
    ("mistral", "https://console.mistral.ai"),
    ("deepseek", "https://platform.deepseek.com"),
    ("novita", "https://novita.ai/dashboard"),
    ("fireworks", "https://fireworks.ai/account/api-keys"),
    ("openrouter", "https://openrouter.ai/keys"),
    ("huggingface", "https://huggingface.co/settings/tokens"),
]


def connect_providers(api_key):
    print_header("Step 3: Connect Auto-Auth Providers")

    AUTO_PROVIDERS = ["agy", "antigravity", "kimi-coding", "amazon-q", "opencode"]

    api_key_overrides = {}
    for p, _ in PROVIDERS_NEEDING_REAL_KEY:
        env_key = os.environ.get(f"OMNIROUTE_{p.upper()}_KEY", "")
        if env_key and not env_key.startswith("free"):
            api_key_overrides[p] = env_key

    connected, already, failed = [], [], []

    for provider in AUTO_PROVIDERS:
        try:
            payload = json.dumps({"name": provider, "provider": provider}).encode()
            req = urllib.request.Request(
                f"{OMNIROUTE_URL}/api/providers",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
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

    for provider, url in PROVIDERS_NEEDING_REAL_KEY:
        real_key = api_key_overrides.get(provider)
        if not real_key:
            continue
        try:
            payload = json.dumps({"name": provider, "provider": provider, "apiKey": real_key}).encode()
            req = urllib.request.Request(
                f"{OMNIROUTE_URL}/api/providers",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=8)
            if resp.status in (200, 201):
                connected.append(f"{provider}(key)")
            elif resp.status == 409:
                already.append(provider)
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
    print_info("Providers that need a real free API key:")
    for p, url in PROVIDERS_NEEDING_REAL_KEY:
        print(f"    {p:<14}  {url}")
    print()
    print_info("Dashboard -> Providers:  http://localhost:20128/dashboard/providers")
    print()
    return total_ok > 0


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
        healthy = sum(1 for c in connections if c.get("isHealthy", False))
        print_ok(f"{healthy}/{len(connections)} connections healthy")
        return healthy
    except Exception as e:
        print_fail(f"Test failed: {e}")
        return 0


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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0,
                             winreg.KEY_SET_VALUE | winreg.KEY_READ)
        for name, value in env_vars.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
            print_ok(f"{name} = {value[:30]}...")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print_fail(f"Failed to set env vars: {e}")
        return False


def configure_codex(api_key):
    print_header("Step 6: Configure Codex CLI")
    config_path = os.path.expanduser(r"~\.codex\config.toml")
    if not os.path.exists(config_path):
        print_info("Codex config not found. Run 'codex' once to generate it.")
        return False
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('model = "gpt-5.6-luna"', 'model = "if/kimi-k3"')
        content = content.replace('model = "gpt-5.6-sol"', 'model = "if/kimi-k3"')
        content = content.replace('model_provider = "litellm-nemotron"', 'model_provider = "omniroute"')
        content = content.replace('model_provider = "nvidia"', 'model_provider = "omniroute"')
        content = content.replace('wire_api = "chat"', 'wire_api = "responses"')

        if '[model_providers.omniroute]' not in content:
            content += f'''

[model_providers.omniroute]
api_url = "{OMNIROUTE_URL}"
api_key = "{api_key}"
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
  Local Endpoint:    {OMNIROUTE_URL}
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
    ... and Anthropic / OpenAI mappings.

  CLIENTS CONFIGURED:
    Claude Code CLI:  claude
    Codex CLI:        codex --dangerously-bypass-approvals-and-sandbox

  NEXT STEPS:
    1. Open dashboard -> Providers and connect:
         - Claude Code   (for Opus 4.8 / Fable 5)
         - Codex or GitHub Copilot  (for GPT-5.6 Sol family)
         - Qoder         (already tried - free Kimi K3 + Qwen 3.8 Max)
    2. Open a NEW terminal and run:
         claude
         codex --dangerously-bypass-approvals-and-sandbox
""")


def main():
    print_header("OmniRoute Complete Setup")
    print("\n  This script will:")
    print("    1. Install OmniRoute as Windows service (auto-start)")
    print("       -> SKIPPED if the service is already RUNNING")
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
        # Continue anyway - might already be running

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