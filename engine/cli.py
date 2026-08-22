"""CLI entrypoint: new / status / step / doctor / selftest."""
from __future__ import annotations

import argparse
import platform
import shutil
import sys

from engine import config as cfg
from engine import paths, run as runmod

NOT_WIRED = ("requires inference wiring — see governance/RETURN_HANDOVER.md "
             "and governance/MODEL_ROUTING.md")


def _cmd_new(args):
    run_dir = runmod.create_run(
        args.client, args.run, args.source,
        source_type=args.source_type, source_ref=args.source_ref,
    )
    print(f"run created: {run_dir} (state=RECEIVED)")
    return 0


def _cmd_status(args):
    run_dir = paths.run_dir(args.client, args.run)
    print(f"{args.client}/{args.run}: {runmod.load_state(run_dir)}")
    return 0


def _cmd_step(args):
    from engine import orchestrator
    from engine.agents.runners import InferenceCallError
    run_dir = paths.run_dir(args.client, args.run)
    try:
        print(f"state -> {orchestrator.step(run_dir)}")
        return 0
    except InferenceCallError as exc:
        print(f"step: inference unavailable: {exc}")
        return 2


def _cmd_doctor(args):
    import json as _json
    import urllib.request as _urlopen
    ok = True
    print(f"python: {platform.python_version()}")
    print(f"os: {platform.platform()}")
    print(f"git: {shutil.which('git') or 'NOT FOUND'}")
    for name in ("engine.toml", "models.json", "qa_floor.json", "secrets.example.json"):
        present = paths.config_path(name).exists()
        print(f"config/{name}: {'ok' if present else 'MISSING'}")
        ok = ok and present
    print("config/secrets.json: "
          + ("present (gitignored)" if paths.config_path("secrets.json").exists()
             else "absent (expected until wiring)"))
    try:
        models_cfg = cfg.load_models()
        print(f"models.json roles: {len(models_cfg['roles'])}")
    except Exception as exc:  # noqa: BLE001 - doctor reports, never crashes
        ok = False
        print(f"models.json: ERROR {exc}")
    try:
        cfg.load_qa_floor()
        print("qa_floor.json: ok")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"qa_floor.json: ERROR {exc}")
    # Live inference probe via OmniRoute
    try:
        from engine.agents.runners import load_secrets, role_model
        provider_cfg = models_cfg["providers"]["omniroute"]
        import os as _os
        secrets = load_secrets()
        base_url = (_os.environ.get(provider_cfg["base_url_env"])
                    or secrets.get(provider_cfg["base_url_env"])
                    or provider_cfg.get("default_base_url"))
        api_key = (_os.environ.get(provider_cfg["api_key_env"])
                   or secrets.get(provider_cfg["api_key_env"]) or "omni")
        # Probe /models endpoint
        models_url = base_url.rstrip("/") + "/models"
        req = _urlopen.Request(models_url,
                               headers={"Authorization": f"Bearer {api_key}"})
        with _urlopen.urlopen(req, timeout=10) as resp:
            model_list = _json.loads(resp.read().decode("utf-8"))
        n_models = len(model_list.get("data", []))
        print(f"omniroute: ok ({n_models} models available)")
        # Quick inference test with a lightweight role
        test_role = "BUILDER_DRAFT"  # free model, cheapest probe
        routing = role_model(test_role)
        body = _json.dumps({
            "model": routing["model"],
            "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
            "max_tokens": 16, "stream": False,
        }).encode("utf-8")
        inf_req = _urlopen.Request(
            base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"}, method="POST")
        with _urlopen.urlopen(inf_req, timeout=60) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"].strip()
        if text:
            print(f"inference: LIVE ({routing['model']} -> {text[:60]!r})")
        else:
            print("inference: EMPTY RESPONSE — model returned nothing")
            ok = False
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"inference: FAIL ({exc})")
    # Show active routing table
    try:
        print("\nActive routing:")
        for role, entry in models_cfg["roles"].items():
            print(f"  {role:16s} -> {entry['model']}")
    except Exception:
        pass
    return 0 if ok else 1


def _cmd_selftest(args):
    import time as _time
    from engine import orchestrator
    run_id = f"st-{int(_time.time())}"
    run_dir = runmod.create_run(
        "selftest", run_id, str(paths.SCRIPTS_DIR / "selftest_idea.txt"),
        source_type="text", source_ref="phase9")
    print("selftest: running with MOCK providers.")
    from engine.agents import runners
    def mock_call_json(role, prompt, context=None, limiter=None, budget=None):
        if role == "ORCHESTRATOR":
            return {
                "idea": {"content": "c", "validation_status": "ok"},
                "requirements": {"flows": [{"id": "f1"}], "edge_cases": [{"id": "e1"}]}
            }
        elif role == "BLUEPRINT":
            return {"components": [], "interfaces": [], "data_flow": "d", "tech_choices": []}
        elif role == "PLAN":
            return {"tasks": [{"id": "T1", "type": "code", "dependencies": [], "acceptance_criteria": ["python -V"], "budget": {}}]}
        elif role == "BUILDER_DRAFT" or role == "BUILDER_FINAL":
            return {"files": {"mock.py": "print('ok')"}}
        elif role == "BEHOLDER":
            return {"passed": True}
        elif role == "QA":
            tests = [{"id": f"Q{i}", "command": "python -V", "requirement_id": "f1", "assertions": ["displays ok"]} for i in range(250)]
            return {"tests": tests}
        elif role == "RELEASE":
            return {"gtm_surface_url": "http://mock.local"}
        return {}
    runners.call_json = mock_call_json
    state = orchestrator.run_to_terminal(run_dir)
    print(f"selftest final state: {state}")
    print("BOOTSTRAP_STATUS:")
    print("PASS" if state == "RELEASED" else "FAILED")
    return 0 if state == "RELEASED" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="engine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="create an isolated run from an intake source")
    p.add_argument("--client", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--source-type", default="text")
    p.add_argument("--source-ref", default="unknown")
    p.set_defaults(fn=_cmd_new)

    p = sub.add_parser("status", help="print run state")
    p.add_argument("--client", required=True)
    p.add_argument("--run", required=True)
    p.set_defaults(fn=_cmd_status)

    p = sub.add_parser("step", help="run one orchestrator step (needs wiring)")
    p.add_argument("--client", required=True)
    p.add_argument("--run", required=True)
    p.set_defaults(fn=_cmd_step)

    p = sub.add_parser("doctor", help="environment + config discovery")
    p.set_defaults(fn=_cmd_doctor)

    p = sub.add_parser("selftest", help="Phase 9 synthetic run (needs wiring)")
    p.set_defaults(fn=_cmd_selftest)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
