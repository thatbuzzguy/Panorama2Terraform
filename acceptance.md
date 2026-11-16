# Acceptance — `ruff format` as a gate

Criteria set 2026-11-16 for the `backlog.md` Nice-to-Haves item, the next actionable slice that
`PLAN.md` §Sequencing and `to-do.md` name. The item is two parts: the one-time format pass, then the
gate that keeps the tree formatted.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule.
- A pin measures content or a name, never the wording of a document.
- A historical record is not kept in the markdown; the git history is the record.

## The two rules this piece states

**1. The format rule is a gate rule, not a housekeeping habit.** `ruff format --check .` is part of the
full run, next to `ruff check .`. The gate has two parts and this piece touches only one:

- The tool's post-run gate on the output it wrote is `docs/ARCHITECTURE.md` §4.6. It reads the files a run
  wrote, so it is unchanged by this piece: `ruff format` reads the repository's own Python, never the
  `.tf` output or a report.
- The development gate is the full run, stated in `docs/ARCHITECTURE.md` §1.1, named by `README.md`
  §Testing, and measured in `agent-status.md`. `ruff format --check .` joins it.

**2. No pin holds the format gate.** `agent-status.md` states that no pin reads the CI workflow file, so the
gate is stated in the workflow and in the documents that own it, and not pinned by a test. `ruff format
--check .` is itself the check that fails when the tree is not formatted, so a pin would restate it.
`pyproject.toml` already configures ruff (`line-length = 120`, the `src` and `[tool.ruff.lint]` rule sets),
so this piece changes no ruff setting: `target-version` stays `py39`, which `backlog.md` records as the
separate `py310` task.

## The one-time format pass

- Scope: the Python files of the repository — `src/` (22 modules), `tests/` (52 test modules plus
  `tests/conftest.py`), and `tools/` (2 scripts). Ruff's default quote style is the double quote, which is
  the reason the diff is large: the tree writes the single quote.
- The pass is its own commit, so the format diff stays reviewable and the gate change is not mixed with the
  largest file diffs: `src/resource_mapping.py` (4,693 lines added, 3,964 removed) and
  `src/panorama_to_terraform.py` (3,043 added, 2,670 removed). `backlog.md` estimated about 1,500 changed lines
  for the second file before the pass was measured.
- The pass changes source shape only, never behaviour. Formatting must not change any tool output byte, any
  golden, the corpus pins, the schema pins, or a pin that reads a module source through `ast` or through
  `read_text`. A golden byte pin or a corpus pin that fails after the pass is a finding: investigate, do not
  weaken the pin.
- `tools/check_documents.py` measures document facts against the code. The license split is measured at the
  commit the document names (`ac7609e`), so the format pass cannot move it. If the pass moves a measured fact
  a document states, the document is corrected through the tool, not by hand-guessing.

## Measurement, before the pass

Baseline measured 2026-11-16 at commit `2ea5afe`:

- `ruff check .`: clean.
- `python3 -m pytest`: 1,685 pins in 52 test modules, all pass, no skips.
- `python3 tools/check_documents.py`: no finding.
- `ruff format --check .`: 73 Python files would be reformatted (22 in `src/`, 49 in `tests/`, 2 in
  `tools/`), which is the set the pass covers. No document or fixture file is reformatted.

## Measurement, after the pass and after the gate

The format pass, committed `c740db8`: 73 files changed, 20,025 lines added, 16,007 removed — 22 modules in
`src/`, 49 in `tests/`, 2 in `tools/` (4 test modules were already formatted). The per-file changed-line counts
are in the commit message. Ten string literals over the 120-line limit are split by hand, and eight pins read the
double-quote spelling of a module source; both sets are named in the commit message. No golden, fixture, or tool
output byte changed, and the pin count is unchanged, so no pin was weakened.

The full gate, measured 2026-11-16 on the gate-adoption commit `7df0570`:

- `ruff check .`: clean.
- `ruff format --check .`: clean, 100 Python files already formatted.
- `python3 -m pytest`: 1,685 pins in 52 test modules, all pass, no skips, 333.87 s (298.35 s on the formatted
  tree before the tool change, and 305.95 s on the tree that carries these tracking edits).
- `python3 tools/check_documents.py`: no finding.

The CI step is `.github/workflows/python-tests.yml`: `ruff format --check .` runs after `ruff check .` on each
matrix leg, before the tests.

Finding recorded. The format commit alone reports 2 findings from `tools/check_documents.py`, because the tool read
a notice's file total from the working tree: `src/panorama_to_terraform.py` held 7,780 lines against the 7,407
`docs/LICENSING.md` states, and `src/split_device_groups.py` held 382 against 383. The numbers in the document are
a measurement at commit `ac7609e`, so the tool reads them at that commit, and no document number was changed by
hand. The finding is closed by `7df0570`; the two numbers in `docs/LICENSING.md` are unchanged.
