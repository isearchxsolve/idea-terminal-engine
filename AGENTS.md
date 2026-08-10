# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Overview

Idea-to-prototype engine that drives raw ideas to verified, running prototypes via autonomous AI agents. Uses OmniRoute as the local inference gateway to route calls across multiple LLM providers (Claude, Gemini, GLM, GPT).

## Commands

```bash
# Run all tests
python -m pytest tests/ -x -q

# Run single test file
python -m pytest tests/test_orchestrator.py -x -q

# Start a new idea run
python -m engine.cli new --client <client-id> --run <run-id> --source path/to/idea.txt --source-type text --source-ref "reference"

# Check run status
python -m engine.cli status --client <client-id> --run <run-id>

# Advance run by one step
python -m engine.cli step --client <client-id> --run <run-id>
```

## Architecture

### Pipeline Flow
```
RECEIVED → DISTILLED → BLUEPRINTED → PLANNED → BUILDING → QA_VERIFYING → RELEASED
                                                    ↓              ↓
                                                REPAIRING ← AWAITING_APPROVAL
                                                    ↓
                                                 FAILED (any state can fail)
```

### Agent Roles (config/models.json)
Each role maps to a specific model with fallback chains:
- **ORCHESTRATOR**: Coordinates pipeline, claude-opus-4-6-thinking
- **BLUEPRINT**: Architecture design, claude-sonnet-4-6
- **PLAN**: Execution planning, claude-sonnet-4-6
- **BUILDER_DRAFT/BUILDER_FINAL**: Code generation, gemini-3.6-flash-high / claude-sonnet-4-6
- **BEHOLDER**: Evidence review, claude-opus-4-6-thinking
- **QA**: Verification, gemini-3.6-flash-high
- **REPAIR_DIAG/REPAIR_APPLY**: Bug fixing, claude-opus/sonnet
- **RELEASE**: Final release, claude-opus-4-6-thinking

### Inference Layer (engine/agents/runners.py)
- `call_model(role, prompt, context)` - Single call with automatic fallback
- `call_json(role, prompt, context)` - Call + robust JSON extraction
- Error classes: `InferenceCallError` (network/rate) vs `VerificationFailureError` (logic) - NEVER conflate
- All calls go through `RateLimiter` and `BudgetTracker`

### Configuration
- `config/models.json` - Provider endpoints, role→model mapping, fallback chains
- `config/secrets.json` - API keys (gitignored), loads via `load_secrets()`
- `config/engine.toml` - Runtime settings (timeouts, max tokens, pacing)

### State Management
- Each run lives in `clients/<client-id>/<run-id>/`
- `state.json` tracks current state machine position
- Artifacts written to subdirectories: `intake/`, `blueprint/`, `execution/`, `artifacts/`, `verification/`, `gtm/`

### Key Conventions
- Python stdlib only (no external deps except pytest for tests)
- All inference calls paced via `RateLimiter.acquire()`/`release()`
- JSON extraction from LLM output handles markdown code blocks, raw JSON, or embedded JSON
- Terminal states (RELEASED, FAILED) are absorbing - no transitions out
- `AWAITING_APPROVAL` is a human gate for critical actions

## OmniRoute Integration

Local gateway at `http://localhost:20128/v1` routes to multiple providers:
- Working models: `antigravity/claude-*`, `agy/claude-*`, `agy/gemini-*`, `nvidia/z-ai/glm-5.2`
- Fallback chains ensure resilience when models are rate-limited or down
- Environment variables: `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`

## Governance

See `governance/` for:
- `rules.md` - Core engineering rules
- `THREADING.md` - Two-thread contract (engine thread vs idea threads)
- `definition-of-done.md` - Completion criteria
- `security.md` - Security constraints
