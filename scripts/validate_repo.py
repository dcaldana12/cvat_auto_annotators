#!/usr/bin/env python3
"""Validate function manifests, labels, documentation links, and tracked secrets."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
)


def error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def validate_function_config(path: Path) -> bool:
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        error(f"{path}: invalid YAML: {exc}")
        return False

    if not isinstance(config, dict):
        error(f"{path}: expected a YAML mapping")
        return False

    metadata = config.get("metadata") or {}
    name = metadata.get("name")
    if not name:
        error(f"{path}: metadata.name is missing")
        return False

    annotations = metadata.get("annotations") or {}
    if annotations.get("type") != "detector":
        error(f"{path}: metadata.annotations.type must be 'detector'")
        return False

    spec = annotations.get("spec")
    if not spec:
        error(f"{path}: metadata.annotations.spec is missing")
        return False

    if isinstance(spec, str):
        try:
            labels = json.loads(spec)
        except json.JSONDecodeError as exc:
            error(f"{path}: annotation spec is not valid JSON: {exc}")
            return False
    else:
        labels = spec

    if not isinstance(labels, list) or not labels:
        error(f"{path}: annotation spec must be a non-empty list")
        return False

    ids = []
    names = []
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            error(f"{path}: label {index} must be an object")
            return False
        if "id" not in label or "name" not in label:
            error(f"{path}: label {index} must contain 'id' and 'name'")
            return False
        ids.append(label["id"])
        names.append(str(label["name"]))

    if len(ids) != len(set(ids)):
        error(f"{path}: label IDs must be unique")
        return False
    if len(names) != len(set(names)):
        error(f"{path}: label names must be unique")
        return False

    function_spec = config.get("spec") or {}
    if function_spec.get("handler") != "main:handler":
        error(f"{path}: spec.handler must be 'main:handler'")
        return False

    if not (path.parent / "main.py").is_file():
        error(f"{path}: expected a sibling main.py")
        return False

    return True


def validate_readme() -> bool:
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    ok = True

    for target in re.findall(r"\]\((\.[^)#]+)(?:#[^)]+)?\)", text):
        if not (ROOT / target).exists():
            error(f"README.md: broken relative link: {target}")
            ok = False

    return ok


def validate_tracked_files() -> bool:
    if not (ROOT / ".git").exists():
        return True

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    ok = True
    for tracked in result.stdout.splitlines():
        path = Path(tracked)
        if path.name == "config.env" or path.suffix == ".env":
            error(f"tracked local configuration file: {tracked}")
            ok = False

    return ok


def main() -> int:
    ok = True

    for filename in REQUIRED_FILES:
        if not (ROOT / filename).is_file():
            error(f"missing required file: {filename}")
            ok = False

    function_configs = sorted(ROOT.glob("**/nuclio/function.yaml"))
    if not function_configs:
        error("no nuclio/function.yaml files found")
        return 1

    for path in function_configs:
        relative = path.relative_to(ROOT)
        if validate_function_config(path):
            print(f"validated {relative}")
        else:
            ok = False

    ok = validate_readme() and ok
    ok = validate_tracked_files() and ok

    if not ok:
        return 1

    print(f"validated {len(function_configs)} function configuration(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
