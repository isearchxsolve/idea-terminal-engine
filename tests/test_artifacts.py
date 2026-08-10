import pytest

from engine import artifacts
from engine.schemas import SchemaError


def idea_data():
    return {"id": "i1", "timestamp": "t", "status": "DISTILLED",
            "source_ref": "r", "content": "an idea",
            "validation_status": "pending"}


def test_roundtrip(tmp_path):
    artifacts.save_artifact(tmp_path, "idea", idea_data())
    loaded = artifacts.load_artifact(tmp_path, "idea")
    assert loaded["version"] == 1
    assert loaded["content"] == "an idea"


def test_version_bump_on_resave(tmp_path):
    artifacts.save_artifact(tmp_path, "idea", idea_data())
    artifacts.save_artifact(tmp_path, "idea", idea_data())
    assert artifacts.load_artifact(tmp_path, "idea")["version"] == 2


def test_invalid_artifact_rejected(tmp_path):
    with pytest.raises(SchemaError):
        artifacts.save_artifact(tmp_path, "idea", {"id": "x"})


def test_unknown_kind_rejected(tmp_path):
    with pytest.raises(KeyError):
        artifacts.save_artifact(tmp_path, "nope", {})
    with pytest.raises(KeyError):
        artifacts.load_artifact(tmp_path, "nope")
