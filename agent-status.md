# Agent Status

## Current Position

- **Epic 1 — Testing and Linting Foundation** (the gate; must finish before Epic 2/3 feature work)
- **Active task:** F1.2 Parser unit tests (next; acceptance criteria to be written before starting)

## Environment Notes

- Python 3.12.3, terraform 1.16.1 (`/usr/bin/terraform`), ruff 0.16.10, pytest 9.1.1.
- PEP 668: system pip is externally managed. Use `uv` / `uvx` for tool installs.
- `lib_docs/` does not exist yet (mentioned in AGENTS.md; create when needed).
- Tests must stay offline: fixtures + provider schema JSON are the static artifacts (PLAN.md, Epic 1 strategy).
- Ruff gate: `ruff check .` (config in `pyproject.toml`, line-length 120). `ruff format` is deliberately not in the gate yet (backlog.md).
- Tests load the root scripts by file path via `conftest.py` fixtures (`converter_module`, `splitter_module`, `run_script`).

## Completed

- **F1.1 Tooling baseline** (committed):
  - `requirements.txt`: pytest 9.1.1, ruff 0.16.10 (pinned).
  - `pyproject.toml`: ruff (E, W, F, I, UP, B, SIM, C4; line-length 120; target py39) + pytest settings.
  - Fixed 1022 ruff findings across both scripts (whitespace, typing modernization, unused code, long lines, f-strings without placeholders).
  - Behavior verified neutral: converter and splitter outputs are byte-identical to pre-change runs on the sample config.
  - `tests/test_smoke.py`: converter runs on sample and emits the core files; splitter --help and full run pass.
  - CI: installs `requirements.txt`, runs `ruff check .` then `pytest`; matrix 3.9-3.12; removed unused `python-docx`/`python-pptx`/`openpyxl`.
  - `.pre-commit-config.yaml`: ruff hook.
  - README requirement corrected: Python 3.9+ (code now uses 3.9 typing syntax).
- **F1.8 Lint both scripts** (done as part of F1.1).

## Next Steps (F1.2)

1. Write acceptance criteria for F1.2 into `acceptance.md`.
2. Enumerate `PanoramaParser` parse methods; write one test per method with isolated XML snippet fixtures under `tests/fixtures/`.
3. Tests must catch silent drops (e.g. same-named objects across device groups) where the current code has them, so Epic 3 fixes have red-to-green coverage.
