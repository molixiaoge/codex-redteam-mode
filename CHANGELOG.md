# Changelog

All notable changes to **Codex Red Team Opt-In Mode** will be documented in this file.

---
## [0.5.0] – 2026-06-14

### Added
- Dedicated routing layer (`codex/router/`) with regex-based router engine supporting Chinese + English pattern detection, pack selector, leaf selector, and method engine
- Session patcher system (`codex/session_patcher/`) — two-tier refusal detector (strong phrases + weak sentence-openers in Chinese + English), JSONL session file cleaner with auto-backup, refusal-content replacement with optional AI-powered rewrite
- Expanded test suite to 7 modules: `test_router`, `test_orchestrator`, `test_automation_tools`, `test_controller`, `test_install`, `test_modes`, `test_session_patcher`
- Enhanced `scripts/validate.py` with per-subsystem file verification (router, orchestrator, automation, session_patcher)

### Changed
- Updated `config.toml`
- Refined installer with managed manifest tracking, idempotent upgrades, stale legacy path cleanup, and `--uninstall` support
- Tightened phase-to-method escalation mappings with per-domain defaults
  
## [0.4.0] - 2026-05-18

### Changed

- Normalized the GitHub version around the effective `phase -> router -> pack -> leaf` runtime model
- Reduced method emphasis to a soft hint instead of the primary routing axis
- Tightened evidence inference to avoid overconfident `confirmed` labels
- Aligned session-start, runtime, docs, and tests with actual pack-first behavior

### Added

- Expanded domain routing for cloud, container, network, crypto, and mobile scenarios
- Added dedicated detail packs for recon, API, auth, injection, file, business logic, cloud, container, network, crypto, and mobile
- Expanded validation coverage for the new routing domains
- Installer cleanup for known stale legacy runtime paths

---

## [0.3.0] - 2026-05-14

### Changed

- Removed methodology layer; subdivided skills for smarter AI behavior during work phases
- Added semantic judgment as fallback for phase detection
- Optimized workflow routing based on community feedback

### Added

- Overlay installation enablement (thanks Nirvana)

---

## [0.2.0] - 2026-05-11

### Added

- Extended router/pack families beyond core phases
- Initial validation and orchestration gate checks
- Prompt-chain verification tests

### Changed

- Improved jailbreak text robustness (thanks PINGS)
- Refined hook injection to stay lightweight

---

## [0.1.0] - 2026-05-07

### Added

- Initial release with opt-in Red Team Mode (`normal` / `redteam-light` / `redteam-full`)
- Structured JSON runtime state with session isolation
- Rule-first phase detection with semantic fallback
- Pack-first routing mainline: `phase -> router -> pack -> leaf`
- Core phase coverage: web, ad, postex, reverse, code-audit, payload, evasion
- Managed incremental installer (Python, PowerShell)
- Reference method layer and technology routing layer from `qiushi-skill`, `yaklang/hack-skills`, and `mukul975/Anthropic-Cybersecurity-Skills`

[0.4.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.4.0
[0.3.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.3.0
[0.2.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.2.0
[0.1.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.1.0
