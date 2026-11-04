# Housekeeping — repository layout — acceptance criteria

The layout is a rule, not a habit. This task states the rule and moves the files that break it. The rule is
in `docs/ARCHITECTURE.md` §1.1, which is the one owner document; `PLAN.md` and the two readme indexes link
to it.

## The layout rule

- The root holds `AGENTS.md`, the two readme indexes (`README.md`, `docs/README.md`) and the tracking
  markdown (`PLAN.md`, `backlog.md`, `to-do.md`, `acceptance.md`, `agent-status.md`).
- `docs/` holds every other document. `tests/` holds every test. `src/` holds the tool's modules.
  `tools/` holds the developer scripts. `examples/` holds the sample input and the two example text files.
  The canonical sample output is the golden set `tests/golden/`, which pins the bytes of a real run.
  `terraform_output/` is only the default value of `--output-dir` and holds no committed sample.
- Each index names every document under it, so a file outside an index is a finding.

## Decision 1 — the import rule

`src/` is one flat namespace of modules. A module in `src/` imports its siblings by plain module name
(`import naming`), so no module builds a path.

- For tests, the one place the path is stated is `pyproject.toml` `[tool.pytest.ini_options]`
  `pythonpath = ["src"]`. It is resolved from the rootdir, so a run from any directory reads the same
  namespace, and no test or helper builds a module path. The entry-point scripts keep the plain-name imports
  they already have.
- For a run, the same namespace comes from Python's script-directory rule: `python3 src/panorama_to_terraform.py`
  puts `src/` on `sys.path`, so an entry point adds no path code.
- No module, test, or script adds a second path rule. `conftest.py` no longer loads a module by file path;
  it reads the namespace `pythonpath` states.
- `tools/` needs no rule: `tools/build_kitchen_sink.py` imports no tool module.

Every import stays offline and deterministic: the project is standard-library only, there is no package
build, and no import reaches the network.

## Decision 2 — the test-directory rule

`tests/` is flat. Test files sit beside `fixtures/` and `golden/`, and `tests/conftest.py` is the single
shared helper file (`tf_files`, `parts`, `file_text`, `written_bytes`, and the path constants the tests read
the layout through). No test file is grouped by rule area, so the layout does not change again.

## Decision 3 — discovery with no test file at the root

`pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]` is the setting that keeps discovery at
the repository root when the root holds no test file. `pythonpath = ["src"]` is added to the same block for
Decision 1. The suite is run as `python3 -m pytest` from the repository root, and `pytest` alone gives the
same result.

## What moves

| Now | After |
|---|---|
| `conftest.py` | `tests/conftest.py` |
| the 20 tool modules, including the two entry points | `src/` |
| `quick_start.sh` | `tools/quick_start.sh` |
| `sample_panorama_config.xml` | `examples/sample_panorama_config.xml` |
| `examples/example_terraform_output.txt` | stays; `examples/README.md` is the index for the three files |

## What may change, and only this

- The pins that read a module source by path: `tests/test_safe_input.py`, the writer scan in
  `tests/test_write_path.py`, the grounding scan in `tests/test_reference_edges.py`, the source reads in
  `tests/test_source_fetch.py`, `tests/test_import_blocks.py`, `tests/test_commit_actions.py`,
  `tests/test_robustness.py`, `tests/test_sanity_gate.py`, `tests/test_entry_coverage.py`. The writer scan
  exclusions are restated for the new paths: the single writer is `src/write_path.py`, and the test harness
  is not a tool module, so it sits outside the scanned set.
- `conftest.py` path constants (`REPO_ROOT`, `SAMPLE_CONFIG`, `FIXTURES_DIR`, `GOLDEN_DIR`, `SRC_DIR`) and
  `run_script`, which resolves a script name under `src/`.
- `quick_start.sh`, the two readme indexes, `docs/USAGE_GUIDE.md`, `docs/ARCHITECTURE.md` §1.1, and the
  `.gitignore` exception and comment.
- No rule, table, shape, naming rule, or gate rule changes.

## Golden set rule

A golden is the bytes of a real run and is never edited by hand. No committed golden names a path or a
module name (the goldens hold only `.tf` files), so no golden byte is expected to move. If a run moves a
golden, the run is re-run and the goldens are regenerated from it, not edited.

## Criteria

1. `ruff check .` is clean and `python3 -m pytest` passes at the repository root (baseline: 1443 tests).
2. Every test import resolves through `pythonpath = ["src"]`; no test builds a module path, and no module
   builds a path.
3. `python3 src/panorama_to_terraform.py examples/sample_panorama_config.xml --output-dir /tmp/hk` runs and
   passes the gate, so the entry point works from the new path with no path code.
4. `tools/quick_start.sh` runs from any directory through the moved paths.
5. Each index names every document under it: the root index names the tracking set and `examples/`;
   `docs/README.md` names every document under `docs/`; `examples/README.md` names the three files under
   `examples/`.
6. `AGENTS.md` names the tracking markdown set, so a document move does not depend on habit.
7. The move is one commit with `git mv`; the tracking markdown is a second commit.

## Result

Met. `ruff check .` is clean and `python3 -m pytest` passes 1443 tests at the repository root. Every test
import resolves through `pythonpath = ["src"]`, `conftest.py` builds no module path, and no module in `src/`
builds a path. `python3 src/panorama_to_terraform.py examples/sample_panorama_config.xml` runs and passes the
gate, and `bash tools/quick_start.sh` runs from any directory. Each index names every file under it, so
`examples/README.md` and `tools/README.md` are the indexes for those two directories and no file is outside an
index. No golden byte moved. The move is commit `ccf93a3`; the tracking markdown is the next commit.
