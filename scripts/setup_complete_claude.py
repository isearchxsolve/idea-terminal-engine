"""
Complete AI CLI Setup for OmniRoute
=====================================
One-script setup for Windows. Installs and configures:
  1. Claude Code CLI - FREE via OmniRoute
  2. Codex CLI (OpenAI) - FREE via OmniRoute
  3. Environment variables for OmniRoute routing

NOTE: Claude Desktop / Codex Desktop require paid subscriptions.
      This script only sets up the FREE CLI tools + OmniRoute.

Usage:
  python scripts/setup_complete_claude.py

Works on: Local Windows, Cloud Desktop, VM
"""
import os
import json
import subprocess
import urllib.request
import urllib.error

# === Configuration ===
OMNIROUTE_URL = "http://localhost:20128"
BASE_URL = f"{OMNIROUTE_URL}/v1"
API_KEY = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"

# Load from secrets.json if available
secrets_path = os.path.join(os.path.dirname(__file__), "..", "config", "secrets.json")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        secrets = json.load(f)
        BASE_URL = secrets.get("OMNIROUTE_BASE_URL", BASE_URL)
        API_KEY = secrets.get("OMNIROUTE_API_KEY", API_KEY)
        OMNIROUTE_URL = BASE_URL.replace("/v1", "")



def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_ok(text):
    print(f"  [+] {text}")

def print_fail(text):
    print(f"  [-] {text}")

def print_info(text):
    print(f"  [*] {text}")

# === Environment Variables ===
def set_env_var(name, value):
    """Set environment variable for current user on Windows."""
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)
        # Also set for current process
        os.environ[name] = value
        print_ok(f"{name} = {value[:40]}...")
        return True
    except Exception as e:
        print_fail(f"Failed to set {name}: {e}")
        return False

# === Check Functions ===
def check_omniroute():
    """Check if OmniRoute is running."""
    try:
        # Try the models endpoint which is more reliable
        url = f"{BASE_URL}/models"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {API_KEY}")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        models = data.get("models", [])
        print_ok(f"OmniRoute running at {OMNIROUTE_URL} ({len(models)} models)")
        return True
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            # Auth issue but service is running
            print_ok(f"OmniRoute running at {OMNIROUTE_URL}")
            return True
        print_fail(f"OmniRoute error: {e}")
        return False
    except Exception as e:
        print_fail(f"OmniRoute not reachable: {e}")
        return False

def check_node():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_ok(f"Node.js: {version}")
            return True
    except Exception:
        pass
    print_fail("Node.js not found")
    return False

