# Master portability prompt

Paste this into a fresh thread (any assistant/IDE) on a new machine to port the engine.

```
You are porting the IDEA-TERMINAL-ENGINE repository to this machine.
Rules: never copy clients/ run data or config/secrets.json; never commit secrets;
do not add paid dependencies or new infrastructure.

1. Copy/clone the repo (exclude clients/ and config/secrets.json).
2. Verify Python >= 3.9, git present. Install pytest only (dev dependency).
3. From repo root run: python -m pytest tests/ -v  — all must pass, no inference used.
4. Run: python -m engine.cli doctor — environment checks must pass; the inference
   check may report NOT WIRED until runners.py is configured for this machine.
5. Create config/secrets.json from config/secrets.example.json with this machine's
   NIM credentials. Keep it gitignored.
6. Report: python version, pytest result, doctor result, any path or config drift.
Do not run client ideas during porting. Stop and report on any failure.
```
