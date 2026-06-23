#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-install validation script for codex-redteam-optin-mode.

Verifies that all required files were deployed correctly and the install
is functional.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple


REQUIRED_CODEX_FILES = [
    "hooks/session-start-context.py",
    "hooks/hook-security-context-hook.py",
    "hooks/redteam_state.py",
    "hooks/core/emitter.py",
    "hooks/core/phase_detector.py",
    "hooks/core/semantic_phase.py",
    "hooks/core/loop_engine.py",
    "hooks/core/supplemental_prompts.py",
    "router/__init__.py",
    "router/router_engine.py",
    "router/mappings.py",
    "router/pack_selector.py",
    "router/leaf_selector.py",
    "router/method_engine.py",
    "orchestrator/__init__.py",
    "orchestrator/planner.py",
    "orchestrator/state_graph.py",
    "orchestrator/artifacts.py",
    "orchestrator/gates.py",
    "orchestrator/task_schema.py",
    "automation/__init__.py",
    "automation/planner.py",
    "automation/artifact_store.py",
    "automation/decision_tree.py",
    "automation/executor.py",
    "automation/gate_engine.py",
    "automation/loop_recorder.py",
    "automation/loop_runtime.py",
    "automation/loop_state.py",
    "automation/quick_cards.py",
    "automation/report_gate.py",
    "automation/report_builder.py",
    "automation/rhythm.py",
    "automation/scope_gate.py",
    "automation/tool_discovery.py",
    "automation/tool_registry.py",
    "session_patcher/__init__.py",
    "session_patcher/__main__.py",
    "session_patcher/cli.py",
    "session_patcher/detector.py",
    "session_patcher/patcher.py",
]

REQUIRED_ROOT_FILES = [
    "instruction.ctf.md",
    "config.toml",
]

OPTIONAL_CODEX_FILES = [
    "prompts/Reverse.md",
]


def _codex_root(codex_home: Path) -> Path:
    """Accept either an installed Codex home or this repository root."""
    if (codex_home / "hooks").exists():
        return codex_home
    if (codex_home / "codex" / "hooks").exists():
        return codex_home / "codex"
    return codex_home


def check_file(codex_root: Path, relative: str) -> Tuple[bool, str]:
    path = codex_root / relative
    if path.exists():
        return True, f"  OK  {relative}"
    return False, f"  MISS {relative}"


def validate_install(codex_home: Path) -> Tuple[bool, List[str]]:
    messages: List[str] = []
    all_ok = True

    codex_root = _codex_root(codex_home)
    repo_root = codex_root.parent if codex_root.name == "codex" else codex_home
    source_tree_mode = codex_root.name == "codex" and (repo_root / "scripts" / "install.py").exists()

    messages.append(f"Validating codex-redteam installation at: {codex_home}")
    messages.append(f"Resolved codex root: {codex_root}")
    messages.append("")

    messages.append("Required files:")
    for rel in REQUIRED_CODEX_FILES:
        ok, msg = check_file(codex_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False
    for rel in REQUIRED_ROOT_FILES:
        ok, msg = check_file(repo_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False

    messages.append("")
    messages.append("Optional files:")
    for rel in OPTIONAL_CODEX_FILES:
        ok, msg = check_file(codex_root, rel)
        if not ok:
            msg = msg.replace("MISS", "WARN (optional)")
        messages.append(msg)

    hooks_path = repo_root / "hooks.json"
    if hooks_path.exists():
        try:
            data = json.loads(hooks_path.read_text(encoding="utf-8"))
            hooks_root = data.get("hooks", {})
            hook_count = sum(
                len(entries) for entries in hooks_root.values()
            )
            messages.append("")
            messages.append(f"hooks.json: valid ({hook_count} hook event groups)")
        except (json.JSONDecodeError, OSError) as e:
            messages.append("")
            messages.append(f"hooks.json: INVALID JSON - {e}")
            all_ok = False
    else:
        messages.append("")
        if source_tree_mode:
            messages.append("hooks.json: not required for source tree validation")
        else:
            messages.append("hooks.json: MISSING")
            all_ok = False

    agents_path = repo_root / "AGENTS.md"
    if agents_path.exists():
        content = agents_path.read_text(encoding="utf-8")
        if "codex-redteam-optin-mode:start" in content:
            messages.append("AGENTS.md: managed block present")
        else:
            messages.append("AGENTS.md: WARNING - no managed block found")
    else:
        if source_tree_mode:
            messages.append("AGENTS.md: not required for source tree validation")
        else:
            messages.append("AGENTS.md: MISSING")
            all_ok = False

    config_path = repo_root / "config.toml"
    if config_path.exists():
        messages.append("config.toml: present")
    else:
        messages.append("config.toml: MISSING")
        all_ok = False

    return all_ok, messages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate codex-redteam-optin-mode installation"
    )
    parser.add_argument(
        "--codex-home",
        required=False,
        help="Path to the codex home directory",
    )
    args = parser.parse_args()

    codex_home = Path(args.codex_home) if args.codex_home else Path.home() / ".codex"
    if not codex_home.exists():
        print(f"ERROR: codex home directory does not exist: {codex_home}")
        sys.exit(1)

    all_ok, messages = validate_install(codex_home)
    for msg in messages:
        print(msg)

    if all_ok:
        print("\nValidation PASSED.")
        sys.exit(0)
    else:
        print("\nValidation FAILED - some required files are missing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
