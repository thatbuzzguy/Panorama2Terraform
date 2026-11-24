# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner
documents hold it. The items that need a fact a live target states are in `backlog.md`. Epic 11 is complete as of
2026-11-23, so its piece list and its open facts are in `backlog.md`, and the acceptance criteria for the current
piece are in `acceptance.md`, with pointers to the Epic 13 and Epic 14 records.

## Epic 13 — the shapes an input can be (design record `docs/INPUT_SHAPES.md`)

Planned in the `input-shapes` worktree, 2026-11-23. The decisions are in `PLAN.md`, the criteria
are in `acceptance.md`, and the live facts are in `backlog.md`. Phase 13A is complete as of 2026-11-24, so its
pieces are in the git history. Each remaining piece needs a decision, or a fact a live target states.

### Phase 13B, the archive producer

Blocked on the two open `docs/INPUT_SHAPES.md` §2 decisions: the rule for a bundle with more than one XML member
(decision 4), and which bytes the provenance record names for an archive read (decision 5).

- **13B.1** — the member decision: single-member gzip and single-XML-member tar.gz are accepted;
  a bundle with more than one XML member is refused until a selection rule exists, and a
  selection that reads member order is refused by the determinism rule, so the decision stays
  open until it is taken.
- **13B.2** — the size rule during decompression: the cap is enforced as the bytes expand, so a
  refusal names the origin and builds no tree, and no second size definition appears.
- **13B.3** — the provenance facts for an archive read: the origin kind, the member name as a
  field the file case does not have, which bytes `size` and `sha256` name, and how the cache rule
  reads for an archive.
- **13B.4** — the pins: both checks run on the decompressed bytes through the door, no producer
  bypasses them, and the archive path adds a producer and no check.

### Phase 13C, the documents

- **13C.1** — how to get the correct export: the Panorama-level export holds the device-group
  rows, a per-device export holds the device's own config with none. Stated in `docs/USAGE_GUIDE.md`
  and `docs/DEVICE_GROUP_SPLITTING.md`; the troubleshooting rows hold no row wording, because they
  name the shape and link to the table, which `tools/check_documents.py` reads.

## Epic 14 — the blocks a run binds to the live config (design record `docs/IMPORT_BINDING.md`)

Planned in the `import-pairing` worktree, 2026-11-23, and merged into main at `9fe33c7`, so the pieces run on
main. The decisions are in `docs/IMPORT_BINDING.md` §2, the criteria are in `acceptance.md`, and the live facts
are in `backlog.md`. No `src/` file is touched until a piece lands, and the shared tracking markdown is joined by
hand against main when a branch still holds work. No piece can be written from an untaken decision, so each piece
names the decision it needs.

### Phase 14A, the mode as data

- **14A.1** — the two mode values and the level the mode sits at (§2 decision 1). Needs the decision on
  whether the mode stops at the unit, because a device group, a template, a vsys and a device are already
  units.
- **14A.2** — the record field that holds the mode: read through `unit_manifest.parse_rows`, merged through
  `codebase_state.py` rule 2, and read by the `data_files` gate rule. Needs decision 2 and the answer to
  fact 11, because a field that enters the shape moves the committed rows.
- **14A.3** — the declaration argument: a scope-name argument read through `container_coverage.is_scope_path`
  and `SCOPE_PATH_ROOTS`, held by the CLI and not by a rule owner. Needs decision 3, which is also the decision
  that an order-dependent declaration is refused.
- **14A.4** — the report section that names the units a run bound, through `entry_coverage.py` and the F3.9
  grouping rule, so no module states a second unit set or a second grouping rule.

### Phase 14B, the facts an id needs

- **14B.1** — the device fact for a bound unit: the site value an operator declares, read through `site_data.py`
  so the block and the id print the same fact through `VALUE_VARIABLES`. Needs decision 6; the half that reads a
  live target stays in `backlog.md`.
- **14B.2** — the rule types: the shape decision in §2 decision 7, then the instance half of
  `import_blocks.IMPORT_ROW_FIELDS` if the shape changes. Blocked on the F3.5 rulebase value and on a source
  that states the position a live rulebase holds, so it stays out of the pieces until both land.
- **14B.3** — the read-through order for a bound unit, which needs decision 8 and the built-in name table.

### Phase 14C, the plan side and permanence

- **14C.1** — the whole-block fact: the name, the owner, the severity, and the report section that names which
  entries of a bound unit can read as zero change. Needs decision 4.
- **14C.2** — the completeness half for a bound unit: one block per entry the run's ledger reads as `emitted`.
  Needs decision 5, which states whether it is the same rule as the round-trip cross-check or a second rule.
- **14C.3** — permanence: `imports.tf` as permanent codebase content or a first-run file, decided on the
  Terraform measurement in fact 10.

## Feature-sized items that stay blocked

Feature-sized items that stay blocked on a fact the tool cannot read offline are recorded in
`backlog.md` and are not pieces here: the rulebase value string and the rule position from a live
target (F3.5), which also gate the rule data column for `rulebase` and the import block for a
rule entry; a config entry inside a stack needs a provider location shape; the EDL
`certificate_profile` field needs a rule that makes the EDL site resolve names; the per-entry
report `profile_name` column needs a value the provider does not declare; the path 2 live facts in
`docs/API_CONVERSION_PATH.md` §4 need a live target; and the two shapes the F5.6 comparison table cannot
state as one name need a fixture that exercises them, because the table's content is read from a
measurement over the committed corpus rather than from a name; the tag half also needs the parse to fill the
`description` key its row declares, which `parse_tags` does not read.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking
  markdown set, and each index names every document under it, so a file outside an index is a
  finding.
- Import rule: `docs/ARCHITECTURE.md` §1.1 is its owner. `src/` is one flat namespace, so a module
  may import any `src/` module without a cycle, and nothing under `tests/` may import another test
  module: a fact more than one test module reads is stated once in `tests/conftest.py` and read
  from there. The one test that checks the rule reads only `src/`. A test may import `src` modules
  and `tests/conftest.py` through `importlib`. `src/` may not import from `tests/`. `tools/` is not
  on the test path, so `tests/test_build_kitchen_sink.py` reads the fixture assembler through
  `importlib` on the path `tests/conftest.py` builds once.
- Path 2 adds two modules, `api_requests.py` and `api_to_terraform.py`, and both must be named in
  the `docs/ARCHITECTURE.md` §1 table. `rule_data.py` is a tool module named in the same table, and the
  iterated block and the rule data files add no second naming rule, no second writer, no second console
  line, and no environment name, so the pins that scan the `src/` set read it with the other modules.
  `codebase_state.py` is a data module named in the same table, so the same pins read it: it holds no
  writer, names no file, and states no key or shape rule of its own.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The
  fixture assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped,
  and the record is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is
  not corpus material, so it sits in its own set (`tests/responses/`), and the pins that state the
  printed fixture set are not changed by it (`docs/ARCHITECTURE.md` §1.1).
