from pathlib import Path
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION = ("AGENTS.md", "README.md", "TODO.md")
VERIFY_TYPES = {"agent", "command", "human", "proof", "property"}


def load_spec() -> dict[str, Any]:
    with (ROOT / "specs" / "ctf.spec.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_root_documentation_exists() -> None:
    for name in DOCUMENTATION:
        assert (ROOT / name).is_file(), name


def test_spec_has_a_name() -> None:
    assert load_spec()["name"] == "common_task_framework"


def test_every_criterion_is_traceable() -> None:
    for criterion in load_spec()["criteria"]:
        assert criterion["description"].strip()
        assert criterion["verify"]["type"] in VERIFY_TYPES
        assert criterion["verify"]["run"].strip()


def test_skips_carry_a_reason() -> None:
    for criterion in load_spec()["criteria"]:
        if "skip" in criterion:
            assert criterion["skip"].strip()
