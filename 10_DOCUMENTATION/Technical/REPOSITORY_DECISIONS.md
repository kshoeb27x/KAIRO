# KAIRO Repository Decisions

**Decision date:** 2026-09-15  
**Scope:** the eight candidates in `00_FOUNDATION/Architecture/Old_Repositories`  
**Evidence:** the existing read-only inventory, capability, and deep-audit reports.

> **Closure note:** The implementation status and final project-level
> classifications are superseded by
> [SOURCE_CAPABILITY_CLOSURE.md](./SOURCE_CAPABILITY_CLOSURE.md). This document
> preserves the original controlled migration decisions and guardrails.

## Guardrails

- These are architecture decisions, not permission to copy, execute, or merge
  third-party code.
- Every `EXTRACT` and `ADAPT` item must pass the license, dependency, security,
  and sandbox-test gates in `REPOSITORY_MIGRATION.md` before implementation.
- Capability scores are discovery signals, not proof of quality, safety, or
  production readiness.

## Decisions

| Scope | Strategy | Decision | Next controlled step |
| --- | --- | --- | --- |
| KAIRO foundation | **KEEP** | Keep the policy-first Python scaffold, security rules, data lifecycle rules, and audit artifacts as the KAIRO-owned baseline. | Repair the local Python toolchain, then add tests before expanding the core. |
| Awesome-Personal-AI | **ADAPT** | It is a small CC0 curated catalog, not an implementation. Use it only to improve the candidate-discovery rubric. | Extract relevant catalog fields into a KAIRO-owned inventory format; do not treat listed projects as approved. |
| memU | **EXTRACT** | Its focused Python memory subsystem, Apache-2.0 license, and existing tests make it the best source for a narrow memory experiment. | Identify a minimal memory interface and one isolated component; review its cloud/API assumptions and write KAIRO tests before copying. |
| MIRA | **REWRITE** | It is a broad, Rust-based AGPL-3.0 personal-agent product. Its requirements are useful, but full integration would create architectural and license coupling. | Preserve selected requirements—provider health, permission-aware skills, and observability—in a KAIRO design brief, then implement them natively. |
| OCT-Agent | **EXTRACT** | It is Apache-2.0 and already separates desktop and CLI packages. It is still too broad to adopt as a whole. | Select one bounded, non-privileged capability after dependency and security review; keep its UI/runtime out of the KAIRO core until sandboxed. |
| Open-Computer-Use | **ADAPT** | Its isolated-workspace approach is relevant, but its Functional Source License requires release-specific license review and its execution surface is security-critical. | Define a KAIRO sandbox-provider interface; evaluate this project only as an optional upstream implementation in an isolated environment. |
| OpenMind | **REWRITE** | It is a pre-v1, broad desktop assistant and no root license file is present in this local copy. Reuse requirements, not implementation. | Capture its local-first permission-gate and visibility requirements in KAIRO-owned specs; rebuild only approved parts. |
| Repos | **ARCHIVE** | This is a 500+ MiB collection of many unrelated repositories, not a coherent dependency. Direct integration would hide provenance and duplicate functionality. | Keep it read-only; inventory and classify individual repositories only when a concrete KAIRO capability needs one. |
| VoltAgent | **ADAPT** | Its modular agent/workflow ideas are useful, but it is a large TypeScript ecosystem and this local copy lacks a root license file despite the README's MIT claim. | Verify provenance and license from the authoritative source before using any package; otherwise implement KAIRO-owned interfaces inspired by its concepts. |

## Integration order

1. Keep and stabilize the KAIRO foundation.
2. Run the `memU` extraction as one isolated memory proof of concept.
3. Define the sandbox-provider interface before evaluating any computer-use runtime.
4. Convert the MIRA and OpenMind requirements into KAIRO-owned design specs.
5. Leave the broad `Repos` collection archived until individual components have a justified use case.

## Exit criteria for EXTRACT or ADAPT

- License and origin recorded.
- Dependencies pinned and vulnerability-reviewed.
- Secrets, permissions, network access, and destructive operations assessed.
- Build and tests pass in an isolated sandbox.
- A KAIRO-owned interface, tests, provenance note, and rollback path exist.
