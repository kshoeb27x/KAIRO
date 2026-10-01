# KAIRO Authorization Coverage Audit

**Audit status:** Source-traced against the currently exposed repository files.  
**Scope:** Agent, tool, runtime, workflow, API, security, and provider execution paths.  
**Implementation status:** PARTIAL / UNVERIFIED. The post-audit implementation update below reflects source changes made after the baseline audit. Runtime behavior has not been validated because the available test runner did not discover the tests and the terminal is not attached to this repository.

## Validation Attempt (2026-10-01)

- **Opened workspace:** `C:\Users\kshoe\Downloads\KAIRO_Foundation\KAIRO` (confirmed by the VS Code workspace environment and visible repository root containing `.git`, `pytest.ini`, `tests`, and `.venv`).
- **Test discovery configuration:** `pytest.ini` sets `testpaths = tests` and `python_files = test_*.py`. `.vscode/settings.json` enables pytest with `tests` as its argument. The authorization test is named `tests/test_authorization_boundary.py`, matching those discovery rules; related tests are under the configured `tests` tree. No configuration mismatch was identified from the available file inspection.
- **Test runner evidence:** An explicit selection of `tests/test_authorization_boundary.py` reported “No tests found.” The full workspace test runner reported `0 passed, 0 failed`, which is zero executed tests and is not a pass.
- **Terminal evidence:** PowerShell started at `C:\`. An attempt to change directory to the opened workspace was denied with `UnauthorizedAccessException` / `Access is denied`. Consequently pytest, Python compilation, `git status`, and `git diff --check` could not execute. No further terminal or script attempt was made against the denied path.
- **Validation result:** **BLOCKED.** The visible pytest and VS Code settings do not explain the test-runner discovery failure; the evidence indicates the test runner is not executing in the opened repository workspace. Do not alter test names or weaken tests to compensate.
- **Still required in an environment attached to this workspace:** run `python -m pytest tests/test_authorization_boundary.py`, focused security/agent/tool/runtime/workflow/API regression tests, the full pytest suite, Python compilation, `git status`, and `git diff --check`; inspect the resulting diff and repair any failures.

## Post-Audit Implementation Update

The implementation now adds a shared immutable execution context and routes authorization decisions through the existing `SecurityManager` for tool, agent, runtime, workflow, API, sandbox, and external model-provider entry points. The API requires an explicitly configured bearer token and permissions. Authorization and execution outcomes are sent to the existing audit subsystem, which now has SQLite-backed persistence. Delegated operations retain the original caller, identify the target and delegating agent, and are checked against the delegator's own grant for each requested permission.

These are source-level changes, not a claim of verified runtime enforcement. Focused behavioral tests have been added, including a test that proves a delegated agent cannot use a capability its delegator lacks. They remain unexecuted; the available test runner reported no tests found, and shell-based validation is unavailable in the current workspace. Accordingly, the implementation is **PARTIAL / UNVERIFIED**, not complete. The findings, execution-path table, and coverage descriptions below document the pre-implementation baseline and should be read as such.

## Executive Summary

**Current implementation status is PARTIAL / UNVERIFIED.** Source changes since the baseline audit connect the existing `SecurityManager` to API, agent, tool, runtime, task, workflow, sandbox, and external model-provider execution. Low-level runtime task and callable executors now also require a verified context. Authentication and permissions are explicitly configured for API access; missing identity or context fails closed. Durable audit storage and enforcement tests were added. None of these changes should be considered runtime-verified until the tests execute successfully in the repository environment.

### Pre-implementation Baseline

The original source-traced audit found multiple security components but no single execution boundary. The separate `AgentAuthorityController` enforced agent lifecycle and local execution permission without global caller identity. Tool metadata was not enforced; API routes had no authentication; runtime/workflow callables lacked caller context; and sandbox approval relied on a caller-provided boolean. These findings describe the baseline before the implementation update, not the current source state.

No concrete filesystem or shell/process tool implementation was found in the inspected canonical tool set. Actual host filesystem/process behavior therefore remains unverified. Synchronous arbitrary code cannot be forcibly interrupted by emergency stop; only new work and cooperative boundaries can be guarded.

## Architecture (Baseline at Audit Time)

- `src/kairo_system.py` composes runtime, core/orchestrator, agents, data, security, and tools.
- `src/integration.py` loads the numbered architecture packages.
- `02_AGENTS/Manager/agent_manager.py` owns a separate agent registry, lifecycle controller, local authority, history, and emergency-stop flag. The orchestrator constructs it with the runtime.
- `06_SECURITY/security_manager.py` composes identity, authority, permission, secret, audit, and sandbox services.
- `04_TOOLS/manager.py` composes registry and executor; no SecurityManager is injected.
- `07_RUNTIME/runtime_manager.py` composes tasks, events, runtime executor, workflows, and scheduler.
- `src/api/server.py` exposes localhost status/tasks/events/chat and task-creation endpoints.
- `config/policy.yaml` declares approval, sandbox, and audit settings; those declarations are not automatically applied to every path.

## Execution Paths (Pre-Implementation Baseline)

| Path | Actual flow | Authorization result |
|---|---|---|
| 1. Agent → Task | API or caller → `KairoSystem.create_task()` → `RuntimeManager.create_task()` → `TaskManager.create()` | **MISSING** shared identity/permission context; task is recorded as created, not as an authorized execution. |
| 2. Agent → Tool | Agent methods do not receive a ToolManager in the inspected composition. Public tool call is `KairoSystem.execute_tool()` → `ToolManager.execute()` → `ToolExecutor.execute()` → tool handler. | **MISSING** SecurityManager authorization; no direct agent-to-tool route was found. |
| 3. Agent → Runtime | Orchestrator/manager → `AgentManager.execute()` → local `AgentAuthorityController.require(EXECUTE)` → `RuntimeManager.execute()` → `RuntimeExecutor.execute()` → agent callable. | **PARTIAL**: local agent execute permission/lifecycle enforced, but no SecurityManager identity, context, or permission check. |
| 4. Agent → API | Agent code does not call an API client through an injected API or server object in the inspected path. The API server separately calls KAIRO. | **UNVERIFIED** for arbitrary provider/agent code; no supported first-class route or delegation boundary was found. |
| 5. Runtime → Tool | Runtime accepts a callable in `RuntimeManager.execute()`; workflow steps accept arbitrary callables. No central call to ToolManager is made. | **MISSING** if a callable closes over or directly invokes a tool manager; no propagated context or common authorization hook. |
| 6. API → Runtime | `POST /api/tasks` → `kairo.create_task()` → runtime task registry; `POST /api/chat` → `kairo.respond()` → orchestrator → task or agent path. | **MISSING** authentication and caller authorization; no identity is attached to tasks or chat dispatch. |
| 7. Tool → filesystem/external | ToolManager → ToolExecutor → tool implementation. API/automation/computer-use/MCP implementations currently support health/describe/echo only; Browser delegates navigate/click/type to an optional provider. | **PARTIAL**: no host filesystem or shell/process implementation was found. Browser provider actions have no SecurityManager permission/approval check at this layer. |
| 8. Agent → Agent | AgentManager has a registry and invokes the selected registered agent. No agent receives a delegated caller context or agent-to-agent protocol. | **MISSING** explicit delegation authorization; no built-in agent-to-agent call API was found. |

## Authorization Coverage (Pre-Implementation Baseline)

`SecurityManager.authorize(identity_id, permission, authority)` is an implemented checker. It requires a known active identity, sufficient assigned authority, and an explicitly granted permission; it audits allowed and denied outcomes. No call site to this method was found in `KairoSystem`, `ToolManager`, `AgentManager`, `RuntimeManager`, workflow, or API execution code inspected.

`AgentAuthorityController.require()` is invoked by the newer agent manager before agent execution. It verifies local lifecycle state is RUNNING and local authority contains `Permission.EXECUTE`. This is a separate permission model and is not sufficient to authorize tools, runtime operations, API callers, or delegated agents.

## Authentication Coverage

**MISSING for the API.** `src/api/server.py` does not validate a token, session, client certificate, or authenticated principal in GET or POST routes. It binds to `127.0.0.1`, which limits network exposure by default but is not authentication. Mutating POST task/chat operations and information-returning GET endpoints are reachable without identity context.

## Tool Permission Coverage

`ToolDefinition.permissions` declares permission strings (for example `network.read`, `computer.interact`, `mcp.execute`, or automation permissions). The inspected `ToolExecutor.execute()` does not read this field. It only checks tool existence and `definition.enabled`, then invokes `tool.execute()`. The tool’s `describe` response reports permission metadata but does not enforce it.

**Result: MISSING enforcement; metadata-only declarations.** Calling `ToolManager.execute()` or `KairoSystem.execute_tool()` bypasses SecurityManager checks.

## Agent Permission Coverage

`02_AGENTS/Manager/agent_manager.py` creates an `AgentControl` with a default local authority containing `Permission.EXECUTE`, transitions it to RUNNING, and calls `AgentAuthorityController.require()` before execution. This protects only the manager execution path. The local agent authority does not bind a KAIRO security identity, does not specify a tool allowlist, and does not consult the global SecurityManager.

Agent identity is currently the registered name. No authenticated human caller identity is propagated as the execution initiator. Agent-to-agent delegation is not an implemented controlled interface.

## Runtime Permission Coverage

`RuntimeManager.create_task()`, `execute()`, `workflow()`, and `schedule()` do not accept an authorization context or call SecurityManager. `RuntimeExecutor` emits execution events and catches/retries callable errors, but does not make a policy decision. `TaskManager` records task data and emits lifecycle events, but tasks do not carry a security identity, permission, or approval record.

**Result: MISSING shared authorization.** Runtime events are not equivalent to security audit decisions.

## API Permission Coverage

`src/api/server.py` exposes GET status/tasks/events and POST chat/tasks. No route authenticates a caller or passes an identity to `KairoSystem`. POST task validates only that the task name is non-empty. POST chat dispatches user text directly to the orchestrator. Error responses handle invalid JSON/value errors and generic exceptions, but no authorization-denied response path exists.

## Workflow Permission Coverage

`RuntimeManager.workflow(name)` constructs a `Workflow` with state and events only. `Workflow.add_step()` accepts any callable; `Workflow.run()` executes those callables sequentially. There is no identity/context, per-step capability, approval gate, cancellation/stop token, or SecurityManager hook. Failures produce a failed WorkflowResult and runtime event, not a security audit event.

## Audit Logging Coverage

- **Implemented, narrow:** `SecurityManager.authorize()` records its own allow/deny decisions, but no execution paths found invoke it.
- **Implemented, separate:** agent lifecycle/execution events are emitted through runtime EventBus when the agent manager has a runtime.
- **Implemented, separate:** runtime execution and task/workflow events describe state changes.
- **Partial:** `AuditLogger` is in-memory and process-local.
- **Missing:** unified structured audit records for tool, agent, runtime, workflow, API, provider, and denied execution, including correlation/request ID, resource, caller, permission, policy decision, result, and error.

## Computer-Control Coverage

`ComputerUseTool` currently exposes health/describe/echo actions; no actual desktop, process, keyboard, mouse, or filesystem control handler was found in the canonical tool implementation inspected. Its declared `computer.interact` permission is not enforced by ToolExecutor. If a real computer provider is later added, the current dispatch boundary would not automatically secure it.

## Model/Provider Access

`01_CORE/AI/ai.py` defines a provider-neutral `KairoAI` and calls its configured provider's `generate(prompt)` method directly. The development fallback only returns a local placeholder response. No concrete external model provider was found in the inspected source, and the provider call has no authorization context, permission check, approval, or security audit hook. **Current external-provider availability: MISSING/UNVERIFIED; provider boundary protection: MISSING.**

## Agent-to-Agent Delegation

The agent registry supports lookup and execution of registered agents. The core orchestrator selects agents for request intents. No explicit agent-to-agent delegation API, caller identity, constrained delegation token, or delegation audit record was found. The existing per-agent EXECUTE permission authorizes an agent to run itself through AgentManager; it does not authorize one agent to invoke another.

## Security Gaps

1. Global SecurityManager is not injected into the active execution pipeline.
2. API requests have no authenticated principal.
3. Tool permission metadata is not checked.
4. Runtime and workflow callable execution have no authorization context.
5. Agent-local authority is disconnected from global identity/permission and tool authority.
6. No explicit approval workflow is connected to critical API, agent, runtime, tool, or workflow operations.
7. Security audit is not generated for ordinary execution and is in-memory only.
8. Agent emergency stop prevents/halts lifecycle transitions for future calls but cannot interrupt a currently executing synchronous callable.
9. No application rollback/restore boundary is connected to privileged operations. Git history is not execution rollback.
10. `SandboxRequest.approved` is a caller-controlled boolean rather than a trusted approval artifact.
11. No actual shell/process/filesystem tool was found in the inspected canonical tool set; those operations are **UNVERIFIED as future/provider behavior**, not currently evidenced as implemented.
12. The optional model provider call is outside the shared authorization/audit boundary.

## Critical Findings (Pre-Implementation Baseline)

### KAIRO-CAP-001 — Tool permissions are not enforced

- **FILE:** `04_TOOLS/executor.py`
- **LINE/METHOD:** `ToolExecutor.execute`
- **CALL PATH:** `KairoSystem.execute_tool` → `ToolManager.execute` → `ToolExecutor.execute` → `tool.execute`
- **CURRENT BEHAVIOR:** Checks registration and enabled flag only; ignores `ToolDefinition.permissions`.
- **EXPECTED BEHAVIOR:** Resolve authenticated caller/agent context, authorize the requested permission and authority, audit decision, then execute only if allowed.
- **RISK:** High; every registered tool call bypasses the declared permission model. Current handlers are mostly stubs, but Browser can delegate to an external provider.
- **REQUIRED FIX:** Add one shared authorization service to ToolExecutor/ToolManager; deny by default when context or permission is missing.
- **TEST REQUIRED:** Prove denied tool handler is never invoked; prove granted permission allows execution; verify both outcomes create audit records.

### KAIRO-CAP-002 — API operations are unauthenticated

- **FILE:** `src/api/server.py`
- **LINE/METHOD:** `KairoHandler.do_GET`, `KairoHandler.do_POST`
- **CALL PATH:** HTTP request → route handler → global `kairo` → task/chat/status/events
- **CURRENT BEHAVIOR:** No caller authentication or identity propagation; POST validates payload shape only.
- **EXPECTED BEHAVIOR:** Authenticate API requests and authorize each operation before exposing or mutating runtime state; fail closed if credentials/identity are absent.
- **RISK:** High for shared or misconfigured deployments; loopback binding alone does not establish caller identity.
- **REQUIRED FIX:** Add a replaceable authenticator/principal resolver and apply operation permissions in one request dispatch boundary; preserve localhost development usage only with an explicit safe test/development configuration.
- **TEST REQUIRED:** Unauthenticated mutation denied; valid principal with permission succeeds; denial is audited and no task/agent/tool action occurs.

### KAIRO-CAP-003 — Agent-local authority is separate from global security

- **FILE:** `02_AGENTS/Manager/agent_manager.py`, `02_AGENTS/authority.py`, `src/kairo_system.py`
- **LINE/METHOD:** `AgentManager.register`, `AgentManager.execute`, `KairoSystem.__init__`
- **CALL PATH:** KairoSystem → orchestrator AgentManager → local controller `require(EXECUTE)` → RuntimeManager.execute → agent
- **CURRENT BEHAVIOR:** Local execution capability is checked; SecurityManager identity/permissions/approval are not consulted, and runtime receives no caller authority context.
- **EXPECTED BEHAVIOR:** The original caller identity and bounded agent identity/capability context must be checked centrally and propagated through runtime.
- **RISK:** High; local agent execute permission does not constrain downstream tools, data access, or API-originated requests.
- **REQUIRED FIX:** Establish a typed immutable execution context and make AgentManager, RuntimeManager, and tool execution use the same SecurityManager decision service. Avoid default unrestricted agent inheritance.
- **TEST REQUIRED:** Denied agent execution is not called; permitted agent execution succeeds; task/runtime events and audit carry the same request identity; delegation cannot escalate.

### KAIRO-CAP-004 — Workflow steps execute arbitrary callables without context

- **FILE:** `07_RUNTIME/Workflows/workflow.py`
- **LINE/METHOD:** `Workflow.add_step`, `Workflow.run`
- **CALL PATH:** RuntimeManager.workflow → Workflow.add_step(callable) → Workflow.run → callable
- **CURRENT BEHAVIOR:** Sequentially invokes each callable; no security context, permission, approval, cancellation, or audit-decision gate.
- **EXPECTED BEHAVIOR:** Each step receives a propagated immutable authority context and authorizes its declared resource/capability before invocation.
- **RISK:** High if a step invokes a privileged tool or provider; the runtime boundary does not prevent that.
- **REQUIRED FIX:** Integrate workflow steps with the shared authorization/execution service and audit every decision and result.
- **TEST REQUIRED:** Denied step is never called; allowed step runs; request/identity/correlation context survives every step; both outcomes are audited.

### KAIRO-CAP-005 — Sandbox approval can be asserted by the caller

- **FILE:** `06_SECURITY/Sandbox/provider.py`
- **LINE/METHOD:** `SandboxRequest.approved`, `SandboxProvider.execute`
- **CALL PATH:** Caller constructs `SandboxRequest(approved=True)` → `SandboxProvider.execute` → capability policy → operation callable
- **CURRENT BEHAVIOR:** The provider checks a boolean on the request; it does not verify a trusted approver, approval record, operation/resource binding, expiration, or single-use approval.
- **EXPECTED BEHAVIOR:** Verify an authenticated, auditable approval decision bound to the requesting identity, operation, capability, resource, and correlation ID.
- **RISK:** High for any caller able to reach this provider; the current tool set does not expose a direct sandbox tool, so exploitability through public KairoSystem routes was not established.
- **REQUIRED FIX:** Replace trust in the boolean with an approval service/record; the execution boundary must verify the record and audit the decision.
- **TEST REQUIRED:** A fabricated `approved=True` value cannot authorize an operation; a valid scoped approval succeeds once; denied and consumed approvals are audited.

## Recommended Architecture (Pre-Implementation Recommendation)

Use one immutable `ExecutionContext` carrying authenticated principal ID/type, optional agent ID, authority level, granted/candidate capability, and correlation ID. A single `AuthorizationService` (backed by `SecurityManager`) should make the policy decision and emit a structured audit decision. Agent, runtime, workflow, and tool entry points must require or explicitly derive this context; missing context must not silently acquire SYSTEM authority. API authentication should construct the context at ingress. Agent delegation should derive a narrower context and cannot add permissions. Existing local agent lifecycle control can remain, but it must be an additional gate rather than a replacement for global authorization.

Privileged results and errors should be audited in a `finally`-style execution boundary after an authorization decision. Durable audit storage should be a separate, follow-up improvement; do not claim in-memory audit is durable.

## Required Fixes (Pre-Implementation)

1. Add typed immutable execution/authorization context and structured policy decision.
2. Provide a secure principal bootstrap for API and explicitly granted service/agent identities.
3. Enforce the permission declared on each tool before calling its handler.
4. Propagate caller context through AgentManager, RuntimeManager, task creation/execution, scheduler, and Workflow steps.
5. Authenticate API requests and authorize each route; do not trust loopback by itself.
6. Bind agent identities to least-privilege capabilities and enforce explicit delegation.
7. Add unified audit records for allowed, denied, failed, and completed privileged operations.
8. Add cancellation-aware execution and define what emergency stop can and cannot interrupt.
9. Keep filesystem/process/computer-control operations unavailable until their provider and capability policy are explicitly implemented and tested.
10. Define rollback boundaries for reversible state changes; do not treat Git rollback as runtime rollback.

## Verification Tests

`tests/test_authorization_boundary.py` now contains behavioral tests for authorization decisions, tool permissions, agent authorization, bounded delegation, runtime context, workflow steps, authenticated task creation, sandbox approval, persistent audit, and emergency stop. Additional checks cover direct runtime executor access and context propagation to runtime callables. These tests have **not executed**: focused test discovery returned “No tests found,” and the workspace test runner returned zero tests rather than a successful test run. Treat all coverage below as required verification, not test evidence.

Existing tests found:

- `tests/test_kairo_system.py`: shared core/runtime object identity, tool registration/echo execution, agent registration/execution.
- `tests/tool_system/test_tool_system.py`: tool definitions, registration, echo execution, errors, tool permission metadata; current permission test checks only that `describe` returns the string.
- `tests/agent_platform/test_agent_platform.py`: agent result, executor success/failure, manager registration/execution.
- `tests/security_system/test_security_system.py`: identity, authority, permission manager, direct SecurityManager authorization, inactive identity denial, sandbox policy, and direct audit recording.
- `tests/command_center/test_command_center.py`: a separate command-center fake security integration tests allow/deny, not the HTTP API or KairoSystem execution pipeline.
- `tests/runtime_v2/test_runtime_v2.py` and related runtime tests: task/runtime behavior; no authorization-context propagation was identified.

Required new enforcement tests:

1. Unauthorized tool denied before handler invocation; authorized tool succeeds; both audited.
2. Unauthorized agent denied; authorized agent succeeds under a non-escalating context.
3. API requests without authentication denied; valid caller permissions map to exact route capabilities.
4. Runtime tasks, scheduled work, and workflow steps preserve identity and correlation ID.
5. Agent-to-agent delegation is explicit, permission-bounded, and audited.
6. Computer-use/provider operation denied absent required capability and approval.
7. Errors, retries, and denied operations retain structured audit outcomes.
8. Emergency stop blocks new work and accurately reports that synchronous in-flight work is not forcibly interrupted.

## Priority/Risk Ranking

| Priority | Finding | Risk |
|---|---|---|
| P0 | Tool and API execution are outside SecurityManager enforcement | High |
| P0 | Runtime/workflow context is absent; callable execution can escape the local agent permission boundary | High |
| P1 | Agent-local authority and global identity/permission model are disconnected | High |
| P1 | No explicit authenticated agent-to-agent delegation | High if delegation is later enabled |
| P1 | General privileged execution has no unified audit decision/result record | Medium-High |
| P1 | Sandbox approval is represented by caller-controlled boolean | High if provider is reachable |
| P2 | Audit log is in-memory and not durable | Medium |
| P2 | Emergency stop cannot interrupt synchronous in-flight operations | Medium |
| P2 | No application rollback boundary for side effects | Medium-High for future destructive actions |
| P3 | Actual filesystem and shell/process paths were not found; optional model-provider call has no auth hook | Filesystem/process behavior unverified; provider boundary missing |

## Final Status

**Authorization coverage: PARTIAL / UNVERIFIED.** The pre-implementation findings above describe the audited baseline. Subsequent source changes wire the existing `SecurityManager` into the principal execution paths and add behavioral tests, but those tests have not been successfully executed and the full execution chain has not been runtime-verified. Do not treat the authorization architecture as complete until targeted and full validation pass in an attached repository workspace.

The audit does not claim that filesystem, shell/process, or live computer-control operations are implemented. Their future/provider behavior is unverified. Synchronous arbitrary code cannot be forcibly interrupted by emergency stop; the implementation only guards new work and checks cancellation at cooperative boundaries. No source behavior outside this audit should be treated as authorized merely because it is local or registered.
