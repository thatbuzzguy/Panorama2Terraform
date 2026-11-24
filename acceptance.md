# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Epic 12 record is main's; the Epic 13 and Epic 14 records came from the `input-shapes` and
`import-pairing` worktrees and merged into main 2026-11-23, so their pieces run on main.

## Piece 12A.1, one owner for the Terraform minimum (main, the current task on main)

Piece 12A.1 of Epic 12, the pins (`PLAN.md`, Epic 12 decision 2). This is the whole piece: the byte
sweep is Piece 12A.2 and the document statements are Piece 12A.3, so no golden file and no document
version statement is changed here.

Owner: `src/commit_actions.py`, `TERRAFORM_MINIMUM`. It is the module whose rule the minimum comes from
(`docs/CODEBASE_ASSEMBLY.md` §12: actions need the action grammar level), and `panorama_to_terraform.py`
already imports it, so `src/` stays one flat namespace with no cycle and no new module, because a new
`src/` module is an index edit pinned by
`tests/test_layout.py::test_the_indexes_name_every_document_under_them`.

Helper: `tests/conftest.py::declared_terraform_minimum`, beside `declared_provider`, the one place the
test set reads the version.

Pin module: `tests/test_commit_actions.py`.

### Criteria

1. The minimum is stated once in `src/`. The three generated places that print it read the constant: the
   `terraform` block in `panorama_to_terraform.py`, the generated `README.md` line, and the `actions.tf`
   header in `commit_actions.py`.
2. No test file states the version as a string. The two pins in `tests/test_commit_actions.py` that state it
   read it through `declared_terraform_minimum`, so a change to the owner moves the pins with it.
3. The pins that read the goldens read them as committed bytes and compare them with the owner, so a
   disagreement between the owner and the goldens is a pin failure and not a silent difference.
4. The pin that reads the generated `terraform` block reads the print site through the owner, so it holds the
   one-owner rule and not a second copy of the version.
5. No golden byte moves in this piece, so the gate must be green on the goldens as committed.
6. `tests/tflint/probe.tf`, `requirements.txt` and `.github/workflows/python-tests.yml` are not read by this
   piece; they are Piece 12A.2 files. The `README.md`, `docs/USAGE_GUIDE.md`, `docs/RESOURCE_MAPPING.md`,
   `docs/COVERAGE_MATRIX.md` and `docs/CODEBASE_ASSEMBLY.md` §12 statements are Piece 12A.3 files.
7. A code comment that states the action grammar level (1.14) is a measured fact about the language, not the
   project minimum, so it is not moved through the constant in this piece.
8. The gate is measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no parallel plugin.

### The finding this piece reports

The decided value `>= 1.16` cannot be written into the owner in this piece. The generator prints the owner, so
writing 1.16 changes the bytes the golden pins read: the 17 golden `provider.tf` files and the 6 golden
`actions.tf` files. That is Piece 12A.2's commit, which moves the template and the goldens together. So this
piece lands the owner, the helper and the pins, and the constant holds the value the committed goldens carry.
The measurement of the disagreement is recorded in `agent-status.md`.

## Epic 13, the shapes an input can be (the `input-shapes` worktree)

The task is the planning of Epic 13 in the `input-shapes` worktree. The Epic 12 criteria this
file held are in `a153b04`. The design record is `docs/INPUT_SHAPES.md`, the pieces are in
`to-do.md`, and the live facts are in `backlog.md`.

### Criteria

1. **The archive input gains a producer, not a check.** The F5.1 rule is unchanged:
   `check_bytes` is the one definition of the two checks, and the door runs them on the
   decompressed bytes. No module states a second size definition, a second DTD rule, or a second
   reader.
2. **The size cap holds during decompression.** A pin hands the door a compressed input that
   expands past the cap, and the refusal names the origin and builds no tree. The pin runs
   offline on a committed fixture, so Goal 1 and the no-network rule are unchanged.
3. **The accepted shapes are read from the bytes, not from the file name.** The single-member
   gzip and single-XML-member tar.gz shapes are accepted only after the member decision is taken.
   A selection rule that reads member order is refused by the determinism rule
   (`docs/ARCHITECTURE.md` §6), so the refusal is the starting shape and the decision must be
   taken before an emitter, a gate rule, or a report can read a selection.
4. **One decision, stated once, for what the provenance record names for an archive read**: the
   origin kind, the member name, which bytes `size` and `sha256` name, and how the cache rule
   reads. The F5.3 rule already answers the byte question for the door — the record names the
   bytes the door checked — so the decision is how the archive enters that rule, not a second
   version of it.
5. **The splitter diagnostic prints the fact, not a guess.** It states the number of
   `device-group/entry` rows read, the shape the tree holds instead, and the source line. The
   finding fits the four parts of the console-line rule (`container_coverage.console_line`,
   `docs/ARCHITECTURE.md` §3.2), or prints in the report only because it compares two sets. The
   exit code stays with the rules that read the files (`docs/ARCHITECTURE.md` §4.6).
6. **Fixtures move the pins in one commit.** Each accepted shape gets a committed fixture read
   through the fixture assembler, and the pins that state the printed fixture set name the new
   fixture count in the same commit (`to-do.md` §Rules the layout keeps).
7. **Version facts stay measurements.** The comparison of the "XML and XPath" page names the
   pages measured — 9.1 and 11.1 & Later, 2026-11-23, same node model and entry shape — and the
   10.2 leg stays open until measured. No document states a version difference it cannot name a
   measurement for. The documentation-to-fixture relationship is owned by
   `docs/API_DOCUMENTATION_AND_MOCKS.md`, so this epic adds no second rule for it.
