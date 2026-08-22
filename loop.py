import sys
from pathlib import Path
from engine.run import create_run
from engine.orchestrator import run_to_terminal

run_dir = Path("clients/client-001/run-011")
if not run_dir.exists():
    create_run("client-001", "run-011", "Build a high-performance, hardened key-value caching service with TTL expiry, thread-safe memory storage, and status dashboard.", source_ref="engine")
    print(f"Created fresh run at {run_dir}")

print(f"Starting {run_dir} to terminal...")
final_state = run_to_terminal(str(run_dir), max_steps=200)
print(f"Finished with final state: {final_state}")
