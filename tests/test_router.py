from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codex"))
sys.path.insert(0, str(ROOT / "codex" / "hooks"))

from router import select_leaf_skill, select_method, select_router, select_skill_pack, select_subphase


class RouterTests(unittest.TestCase):
    def test_hooks_core_method_engine_imports_directly(self):
        from hooks.core.method_engine import select_method as hook_select_method

        self.assertEqual(
            hook_select_method("Build an overall roadmap for this validation", "web", "redteam-light"),
            "overall-planning",
        )

    def test_auth_pack(self):
        p = "Review Burp JWT login traffic and verify token boundary reuse risks"
        self.assertEqual(select_router(p, "web"), "auth-sec")
        self.assertEqual(select_skill_pack("web", "auth-sec"), "redteam-auth-detail-pack")
        self.assertEqual(select_leaf_skill(p, "web", "auth-sec"), "jwt-oauth-token-attacks")

    def test_chinese_auth_routing(self):
        p = "请分析登录鉴权、token 重放和越权边界，并验证是否存在 JWT 复用问题"
        self.assertEqual(select_router(p, "web"), "auth-sec")
        self.assertEqual(select_leaf_skill(p, "web", "auth-sec"), "jwt-oauth-token-attacks")

    def test_reverse_pack(self):
        p = "The sample unpacks resources and launches a child process; help me recover the loader chain"
        self.assertEqual(select_router(p, "reverse"), "malware-loader-analysis")
        self.assertEqual(select_subphase(p, "reverse"), "loader")
        self.assertEqual(select_skill_pack("reverse", "malware-loader-analysis"), "redteam-reverse-detail-pack")

    def test_chinese_reverse_and_postex_subphases(self):
        self.assertEqual(select_subphase("分析这个恶意样本的执行链、释放资源和回调流程", "reverse"), "loader")
        self.assertEqual(
            select_leaf_skill("已经拿到 shell，下一步做提权和凭证搜集", "postex", "post-exploitation-playbook"),
            "credential-access-operations",
        )

    def test_chinese_phase_router_leaf_method_truth_cases(self):
        from hooks.core.phase_detector import detect_phase

        p = "请分析登录接口鉴权边界和 JWT 令牌复用问题"
        self.assertEqual(detect_phase(p), "web")
        self.assertEqual(select_router(p, "web"), "auth-sec")
        self.assertEqual(select_leaf_skill(p, "web", "auth-sec"), "jwt-oauth-token-attacks")

        container = "分析 Kubernetes 容器逃逸和 hostPath 权限边界"
        self.assertEqual(detect_phase(container), "container")
        self.assertEqual(select_router(container, "container"), "container-escape-techniques")

        self.assertEqual(select_method("请梳理整体规划和多阶段工作流", "web", "redteam-light"), "workflows")

    def test_expanded(self):
        self.assertEqual(select_skill_pack("cloud", "cloud-iam-abuse"), "redteam-cloud-detail-pack")
        self.assertEqual(select_skill_pack("container", "container-escape-techniques"), "redteam-container-detail-pack")
        self.assertEqual(select_skill_pack("network", "websocket-security"), "redteam-network-detail-pack")
        self.assertEqual(select_skill_pack("crypto", "hash-attack-techniques"), "redteam-crypto-detail-pack")
        self.assertEqual(select_skill_pack("mobile", "mobile-ssl-pinning-bypass"), "redteam-mobile-detail-pack")


if __name__ == "__main__":
    unittest.main()
