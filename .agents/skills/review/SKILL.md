---
name: review
description: Conduct authoritative code review on python-roborock changes against repository architectural hierarchy, typing standards, and maintainer conventions.
---

# Code Review Skill

Use this skill when reviewing pull requests, inspecting code changes, or verifying new device traits in `python-roborock`.

All reviews are evaluated against the engineering conventions defined in [AGENTS.md](../../AGENTS.md).

---

## Review Workflow

1. **Classify Changed Files by Layer**:
   Group changed files according to the 3-tier architectural hierarchy:
   - **Priority 1: Public Trait APIs & Consumer Contracts** (`roborock/devices/traits/`, `roborock/data/containers.py`)
   - **Priority 2: Data Lifecycle & State Management** (trait state, callbacks, `RoborockDevice.close()`)
   - **Priority 3: Wire Protocols, Codecs & Cryptography** (`roborock/protocols/`, `roborock/devices/transport/`, `roborock/devices/rpc/`)

2. **Evaluate Layer 1: Public Trait APIs & Consumer Contracts**:
   - Are trait models subclassing `RoborockBase` with `@dataclass`?
   - Is `TypedDict` completely avoided for domain data models?
   - Is `Any` strictly prohibited on public trait boundaries?
   - Are trait abstractions consumer-agnostic (not hardcoded exclusively to Home Assistant entities)?
   - Are transport details (keys, tokens, sockets) cleanly isolated from traits?

3. **Evaluate Layer 2: Lifecycle, State & Simplification**:
   - **Value-Returning Helpers**: Do helper functions return values instead of modifying `self` via hidden side effects?
   - **Direct Flow**: Is the execution path straightforward and direct, avoiding unnecessary indirection or ping-ponging between methods?
   - **Concurrency**: Does 1:1 async command-response matching use `asyncio.Future` mapped by `msg_id`?
   - **Teardown**: Are all tasks, event listeners, and channels cleanly unhooked in `RoborockDevice.close()`?
   - **Capability Gating**: Is feature gating checking BOTH protocol version (`pv`) and product category (`RoborockCategory`)?

4. **Evaluate Layer 3: Wire Protocols, Codecs & Resilient Enums**:
   - Do status and error code enums subclass `RoborockEnum` (with lowercase `unknown = -1` member) or `RoborockModeEnum` (with `from_code_optional()`)?
   - Are unexpected wire codes prevented from crashing via unhandled `ValueError`?
   - Is wire-contained `Any` properly scoped to genuine protocol polymorphism (e.g. Tuya DPS maps)?

5. **Evaluate Tests & Fixtures**:
   - **Test Mirroring & Colocation**: Are tests colocated in the matching mirror path under `tests/` for the module being tested (e.g., tests for `roborock/devices/traits/battery.py` in `tests/devices/traits/test_battery.py`; new modules have corresponding new test suites under the mirror directory)?
   - **No One-Off Bugfix Test Files**: Flag any fragmented single-bug or single-PR test files (e.g., `tests/test_battery_low_voltage_fix.py`). Tests must be integrated into the module's corresponding test suite.
   - Are tests using `fake_channel` and `@pytest.mark.parametrize` rather than hand-rolled mocks or duplicate methods?
   - Do assertions verify public behavior rather than private `_state` variables?

6. **Format Review Output**:
   Structure review comments with clear rationale and actionable code recommendations:
   - **Priority Level & File Reference**
   - **Issue / Anti-Pattern Identified**
   - **Grounded Rationale** (citing protocol resilience, consumer stability, or maintainability)
   - **Concrete Before / After Diff or Suggested Fix**
