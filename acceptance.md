# Acceptance Criteria — current task

No feature is in progress. F5.4 (the cross-source shadow report) is complete and committed; its
acceptance criteria are in the git history.

Write the acceptance criteria here before writing code or tests for the next feature. The next
feature is F5.6 (Terraform state as a source); the pieces that need a decision are in `to-do.md`.

The gates that do not change between features:

- `ruff check .` clean, `pytest` green.
- Both golden sets byte-identical. The goldens cover `.tf` files only.
- Report and record determinism: the same arguments and the same bytes write the same bytes.
- Exit codes unchanged: an input refusal is 1, an argument error is 2, and the F4.1 gate decides the
  conversion exit code. A WARN does not fail a run.
- Every test runs offline: no test opens a connection, so CI passes with no server.
- No backward compatibility: migrate the old path and the old pins to the new rule.
