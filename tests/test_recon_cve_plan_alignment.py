from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex"))
sys.path.insert(0, str(ROOT / "codex" / "hooks"))


class ReconCvePlanAlignmentTests(unittest.TestCase):
    def test_no_legacy_skill_cards_or_references_remain(self):
        skills = ROOT / "agents" / "skills"
        self.assertEqual(list(skills.glob("*/skill_card.yaml")), [])
        self.assertEqual(list(skills.glob("*/skill_card.yml")), [])
        self.assertEqual(list(skills.glob("*/skill_card.json")), [])
        self.assertEqual([p for p in skills.glob("*/references") if p.is_dir()], [])

    def test_skill_md_loader_reads_runtime_card(self):
        from hooks.core.skill_card import load_skill_card

        card = load_skill_card(ROOT / "agents" / "skills", "redteam-recon-intake")

        self.assertIsNotNone(card)
        self.assertEqual(card.skill_id, "redteam-recon-intake")
        self.assertIn("recon_profile", card.exit_gate.required_artifacts)
        self.assertTrue(card.pivot_hints)

    def test_bare_domain_routes_to_recon_intake(self):
        from hooks.core.controller import process_turn
        from hooks.redteam_state import default_state

        state = default_state("bare-domain-recon")
        state.mode = "redteam-light"

        result = process_turn(
            prompt="example.com",
            state=state,
            codex_dir=ROOT / "codex",
            assistant_summary="",
        )

        self.assertEqual(result.state.phase, "recon")
        self.assertEqual(result.state.router, "recon-intake")
        self.assertEqual(result.state.skill_pack, "redteam-recon-intake")
        self.assertIn("[automation-loop:executed]", result.brief)

    def test_real_chinese_bare_target_routes_to_recon_intake(self):
        from hooks.core.controller import process_turn
        from hooks.redteam_state import default_state

        state = default_state("bare-domain-recon-zh")
        state.mode = "redteam-light"

        result = process_turn(
            prompt="看一下 example.com",
            state=state,
            codex_dir=ROOT / "codex",
            assistant_summary="",
        )

        self.assertEqual(result.state.phase, "recon")
        self.assertEqual(result.state.router, "recon-intake")
        self.assertEqual(result.state.skill_pack, "redteam-recon-intake")

    def test_real_chinese_direction_is_not_bare_target(self):
        from hooks.core.target_parser import extract_target

        intent = extract_target("测试 example.com 的 SQL 注入和登录鉴权")

        self.assertEqual(intent.target, "example.com")
        self.assertTrue(intent.explicit_direction)
        self.assertFalse(intent.bare_target)

    def test_gate_soft_fail_allows_plan_only(self):
        from automation.gate_engine import evaluate_tool_gate

        result = evaluate_tool_gate(
            required_capabilities=("cve_lookup",),
            missing_capabilities=("cve_lookup",),
            plan_only_allowed=True,
        )

        self.assertEqual(result.grade, "soft_fail")
        self.assertEqual(result.next_required_action, "plan_without_tool")

    def test_loop_runtime_increments_iteration_and_preserves_target(self):
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState

        with tempfile.TemporaryDirectory() as td:
            state = LoopRuntimeState(
                run_id="run-align",
                session_id="session-align",
                objective="example.com",
                mode="redteam-light",
                phase="recon",
                loop_iteration=4,
                notes={"target": "example.com"},
            )

            result = LoopRuntime(log_root=Path(td)).run_once(state)

            self.assertEqual(result.state.loop_iteration, 5)
            self.assertEqual(result.state.notes["target"], "example.com")

    def test_external_leaf_without_exit_gate_falls_back_to_project_pack_gate(self):
        from hooks.core.controller import process_turn
        from hooks.redteam_state import default_state

        state = default_state("external-leaf-pack-fallback")
        state.mode = "redteam-light"

        result = process_turn(
            prompt="测试 example.net 的 SQL 注入和登录鉴权",
            state=state,
            codex_dir=ROOT / "codex",
            assistant_summary="",
        )

        self.assertNotIn("exit_gate_not_declared", result.brief)
        self.assertIn("[feedback-gate:Skill Exit Gate]", result.brief)


if __name__ == "__main__":
    unittest.main()
