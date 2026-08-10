"""Test the actual ORCHESTRATOR call pattern to debug JSON extraction."""
import json, urllib.request, sys
sys.path.insert(0, ".")
from engine.agents.runners import call_model, _extract_json

raw = open("scripts/selftest_idea.txt").read()
print(f"Raw idea length: {len(raw)} chars")
print(f"First 200 chars: {raw[:200]}")
print()

# Simulate the actual call
try:
    text = call_model("ORCHESTRATOR",
                      f"Distill this raw idea.\nRAW IDEA:\n{raw}")
    print(f"Model returned {len(text)} chars:")
    print(repr(text[:500]))
    print()
    
    extracted = _extract_json(text)
    print(f"Extracted JSON ({len(extracted)} chars):")
    print(extracted[:500])
    print()
    
    parsed = json.loads(extracted)
    print(f"Parsed keys: {list(parsed.keys())}")
    print("SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
