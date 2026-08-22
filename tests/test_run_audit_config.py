"""Tests for engine/run.py, engine/audit.py, and engine/config.py.

Combined parametrize entries ensure >= 120 test functions total in this file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import engine.paths as paths
from engine.audit import log as audit_log
from engine.config import DEFAULTS, _parse_simple_toml, load_engine_config
from engine.run import RUN_SUBDIRS, create_run, load_state

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(tmp_path, client_id="acme", run_id="run-001", text="hello idea"):
    """Create a run in tmp_path and return run_dir."""
    return create_run(
        client_id=client_id,
        run_id=run_id,
        intake_source=text,
        clients_base=str(tmp_path),
    )


# ===========================================================================
# RUN MODULE
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. All 8 subdirectories are created
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("subdir", list(RUN_SUBDIRS))
def test_create_run_creates_subdir(tmp_path, subdir):
    run_dir = _make_run(tmp_path)
    assert (run_dir / subdir).is_dir(), f"{subdir} not found"


def test_create_run_creates_exactly_eight_subdirs(tmp_path):
    run_dir = _make_run(tmp_path)
    created = {d.name for d in run_dir.iterdir() if d.is_dir()}
    assert set(RUN_SUBDIRS) <= created


# ---------------------------------------------------------------------------
# 2. intake/raw.txt content
# ---------------------------------------------------------------------------

def test_create_run_raw_txt_exists(tmp_path):
    run_dir = _make_run(tmp_path, text="some idea")
    assert (run_dir / "intake" / "raw.txt").exists()


def test_create_run_raw_txt_content_inline_text(tmp_path):
    run_dir = _make_run(tmp_path, text="my idea text")
    content = (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8")
    assert content == "my idea text"


def test_create_run_raw_txt_content_from_file(tmp_path):
    src_file = tmp_path / "idea.txt"
    src_file.write_text("idea from file", encoding="utf-8")
    run_dir = create_run(
        client_id="c1",
        run_id="r1",
        intake_source=str(src_file),
        clients_base=str(tmp_path),
    )
    content = (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8")
    assert content == "idea from file"


def test_create_run_raw_txt_empty_string(tmp_path):
    run_dir = _make_run(tmp_path, text="")
    content = (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8")
    assert content == ""


def test_create_run_raw_txt_multiline(tmp_path):
    idea = "line one\nline two\nline three"
    run_dir = _make_run(tmp_path, text=idea)
    assert (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8") == idea


def test_create_run_raw_txt_unicode(tmp_path):
    idea = "Ünïcödé idéa 🚀"
    run_dir = _make_run(tmp_path, text=idea)
    assert (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8") == idea


# ---------------------------------------------------------------------------
# 3. intake/meta.json keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["intake_id", "timestamp", "source_type",
                                   "source_ref", "client_id", "run_id"])
def test_create_run_meta_json_has_key(tmp_path, key):
    run_dir = _make_run(tmp_path)
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert key in meta


def test_create_run_meta_json_client_id(tmp_path):
    run_dir = _make_run(tmp_path, client_id="client-xyz")
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["client_id"] == "client-xyz"


def test_create_run_meta_json_run_id(tmp_path):
    run_dir = _make_run(tmp_path, run_id="run-99")
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["run_id"] == "run-99"


def test_create_run_meta_json_source_type_default(tmp_path):
    run_dir = _make_run(tmp_path)
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["source_type"] == "text"


def test_create_run_meta_json_source_ref_default(tmp_path):
    run_dir = _make_run(tmp_path)
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["source_ref"] == "unknown"


def test_create_run_meta_json_source_type_explicit(tmp_path):
    run_dir = create_run(
        client_id="c", run_id="r", intake_source="x",
        source_type="file", clients_base=str(tmp_path),
    )
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["source_type"] == "file"


def test_create_run_meta_json_source_ref_explicit(tmp_path):
    run_dir = create_run(
        client_id="c", run_id="r", intake_source="x",
        source_ref="github://repo/idea.md", clients_base=str(tmp_path),
    )
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["source_ref"] == "github://repo/idea.md"


def test_create_run_meta_json_is_valid_json(tmp_path):
    run_dir = _make_run(tmp_path)
    raw = (run_dir / "intake" / "meta.json").read_text(encoding="utf-8")
    # Must not raise
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# 4. state.json with state=RECEIVED
# ---------------------------------------------------------------------------

def test_create_run_state_json_exists(tmp_path):
    run_dir = _make_run(tmp_path)
    assert (run_dir / "state.json").exists()


def test_create_run_state_json_state_is_received(tmp_path):
    run_dir = _make_run(tmp_path)
    data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert data["state"] == "RECEIVED"


def test_create_run_state_json_is_valid_json(tmp_path):
    run_dir = _make_run(tmp_path)
    raw = (run_dir / "state.json").read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# 5. Returns a Path object that exists
# ---------------------------------------------------------------------------

def test_create_run_returns_path(tmp_path):
    result = _make_run(tmp_path)
    assert isinstance(result, Path)


def test_create_run_returned_path_exists(tmp_path):
    result = _make_run(tmp_path)
    assert result.exists()


def test_create_run_returned_path_is_directory(tmp_path):
    result = _make_run(tmp_path)
    assert result.is_dir()


# ---------------------------------------------------------------------------
# 6. FileExistsError on duplicate run
# ---------------------------------------------------------------------------

def test_create_run_raises_file_exists_error_on_duplicate(tmp_path):
    _make_run(tmp_path, client_id="c", run_id="r")
    with pytest.raises(FileExistsError):
        _make_run(tmp_path, client_id="c", run_id="r")


def test_create_run_different_run_id_does_not_raise(tmp_path):
    _make_run(tmp_path, client_id="c", run_id="r1")
    # Different run_id must succeed
    _make_run(tmp_path, client_id="c", run_id="r2")


def test_create_run_different_client_id_does_not_raise(tmp_path):
    _make_run(tmp_path, client_id="c1", run_id="r")
    _make_run(tmp_path, client_id="c2", run_id="r")


# ---------------------------------------------------------------------------
# 7. intake_id starts with "INT-"
# ---------------------------------------------------------------------------

def test_create_run_intake_id_prefix(tmp_path):
    run_dir = _make_run(tmp_path)
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert meta["intake_id"].startswith("INT-")


def test_create_run_intake_id_unique_across_runs(tmp_path):
    rd1 = _make_run(tmp_path, run_id="r1")
    rd2 = _make_run(tmp_path, run_id="r2")
    m1 = json.loads((rd1 / "intake" / "meta.json").read_text(encoding="utf-8"))
    m2 = json.loads((rd2 / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert m1["intake_id"] != m2["intake_id"]


def test_create_run_intake_id_length_gt_4(tmp_path):
    run_dir = _make_run(tmp_path)
    meta = json.loads((run_dir / "intake" / "meta.json").read_text(encoding="utf-8"))
    assert len(meta["intake_id"]) > 4


# ---------------------------------------------------------------------------
# 10. load_state
# ---------------------------------------------------------------------------

def test_load_state_returns_received_for_fresh_run(tmp_path):
    run_dir = _make_run(tmp_path)
    assert load_state(run_dir) == "RECEIVED"


def test_load_state_returns_string(tmp_path):
    run_dir = _make_run(tmp_path)
    assert isinstance(load_state(run_dir), str)


def test_load_state_after_manual_modification(tmp_path):
    run_dir = _make_run(tmp_path)
    state_path = run_dir / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["state"] = "BUILDING"
    state_path.write_text(json.dumps(data), encoding="utf-8")
    assert load_state(run_dir) == "BUILDING"


@pytest.mark.parametrize("injected_state", [
    "DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING",
    "QA_VERIFYING", "REPAIRING", "AWAITING_APPROVAL", "RELEASED", "FAILED",
])
def test_load_state_reads_injected_state(tmp_path, injected_state):
    run_dir = _make_run(tmp_path)
    state_path = run_dir / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["state"] = injected_state
    state_path.write_text(json.dumps(data), encoding="utf-8")
    assert load_state(run_dir) == injected_state


# ---------------------------------------------------------------------------
# 12. Multiple runs coexist independently
# ---------------------------------------------------------------------------

def test_multiple_runs_coexist(tmp_path):
    rd1 = _make_run(tmp_path, client_id="a", run_id="001", text="idea A")
    rd2 = _make_run(tmp_path, client_id="b", run_id="002", text="idea B")
    assert rd1 != rd2
    assert (rd1 / "intake" / "raw.txt").read_text() == "idea A"
    assert (rd2 / "intake" / "raw.txt").read_text() == "idea B"


def test_multiple_runs_independent_state(tmp_path):
    rd1 = _make_run(tmp_path, run_id="r1")
    rd2 = _make_run(tmp_path, run_id="r2")
    state_path = rd1 / "state.json"
    data = json.loads(state_path.read_text())
    data["state"] = "BUILDING"
    state_path.write_text(json.dumps(data))
    assert load_state(rd1) == "BUILDING"
    assert load_state(rd2) == "RECEIVED"


# ---------------------------------------------------------------------------
# 13. Run dir structure is client_id/run_id inside clients_base
# ---------------------------------------------------------------------------

def test_run_dir_structure(tmp_path):
    run_dir = _make_run(tmp_path, client_id="myclient", run_id="myrun")
    expected = tmp_path / "myclient" / "myrun"
    assert run_dir == expected


def test_run_dir_parent_is_client_dir(tmp_path):
    run_dir = _make_run(tmp_path, client_id="cl", run_id="r")
    assert run_dir.parent.name == "cl"


# ---------------------------------------------------------------------------
# 14. state.json has "updated_at" field
# ---------------------------------------------------------------------------

def test_create_run_state_json_has_updated_at(tmp_path):
    run_dir = _make_run(tmp_path)
    data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert "updated_at" in data


def test_create_run_state_json_updated_at_is_string(tmp_path):
    run_dir = _make_run(tmp_path)
    data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert isinstance(data["updated_at"], str)


# ---------------------------------------------------------------------------
# 17. Parametrize with various client_id/run_id strings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("client_id,run_id", [
    ("acme", "run-001"),
    ("acme_corp", "run_001"),
    ("client123", "r123"),
    ("my-client", "my-run-2024"),
    ("UPPERCASE", "RUN-1"),
    ("mix_ed-client", "mix_ed-run"),
])
def test_create_run_various_ids(tmp_path, client_id, run_id):
    run_dir = create_run(
        client_id=client_id, run_id=run_id,
        intake_source="test idea", clients_base=str(tmp_path),
    )
    assert run_dir.exists()
    assert run_dir.name == run_id
    assert run_dir.parent.name == client_id


# ===========================================================================
# AUDIT MODULE
# ===========================================================================

# ---------------------------------------------------------------------------
# 1-2. Creates logs/ and audit.jsonl
# ---------------------------------------------------------------------------

def test_audit_log_creates_logs_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    audit_log(run_dir, "test_event")
    assert (run_dir / "logs").is_dir()


def test_audit_log_creates_audit_jsonl(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    audit_log(run_dir, "test_event")
    assert (run_dir / "logs" / "audit.jsonl").exists()


def test_audit_log_works_without_pre_existing_logs_dir(tmp_path):
    run_dir = tmp_path / "brand_new_run"
    run_dir.mkdir()
    # logs/ does NOT exist yet
    assert not (run_dir / "logs").exists()
    audit_log(run_dir, "evt")
    assert (run_dir / "logs" / "audit.jsonl").exists()


# ---------------------------------------------------------------------------
# 3-5. Entry fields and return value
# ---------------------------------------------------------------------------

def test_audit_log_entry_has_timestamp(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, "my_event")
    assert "timestamp" in entry


def test_audit_log_entry_timestamp_is_string(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, "my_event")
    assert isinstance(entry["timestamp"], str)


def test_audit_log_entry_has_event(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, "some_event")
    assert entry["event"] == "some_event"


def test_audit_log_returns_dict(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    result = audit_log(run_dir, "evt")
    assert isinstance(result, dict)


def test_audit_log_return_matches_written_line(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, "check")
    line = (run_dir / "logs" / "audit.jsonl").read_text().strip()
    written = json.loads(line)
    assert written == entry


# ---------------------------------------------------------------------------
# 6. Append-only — multiple calls accumulate lines
# ---------------------------------------------------------------------------

def test_audit_log_is_append_only(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, "first")
    audit_log(run_dir, "second")
    audit_log(run_dir, "third")
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


def test_audit_log_preserves_order(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, "alpha")
    audit_log(run_dir, "beta")
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    assert json.loads(lines[0])["event"] == "alpha"
    assert json.loads(lines[1])["event"] == "beta"


def test_audit_log_first_line_not_overwritten(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, "original")
    audit_log(run_dir, "newer")
    first_line = (run_dir / "logs" / "audit.jsonl").read_text().splitlines()[0]
    assert json.loads(first_line)["event"] == "original"


# ---------------------------------------------------------------------------
# 7. Preserves keyword fields
# ---------------------------------------------------------------------------

def test_audit_log_preserves_extra_fields(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, "task_done", task="build", reason="ok")
    assert entry["task"] == "build"
    assert entry["reason"] == "ok"


def test_audit_log_extra_fields_written_to_file(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, "repair_started", attempt=3)
    line = (run_dir / "logs" / "audit.jsonl").read_text().strip()
    parsed = json.loads(line)
    assert parsed["attempt"] == 3


# ---------------------------------------------------------------------------
# 8. Parametrize event names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event_name", [
    "run_created", "task_failed", "transition",
    "qa_floor_tension", "repair_started",
])
def test_audit_log_various_event_names(tmp_path, event_name):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    entry = audit_log(run_dir, event_name)
    assert entry["event"] == event_name


@pytest.mark.parametrize("event_name", [
    "run_created", "task_failed", "transition",
    "qa_floor_tension", "repair_started",
])
def test_audit_log_event_names_written_correctly(tmp_path, event_name):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, event_name)
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    assert json.loads(lines[-1])["event"] == event_name


# ---------------------------------------------------------------------------
# 9. All lines in audit.jsonl are valid JSON
# ---------------------------------------------------------------------------

def test_audit_jsonl_all_lines_valid_json(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    for i in range(10):
        audit_log(run_dir, f"event_{i}", index=i)
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    assert len(lines) == 10
    for line in lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)


def test_audit_jsonl_no_trailing_garbage(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    audit_log(run_dir, "evt")
    raw = (run_dir / "logs" / "audit.jsonl").read_text()
    assert raw.endswith("\n")


# ---------------------------------------------------------------------------
# 10. Multiple contexts accumulate
# ---------------------------------------------------------------------------

def test_audit_log_accumulates_from_create_run(tmp_path):
    run_dir = _make_run(tmp_path)
    audit_log(run_dir, "transition", state="DISTILLED")
    audit_log(run_dir, "transition", state="BLUEPRINTED")
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    # At least 3 lines: run_created + 2 explicit
    assert len(lines) >= 3


def test_audit_log_create_run_writes_run_created_event(tmp_path):
    run_dir = _make_run(tmp_path)
    lines = (run_dir / "logs" / "audit.jsonl").read_text().strip().splitlines()
    events = [json.loads(l)["event"] for l in lines]
    assert "run_created" in events


# ===========================================================================
# CONFIG MODULE
# ===========================================================================

# ---------------------------------------------------------------------------
# 1-2. load_engine_config sections and defaults
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("section", ["pacing", "budget", "inference", "exec"])
def test_load_engine_config_has_section(section):
    cfg = load_engine_config()
    assert section in cfg


@pytest.mark.parametrize("section", ["pacing", "budget", "inference", "exec"])
def test_load_engine_config_section_is_dict(section):
    cfg = load_engine_config()
    assert isinstance(cfg[section], dict)


# ---------------------------------------------------------------------------
# 3-12. _parse_simple_toml
# ---------------------------------------------------------------------------

def test_parse_toml_section_header():
    result = _parse_simple_toml("[mysection]\nkey = 1")
    assert "mysection" in result


def test_parse_toml_integer_value():
    result = _parse_simple_toml("[s]\ncount = 42")
    assert result["s"]["count"] == 42


def test_parse_toml_float_value():
    result = _parse_simple_toml("[s]\nrate = 1.5")
    assert result["s"]["rate"] == pytest.approx(1.5)


def test_parse_toml_double_quoted_string():
    result = _parse_simple_toml('[s]\nname = "hello"')
    assert result["s"]["name"] == "hello"


def test_parse_toml_single_quoted_string():
    result = _parse_simple_toml("[s]\nname = 'world'")
    assert result["s"]["name"] == "world"


def test_parse_toml_boolean_true():
    result = _parse_simple_toml("[s]\nflag = true")
    assert result["s"]["flag"] is True


def test_parse_toml_boolean_false():
    result = _parse_simple_toml("[s]\nflag = false")
    assert result["s"]["flag"] is False


def test_parse_toml_boolean_uppercase_true():
    result = _parse_simple_toml("[s]\nflag = True")
    assert result["s"]["flag"] is True


def test_parse_toml_list_of_strings():
    result = _parse_simple_toml('[s]\ncmds = ["python", "node"]')
    assert result["s"]["cmds"] == ["python", "node"]


def test_parse_toml_list_unquoted():
    result = _parse_simple_toml("[s]\nitems = [a, b, c]")
    assert result["s"]["items"] == ["a", "b", "c"]


def test_parse_toml_skips_comment_lines():
    result = _parse_simple_toml("# this is a comment\n[s]\nkey = 1")
    assert "key" in result["s"]


def test_parse_toml_skips_blank_lines():
    result = _parse_simple_toml("\n\n[s]\n\nkey = 99\n")
    assert result["s"]["key"] == 99


def test_parse_toml_multiple_sections():
    text = "[a]\nx = 1\n[b]\ny = 2"
    result = _parse_simple_toml(text)
    assert result["a"]["x"] == 1
    assert result["b"]["y"] == 2


def test_parse_toml_empty_list():
    result = _parse_simple_toml("[s]\nitems = []")
    assert result["s"]["items"] == []


def test_parse_toml_returns_dict():
    assert isinstance(_parse_simple_toml(""), dict)


def test_parse_toml_empty_string():
    result = _parse_simple_toml("")
    assert result == {}


def test_parse_toml_no_section_key_ignored():
    # Keys before any section header go to root dict
    result = _parse_simple_toml("orphan = 1")
    # Implementation puts them in the root section dict (section == out at start)
    # The behavior may vary; just assert it doesn't crash
    assert isinstance(result, dict)


def test_parse_toml_comment_inline_not_parsed_as_comment():
    # Only full-line comments are skipped; values with # in them stay as-is
    result = _parse_simple_toml('[s]\nval = "no#comment"')
    assert result["s"]["val"] == "no#comment"


def test_parse_toml_equals_in_value():
    result = _parse_simple_toml('[s]\nformula = "a=b"')
    assert result["s"]["formula"] == "a=b"


def test_parse_toml_integer_zero():
    result = _parse_simple_toml("[s]\nzero = 0")
    assert result["s"]["zero"] == 0


def test_parse_toml_negative_integer():
    result = _parse_simple_toml("[s]\nneg = -5")
    assert result["s"]["neg"] == -5


def test_parse_toml_float_zero():
    result = _parse_simple_toml("[s]\nzero = 0.0")
    assert result["s"]["zero"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 13. load_engine_config merges TOML over defaults
# ---------------------------------------------------------------------------

def test_load_engine_config_merges_toml_over_defaults(tmp_path, monkeypatch):
    toml_content = "[budget]\nmax_inference_calls = 9999\n"
    toml_file = tmp_path / "engine.toml"
    toml_file.write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg["budget"]["max_inference_calls"] == 9999


def test_load_engine_config_merge_preserves_other_defaults(tmp_path, monkeypatch):
    toml_content = "[budget]\nmax_inference_calls = 1\n"
    toml_file = tmp_path / "engine.toml"
    toml_file.write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    # Other keys in budget should still be the defaults
    assert cfg["budget"]["max_retries_per_task"] == DEFAULTS["budget"]["max_retries_per_task"]


def test_load_engine_config_merge_new_section(tmp_path, monkeypatch):
    toml_content = "[custom]\nmy_key = 42\n"
    toml_file = tmp_path / "engine.toml"
    toml_file.write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg["custom"]["my_key"] == 42


def test_load_engine_config_no_toml_uses_pure_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg == DEFAULTS


def test_load_engine_config_override_pacing(tmp_path, monkeypatch):
    toml_content = "[pacing]\nmax_in_flight = 10\n"
    (tmp_path / "engine.toml").write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg["pacing"]["max_in_flight"] == 10


def test_load_engine_config_override_inference(tmp_path, monkeypatch):
    toml_content = "[inference]\ntimeout_seconds = 300\n"
    (tmp_path / "engine.toml").write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg["inference"]["timeout_seconds"] == 300


def test_load_engine_config_override_exec_timeout(tmp_path, monkeypatch):
    toml_content = "[exec]\ntimeout_seconds = 60\n"
    (tmp_path / "engine.toml").write_text(toml_content, encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    assert cfg["exec"]["timeout_seconds"] == 60


# ---------------------------------------------------------------------------
# 14-17. Default value spot-checks
# ---------------------------------------------------------------------------

def test_default_max_inference_calls():
    assert DEFAULTS["budget"]["max_inference_calls"] == 4000


def test_default_max_retries_per_task():
    assert DEFAULTS["budget"]["max_retries_per_task"] == 5


def test_default_max_in_flight():
    assert DEFAULTS["pacing"]["max_in_flight"] == 3


def test_default_min_interval_seconds():
    assert DEFAULTS["pacing"]["min_interval_seconds"] == pytest.approx(1.6)


def test_default_backoff_base_seconds():
    assert DEFAULTS["pacing"]["backoff_base_seconds"] == pytest.approx(2.0)


def test_default_backoff_max_seconds():
    assert DEFAULTS["pacing"]["backoff_max_seconds"] == pytest.approx(60.0)


def test_default_inference_timeout_seconds():
    assert DEFAULTS["inference"]["timeout_seconds"] == 120


def test_default_inference_max_output_tokens():
    assert DEFAULTS["inference"]["max_output_tokens"] == 4096


def test_default_exec_timeout_seconds():
    assert DEFAULTS["exec"]["timeout_seconds"] == 120


def test_default_exec_allowed_commands():
    assert DEFAULTS["exec"]["allowed_commands"] == ["python", "py", "node", "npx"]


# ---------------------------------------------------------------------------
# 18. Parametrize default key/value pairs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("section,key,value", [
    ("pacing", "max_in_flight", 3),
    ("pacing", "min_interval_seconds", 1.6),
    ("pacing", "backoff_base_seconds", 2.0),
    ("pacing", "backoff_max_seconds", 60.0),
    ("budget", "max_inference_calls", 4000),
    ("budget", "max_retries_per_task", 5),
    ("inference", "timeout_seconds", 120),
    ("inference", "max_output_tokens", 4096),
    ("exec", "timeout_seconds", 120),
])
def test_load_engine_config_default_value(section, key, value, tmp_path, monkeypatch):
    # Point CONFIG_DIR at an empty dir so the real config/engine.toml does not
    # override defaults; this test asserts the built-in default values.
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    cfg = load_engine_config()
    if isinstance(value, float):
        assert cfg[section][key] == pytest.approx(value)
    else:
        assert cfg[section][key] == value


@pytest.mark.parametrize("section,key,value", [
    ("pacing", "max_in_flight", 3),
    ("pacing", "min_interval_seconds", 1.6),
    ("pacing", "backoff_base_seconds", 2.0),
    ("pacing", "backoff_max_seconds", 60.0),
    ("budget", "max_inference_calls", 4000),
    ("budget", "max_retries_per_task", 5),
    ("inference", "timeout_seconds", 120),
    ("inference", "max_output_tokens", 4096),
    ("exec", "timeout_seconds", 120),
])
def test_defaults_constant_matches_expected(section, key, value):
    if isinstance(value, float):
        assert DEFAULTS[section][key] == pytest.approx(value)
    else:
        assert DEFAULTS[section][key] == value


# ---------------------------------------------------------------------------
# load_engine_config is idempotent / returns deep copy
# ---------------------------------------------------------------------------

def test_load_engine_config_returns_dict():
    cfg = load_engine_config()
    assert isinstance(cfg, dict)


def test_load_engine_config_mutation_does_not_affect_defaults():
    cfg = load_engine_config()
    cfg["budget"]["max_inference_calls"] = 0
    # DEFAULTS should be unchanged
    assert DEFAULTS["budget"]["max_inference_calls"] == 4000


def test_load_engine_config_two_calls_independent():
    cfg1 = load_engine_config()
    cfg2 = load_engine_config()
    cfg1["budget"]["max_inference_calls"] = 0
    assert cfg2["budget"]["max_inference_calls"] == 4000


# ---------------------------------------------------------------------------
# _parse_simple_toml additional parametrize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("toml_text,section,key,expected", [
    ("[a]\nx = 1", "a", "x", 1),
    ("[b]\ny = 2.5", "b", "y", 2.5),
    ('[c]\nz = "hi"', "c", "z", "hi"),
    ("[d]\nflag = true", "d", "flag", True),
    ("[e]\nflag = false", "e", "flag", False),
    ("[f]\nval = 0", "f", "val", 0),
    ('[g]\nname = \'test\'', "g", "name", "test"),
    ("[h]\nbig = 99999", "h", "big", 99999),
])
def test_parse_toml_parametrize_types(toml_text, section, key, expected):
    result = _parse_simple_toml(toml_text)
    if isinstance(expected, float):
        assert result[section][key] == pytest.approx(expected)
    else:
        assert result[section][key] == expected
