#!/usr/bin/env python3
"""Fast artifact smoke test for reviewer verification."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
TOY_INSTANCE = REPO_ROOT / "instances" / "toy.json"


def run_command(command: Sequence[str]) -> None:
    printable = " ".join(str(part) for part in command)
    print(f"$ {printable}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def validate_output(path: Path, require_meta: bool = False) -> None:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if "scheduled_programs" not in payload:
        raise AssertionError(f"Missing scheduled_programs in {path}")
    if not isinstance(payload["scheduled_programs"], list):
        raise AssertionError(f"scheduled_programs is not a list in {path}")
    if "total_score" not in payload or not isinstance(payload["total_score"], (int, float)):
        raise AssertionError(f"Missing numeric total_score in {path}")
    if require_meta and "meta" not in payload:
        raise AssertionError(f"Missing GA metadata in {path}")

    for item in payload["scheduled_programs"]:
        required = {"program_id", "channel_id", "start", "end"}
        missing = required.difference(item)
        if missing:
            raise AssertionError(f"Missing fields {sorted(missing)} in {path}")
        if item["start"] >= item["end"]:
            raise AssertionError(f"Invalid interval in {path}: {item}")


def main() -> None:
    if not TOY_INSTANCE.exists():
        raise FileNotFoundError(f"Toy instance not found: {TOY_INSTANCE}")

    with tempfile.TemporaryDirectory(prefix="smart-tv-scheduling-smoke-") as tmp:
        tmp_dir = Path(tmp)
        deterministic_out = tmp_dir / "toy_deterministic.json"
        ga_out = tmp_dir / "toy_ga.json"
        ga_ls_out = tmp_dir / "toy_ga_ls.json"

        run_command([
            PYTHON,
            str(REPO_ROOT / "src" / "smart_tv_scheduler_scoreboost.py"),
            str(TOY_INSTANCE),
            str(deterministic_out),
        ])
        validate_output(deterministic_out)

        run_command([
            PYTHON,
            str(REPO_ROOT / "src" / "smart_tv_scheduler_ga2.py"),
            str(TOY_INSTANCE),
            str(ga_out),
            "--runs",
            "1",
            "--time-limit",
            "1",
            "--population",
            "8",
            "--elite",
            "1",
            "--top-k",
            "8",
            "--seed",
            "42",
        ])
        validate_output(ga_out, require_meta=True)

        run_command([
            PYTHON,
            str(REPO_ROOT / "src" / "smart_tv_scheduler_ga2_with_local_search.py"),
            str(TOY_INSTANCE),
            str(ga_ls_out),
            "--runs",
            "1",
            "--time-limit",
            "1",
            "--population",
            "8",
            "--elite",
            "1",
            "--top-k",
            "8",
            "--seed",
            "42",
            "--no-local-search",
        ])
        validate_output(ga_ls_out, require_meta=True)

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
