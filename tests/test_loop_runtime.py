from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex"))
sys.path.insert(0, str(ROOT / "codex" / "hooks"))

from hooks.redteam_state import default_state


class LoopDecisionMetadataTests(unittest.TestCase):
    def test_loop_decision_includes_trigger_feedback_gate_and_exit_condition(self):
        from hooks.core.loop_engine import decide_loop_action

        state = default_state("loop-metadata")
        state.workflow_phase = "recon"
        decision = decide_loop_action(
            state=state,
            evidence_level="unknown",
            gate_ok=False,
            verify_passed=False,
            taskbook={"todo_items": [{"id": "task-1"}]},
            current_task_id="task-1",
        )

        self.assertEqual(decision.action, "verify")
        self.assertEqual(decision.trigger, "missing_gate_evidence")
        self.assertEqual(decision.feedback_gate, "Artifact Gate")
        self.assertEqual(decision.exit_condition, "collect_required_artifact")
        self.assertEqual(decision.required_artifact, "validation_artifact")

    def test_controller_brief_emits_loop_feedback_metadata(self):
        from hooks.core.controller import process_turn

        state = default_state("controller-loop-metadata")
        state.mode = "redteam-full"
        result = process_turn(
            prompt="Analyze JWT login flow and validate token reuse risk",
            state=state,
            codex_dir=ROOT / "codex",
            assistant_summary="",
        )

        self.assertIn("[loop-trigger:", result.brief)
        self.assertIn("[feedback-gate:", result.brief)
        self.assertIn("[exit-condition:", result.brief)


