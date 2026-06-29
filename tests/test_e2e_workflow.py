"""End-to-end workflow validation for codex-redteam-mode v1.0.0.

Checks that all core modules load, SKILL.md files are parseable,
and the phase-drive pipeline can be instantiated without errors.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex"))
sys.path.insert(0, str(ROOT / "codex" / "hooks"))

SKILLS_DIR = ROOT / "agents" / "skills"


def check(label, fn):
    """Run fn(); return (label, True) on success, (label, False) on exception."""
    try:
        fn()
        return (label, True)
    except Exception as e:
        print(f"  FAIL [{label}]: {e}")
        return (label, False)


def test_core_imports():
    """All core hook modules import without error."""
    def _run():
        from hooks.core.skill_card import load_skill_card
        from hooks.core.phase_detector import detect_phase
        from hooks.core.method_engine import select_method
        from hooks.core.intent_engine import detect_intent
        from hooks.redteam_state import RedTeamState, default_state
        from router import select_router, select_skill_pack, select_leaf_skill
    return check("core_imports", _run)


def test_automation_imports():
    """Automation modules import without error."""
    def _run():
        from automation.loop_runtime import LoopRuntime
        from automation.decision_tree import DecisionTree
        from automation.gate_engine import GateEngine
        from automation.loop_state import LoopState
    return check("automation_imports", _run)


def test_skill_cards_parseable():
    """All SKILL.md files in agents/skills/ are parseable."""
    def _run():
        from hooks.core.skill_card import load_skill_card
        count = 0
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                card = load_skill_card(str(skill_dir))
                assert card is not None, f"Failed to parse {skill_md}"
                count += 1
        assert count >= 30, f"Expected >=30 skill cards, got {count}"
    return check("skill_cards_parseable", _run)


def test_phase_detection():
    """Phase detection returns valid phases for sample prompts."""
    def _run():
        from hooks.core.phase_detector import detect_phase
        cases = [
            ("Analyze JWT login flow", "web"),
            ("Recover the loader chain from this malware sample", "reverse"),
            ("Enumerate subdomains for target.com", "recon"),
        ]
        for prompt, expected in cases:
            result = detect_phase(prompt)
            assert result == expected, f"detect_phase({prompt!r}) = {result!r}, expected {expected!r}"
    return check("phase_detection", _run)


def test_router_selection():
    """Router selection works for known prompts."""
    def _run():
        from router import select_router
        result = select_router("Review Burp JWT login traffic and verify token boundary reuse risks", "web")
        assert result == "auth-sec", f"Expected auth-sec, got {result}"
    return check("router_selection", _run)


def test_python_syntax():
    """All .py files in codex/ pass ast.parse."""
    def _run():
        codex_dir = ROOT / "codex"
        errors = []
        for py_file in codex_dir.rglob("*.py"):
            try:
                ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append(f"{py_file.name}: {e}")
        assert not errors, f"Syntax errors: {errors}"
    return check("python_syntax", _run)


def test_install_script_syntax():
    """install.py passes ast.parse."""
    def _run():
        install = ROOT / "scripts" / "install.py"
        ast.parse(install.read_text(encoding="utf-8"))
    return check("install_script_syntax", _run)


def main():
    print("=" * 50)
    print("E2E Workflow Validation - codex-redteam-mode v1.0.0")
    print("=" * 50)

    results = [
        test_core_imports(),
        test_automation_imports(),
        test_skill_cards_parseable(),
        test_phase_detection(),
        test_router_selection(),
        test_python_syntax(),
        test_install_script_syntax(),
    ]

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed:
        print("\nFailed checks:")
        for label, ok in results:
            if not ok:
                print(f"  - {label}")
    print("=" * 50)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
