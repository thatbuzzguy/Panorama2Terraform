# Acceptance — `pyproject.toml` `target-version` to the Python floor (Piece 12)

Criteria set 2026-11-18 for the `backlog.md` Nice-to-Haves item: `target-version` states the syntax level
the lint gate enforces, and that level becomes the floor the project already runs on. The piece is the
one-time pass that moves the codebase to that level, plus the pins that read a module's source spelling and
the documents that state the level.

Owners: `pyproject.toml` for the level the lint gate enforces and for the Python floor;
`docs/ARCHITECTURE.md` §1.1 for the gate and for the layout the pass cannot change; `README.md` and
`docs/USAGE_GUIDE.md` for the floor as a requirement; `.github/workflows/python-tests.yml` for the CI gate;
`tools/README.md` for `tools/check_documents.py`, which is a document-review script and not part of the gate;
`agent-status.md` for the measured count and the recorded run time.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule. `agent-status.md` and
  `acceptance.md` hold the measurement.
- A pin measures content or a name, never the wording of a document.
- No pin is weakened or removed. When a pin changes what it reads, the reason is recorded here.
- Standard library only; everything stays offline and deterministic. `target-version` is a lint setting, not a
  dependency, so the pass adds no package and no import.

## Item 1 — the findings, re-measured

**Decision.** The count is measured at the level `pyproject.toml` states, on the tree as it stands, not
carried from the 2026-11-11 audit.

Measured 2026-11-18, `ruff check .` with `target-version = "py310"`: 110 findings, 26 files.

| Rule | Meaning | Measured |
|---|---|---|
| `UP045` | `Optional[X]` becomes `X \| None` | 85 |
| `B905` | `zip` with no `strict` | 20 |
| `UP035` | `typing.Callable` becomes `collections.abc.Callable` | 4 |
| `UP007` | `Union[X, Y]` becomes `X \| Y` | 1 |

The audit measured 101 (80 `UP045`, 16 `B905`, 4 `UP035`, 1 `UP007`). The tree changed since, so the
difference is the tree, not the rule: 5 more `UP045` and 4 more `B905` are the typing and the `zip` calls the
pieces since the audit wrote.

- AC-1.1: at `py310`, `ruff check .` reports no finding after the pass. Held by the gate run, not by a pin,
  because no pin reads `pyproject.toml` or the CI workflow file. The gate is the order `ruff check .`,
  `ruff format --check .`, `python3 -m pytest`, `python3 tools/check_documents.py`.

## Item 2 — the typing pass, and the pins that read a source spelling

**Decision.** The three annotation rules are applied as the rules state them: `X | None` for `Optional`,
`X | Y` for `Union`, and `collections.abc` for `Callable`. No `from __future__ import annotations` is added:
the floor evaluates a PEP 604 union at runtime, so a future import would be a second mechanism for the same
fact. Where a `typing` import stops being read, it is removed, because the import line is the statement of the
spelling.

Two pins read a module's source spelling, so they read the new spelling. Each keeps the fact it measured.

- AC-2.1: `tests/test_reference_edges.py::test_the_module_resolves_no_name_and_records_no_name` holds the
  import set of `src/reference_edges.py` as the statement that the module reads the fact order through its
  owner. The import list it reads gains `collections.abc` where `typing` was, so the pin reads the new name.
  The fact is unchanged: the module reads its owners and states no rule of its own.
- AC-2.2: `tests/test_source_fetch.py::test_source_fetch_imports_are_standard_library` holds the allowed set
  as the set of standard-library names the fetch layer may read. `src/source_fetch.py` now reads
  `collections.abc`, so the allowed set names `collections` where it named `typing`. The fact is unchanged: no
  third-party import, and the `pan-os-python` producer stays refused.
