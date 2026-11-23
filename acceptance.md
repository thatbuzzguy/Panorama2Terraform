# Acceptance criteria

Two tasks are active on two branches, so this file carries both records (joined manually during
the merge of `input-shapes`, 2026-11-23). Each section names the worktree that owns it.

## Piece 11C.2, the run's report section (main, the current task on main)

Piece 11C.2 of Epic 11, the codebase several runs write into
(`docs/MULTI_RUN_CODEBASE.md`). This is the whole task: Piece 11C.3 (the
write boundary) is not started here.

Owner documents: `docs/MULTI_RUN_CODEBASE.md` §7 (the report section rule)
and §8 (the module owners). Owner modules: `entry_coverage.py` for the report
rule, `unit_manifest.py` for the two sets, `codebase_state.py` for the join
that reads the merged site rows. Pin module: `tests/test_reports.py`.

### Definition of done

1. The section prints after the report sections the report rule already
   orders (header, summary, gaps, property findings, shadows, repeated names,
   reference cycles, state ownership, drift) and follows the same shape the
   other report sections use: the `--- heading ---` line, the rule paragraph,
   then the grouped body.
2. The section names the run's unit set and the codebase's unit set, read
   through `unit_manifest.units`, the one unit rule, so no module states a
   second unit set and no gate rule states a unit rule of its own.
3. A unit is named by its name, the deepest scope the export declares, read
   through `unit_manifest.unit_name` and `unit_manifest.facts_of`; the report
   names no directory and no path.
4. The body is grouped by the F3.9 scope rule
   (`TerraformGenerator._report_scope_path` and `_report_section_header`), so
   no module states a second grouping rule.
5. The section prints only when the codebase set holds a unit the run set
   does not. A run that reads the whole codebase prints no such section, so
   its report bytes are unchanged and no committed golden report moves.
6. Report content only: no console line. The console line shape has one owner,
   `container_coverage.console_line`.
7. The site-record finding #2 is closed: `unit_manifest.units` reads a row set
   through `facts_of`, so a site row (fields `directory`, `variables`, no
   facts) names no unit, and the rule that reads the merged site rows is
   `codebase_state.py`'s join key on `directory` plus the data rule. The report
   states no site row field.

### Pins to write (tests/test_reports.py, plus one in test_codebase_state.py)

- The section prints for a run that does not read the whole codebase, and its
  unit lines name the units through `unit_manifest.units` for the committed
  pair (`tests/fixtures/kitchen_sink.xml` then `tests/fixtures/address_objects.xml`).
- The section does not print for a run that reads the whole codebase, and the
  report bytes of a whole-codebase run are unchanged.
- The section prints after the sections the report rule already orders.
- The section names no directory: no line in it matches a unit directory name.
- The report gains no console line: the section text is not in the console
  output.
- Site-row pin: every merged site row's `directory` is `unit_manifest.directory_name`
  for a unit the merged manifest names, so the site half names the same units
  through the join and adds none.

Pins measure content and names, not document wording. No test module imports
another test module; shared facts come from `tests/conftest.py`
(`CODEBASE_FIXTURE`, `RUN_FIXTURE`, `record_rows`, `partial_run`). No
hand-built rows.

### Gate

`ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`; single-threaded and conservative.

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
