# Repository Engineering Guidelines: python-roborock

## Overview & Scope
`python-roborock` is an asynchronous (`asyncio`) device integration library supporting multi-protocol Roborock vacuum and home appliances (V1 JSON-RPC over AES, B01 Tuya DPS for Q7/Q10, and A01 Tuya DPS for Dyad/Zeo). While Home Assistant Core is a primary downstream consumer, `python-roborock` is an independent client library whose public abstractions must remain general-purpose and consumer-agnostic.

This document serves as the authoritative, single source of truth for engineering conventions, architectural standards, and automated code reviews across all development tools and coding agents (**OpenAI Codex**, **Google Antigravity**, **Anthropic Claude Code**, and **GitHub Copilot**).

---

## Environment & Tooling Standards
- **Python Target**: Python 3.11+
- **Build Backend**: Hatchling
- **Package & Dependency Manager**: `uv`
- **Linting & Formatting**: Ruff (line length 120)
- **Type Checking**: Mypy (`check_untyped_defs = true`)
- **Testing**: pytest (`pytest-asyncio`)

### Key Developer Commands
```bash
# Environment setup
uv venv
uv sync

# Run tests
pytest

# Run tests for a specific trait or protocol
pytest tests/devices/traits/test_battery.py
pytest tests/protocols/test_v1.py

# Lint and typecheck
pre-commit run --all-files
# or directly:
ruff check roborock tests
mypy roborock tests
```

---

## Core Architectural Hierarchy & Review Priorities
Review every proposed change against the repository's three core architectural layers, in strict order of priority:

1. **Priority 1: Public Trait APIs & Consumer Contracts** (Highest Priority)
   - Clean, stable user-facing abstractions suitable for downstream consumers (e.g., Home Assistant, CLI, or standalone scripts) without coupling the library's design to any single framework.
   - Strictly decoupled from wire protocol details, Tuya DPS keys, encryption keys, or transport sockets.
   - Strongly typed with concrete models subclassing `RoborockBase`; never expose raw protocol dictionaries or `Any` on public boundaries.

2. **Priority 2: Data Lifecycle & State Management**
   - **Radical Simplification & Linear Data Flow**: Keep logic simple and readable. Avoid unnecessary indirection, multi-layered helper cascades, or back-and-forth ping-ponging across methods.
   - **Value-Returning Helpers Over Side Effects**: Helper functions MUST be pure transformations that compute and return values (e.g., dictionaries, tuples, or dataclasses) rather than mutating internal object state as a side effect. Make state assignments explicit and visible at the call site (e.g., `new_data = self._parse_response(response, segment_map); self._update_trait_values(new_data)`).
   - **Cohesive Lifecycle**: All event listeners, callbacks, background tasks, and channels cleanly torn down in `close()`.
   - **Concurrency**: Request/response matching across async push channels uses `asyncio.Future` mapped by message ID (`msg_id`).
   - **Presentation vs State**: Transform data in render pipelines; never mutate cached telemetry state or raw packets for presentation effects.

3. **Priority 3: Wire Protocol Parsers, Codecs & Cryptography**
   - Isolate cryptography (AES, MD5), protocol framing, and raw sockets to `roborock.protocols` and `roborock.devices.transport` / `roborock.devices.rpc`.
   - Keep protocol families (V1 JSON-RPC, B01 Tuya DPS, A01 Tuya DPS) strictly isolated; never conflate schemas across families.
   - Enforce enum fallback resilience (`RoborockEnum` with lowercase `unknown = -1` or `RoborockModeEnum.from_code_optional()`); never crash on unexpected firmware codes.

---

## Detailed Engineering Conventions

### 1. Typing & Data Models
- **Subclass `RoborockBase`**: All serializable cloud API payloads, JSON-RPC models, and Tuya DPS data containers MUST subclass `roborock.data.containers.RoborockBase` and be decorated with `@dataclass`. Rely on `RoborockBase` built-in camelCase <-> snake_case translation (`from_dict`, `as_dict`).
  - *Exemptions*: Internal binary protocol map packets (`Q10MapPacket`), transport message envelopes (`RoborockMessage`), map layers (`GridLayers`), transport parameters (`MqttParams`, `UserParams`), and push payloads (`CleanRecordPush`).
