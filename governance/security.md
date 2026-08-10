# Security

- Avoid destructive commands by default.
- Avoid credential exposure: never log/commit API keys. Environment variables or `config/` only. Secrets in `.gitignore`.
- Avoid arbitrary network access unless required by a verified task.
- Identify dangerous commands before execution.
- Require explicit human approval for irreversible operations (delete, deploy, spend budget, push to public).
- Per-run isolation: an idea thread may not write outside `clients/<client-id>/<run-id>/`. Engine code is read-only from any run thread.
- `.gitignore` at repo root MUST exclude: `config/secrets.json`, `.env`, any `clients/**/logs/*` containing raw model output if it may include secrets, `__pycache__/`, `.venv/`, node_modules.