8. **Live-target facts stay in `backlog.md`**: the UI download form, the backup DOCTYPE question,
   multi-member bundles, and the unfinished comparison leg. Nothing in the design record states
   them as facts.
9. **The layout rules hold**: `docs/INPUT_SHAPES.md` is named in the `docs/README.md` index and
   carries its owner row; the shape table names its owner module in the `docs/ARCHITECTURE.md` §1
   table when it lands; no new module states a second naming rule, writer, console line, or
   environment name, so the pins that scan the `src/` set read it with the other modules.
10. **No `src/` path that Epic 11C or Epic 12 runs on is touched by this worktree**, and the
    shared tracking markdown is merged by hand against main.

### Definition of done

Every rule in `docs/INPUT_SHAPES.md` names its owner. Each pending decision in §2 is recorded as
a decision before the code that reads it lands, and the pins that hold each rule run offline on
committed material.

## Epic 14, the blocks a run binds to the live config (the `import-pairing` worktree)

The task was the planning of Epic 14 in the `import-pairing` worktree, on branch `import-pairing` from main
`c845f07`, 2026-11-23, merged into main at `9fe33c7`. The design record is `docs/IMPORT_BINDING.md`, the pieces are
in `to-do.md`, and the live facts are in `backlog.md`. No `src/` file was touched during the planning, and no
decision is taken yet, so no piece can be written from a decision.

### Criteria

1. **The mode is data read through its record owner.** A later run reads the decision back through
   `unit_manifest.parse_rows`, and the merged record is the codebase-level view, so no report or gate rule states
   a second mode rule. `--selection` names the read set only (`docs/MULTI_RUN_CODEBASE.md` §2 rule 1), so the mode
   needs its own scope-name argument, read through `container_coverage.is_scope_path` and `SCOPE_PATH_ROOTS`, the
   one scope-path definition, and no module states a second unit set.
2. **The mode sits at one level until the entry-level decision is taken.** A device, a virtual system, a device
   group and a template are already units, so a per-device or per-device-group request needs no new level. If an
   entry-level mode is taken, `OWNERSHIP.json` is the record that holds it, because that record already holds one
   row per entry the run emits, and `unit_manifest.units` stays the one unit set.
3. **The mode cannot depend on order.** A declaration that reads the order the entries appear in is refused by
   `docs/ARCHITECTURE.md` §6, so the argument is an explicit list of scopes or a refusal, and a mode a run
   declares must agree with the mode the merged record names for the same unit. The argument is held by the CLI
   and not by a rule owner, which is the rule the no-flag scan holds.
4. **A shape change names the committed files it moves.** A field that enters `unit_manifest.FIELD_ORDER` is
   printed for every row, so the golden data files move in the same commit as the pins that read the row. The
   criterion is not that no golden moves, but that a piece states which committed files it moves; a run that
   declares no mode writes today's bytes only where the decision says so, which is the F5.5 and F6.4 precedent.
5. **The whole-block fact is a coverage fact.** It compares the properties a matrix row declares with the fields
   the emitter reads on a run, so it is a WARN and the exit code stays with the rules that read the files
   (`docs/ARCHITECTURE.md` §4.6). Its owner is the property scan through `entry_coverage.py`, its report section
   follows the F3.9 grouping rule, and the finding fits the four parts of the console-line shape
   (`container_coverage.console_line`) or prints in the report only.
6. **The completeness half states no rule of its own.** It compares the block set the one block reader read with
   the entry set the run's ledger read, so it is the same shape as the round-trip cross-check; it reads the unit
   through `unit_manifest.units` and the mode through the record, and the agreement half stays in
   `sanity_checks.check_import_blocks`.
7. **A device fact reaches an id only through a source the provenance record can name.** The offline half is a
   site value the operator declares, read through `site_data.py` and printed through `VALUE_VARIABLES` so the
   block and the id state the same fact. The rule that a run with no network passes CI is unchanged, and the live
   half stays in `backlog.md`.
8. **The rule types stay reported until the shape decision and the F3.5 rulebase value land.** No unverified
   value is written, and the order pins, the iterated block rule and the goldens move together if the shape
   changes, so a shape change cannot be a print-only change.
9. **Read-through and binding cannot both claim one name.** A unit that binds its entries writes no `data` block
   for a name it binds, and a read-through scope stays labelled in the generated `README.md` until the built-in
   name table lands.
10. **Plan facts stay measurements.** No test can pin a plan, because a plan needs a device, so the offline
    reading is the property scan measured on a run, and the Terraform behaviour for an import block whose resource
    is already in state is recorded as a decision to take on measurement.
11. **Every rule names its owner, and a pending owner is named by the decision that takes it.** A document names
    only tests that exist, and a pending pin says it is pending.
12. **The layout rules hold**: `docs/IMPORT_BINDING.md` is named in the `docs/README.md` index and carries its
    owner row; no new module states a second naming rule, writer, console line, or environment name, so the pins
    that scan the `src/` set read it with the other modules.
13. **The planning touched no `src/` path that Epic 11C or Epic 12 runs on.** It merged into main 2026-11-23, so
    the pieces run on main, and a piece touches only the paths its decision names.

### Definition of done

Every rule in `docs/IMPORT_BINDING.md` names its owner. Each pending decision in §2 is recorded as a decision
before the code that reads it lands, each live fact is recorded in `backlog.md`, and the pins that hold each rule
run offline on committed material.