- **Prefer `RoborockBase` Over `TypedDict`**: Do not use `TypedDict` or loose dictionaries for structured domain data; always define a `@dataclass` subclassing `RoborockBase`.
- **Enum Fallback Resilience**: All enum types representing device status, firmware modes, error codes, and wire protocol integer codes where unknown values arrive from firmware MUST inherit from `RoborockEnum` or `RoborockModeEnum`.
  - For `RoborockEnum` (an `IntEnum` subclass), define a lowercase fallback member (e.g. `unknown = -1` or `unknown = 0`); `RoborockEnum._missing_` automatically returns `cls.unknown` with a deduplicated warning without raising `ValueError`.
  - For `RoborockModeEnum` (pairing string names with integer codes), use `from_code_optional(code) -> Self | None` for optional fallback.
  - Standard internal repository enums (e.g. `RoborockCommand`, `DeviceVersion`, `RoborockCategory`) that do not decode unknown codes from firmware remain standard `Enum`, `IntEnum`, or `StrEnum`.
- **Strongly Type What You Know; Contain `Any` to the Wire**:
  - Public trait APIs, method signatures, properties, and domain models MUST declare concrete types (`RoborockBase` dataclasses, enums, or primitives). Never use `Any` or raw `dict` as a lazy shortcut for domain models that can be typed.
  - `Any` is natural, expected, and accepted where the underlying wire protocol or transport is genuinely dynamic or polymorphic (such as Tuya DPS maps, low-level channel RPC dispatch, serialization helpers, or evolving cloud API schemas).
- **Explicit Parameter Requirements**: Do NOT mark arguments or dataclass fields as `Optional[...]` or default them to `None` if they are always required by the protocol or caller.
- **Trust Type Annotations**: Prohibit defensive runtime `isinstance` checks on statically typed parameters in business and trait logic (e.g. `def parse_map(data: Q10MapInfo): if not isinstance(data, Q10MapInfo): ...`). Do not add redundant runtime guards where static types suffice. (Note: dynamic payload unpacking and wire-level type narrowing on untyped raw inputs in `from_dict` or RPC deserializers is legitimate and expected).

### 2. Protocol & Device Communications
- **Cryptographic & Transport Layer Decoupling**: Encapsulate all AES encryption, MD5 hashing, protocol salts, raw TCP sockets, and MQTT credentials strictly within `roborock.protocols` and `roborock.devices.transport` / `roborock.devices.rpc`.
- **Channel Trait Boundary**: Traits MUST only receive an abstract communication channel (e.g., `Channel`, `RpcChannel`). NEVER pass device local keys, security tokens, IP addresses, or transport sockets into `Trait` instances.
- **RPC Correlation via `asyncio.Future`**: Asynchronous 1:1 request/response matching across MQTT push channels MUST use `asyncio.Future` mapped by message sequence ID (`msg_id`). The channel creates a loop future, registers unsubscription cleanup, and sets the future result/exception upon message arrival. (Multi-packet query streaming in `a01_channel.py` legitimately uses `asyncio.Event` with a result accumulator).
- **Protocol Version Isolation**: Keep V1 (vacuum JSON-RPC), B01 (Q7/Q10 Tuya DPS), and A01 (Dyad/Zeo Tuya DPS) parser pipelines strictly isolated. Do not bleed Tuya DPS decoding logic into V1 or vice versa.
- **Rendering Transformations vs State Mutation**: When changing how data is displayed or rendered (such as clearing map traces while docked), transform the values within the render pipeline. NEVER mutate or discard cached protocol packet state to achieve rendering effects.

### 3. Trait Design & Client Integration Idioms
- **Compound Capability Gating**: Capability and trait availability MUST be gated by BOTH protocol version AND `RoborockCategory` using authentic codebase attributes: protocol version string `device.pv == "1.0"` (or `device.pv == DeviceVersion.V1`) and product category `product.category == RoborockCategory.VACUUM`. Never assume protocol V1 ("1.0") implies a vacuum robot; mowers and wet/dry vacuums also share protocol variants.
- **Value-Returning Helpers Over Mutating Side Effects**: Methods that parse responses, extract mappings, or transform telemetry MUST compute and return values (e.g., returning a dict, tuple, or dataclass) rather than mutating internal object state as a side effect. Keep state assignment and notifications explicit and visible in the calling method.
- **Aggressive Simplification & Direct Flow**: Avoid convoluted back-and-forth between helper methods or redundant checks for default properties. Strive for simple, linear data flow that makes all side effects immediately visible.
- **Exhaustive Lifecycle Teardown**: All background listeners, event subscriptions, state callbacks, and channel connections MUST be cleanly unhooked and canceled inside `RoborockDevice.close()`.
- **Trait Boundary Simplicity**: Design traits around cohesive, general-purpose consumer concepts (e.g., `CleanHistoryTrait`, `DockTrait`, `ConsumableTrait`), suitable for downstream consumers like Home Assistant or CLI tools, not low-level firmware registers or raw Tuya DPS numbers.
- **Diagnostic Safety & Privacy**: Exclude sensitive user information (such as Wi-Fi SSIDs, passwords, cloud tokens, or encryption keys) from device diagnostics and logs to prevent privacy leaks in downstream clients.