class LoopRuntimeSupportTests(unittest.TestCase):
    def test_quick_card_refreshes_for_pivot_stagnation_and_pseudo_complete(self):
        from automation.quick_cards import build_quick_card, should_refresh_quick_card
        from hooks.core.loop_engine import LoopDecision

        decision = LoopDecision(
            action="pivot",
            reason="stagnation_threshold",
            next_stage="strategy",
            next_step="Choose a narrower validation step.",
            trigger="stagnation_threshold",
            feedback_gate="Rhythm Gate",
            exit_condition="select_new_path",
        )

        self.assertTrue(should_refresh_quick_card(decision, loop_iteration=2))
        card = build_quick_card(
            objective="validate jwt reuse",
            selected_path="auth-boundary",
            decision=decision,
            recent_artifacts=("webfetch_summary",),
        )
        self.assertIn("[quick-card]", card)
        self.assertIn("objective=validate jwt reuse", card)
        self.assertIn("artifacts=webfetch_summary", card)

    def test_decision_tree_prefers_auth_for_login_and_jadx_for_apk(self):
        from automation.decision_tree import select_decision_path

        auth = select_decision_path("Review login token and session boundary", phase="web")
        self.assertEqual(auth.path, "auth-boundary")
        self.assertIn("browser_automation", auth.required_capabilities)

        apk = select_decision_path("Analyze Android APK and extract backend API inventory", phase="mobile")
        self.assertEqual(apk.path, "apk-api-inventory")
        self.assertIn("apk_decompile", apk.required_capabilities)
        self.assertIn("jadx_api_inventory", apk.expected_artifacts)

    def test_executor_plan_only_returns_skipped_result_without_running_tools(self):
        from automation.executor import Executor
        from automation.planner import AutomationStep

        step = AutomationStep(
            id="step-1",
            tool="Browser MCP",
            required_capability="browser_automation",
            preferred_tool="Browser MCP",
            risk="active_low",
            fallback_reason="preferred_tool_available",
            expected_artifact="browser_trace",
        )
        result = Executor(plan_only=True).run_step(step, args={"target": "https://example.com"})

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.artifact_type, "browser_trace")
        self.assertFalse(result.retryable)

    def test_executor_runs_registered_adapter_and_returns_success_result(self):
        from automation.executor import Executor
        from automation.planner import AutomationStep

        step = AutomationStep(
            id="step-1",
            tool="webfetch-compatible",
            required_capability="page_fetch",
            preferred_tool="WebFetch",
            risk="passive",
            fallback_reason="preferred_tool_unavailable",
            expected_artifact="webfetch_summary",
        )
        executor = Executor(plan_only=False)
        executor.register_adapter(
            "webfetch-compatible",
            lambda step, args: {
                "summary": "fetched local fixture",
                "artifact": {"status": 200, "target": args["target"]},
            },
        )
        result = executor.run_step(step, args={"target": "https://example.com"})

        self.assertEqual(result.status, "success")
        self.assertEqual(result.artifact_type, "webfetch_summary")
        self.assertEqual(result.summary, "fetched local fixture")
        self.assertEqual(result.artifact_payload["status"], 200)

    def test_loop_recorder_writes_jsonl_decision_log(self):
        from automation.loop_recorder import LoopRecorder
        from hooks.core.loop_engine import LoopDecision

        with tempfile.TemporaryDirectory() as td:
            recorder = LoopRecorder(Path(td))
            recorder.record_decision(
                run_id="run-1",
                iteration=1,
                decision=LoopDecision(
                    action="verify",
                    reason="missing_gate_evidence",
                    next_stage="recon",
                    next_step="Collect evidence.",
                    trigger="missing_gate_evidence",
                    feedback_gate="Artifact Gate",
                    exit_condition="collect_required_artifact",
                ),
            )

            log_path = Path(td) / "decision-log.jsonl"
            self.assertTrue(log_path.exists())
            payload = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["run_id"], "run-1")
            self.assertEqual(payload["decision"]["trigger"], "missing_gate_evidence")

    def test_loop_runtime_run_once_exposes_rhythm_path_and_gate_state(self):
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState

        with tempfile.TemporaryDirectory() as td:
            state = LoopRuntimeState(
                run_id="run-1",
                session_id="session-1",
                objective="Review login token reuse",
                mode="redteam-full",
                phase="web",
                loop_iteration=1,
            )
            result = LoopRuntime(log_root=Path(td)).run_once(state)

            self.assertEqual(result.state.selected_path, "auth-boundary")
            self.assertIn(result.state.rhythm_state, {"healthy", "drifting", "stagnant", "pseudo_complete"})
            self.assertIn("Artifact Gate", {gate.gate_name for gate in result.state.gate_results})
            self.assertTrue((Path(td) / "decision-log.jsonl").exists())

    def test_loop_runtime_executes_registered_adapter_saves_artifact_and_advances(self):
        from automation.executor import Executor
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState
        from automation.scope_gate import Scope

        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                json.dumps(
                    {
                        "mcp_tools": [
                            {"name": "webfetch-compatible", "capabilities": ["page_fetch"]},
                            {"name": "browser-compatible", "capabilities": ["browser_automation"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            executor = Executor(plan_only=False)
            executor.register_adapter(
                "webfetch-compatible",
                lambda step, args: {
                    "summary": "web fixture collected",
                    "artifact": {"kind": step.expected_artifact, "target": args["target"]},
                },
            )
            executor.register_adapter(
                "browser-compatible",
                lambda step, args: {
                    "summary": "browser trace collected",
                    "artifact": {"kind": step.expected_artifact, "target": args["target"]},
                },
            )
            state = LoopRuntimeState(
                run_id="run-automation",
                session_id="session-automation",
                objective="Review login token and session boundary",
                mode="redteam-full",
                phase="web",
                loop_iteration=1,
                evidence_level="confirmed",
                notes={"target": "https://example.com/login"},
            )

            result = LoopRuntime(
                log_root=Path(td),
                executor=executor,
                tool_config_paths=(cfg,),
                artifact_root=Path(td) / "artifacts",
                scope=Scope(in_scope=("https://example.com",)),
            ).run_once(state)

            self.assertEqual(result.decision.action, "advance")
            self.assertTrue(result.plan.steps)
            self.assertEqual({item.status for item in result.execution_results}, {"success"})
            self.assertIn("webfetch_summary", result.artifacts)
            self.assertIn("browser_trace", result.artifacts)
            self.assertIn("[execution:success]", result.brief)
            self.assertTrue(list((Path(td) / "artifacts").glob("*.json")))

    def test_loop_runtime_blocks_scoped_tool_when_target_is_missing(self):
        from automation.executor import Executor
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState
        from automation.scope_gate import Scope

        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                json.dumps({"mcp_tools": [{"name": "webfetch-compatible", "capabilities": ["page_fetch"]}]}),
                encoding="utf-8",
            )
            executor = Executor(plan_only=False)
            executor.register_adapter(
                "webfetch-compatible",
                lambda step, args: {"summary": "should not run", "artifact": {"unexpected": True}},
            )
            state = LoopRuntimeState(
                run_id="run-scope",
                session_id="session-scope",
                objective="Collect web baseline",
                mode="redteam-full",
                phase="web",
                loop_iteration=1,
                evidence_level="confirmed",
            )

            result = LoopRuntime(
                log_root=Path(td),
                executor=executor,
                tool_config_paths=(cfg,),
                scope=Scope(in_scope=("https://example.com",)),
            ).run_once(state)

            self.assertEqual(result.execution_results[0].status, "blocked")
            self.assertEqual(result.execution_results[0].error, "missing_target")
            self.assertEqual(result.artifacts, ())
            self.assertIn("Scope Gate", {gate.gate_name for gate in result.gate_results})

    def test_loop_runtime_retries_retryable_tool_failure(self):
        from automation.executor import Executor
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState
        from automation.scope_gate import Scope

        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                json.dumps({"mcp_tools": [{"name": "webfetch-compatible", "capabilities": ["page_fetch"]}]}),
                encoding="utf-8",
            )
            attempts = {"count": 0}

            def flaky_adapter(step, args):
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise TimeoutError("temporary timeout")
                return {"summary": "retried ok", "artifact": {"status": 200}}

            executor = Executor(plan_only=False)
            executor.register_adapter("webfetch-compatible", flaky_adapter)
            state = LoopRuntimeState(
                run_id="run-retry",
                session_id="session-retry",
                objective="Collect web baseline",
                mode="redteam-full",
                phase="web",
                loop_iteration=1,
                evidence_level="confirmed",
                notes={"target": "https://example.com"},
            )

            result = LoopRuntime(
                log_root=Path(td),
                executor=executor,
                tool_config_paths=(cfg,),
                scope=Scope(in_scope=("https://example.com",)),
                max_retries=1,
            ).run_once(state)

            self.assertEqual(attempts["count"], 2)
            self.assertEqual(result.execution_results[-1].status, "success")
            self.assertIn("webfetch_summary", result.artifacts)

    def test_loop_runtime_does_not_verify_empty_execution_results(self):
        from automation.decision_tree import DecisionPath
        from automation.planner import AutomationPlan
        import automation.loop_runtime as loop_runtime_module
        from automation.loop_runtime import LoopRuntime
        from automation.loop_state import LoopRuntimeState

        original_selector = loop_runtime_module.select_decision_path
        original_planner = loop_runtime_module.create_automation_plan
        loop_runtime_module.select_decision_path = lambda objective, phase="general", **kwargs: DecisionPath(
            path="metadata-only-path",
            priority="low",
            reason="test empty execution path",
            required_capabilities=(),
            expected_artifacts=(),
        )
        loop_runtime_module.create_automation_plan = lambda **kwargs: AutomationPlan(
            objective=kwargs["objective"],
            phase=kwargs["phase"],
            steps=(),
            required_capabilities=(),
            missing_capabilities=(),
        )
        try:
            with tempfile.TemporaryDirectory() as td:
                state = LoopRuntimeState(
                    run_id="run-empty-execution",
                    session_id="session-empty-execution",
                    objective="Metadata-only path",
                    mode="redteam-full",
                    phase="general",
                    loop_iteration=1,
                    evidence_level="confirmed",
                )

                result = LoopRuntime(log_root=Path(td)).run_once(state)

                # When execution_results is empty, verify step should not block
                self.assertEqual(result.execution_results, ())
                # The decision should still be produced (not crash)
                self.assertIsNotNone(result.decision)
                # Artifact gate runs even with no execution
                self.assertIn("Artifact Gate", {g.gate_name for g in result.gate_results})
                # State should advance iteration
                self.assertEqual(result.state.loop_iteration, 2)
                # Decision log should be written
                self.assertTrue((Path(td) / "decision-log.jsonl").exists())
        finally:
            loop_runtime_module.select_decision_path = original_selector
            loop_runtime_module.create_automation_plan = original_planner


if __name__ == "__main__":
    unittest.main()
