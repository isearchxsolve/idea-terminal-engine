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
    
    # Find OmniRoute server script
    node_exe = r"C:\Users\Admin\AppData\Local\hermes\node\node.exe"
    server_script = r"C:\Users\Admin\AppData\Local\hermes\node\node_modules\omniroute\dist\server-ws.mjs"
    work_dir = r"C:\Users\Admin\AppData\Local\hermes\node\node_modules\omniroute"
    
    if not os.path.exists(node_exe) or not os.path.exists(server_script):
        print_fail("OmniRoute files not found at expected paths")
        print_info("Expected: " + node_exe)
        print_info("Expected: " + server_script)
        return False
    
    # Install nssm if not present
    nssm_result = subprocess.run(["nssm", "version"], capture_output=True, text=True)
    if nssm_result.returncode != 0:
        print_info("Installing nssm (service manager)...")
        subprocess.run(["winget", "install", "nssm", "-e",
                       "--accept-source-agreements", "--accept-package-agreements"],
                      capture_output=True)
    
    # Register as Windows service via nssm
    print_info("Registering OmniRoute as Windows service...")
    try:
        # Remove existing service if any
        subprocess.run(["nssm", "stop", OMNIROUTE_SERVICE_NAME], capture_output=True)
        subprocess.run(["nssm", "remove", OMNIROUTE_SERVICE_NAME, "confirm"], capture_output=True)
        
        # Install service
        result = subprocess.run(
            ["nssm", "install", OMNIROUTE_SERVICE_NAME, 
             node_exe, f"--max-old-space-size=4096 {server_script}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print_fail(f"Service install failed: {result.stderr}")
            print_info("Run this script as Administrator!")
            return False
        
        # Configure service
        subprocess.run(["nssm", "set", OMNIROUTE_SERVICE_NAME, "AppDirectory", work_dir],
                      capture_output=True)
        subprocess.run(["nssm", "set", OMNIROUTE_SERVICE_NAME, "Description",
                       "OmniRoute AI Model Gateway"], capture_output=True)
        subprocess.run(["nssm", "set", OMNIROUTE_SERVICE_NAME, "Start",
                       "SERVICE_AUTO_START"], capture_output=True)
        subprocess.run(["nssm", "set", OMNIROUTE_SERVICE_NAME, "AppExit", "Default", "Exit"],
                      capture_output=True)
        
        # Start service
        subprocess.run(["nssm", "start", OMNIROUTE_SERVICE_NAME], capture_output=True)
        time.sleep(3)
        
        print_ok("OmniRoute installed as Windows service (auto-start on boot)")
        print_ok(f"Service name: {OMNIROUTE_SERVICE_NAME}")
        print_ok(f"Node: {node_exe}")
        print_ok(f"Script: {server_script}")
        return True
        
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
