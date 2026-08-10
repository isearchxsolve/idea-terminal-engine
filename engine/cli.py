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
        print(f"models.json roles: {len(cfg.load_models()['roles'])}")
    except Exception as exc:  # noqa: BLE001 - doctor reports, never crashes
        ok = False
        print(f"models.json: ERROR {exc}")
    try:
        cfg.load_qa_floor()
        print("qa_floor.json: ok")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"qa_floor.json: ERROR {exc}")
    print(f"inference: NOT WIRED (scaffold) — {NOT_WIRED}")
    return 0 if ok else 1


def _cmd_selftest(args):
    import time as _time
    from engine import orchestrator
    from engine.agents.runners import InferenceCallError
    run_id = f"st-{int(_time.time())}"
    run_dir = runmod.create_run(
        "selftest", run_id, str(paths.SCRIPTS_DIR / "selftest_idea.txt"),
        source_type="text", source_ref="phase9")
    try:
        state = orchestrator.run_to_terminal(run_dir)
    except InferenceCallError as exc:
        print(f"selftest: inference unavailable: {exc}")
        return 2
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