### 4. Error Handling & Exceptions
- **Hierarchy Rooting**: All custom exceptions raised within the library MUST inherit from `roborock.exceptions.RoborockException`.
- **Specific Exception Narrowing**: Catch only specific, expected exception classes (`RoborockTimeout`, `RoborockConnectionException`, `json.JSONDecodeError`).
- **Context-Rich Parsing Exceptions**: Wrap deserialization, decoding, and schema mapping errors into `RoborockParsingException` providing rich context: `RoborockParsingException(trait_name=..., command=..., payload=..., inner_error=err)`.
- **Guard Clauses & Early Exits**: Flatten deeply nested conditional branches by using guard clauses (`if not condition: return`). Keep the primary execution path at the lowest possible indentation level.

### 5. Test Patterns & Fixtures
- **Test Mirroring & Module Colocation**: Place and maintain unit tests in the matching mirror path under `tests/` corresponding to the module under test (e.g. tests for `roborock/devices/traits/battery.py` belong in `tests/devices/traits/test_battery.py`; a new parser `roborock/map/q10.py` belongs in `tests/map/test_q10.py`). When extending existing functionality, augment the canonical test file rather than creating separate one-off test files.
- **Avoid One-Off Test Files (Anti-Pattern)**: Do NOT create fragmented, single-bug or single-PR test files (such as `tests/test_battery_low_voltage_fix.py`). Integrate tests into the module's corresponding test suite.
- **Standard Fixture Reuse**: Reuse existing shared fixtures (`fake_channel`, `message_builder`, `device_fixture`, `v1_simulator`) in `tests/`.
- **Table-Driven Parametrization**: Use `@pytest.mark.parametrize` for testing multi-dock variants, work modes, error codes, and protocol matrices. Avoid copy-pasting duplicate test methods.
- **Behavior-Driven Assertions**: Assert on public trait methods, return values, and emitted channel commands. Do NOT assert on private object attributes (`_state`) or internal implementation flags.
- **State Injection via Fixtures**: Construct test scenarios by feeding `HomeData` or payload fixtures through `device_fixture`, rather than monkeypatching trait internals in test functions.

### 6. PR Hygiene & Sizing
- **Scoping & Splitting Large Pull Requests**: Large pull requests (>500–1,000 LOC or mixing protocol parsers, device traits, and consumer fixes) take much longer to review and block releases.
  - Keep PRs focused on a single logical change or subsystem where possible (e.g. implementing a parser module with its tests in one PR, then introducing or updating traits that consume it in a follow-up PR).
  - When reviewing large PRs, maintainers prioritize how consumer traits and public APIs are shaped before digging into parser internals. Keep public APIs and state management clean and readable even if parser internals are complex.
- **CI Requirements**: PRs must pass automated GitHub Actions CI (`.github/workflows/ci.yml`):
  - **Commitlint**: Commit messages and PR titles MUST follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`) to support automated releases.
  - **Pre-commit**: Ruff, Mypy (`check_untyped_defs = true`), and Codespell must pass (`pre-commit run --all-files`).
  - **Pytest**: All unit tests must pass (`pytest`).
- **Logical Module Placement**: Place constants, enums, and utility functions in the module where they are consumed or in `roborock.data.code_mappings`. Do not scatter domain constants across unrelated modules.

---

## Available Agent Skills

Portable agent skills following the [Agent Skills specification](https://agentskills.io/specification) are located under `.agents/skills/`:

- **Code Review Skill** (`.agents/skills/review/SKILL.md`):  
  A structured, interactive review workflow for evaluating pull requests and diffs against the repository's architectural hierarchy, typing rules, and testing standards. To invoke during interactive sessions, refer to [.agents/skills/review/SKILL.md](.agents/skills/review/SKILL.md).
