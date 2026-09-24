# KAIRO Permission Model

Default: deny.

Levels:
- L0: read-only public/local data
- L1: create/modify sandbox artifacts
- L2: execute approved tools in sandbox
- L3: staging operations
- L4: production operations with policy checks
- L5: critical/irreversible actions requiring explicit authorization

Never store credentials in source code. Use a dedicated secrets manager when the system moves beyond local development.
