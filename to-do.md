# To Do

The tracking markdown for the completed pieces is removed here; the git history and the owner
documents hold it. The items that need a fact a live target states are in `backlog.md`.

## Epic 11 — the codebase several runs write into

The design record is `docs/MULTI_RUN_CODEBASE.md`; its pins are pending until each piece lands. Acceptance
criteria for the open piece are in `acceptance.md`.

### Phase 11A, the run's read set

- **11A.1 (open)** — the selection vocabulary: the shape a run names as its read set, read through
  `container_coverage.is_scope_path`, and the argument rule for a selection that names no unit in the read set
  (exit 2, the `--path` shape). No module gains a second path rule. A run that reads a whole export declares no
  selection: the whole export is one source, and the run's unit set stays `unit_manifest.units`.
- **11A.2** — the targeted read set: the selected scope plus the membership facts a unit identity cannot state
  on its own, read through `api_requests`; a name the selection excludes is not an index entry, so the join
  reports no finding for it.
- **11A.3** — the byte agreement between a targeted run and a full run for the same unit, for content that names
  no read-through name; the read-through exception stays labelled by the F5.5 rule.

### Phase 11B, the records as codebase state

- **11B.1** — the merge rule in `codebase_state.py`, one join key per record, read through each record module's
  `parse_rows`; a record with no existing file writes the bytes the rules state today, so the committed goldens
  are unchanged.
- **11B.2** — the run's unit set against the codebase's unit set, and the rule that the run writes no directory
  for a unit it read only through the record.
- **11B.3** — ownership, edges and the plan order read over the merged set, so an edge and `after` can name a
  unit another run wrote.
- **11B.4** — the gate for a partial run: the block rules read the whole codebase, the data rule reads the merged
  records, the two two-set rules read the run's unit set, and the plan check and the rule-set check run once per
  directory the run wrote.

### Phase 11C, the update run

- **11C.1** — the existing records as a reference source, read the way the state document is read, and the rule
  that the run names the units it wrote.
- **11C.2** — the run's report section, the sets it names and the rule that it prints only when the codebase
  holds a unit the run did not read.
- **11C.3** — the write boundary: the run writes what it built and deletes nothing; the tool owns every file it
  writes and the byte difference between two runs is read through git.

The move fact, the stale-file boundary, the selection for a `vsys` or a device unit, and the `--prune-cache`
consequence are in `backlog.md`.

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
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the scan
  reports for the other fixtures, so pins that state the printed set name the fixture count. The
  fixture assembler reads the same set by rule: a fixture the F3.8 input rule refuses is skipped,
  and the record is not an input (`tests/test_build_kitchen_sink.py`). A committed API response is
  not corpus material, so it sits in its own set (`tests/responses/`), and the pins that state the
  printed fixture set are not changed by it (`docs/ARCHITECTURE.md` §1.1).
