# Ticket 001: Read-only CQRS command drift probing and baseline Wellman adoption

- **ID**: ticket-001
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-01

## Scope
1. Make `CQRSValidator` command live-drift verification strictly read-only by default (`allow_mutations=False`, using HTTP `OPTIONS` probes instead of mutating `POST` requests with `data=b"{}"`), adding explicit `--allow-mutations` opt-in when active mutation testing is intended.
2. Add regression tests in `tests/test_ecosystem_cqrs.py` verifying zero mutating requests by default, `404` drift detection on `OPTIONS`, and opt-in `POST` behavior.
3. Add baseline Wellman governance adoption in the isolated ticket worktree so `wellman check` passes cleanly without modifying `main`.
