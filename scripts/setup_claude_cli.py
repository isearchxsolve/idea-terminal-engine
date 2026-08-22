"""
OmniRoute + Claude Code CLI Setup
===================================
Configures Claude Code CLI to use OmniRoute as the API backend.
Works on any machine (local Windows, cloud desktop, VM, etc.)

Requirements:
  - OmniRoute running on localhost:20128 (or change BASE_URL below)
  - Node.js installed (for Claude Code CLI)
  - Claude Code CLI installed: npm install -g @anthropic-ai/claude-code

Usage:
  python scripts/setup_claude_cli.py
  # Or on cloud desktop, just copy this script and run it.
"""
import os
import sys
import json
import subprocess

# Configuration - change these if needed
BASE_URL = "http://localhost:20128/v1"
API_KEY = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"

# Also load from secrets.json if available
secrets_path = os.path.join(os.path.dirname(__file__), "..", "config", "secrets.json")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        secrets = json.load(f)
        BASE_URL = secrets.get("OMNIROUTE_BASE_URL", BASE_URL)
        API_KEY = secrets.get("OMNIROUTE_API_KEY", API_KEY)

def set_env_var_windows(name, value):
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
        print(f"  [+] Set {name} = {value[:30]}...")
        return True
    except Exception as e:
        print(f"  [-] Failed to set {name}: {e}")
        return False

def set_env_var_unix(name, value):
    """Set environment variable in shell profile on Linux/Mac."""
    shell = os.environ.get("SHELL", "/bin/bash")
    if "zsh" in shell:
        profile = os.path.expanduser("~/.zshrc")
    else:
        profile = os.path.expanduser("~/.bashrc")
    
    line = f'export {name}="{value}"\n'
    
    # Check if already set
    if os.path.exists(profile):
        with open(profile) as f:
            content = f.read()
            if name in content:
                print(f"  [*] {name} already in {profile}")
                return True
    
    with open(profile, "a") as f:
        f.write("\n# OmniRoute + Claude Code CLI\n")
        f.write(line)
    print(f"  [+] Added {name} to {profile}")
    return True

def check_omniroute():
    """Check if OmniRoute is running."""
    import urllib.request
    import urllib.error
    try:
        url = BASE_URL.replace("/v1", "") + "/api/health"
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=5)
        print(f"  [+] OmniRoute is running at {BASE_URL.replace('/v1', '')}")
        return True
    except Exception as e:
        print(f"  [-] OmniRoute not reachable: {e}")
        print("      Start OmniRoute first, or change BASE_URL in this script.")
        return False

def check_claude_cli():
    """Check if Claude Code CLI is installed."""
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  [+] Claude Code CLI: {version}")
            return True
    except Exception:
        pass
    print("  [-] Claude Code CLI not found.")
    print("      Install with: npm install -g @anthropic-ai/claude-code")
    return False

def main():
    print("=" * 60)
    print("OmniRoute + Claude Code CLI Setup")
    print("=" * 60)
    
    # Check prerequisites
    print("\n[1] Checking prerequisites...")
    omniroute_ok = check_omniroute()
    claude_ok = check_claude_cli()
    
    # Set environment variables
    print("\n[2] Setting environment variables...")
    if sys.platform == "win32":
        set_env_var_windows("ANTHROPIC_BASE_URL", BASE_URL)
        set_env_var_windows("ANTHROPIC_API_KEY", API_KEY)
    else:
        set_env_var_unix("ANTHROPIC_BASE_URL", BASE_URL)
        set_env_var_unix("ANTHROPIC_API_KEY", API_KEY)
    
    # Also set for current process
    os.environ["ANTHROPIC_BASE_URL"] = BASE_URL
    os.environ["ANTHROPIC_API_KEY"] = API_KEY
    
    print(f"\n  BASE_URL: {BASE_URL}")
    print(f"  API_KEY:  {API_KEY[:20]}...")
    
    # Summary
    print("\n" + "=" * 60)
    if omniroute_ok and claude_ok:
        print("Setup complete! Claude Code CLI is ready to use.")
        print("\nTo use:")
        print("  claude           # Start interactive session")
        print("  claude 'query'   # One-shot query")
        print("\nNote: Open a NEW terminal for env vars to take effect.")
    else:
        print("Setup partial. Fix the issues above and re-run.")
        if not omniroute_ok:
            print("\n  OmniRoute: Download from https://omniroute.dev")
        if not claude_ok:
            print("\n  Claude CLI: npm install -g @anthropic-ai/claude-code")
    print("=" * 60)

if __name__ == "__main__":
    main()
