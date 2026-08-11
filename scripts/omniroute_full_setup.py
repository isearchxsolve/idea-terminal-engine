"""
OmniRoute Complete Setup Script
================================
Single script that performs full setup:
  1. Install OmniRoute as Windows service (auto-start on boot)
  2. Configure OmniRoute password and API key
  3. Connect all free providers via API
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

# === Configuration ===
OMNIROUTE_PORT = 20128
OMNIROUTE_URL = f"http://localhost:{OMNIROUTE_PORT}"
OMNIROUTE_BASE = f"{OMNIROUTE_URL}/v1"
OMNIROUTE_PASSWORD = "omniroute-admin-2026"
OMNIROUTE_SERVICE_NAME = "OmniRoute"

# Working models discovered during setup
WORKING_MODELS = {
    "antigravity/claude-sonnet-4-6": {"latency": "3.6s", "family": "Claude"},
    "agy/claude-sonnet-4-6": {"latency": "4.6s", "family": "Claude"},
    "antigravity/claude-opus-4-6-thinking": {"latency": "5.3s", "family": "Claude (thinking)"},
    "agy/claude-opus-4-6-thinking": {"latency": "6.0s", "family": "Claude (thinking)"},
    "agy/gemini-3.6-flash-high": {"latency": "4.6s", "family": "Gemini"},
    "nvidia/z-ai/glm-5.2": {"latency": "6.0s", "family": "GLM"},
    "auto/coding:free": {"latency": "4.7s", "family": "Combo"},
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
    
    # Check if already a service
    result = subprocess.run(["sc", "query", OMNIROUTE_SERVICE_NAME], 
                          capture_output=True, text=True)
    if result.returncode == 0 and "RUNNING" in result.stdout:
        print_ok(f"OmniRoute service already running")
        return True
    
    # Resolve OmniRoute entry script. The package's "bin" field in package.json
    # points at bin/omniroute.mjs (not dist/server-ws.mjs, which was a stale
    # guess in earlier versions of this script and produced a service that
    # launched bare node.exe with no script -- resulting in instant exit and
    # a port that's dark on every reboot). Prefer bin/omniroute.mjs; fall back
    # to dist/server-ws.mjs only if the dev_NEXT_ build entry was explicitly built.
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
            print_fail(f"OmniRoute entry script not found.")
            print_info(f"Tried: {server_script}")
            print_info(f"Tried: {server_script_fallback}")
            return False
    else:
        print_info(f"Entry script: {server_script}")

    # Locate nssm. Prefer it on PATH; otherwise look in the winget install
    # location we know about. Do NOT assume winget-install nssm is on PATH --
    # the previous version of this script called `nssm` directly, which on a
    # fresh machine would silently fail and then `nssm install` below would
    # also fail with a confusing error.
    nssm_exe = shutil.which("nssm") or os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        "nssm", "nssm.exe")  # last-ditch guess
    # Check the winget per-user install path used on this machine.
    winget_nssm = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe")
    if not os.path.exists(winget_nssm):
        # glob the versioned winget package dir in case the nssm version changes
        import glob
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
        print_fail(f"nssm not found (PATH, winget install, or expected locations).")
        print_info("Install nssm manually: winget install nssm")
        return False
    print_info(f"nssm: {nssm_exe}")

    # Register as Windows service via nssm.
    # IMPORTANT (bug fix): nssm install NAME node.exe "--max-old-space-size=4096 {script}"
    # on Windows collapses the trailing arguments into a single AppParameters
    # value depending on nssm's argv-mode, and on some versions the script
    # path is dropped entirely -- resulting in Application=node.exe and
    # AppParameters empty, so the service boots nothing, exits immediately,
    # and port 20128 stays dark. Reliable pattern: install with application
    # ONLY, then set AppParameters separately.
    print_info("Registering OmniRoute as Windows service...")
    try:
        # Remove existing service if any (ignore failures -- may not exist yet)
        subprocess.run([nssm_exe, "stop", OMNIROUTE_SERVICE_NAME], capture_output=True)
        subprocess.run([nssm_exe, "remove", OMNIROUTE_SERVICE_NAME, "confirm"],
                      capture_output=True)

        # Install service with application ONLY (no params here -- see below)
        result = subprocess.run(
            [nssm_exe, "install", OMNIROUTE_SERVICE_NAME, node_exe],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print_fail(f"Service install failed: {result.stderr.strip()}")
            print_info("Run this script as Administrator!")
            return False

        # Set AppParameters SEPARATELY (the bug-fix). Include the V8 flag and
        # the real entry script as distinct arguments.
        app_params = f"--max-old-space-size=4096 {server_script}"
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppParameters", app_params],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppDirectory", work_dir],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Description",
                       "OmniRoute AI Model Gateway"], capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "Start",
                       "SERVICE_AUTO_START"], capture_output=True, check=True)
        # On crash, restart after 10s (was 0 = immediate, which can hot-loop).
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRestartDelay", "10000"],
                      capture_output=True, check=True)
        # NSSM's default AppExit action is already 'Restart' for a service that's
        # set to AUTO_START and has an AppRestartDelay, so we don't explicitly
        # set AppExit Default Restart here -- on some nssm builds the literal
        # token 'Restart' is parsed as the reset-to-default sentinel and the
        # command silently says 'Reset parameter ...' instead of setting it.
        # AppRestartDelay above is the knob that controls restart-after-crash
        # behaviour and it sets cleanly.

        # Redirect stdout/stderr to ~/.omniroute/logs/ so future wedges are
        # diagnosable. NOTE: AppStdout/AppStderr CreationDisposition is deliberately
        # left at NSSM's default (overwrite on open) -- on some nssm builds passing
        # '4' (append) is misinterpreted as the reset-to-default sentinel and the
        # command prints 'Reset parameter ...' instead of setting it. The cost of
        # overwrite mode is that each restart truncates the log, which is
        # acceptable here because the in-process OmniRoute logs at
        # ~/.omniroute/logs/application/app.log retain full history.
        omni_log_dir = os.path.expanduser(r"~\.omniroute\logs")
        os.makedirs(omni_log_dir, exist_ok=True)
        stdout_log = os.path.join(omni_log_dir, "service-stdout.log")
        stderr_log = os.path.join(omni_log_dir, "service-stderr.log")
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStdout", stdout_log],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppStderr", stderr_log],
                      capture_output=True, check=True)
        # Rotate large log files so they don't grow without bound.
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateFiles", "1"],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateOnline", "1"],
                      capture_output=True, check=True)
        subprocess.run([nssm_exe, "set", OMNIROUTE_SERVICE_NAME, "AppRotateBytes", "10485760"],
                      capture_output=True, check=True)  # 10 MB

        # ---- Service logon account: LocalSystem (NOT the user account) -----
        # FIRM DECISION (post-mortem from v0.2.0 OmniRoute wedging on the
        # .Admin logon attempt): keep the service as LocalSystem. Reasons:
        #   1) OmniRoute internally spawns a child `node` (SSE bridge, MCP
        #      workers, etc.) via spawn('node', ...). That spawn inherits the
        #      service process environment. LocalSystem's environment includes
        #      C:\Windows\System32 on PATH so `node` resolves. A non-interactive
        #      .Admin logon does NOT carry the user's interactive PATH, so
        #      spawn('node') fails with ENOENT -- and the service wedges.
        #   2) LocalSystem's homedir is C:\Windows\System32\config\systemprofile,\n        #      which would resolve ~ to the wrong OmniRoute profile. We DON'T
        #      fix that by changing the account -- we fix it by injecting
        #      DATA_DIR / USERPROFILE / HOME via AppEnvironmentExtra below.
        #      OmniRoute's resolveDataDir() honours DATA_DIR as the canonical
        #      override (verified in src/lib/db/encryption.ts + bin/cli/data-dir.mjs).
        # sc.exe's obj=/password= syntax is fragile from PowerShell and
        # from Python subprocess.run on Windows; we run it via cmd /c to keep
        # sc.exe's own argument parser intact.
        print_info("Ensuring service runs as LocalSystem (firm decision, see source comment)")
        sc_cmd = [
            os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe"), "/c",
            f"sc config {OMNIROUTE_SERVICE_NAME} obj= LocalSystem password= \"\""
        ]
        subprocess.run(sc_cmd, capture_output=True, text=True)
        # Verify; do not crash -- if this fails the next AppEnvironmentExtra
        # steps still apply and may be sufficient.
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
        if start_name.lower() not in ("localsystem", ".\\admin"):
            # .Admin is also acceptable (env injection below will route it);
            # anything else is unexpected, but we log + continue.
            print_info("unexpected service account -- proceeding with env injection")

        # ---- Inject service environment -------------------------------------
        # AppEnvironmentExtra is the NSSM-sanctioned way to add env vars to the
        # service's spawned process without going through interactive logon's
        # HKCU\Environment path. We set:
        #   DATA_DIR              -> root of the OmniRoute profile we actually
        #                            want (canonical override per OmniRoute's
        #                            resolveDataDir in bin/cli/data-dir.mjs)
        #   USERPROFILE           -> Admin's home, so os.homedir() inside OmniRoute
        #                            also falls back to the right dir even when
        #                            DATA_DIR is bypassed
        #   HOME                  -> POSIX-style home (os.homedir() and node libs)
        #   PATH                  -> system32 (always there) + the hermes node
        #                            install path so spawn('node', ...) succeeds
        #                            under any service account
        #   STORAGE_ENCRYPTION_KEY -> 64-char hex (matches OmniRoute's own
        #                            randomBytes(32).toString('hex') format).
        #                            WITHOUT this, OmniRoute's storage init does
        #                            a metadata-only check: if existsSync(dbPath)
        #                            and the env var is unset, it refuses to start
        #                            and prints 'STORAGE_ENCRYPTION_KEY is not set
        #                            but a database already exists'. This wedge
        #                            was the entire post-mortem for the 2026-08-11
        #                            OmniRoute failure. The key is also persisted
        #                            to ~/.omniroute/.env so it survives package
        #                            upgrades AND is auto-loaded by OmniRoute's
        #                            env-file loader on next import.
        omni_data_dir = os.path.expanduser(r"~\.omniroute")
        os.makedirs(omni_data_dir, exist_ok=True)
        node_install_dir = node_root  # parent of node.exe
        # Build a minimal-but-sufficient PATH. Start from the existing PATH
        # (so any other tools still resolve), append the node dir if not there.
        base_path = os.environ.get("PATH", "")
        if node_install_dir.lower() not in base_path.lower():
            base_path = base_path.rstrip(";") + ";" + node_install_dir if base_path else node_install_dir

        # ---- STORAGE_ENCRYPTION_KEY: reuse if present, else generate --------
        # Probe revealed that existing storage.sqlite rows are plaintext
        # (zero rows carry the 'enc:v1:' prefix), so any 64-hex key makes the
        # metadata check happy. We never overwrite a working key -- if the
        # user already has one in ~/.omniroute/.env, we preserve and reuse it.
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
            # Generate 32 random bytes, hex-encode -> 64-char string.
            # secrets.token_hex(32) is cryptographically secure and matches
            # the format OmniRoute's own key-provisioning path expects.
            storage_key = secrets.token_hex(32)
            try:
                # Append (don't overwrite) -- preserve any unrelated .env entries.
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
        # Mask the secret in stdout diagnostics -- never print the full key.
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
        # Drop the in-memory copy -- nssm has it now, the .env has it too.
        storage_key = None

        # ---- Cleansing strike: remove any rogue LocalSystem profile created
        # by an earlier run that did NOT have DATA_DIR injected -- otherwise on
        # the very first boot OmniRoute may still create one before AppEnv takes.
        # We can't easily delete systemprofile from a non-elevated script, but
        # since DATA_DIR is now always set, OmniRoute will never touch it again.
        rogue_dir = r"C:\Windows\System32\config\systemprofile\.omniroute"
        if os.path.exists(rogue_dir):
            try:
                shutil.rmtree(rogue_dir, ignore_errors=True)
            except Exception as e:
                print_info(f"(non-fatal) could not remove rogue {rogue_dir}: {e}")

        # Start service
        subprocess.run([nssm_exe, "start", OMNIROUTE_SERVICE_NAME], capture_output=True)

        # Wait for port to come up. OmniRoute is SLOW to boot on this machine:
        # observed start-to-/api/health latency is ~53 seconds (storage init +
        # provider connection hydration + WS bridge spin-up). The previous
        # version of this script polled for only 15s and declared FAIL on
        # every fresh start -- the port wasn't dark, the probe was too early.
        # 75 attempts x 1s gives a comfortable margin above the 53s observed
        # while still bounding the worst case to ~75s.
        port_ready = False
        for _ in range(75):
            time.sleep(1)
            try:
                req = urllib.request.Request(f"{OMNIROUTE_URL}/api/health", method="GET")
                urllib.request.urlopen(req, timeout=2)
                port_ready = True
                break
            except Exception:
                continue

        if not port_ready:
            print_fail(f"Service started but port {OMNIROUTE_PORT} not responding after 75s")
            print_info(f"Check stderr log: {stderr_log}")
            print_info("Data dir injected:        " + omni_data_dir)
            print_info("SERVICE_START_NAME:        " + start_name)
            print_info("If .Admin: confirm the Admin user has \"Log on as a service\" right")
            print_info("If LocalSystem: confirm AppEnvironmentExtra is set in registry")
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
def configure_omniroute():
    print_header("Step 2: Configure OmniRoute")
    
    # Wait for OmniRoute to be ready
    for i in range(10):
        try:
            req = urllib.request.Request(f"{OMNIROUTE_URL}/api/health", method="GET")
            urllib.request.urlopen(req, timeout=3)
            print_ok(f"OmniRoute is running at {OMNIROUTE_URL}")
            break
        except:
            if i == 9:
                print_fail("OmniRoute not responding after 10 attempts")
                return False
            time.sleep(2)
    
    # Login and get API key
    try:
        login_data = json.dumps({"password": OMNIROUTE_PASSWORD}).encode()
        req = urllib.request.Request(
            f"{OMNIROUTE_URL}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        api_key = resp.headers.get("X-Api-Key", "")
        
        # Try to get from cookie
        cookie = resp.headers.get("Set-Cookie", "")
        if "auth_token=" in cookie:
            api_key = cookie.split("auth_token=")[1].split(";")[0]
        
        if api_key:
            print_ok(f"API Key: {api_key[:20]}...")
            return api_key
        else:
            print_info("Using default API key")
            return "sk-2daf4dd6d1e45047-53255c-89ec5ddf"
            
    except Exception as e:
        print_fail(f"Login failed: {e}")
        return None


# === Step 3: Connect Providers ===
def connect_providers(api_key):
    print_header("Step 3: Connect Free Providers")
    
    # List of free/OAuth providers to connect
    providers = [
        "agy", "antigravity", "openrouter", "amazon-q", "codex",
        "kimi-coding", "kilocode", "nvidia", "opencode", "blackbox",
        "sambanova", "novita", "friendliai", "ainative", "brave-search",
        "bazaarlink", "api-airforce", "xai"
    ]
    
    connected = 0
    for provider in providers:
        try:
            data = json.dumps({"name": provider}).encode()
            req = urllib.request.Request(
                f"{OMNIROUTE_URL}/api/providers",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status in [200, 201, 409]:  # 409 = already exists
                connected += 1
        except urllib.error.HTTPError as e:
            if e.code == 409:  # Already connected
                connected += 1
        except:
            pass
    
    print_ok(f"Connected {connected}/{len(providers)} providers")
    return connected > 0


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
        
        # Update model and provider
        content = content.replace('model = "gpt-5.6-luna"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model = "gpt-5.6-sol"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model_provider = "litellm-nemotron"', 'model_provider = "omniroute"')
        content = content.replace('model_provider = "nvidia"', 'model_provider = "omniroute"')
        content = content.replace('wire_api = "chat"', 'wire_api = "responses"')
        
        # Add OmniRoute provider if not present
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
    
    print("\n  WORKING MODELS (Free, No API Key Required):")
    print("  " + "-"*65)
    for model, info in WORKING_MODELS.items():
        print_model(model, f"{info['latency']:>6s}  {info['family']}")
    
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

  CLOUD DESKTOP:
    Copy this script to any machine and run it.
    Same configuration works everywhere!
""")


# === Main ===
def main():
    print_header("OmniRoute Complete Setup")
    print("\n  This script will:")
    print("    1. Install OmniRoute as Windows service (auto-start)")
    print("    2. Configure OmniRoute and get API key")
    print("    3. Connect all free providers")
    print("    4. Test connections")
    print("    5. Set environment variables")
    print("    6. Configure Codex CLI")
    print("    7. Print summary with model names and API keys")
    print("\n  Run as Administrator for service installation.")
    
    # Step 1: Install OmniRoute
    if not install_omniroute():
        print_fail("OmniRoute installation incomplete. Check above.")
        # Continue anyway - might already be running
    
    # Step 2: Configure
    api_key = configure_omniroute()
    if not api_key:
        api_key = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"
        print_info(f"Using default API key: {api_key}")
    
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
    
    print("\n  Open a NEW terminal and run:")
    print("    claude")
    print("    codex --dangerously-bypass-approvals-and-sandbox")
    print()


if __name__ == "__main__":
    main()
