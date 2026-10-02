# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.

## Tech Debt

- `.gitignore` consistency: `*.xml` is ignored, yet `sample_panorama_config.xml` is committed (audit §4.9).
- Escape handling does not cover `\r` and control characters (audit §4.6). Fix lands with F1.7.

## Out of Scope

- Live Panorama API integration.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.