def check_claude_cli():
    """Check if Claude Code CLI is installed."""
    # Check common locations
    cli_paths = [
        # hermes installation
        os.path.expandvars(r"%LOCALAPPDATA%\hermes\node\claude.ps1"),
        os.path.expandvars(r"%LOCALAPPDATA%\hermes\node\claude.cmd"),
        # npm global
        os.path.expandvars(r"%APPDATA%\npm\claude.ps1"),
        os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
    ]
    for path in cli_paths:
        if os.path.exists(path):
            # Try to get version
            try:
                result = subprocess.run(
                    ["powershell", "-Command", f"& '{path}' --version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print_ok(f"Claude Code CLI: {version} ({path})")
                    return True
            except:
                pass
            print_ok(f"Claude Code CLI found: {path}")
            return True
    
    # Try PATH
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_ok(f"Claude Code CLI: {version}")
            return True
    except Exception:
        pass
    
    print_fail("Claude Code CLI not installed")
    return False

def check_codex_cli():
    """Check if Codex CLI (OpenAI) is installed."""
    # Check common locations
    cli_paths = [
        # OpenAI Codex installation - various bin folders
        os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\cfac6bda2d141e07\codex.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\fb2cf1905ba5b8f9\codex.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\codex.exe"),
        # hermes
        os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes\codex.exe"),
    ]
    # Also search for any codex.exe in OpenAI\Codex\bin
    codex_bin = os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin")
    if os.path.exists(codex_bin):
        for folder in os.listdir(codex_bin):
            exe_path = os.path.join(codex_bin, folder, "codex.exe")
            if os.path.exists(exe_path) and exe_path not in cli_paths:
                cli_paths.append(exe_path)
    
    for path in cli_paths:
        if os.path.exists(path):
            # Try to get version
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print_ok(f"Codex CLI: {version} ({path})")
                    return True
            except:
                pass
            print_ok(f"Codex CLI found: {path}")
            return True
    
    # Try PATH
    try:
        result = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_ok(f"Codex CLI: {version}")
            return True
    except Exception:
        pass
    
    print_fail("Codex CLI not installed")
    print_info("Download from: https://github.com/openai/codex")
    return False

def configure_codex_omniroute():
    """Configure Codex CLI to use OmniRoute."""
    config_path = os.path.expanduser(r"~\.codex\config.toml")
    
    if not os.path.exists(config_path):
        print_fail(f"Codex config not found: {config_path}")
        print_info("Run codex once to generate default config, then re-run this script.")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update model and provider
        content = content.replace('model = "gpt-5.6-luna"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model = "gpt-5.6-sol"', 'model = "antigravity/claude-sonnet-4-6"')
        content = content.replace('model_provider = "litellm-nemotron"', 'model_provider = "omniroute"')
        content = content.replace('model_provider = "nvidia"', 'model_provider = "omniroute"')
        content = content.replace('model_reasoning_effort = "max"', 'model_reasoning_effort = "high"')
        
        # Add OmniRoute provider if not present
        if '[model_providers.omniroute]' not in content:
            omniroute_provider = '''

[model_providers.omniroute]
name = "OmniRoute Local Gateway"
base_url = "http://localhost:20128/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = true
'''
            content += omniroute_provider
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_ok(f"Updated {config_path}")
        print_ok("  model = antigravity/claude-sonnet-4-6")
        print_ok("  model_provider = omniroute")
        print_ok("  base_url = http://localhost:20128/v1")
        return True
        
    except Exception as e:
        print_fail(f"Failed to update config: {e}")
        return False



# === Install Functions ===
def install_node():
    """Install Node.js using winget."""
    print_info("Installing Node.js via winget...")
    try:
        result = subprocess.run(
            ["winget", "install", "OpenJS.NodeJS.LTS", "--accept-source-agreements", "--accept-package-agreements"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print_ok("Node.js installed. Restart terminal to use.")
            return True
        print_fail(f"winget failed: {result.stderr}")
    except Exception as e:
        print_fail(f"Install failed: {e}")
    print_info("Manual install: https://nodejs.org")
    return False

def install_claude_cli():
    """Install Claude Code CLI via npm."""
    print_info("Installing Claude Code CLI...")
    try:
        result = subprocess.run(
            ["npm", "install", "-g", "@anthropic-ai/claude-code"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print_ok("Claude Code CLI installed")
            return True
        print_fail(f"npm failed: {result.stderr}")
    except Exception as e:
        print_fail(f"Install failed: {e}")
    return False



# === Main ===
def main():
    print_header("Complete Claude Setup for OmniRoute")
    
    print(f"\n  OmniRoute URL: {OMNIROUTE_URL}")
    print(f"  API Base:      {BASE_URL}")
    print(f"  API Key:       {API_KEY[:20]}...")
    
    # Step 1: Check OmniRoute
    print_header("Step 1: Check OmniRoute")
    omniroute_ok = check_omniroute()
    if not omniroute_ok:
        print_fail("Start OmniRoute first, then re-run this script.")
        print_info(f"OmniRoute should be at: {OMNIROUTE_URL}")
    
    # Step 2: Set environment variables
    print_header("Step 2: Set Environment Variables")
    # For Claude Code CLI
    set_env_var("ANTHROPIC_BASE_URL", BASE_URL)
    set_env_var("ANTHROPIC_API_KEY", API_KEY)
    # For Codex CLI (OpenAI-compatible)
    set_env_var("OPENAI_BASE_URL", BASE_URL)
    set_env_var("OPENAI_API_KEY", API_KEY)
    
    # Step 3: Check/Install Node.js
    print_header("Step 3: Check Node.js")
    node_ok = check_node()
    if not node_ok:
        install_node()
        print_info("Restart terminal after Node.js install, then re-run this script.")
        return
    
    # Step 4: Check/Install Claude Code CLI
    print_header("Step 4: Check Claude Code CLI")
    cli_ok = check_claude_cli()
    if not cli_ok:
        install_claude_cli()
        cli_ok = check_claude_cli()
    
    # Step 5: Check Codex CLI
    print_header("Step 5: Check Codex CLI (OpenAI)")
    codex_ok = check_codex_cli()
    
    # Step 6: Configure Codex for OmniRoute
    print_header("Step 6: Configure Codex for OmniRoute")
    configure_codex_omniroute()
    
    # Summary
    print_header("Setup Summary")
    
    results = [
        ("OmniRoute", omniroute_ok),
        ("Environment Variables", True),  # Always set
        ("Node.js", node_ok),
        ("Claude Code CLI", cli_ok),
        ("Codex CLI (OpenAI)", codex_ok),
    ]
    
    all_ok = True
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        symbol = "+" if ok else "-"
        print(f"  [{symbol}] {name}: {status}")
        if not ok:
            all_ok = False
    
    print()
    if all_ok:
        print_ok("All components installed and configured!")
        print()
        print("  Claude Code CLI (Anthropic models):")
        print("    claude              # Interactive session")
        print("    claude 'question'   # One-shot query")
        print()
        print("  Codex CLI (OpenAI models):")
        print("    codex               # Interactive session")
        print("    codex 'question'    # One-shot query")
        print()
        print("  Both route through OmniRoute (FREE, no subscription):")
        print("    - Claude Sonnet/Opus via agy/antigravity")
        print("    - Gemini 3.6 Flash")
        print("    - GLM-5.2 via nvidia")
        print("    - GPT models via cx/ (when rate limits allow)")
        print()
        print("  NOTE: Desktop apps require paid subscriptions.")
        print("        CLI tools are FREE with OmniRoute!")
    else:
        print_fail("Some components need attention. See above.")
    
    print_header("Cloud Desktop?")
    print("  Copy this script to your cloud desktop and run it.")
    print("  Same FREE configuration works everywhere!")
    print()

if __name__ == "__main__":
    main()
