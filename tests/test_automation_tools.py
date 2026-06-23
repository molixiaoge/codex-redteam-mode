from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex"))

from automation.tool_discovery import discover_tools_from_config, select_tools_for_task
from automation.tool_registry import ToolRegistry
from automation.planner import create_automation_plan
from automation.scope_gate import Scope, ScopeGate
from automation.artifact_store import ArtifactStore
from automation.report_gate import ReportGate


class AutomationToolTests(unittest.TestCase):
    def test_discovery_prefers_five_tool_classes_but_allows_equivalent_fallbacks(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                """
                {
                  "mcp_tools": [
                    {"name": "browser-use", "capabilities": ["browser_automation", "dom_snapshot", "screenshot"]},
                    {"name": "radare2-mcp", "capabilities": ["binary_reverse", "protocol_analysis"]},
                    {"name": "codex", "capabilities": ["code_generation", "ai_coding"]}
                  ]
                }
                """,
                encoding="utf-8",
            )

            inventory = discover_tools_from_config(cfg)
            selected = select_tools_for_task(
                ["browser_automation", "binary_reverse", "code_generation"],
                inventory,
            )

            self.assertEqual(selected["browser_automation"].selected_tool, "browser-use")
            self.assertEqual(selected["browser_automation"].preferred_tool, "Browser MCP")
            self.assertEqual(selected["browser_automation"].fallback_reason, "preferred_tool_unavailable")
            self.assertEqual(selected["binary_reverse"].selected_tool, "radare2-mcp")
            self.assertEqual(selected["code_generation"].selected_tool, "codex")
            self.assertEqual(selected["code_generation"].preferred_tool, "Current AI Agent")

    def test_registry_rejects_unregistered_tools_and_records_selection_reason(self):
        registry = ToolRegistry()
        registry.register_selected(
            capability="page_fetch",
            preferred_tool="WebFetch",
            selected_tool="webfetch-compatible",
            risk="passive",
            fallback_reason="preferred_tool_unavailable",
        )

        spec = registry.require("webfetch-compatible")
        self.assertEqual(spec.capability, "page_fetch")
        self.assertEqual(spec.preferred_tool, "WebFetch")
        self.assertEqual(spec.fallback_reason, "preferred_tool_unavailable")
        with self.assertRaises(KeyError):
            registry.require("nmap")

    def test_planner_reads_local_tools_and_uses_fallback_when_preferred_missing(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                """
                {
                  "mcp_tools": [
                    {"name": "browser-use", "capabilities": ["browser_automation", "page_fetch"]},
                    {"name": "jadx-alt", "capabilities": ["apk_decompile", "android_static_analysis"]}
                  ]
                }
                """,
                encoding="utf-8",
            )

            plan = create_automation_plan(
                objective="分析 Android APK 并验证页面交互",
                phase="mobile",
                tool_config_paths=[cfg],
            )

            tools = {step.required_capability: step.tool for step in plan.steps}
            self.assertEqual(tools["apk_decompile"], "jadx-alt")
            self.assertEqual(tools["browser_automation"], "browser-use")
            self.assertIn("preferred_tool_unavailable", {step.fallback_reason for step in plan.steps})

    def test_planner_reports_missing_capabilities(self):
        plan = create_automation_plan(
            objective="分析页面并生成报告",
            phase="web",
            tool_config_paths=[],
        )
        self.assertEqual(plan.steps, ())
        self.assertIn("page_fetch", plan.missing_capabilities)
        self.assertIn("code_generation", plan.missing_capabilities)

    def test_discovery_supports_mcpservers_and_name_inference(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                """
                {
                  "mcpServers": {
                    "webfetch": {"command": "webfetch-mcp"},
                    "JADX MCP": {"command": "jadx-cli"}
                  }
                }
                """,
                encoding="utf-8",
            )
            inventory = discover_tools_from_config(cfg)
            names = {item.name for item in inventory}
            self.assertIn("webfetch", names)
            self.assertIn("JADX MCP", names)
            selected = select_tools_for_task(["page_fetch", "apk_decompile"], inventory)
            self.assertEqual(selected["page_fetch"].selected_tool, "webfetch")
            self.assertEqual(selected["apk_decompile"].selected_tool, "JADX MCP")

    def test_name_inference_does_not_match_ida_inside_unrelated_words(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp_tools.json"
            cfg.write_text(
                """
                {
                  "mcpServers": {
                    "candidate-tool": {"command": "candidate"}
                  }
                }
                """,
                encoding="utf-8",
            )
            inventory = discover_tools_from_config(cfg)
            selected = select_tools_for_task(["binary_reverse"], inventory)
            self.assertNotIn("binary_reverse", selected)

    def test_scope_gate_blocks_out_of_scope_network_tool(self):
        registry = ToolRegistry()
        registry.register_selected(
            capability="page_fetch",
            preferred_tool="WebFetch",
            selected_tool="WebFetch",
            risk="passive",
            fallback_reason="preferred_tool_available",
        )
        gate = ScopeGate(Scope(in_scope=("https://example.com",), out_of_scope=("https://admin.example.com",)))
        self.assertTrue(gate.check_tool("WebFetch", {"target": "https://example.com/app"}, registry).allowed)
        blocked = gate.check_tool("WebFetch", {"target": "https://admin.example.com"}, registry)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.reason, "out_of_scope")

    def test_scope_gate_rejects_deceptive_subdomain(self):
        registry = ToolRegistry()
        registry.register_selected(
            capability="page_fetch",
            preferred_tool="WebFetch",
            selected_tool="WebFetch",
            risk="passive",
            fallback_reason="preferred_tool_available",
        )
        gate = ScopeGate(Scope(in_scope=("https://example.com",), out_of_scope=()))
        decision = gate.check_tool("WebFetch", {"target": "https://example.com.evil.org"}, registry)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "not_in_scope")

    def test_registry_marks_unknown_risk_as_approval_required(self):
        registry = ToolRegistry()
        spec = registry.register_selected(
            capability="custom",
            preferred_tool="Custom Tool",
            selected_tool="custom-tool",
            risk="unknown",
            fallback_reason="preferred_tool_unavailable",
        )
        self.assertTrue(spec.requires_approval)

    def test_scope_gate_blocks_missing_target_for_scoped_tools(self):
        registry = ToolRegistry()
        registry.register_selected(
            capability="page_fetch",
            preferred_tool="WebFetch",
            selected_tool="WebFetch",
            risk="passive",
            fallback_reason="preferred_tool_available",
        )
        decision = ScopeGate(Scope(in_scope=("https://example.com",))).check_tool("WebFetch", {}, registry)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "missing_target")

    def test_scope_gate_requires_declared_scope_for_scoped_targets(self):
        registry = ToolRegistry()
        registry.register_selected(
            capability="page_fetch",
            preferred_tool="WebFetch",
            selected_tool="WebFetch",
            risk="passive",
            fallback_reason="preferred_tool_available",
        )

        decision = ScopeGate(Scope()).check_tool("WebFetch", {"target": "https://example.com"}, registry)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "missing_scope")

    def test_artifact_store_writes_jsonl_and_report_gate_requires_core_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            store = ArtifactStore(Path(td))
            store.save("webfetch_summary", {"status": 200})
            store.save("browser_trace", {"steps": ["open"]})
            store.save("generated_code", {"kind": "local_harness"})

            artifacts = store.list_types()
            self.assertIn("webfetch_summary", artifacts)
            decision = ReportGate().check(artifacts)
            self.assertTrue(decision.passed)

            missing = ReportGate().check(("webfetch_summary",))
            self.assertFalse(missing.passed)
            self.assertIn("reproduction_artifact", missing.missing)

    def test_artifact_store_sanitizes_type_and_rehydrates_existing_records(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = ArtifactStore(root)
            path = store.save("../evil", {"ok": True})
            self.assertEqual(path.parent, root)
            self.assertNotIn("..", path.name)

            reopened = ArtifactStore(root)
            self.assertIn("evil", reopened.list_types())

    def test_report_gate_accepts_mobile_or_reverse_evidence_paths(self):
        mobile = ReportGate().check(("jadx_api_inventory", "generated_code"))
        self.assertTrue(mobile.passed)

        reverse = ReportGate().check(("ida_function_notes", "local_harness"))
        self.assertTrue(reverse.passed)

    def test_report_gate_strict_mode_requires_all_seven_gates(self):
        decision = ReportGate(strict=True).check(("webfetch_summary", "generated_code", "scope_proof"))
        self.assertFalse(decision.passed)
        self.assertIn("impact_proof", decision.missing)
        self.assertIn("multi_id_or_parameter_check", decision.missing)
        self.assertIn("false_positive_exclusion", decision.missing)
        self.assertIn("parameter_portability", decision.missing)
        self.assertIn("cia_impact", decision.missing)

        passed = ReportGate(strict=True).check(
            (
                "webfetch_summary",
                "generated_code",
                "impact_proof",
                "multi_id_check",
                "scope_proof",
                "false_positive_exclusion",
                "parameter_portability",
                "cia_impact",
            )
        )
        self.assertTrue(passed.passed)


if __name__ == "__main__":
    unittest.main()
