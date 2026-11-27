# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner
documents hold it. The items that need a fact a live target states are in `backlog.md`. Epic 11 is complete as of
2026-11-23 and Epic 13 as of 2026-11-25, so their piece lists are in the git history and their open facts are in
`backlog.md`. The acceptance criteria for the current piece are in `acceptance.md`, with pointers to the Epic 13
design record and the Epic 14 record.

## Epic 14 — the blocks a run binds to the live config (design record `docs/IMPORT_BINDING.md`)

Planned in the `import-pairing` worktree, 2026-11-23, and merged into main at `9fe33c7`, so the pieces run on
main. The decisions are in `docs/IMPORT_BINDING.md` §2, the criteria are in `acceptance.md`, and the live facts
are in `backlog.md`. No `src/` file is touched until a piece lands, and the shared tracking markdown is joined by
hand against main when a branch still holds work. No piece can be written from an untaken decision, so each piece
names the decision it needs.

### Phase 14A, the mode as data — complete on main, 2026-11-26

The four pieces are complete and committed, so their records live in the git history and the measurements are in
`agent-status.md`. Decision 1 is taken: the two values, and the level the mode sits at. Decision 2 is taken: the field,
the owner that states it, and the answer for a unit the run did not mark. Decision 3 is taken, 2026-11-26: the
declaration names units through `scope=mode` pairs sorted by place, the argument is `--import-mode` held by the CLI, a
declaration that disagrees with a record row is refused before the first write, and `--import-blocks` is removed.
Decision 4 is taken, 2026-11-26: the name is `whole_block`, the owner is the property scan through
`entry_coverage.py`, the severity is WARN, and the fact prints in the report only, so the report gains one section that
names the units a run marked and the entries inside them the scan reads as zero change, grouped by the F3.9 rule, and
prints nothing for a run that marked no unit. The pair and the level are data in `src/import_blocks.py`, the field and
the declaration rule are data and rules in `src/unit_manifest.py`, the pair between a place and the fact it names is
rule 4 of `src/container_coverage.py`, the fact name and the pair answer are rule 4 of `src/entry_coverage.py`, and the
pins that read them as data are in `tests/test_import_blocks.py` group 8 and group 9, `tests/test_unit_manifest.py`
group 10, `tests/test_container_coverage.py` group 5, `tests/test_data_file_gate.py`, `tests/test_codebase_state.py`,
`tests/test_property_coverage.py` and `tests/test_reports.py`, with the pair and the declaration shape read through
`tests/conftest.py`. No committed golden byte moved, because `tests/golden` holds no data file.

### Phase 14B, the facts an id needs

- **14B.1** — the device serial fact for a bound unit, complete on main, 2026-11-27, and committed, so this piece's
  record lives in the git history. Decision 6 was taken 2026-11-26, so the piece read the state document as the
  source, and the live-target half stays in `backlog.md`.
- **14B.2** — the rule types: the shape decision in §2 decision 7, then the instance half of
  `import_blocks.IMPORT_ROW_FIELDS` if the shape changes. Blocked on the F3.5 rulebase value and on a source
  that states the position a live rulebase holds, so it stays out of the pieces until both land.
- **14B.3** — the read-through order for a bound unit, which needs decision 8 and the built-in name table.

### Phase 14C, the plan side and permanence

- **14C.2** — the completeness half for a bound unit: one block per entry the run's ledger reads as `emitted`.
  Needs decision 5, which states whether it is the same rule as the round-trip cross-check or a second rule.
- **14C.3** — permanence: `imports.tf` as permanent codebase content or a first-run file, decided on the
  Terraform measurement in fact 10.

## Process debt, the rules with no owner document (the `backlog.md` entry "Permanent rules have no owner document")

- **Piece, the writing rules** — complete on main, 2026-11-25, and committed, so this piece's record lives in the
  git history. The writing rules moved from `agent-status.md` to their owner document `docs/WRITING_RULES.md`,
  named by `docs/README.md` and by the root index, and `agent-status.md` keeps the status and the links.
- **Piece, the five pins read the committed pair through the constants** — complete on main, 2026-11-25, and
  committed, so this piece's record lives in the git history. The five pins that read the merged rows read the pair
  through `CODEBASE_FIXTURE` and `RUN_FIXTURE`, the constants `tests/conftest.py` owns, and each of the three modules
  reads the two names from `conftest`. No test module defines a pair of its own, no test module imports another test
  module, and the rule that `tests/conftest.py` is the one place the path to each set is built did not move. The item
  is closed, so the record is removed from `backlog.md`, and the names the three modules hold for their own facts are
  recorded there as the part that stays open.
- **Piece, the gate and CI rules** — complete on main, 2026-11-27, and committed, so this piece's record lives in the
  git history. The name was taken by the operator on 2026-11-27 as `docs/GATE_AND_CI.md`, and that document now holds
  the gate-size decision, the shared test definitions rule, the Python floor rule, the missing-binary skip rule, and
  the one-owner rule for the tool pins. It is named by `docs/README.md`, so
  `tests/test_layout.py::test_the_indexes_name_every_document_under_them` reads it, and `agent-status.md` keeps the
  status, the links and the recorded measurements. The writing rule that a wording check lives in
  `tools/check_documents.py` is not restated there; the document links to `docs/WRITING_RULES.md` rule 4.
- **Piece, the watch list** — open, and it runs next. Needs one owner document named by `docs/README.md`, holding each
  watched rule with the link to the owner document or module that already states it, and no restatement. The name is
  taken as `docs/WATCHED_RULES.md`, so the piece writes the document under that name.
- Both pieces are documents only, so the pin they can move is
  `tests/test_layout.py::test_the_indexes_name_every_document_under_them`, the pin that holds the index rule. The gate
  and CI piece is complete, so the watch-list piece is the one that can move it.

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