- AC-2.3: no other pin reads a typing spelling. Measured 2026-11-18: the pins that read a module's import set
  are the two above, plus `tests/test_api_requests.py` (the scope index's import set, read on
  `src/api_requests.py`) and `tests/test_api_path.py` (the path 2 entry point's import set, read on
  `src/api_to_terraform.py`), and the pins that read `tools/build_kitchen_sink.py` read string literals.
  Neither of those two modules takes a `typing` import, so the pass cannot move them.
  `src/panorama_to_terraform.py` keeps `from typing import Any`, which no pin reads, because `Any` states no
  value shape and is not one of the three spellings.
- AC-2.4: the pass changes no value, no name, and no byte a run writes, so the goldens and the byte pins are
  unchanged.
- AC-2.5: the pass's own output has to satisfy the format gate, so two files also carry a format change:
  `src/resource_mapping.py` (the blank line between the module docstring and the table comment) and
  `src/sanity_checks.py` (the `check_terraform` signature, which fits on one line at the gate's 120 columns).
  The import rule moved one block, in `src/source_fetch.py`, because `collections.abc` sorts before
  `dataclasses`. No value, name or byte is changed by these.

## Item 3 — `zip` with a `strict` decision, read call site by call site

**Decision.** `strict=True` is written where the two sides are the same set by construction, which is the fact
the call already asserts: a field order and the values in that order, one record and one line per record, one
row and the row the rule fills. `strict=False` is written where the two sides are not the same set by
construction, with a short comment for why. A call site is not given `strict=True` when the shorter side is
what the code means to read.

The 20 sites, each with its decision.

| Site | What the two sides are | Decision |
|---|---|---|
| `src/unit_manifest.py` `build_rows` | `FACT_KEYS`, and the facts of one ledger row read through `facts_of` | `strict=True` |
| `src/ownership.py` `row_key` | `FACT_KEYS`, and `row_facts`, which reads the row through `FACT_KEYS` | `strict=True` |
| `src/ownership.py` `scan_row` (two sites) | `FACT_KEYS`, and `unit_manifest.facts_of(row)` | `strict=True` |
| `src/reference_edges.py` `build_rows` | `FIELD_ORDER`, and the four values the row states in that order | `strict=True` |
| `src/sanity_checks.py` `check_data_files` | the manifest rows, and the rows `reference_edges.order` fills, one per manifest row | `strict=True`, so a row the order rule left unfilled cannot read as a pass |
| `src/split_device_groups.py` `split_panorama_config` | the device-group rows, and the file names `split_file_names` builds from those rows, one name per row | `strict=True` |
| `tests/conftest.py` `check_chain_semantics` | a chain, and the chain without its first rule, so the two sides differ by one by construction: each rule is read against the rule before it | `strict=False`, with the comment. `strict=True` would refuse a chain of any length |
| `tests/test_commit_actions.py` `_row` | `unit_manifest.FACT_KEYS`, and the identity tuple built from `FACT_KEYS` | `strict=True` |
| `tests/test_data_file_gate.py` `_manifest_row` | `unit_manifest.FACT_KEYS`, and the facts the pin names for the row | `strict=True` |
| `tests/test_data_file_gate.py` `_ownership_row` | `ownership.FACT_KEYS`, and the facts the pin names for the row | `strict=True` |
| `tests/test_reference_edges.py` corpus pin | `FIELD_ORDER`, and each pair the pin built from `FIELD_ORDER` | `strict=True` |
| `tests/test_container_coverage.py` console pin | the findings, and the block's lines after its header, one line per finding (`docs/ARCHITECTURE.md` §3.2) | `strict=True` |
| `tests/test_property_coverage.py` console pin | the finding rows, and the block's lines after its header, one line per row | `strict=True` |
| `tests/test_shadow_coverage.py` console pin | the findings, and the line the rule printed for each | `strict=True` |
| `tests/test_provenance.py` record pin | the requests the run read, and the record entries the run wrote, one per read | `strict=True`, which is the fact the pin already asserts |
| `tests/test_api_path.py` agreement pin | the two row sets, which the pin compares after asserting they hold the same number | `strict=True` |
| `tests/test_robustness.py` static-route pin | the router's routes, and the local names the naming rule and the digest rule produce for each | `strict=True` |
| `tests/test_split_device_groups.py` two-entry pin | the two rows, and the two templates the fixture states for them | `strict=True` |
| `tests/test_sanity_gate.py` two-path pin | the two reports' check results, one per rule in `CHECK_ORDER` for both runs | `strict=True` |

- AC-3.1: every `zip` call in the tree states its `strict`. Held by the gate at the new level
  (`pyproject.toml` states the level, and `B905` is in the selected rule set), not by a pin.
- AC-3.2: no call site changed from truncation to a refusal in a way that can change a run's result on the
  committed material. Measured: every `strict=True` site reads two sets that the code builds to the same
  length, so a pass that reports nothing before the change reports nothing after it. The one site where the
  lengths differ by construction keeps `strict=False`.

## Item 4 — the level, the floor, and the documents that state them

**Decision.** `pyproject.toml` `target-version` becomes `py310`, and the Python floor stays 3.10: the piece
does not move the floor. `pyproject.toml` is the owner of the level, so the comment there states what the
value is now, and every other document links to it or states the requirement.

- AC-4.1: `target-version` equals the floor, so the comment that kept it at `py39` for the codebase's pre-3.10
  spelling is gone, because the pass removed that spelling.
- AC-4.2: `README.md` and `docs/USAGE_GUIDE.md` state the floor as a requirement (3.10 or later), which the
  piece does not move, so neither changes. Measured 2026-11-18: the only document that stated the level as a
  fact below the floor is `docs/ARCHITECTURE.md` §1.1, which now states that the gate enforces the level
  `pyproject.toml` states and that the level equals the floor, and names the two import-set pins.
  `tools/README.md` states no level, so it does not change. One owner per rule: `pyproject.toml` owns the
  level, `README.md` and `docs/USAGE_GUIDE.md` own the requirement, and §1.1 links to `pyproject.toml`.
- AC-4.3: the CI matrix legs start at 3.10, so no leg runs a Python below the level the lint gate enforces,
  and the workflow reads `pyproject.toml` for the level rather than stating its own. Measured 2026-11-18: the
  workflow file states no `target-version`, so it does not change. No pin reads the workflow file, so this is
  the CI measurement.
- AC-4.4: `tools/check_documents.py` reports no finding, and the pass cannot move a document fact: it reads
  the license split and each notice's file total at the commit `docs/LICENSING.md` names, and the code tables
  it compares with the document tables are data, so an annotation change moves no table.

## Item 5 — no pin is weakened

- AC-5.1: no pin is removed, and no pin's assertion is narrowed. The two pins in Item 2 read a different name
  for the same fact; the `strict` argument is added to the pins in Item 3, which can only add a failure, so no
  pin that passed before can pass now when it failed before.
- AC-5.2: the pin count is recorded before and after, so a change in the count is visible. Expected:
  unchanged, because this piece adds no pin.

## Gate

Run in order, with no parallel runner: `ruff check .` (at the level `pyproject.toml` states),
`ruff format --check .`, `python3 -m pytest`, `python3 tools/check_documents.py`.

Baseline, measured 2026-11-18 on the tree at commit `698c957` in a detached worktree, in that order, with
tflint 0.66.0 present: `ruff check .` clean at `py39`, `ruff format --check .` clean on the 100 Python files,
1,697 pins in 52 modules, all pass, no skips, 339.42 s, and the document check reports no finding. The same
tree read at `py310` reports the 110 findings Item 1 measures, which is this piece.

After the pass, measured 2026-11-18 on the committed tree, in that order, with tflint 0.66.0 present:
`ruff check .` clean at `py310`, `ruff format --check .` clean on the 100 Python files, 1,697 pins in 52
modules, all pass, no skips, 273.21 s, and the document check reports no finding. The count is unchanged, so
no pin was added, removed, or weakened (AC-5.2). No pin reads a markdown file, so the document edits this piece
made cannot move a pin; the document check was run again after them and reports no finding.
