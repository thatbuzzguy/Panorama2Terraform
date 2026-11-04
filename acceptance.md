# Decision — the console line shape and the shadow source field — acceptance criteria

This slice closes the open backlog item: the console prints the gap lines only, because a
property finding and a shadow print in `CONVERSION_REPORT.txt` and each names a matrix row. To print
them on the console the line shape must be decided first, so a run does not print a row it has no
room for, and the shadow line must be given its source field with the shape.

## Facts

- The console prints, in order: the parse `Found:` counts, one line per container coverage finding,
  the per-entry summary lines plus one line per gap entry, the gate summary, the next steps. A
  property finding and a shadow print only in `CONVERSION_REPORT.txt`.
- The report line shapes are fixed-width and name the matrix row (F4.3 rule 2, F4.4, F5.4):
  `  line <n>  <object type>/<entry name>  <matrix row>  <fact>`. A console line is one narrow line,
  so it has no room for a column.
- A report row is keyed per entry, and the position it names is the entry's opening line (F4.3,
  `backlog.md`). Captured fields are the keys of the object the parse method built, not the XML tag.
- The provenance record holds eight fields (`provenance.py`, F5.3), and its pruning rule states that
  a printed line protects nothing. A console line cannot carry the record.
- `docs/ARCHITECTURE.md` §3.2 is the owner document for the line shapes, and §3.2 states the shape once
  per report kind.
- Console pins found before deciding (`grep -rn "console" tests/`): `test_container_coverage.py::test_console_lists_the_findings`
  (the container finding line), `test_entry_coverage.py::test_console_reports_the_gaps_and_prints_nothing_extra`
  (the gap line), `test_shadow_coverage.py::test_the_console_prints_no_shadow_line_and_the_exit_code_is_unchanged`,
  `test_state_coverage.py::test_the_console_prints_no_state_line_and_the_exit_code_is_unchanged`,
  `test_ownership.py::test_a_finding_does_not_change_the_exit_code_and_the_console_prints_no_line`,
  `test_reference_edges.py::test_a_cycle_does_not_change_the_exit_code_and_the_console_prints_no_line`,
  `test_sanity_gate.py::test_console_summary_reports_the_result`, `test_data_blocks.py`, `test_data_file_gate.py`,
  `test_write_path.py` (the one writer, so a console test writes no file).

## Decision

**The console line shape**, stated in one place (`container_coverage.console_line`):

```text
  - <scope>  <position>  <identity>  <fact>
```

A console line may name four things, and nothing else:

1. `<scope>` — the F3.9 grouping rule, the scope the report section names. A finding the report does
   not group (the container coverage section, which names its source instead) prints no scope part.
2. `<position>` — one position, the entry's source line, or `position unknown`. The console keys a
   finding on the same line number the report row keys it on, so the console line and the report row
   name the same entry. A console line names one position only, so a fact that needs a second
   position (the parent line, the state resource address) keeps it in the report.
3. `<identity>` — the F4.3 row identity `<object type>/<entry name>`, or the container path for a
   container finding, because a container finding names a container rather than one entry. One identity
   per line: a fact that compares two entries, or two units, has no room.
4. `<fact>` — the finding's fact phrase, in the words its report line already uses, so the console and
   the report cannot disagree. The fact may name captured fields, and they are the parsed-object key
   names, never the XML tag; it may name the entries the fact covers.

A console line may not name a fixed-width matrix-row column, so the matrix row stays in the report.
The source field a console line may name is the minimum actionable part of the record: the source name,
the same report value the report bodies use (F4.2 rule 6). Never the path, and never a record field.
For the shadow line that field is the parent source name: the operator's action is to open the source
that holds the parent entry, and the name identifies it; the path is in `SOURCE.txt` and the parent line
stays in the report.

**Which findings print.** The container coverage finding, the gap entry, the property finding, and the
shadow line. The ownership, state and edge scans keep no console line: their fact names two identities
(an entry and its ancestor, or two units) or a second position, which the shape forbids, so they print
in the report only. A block prints only when it has a finding; a run with no finding in that kind prints
nothing new. Existing console lines are unchanged, except the container finding line, which is
deliberately migrated to the shape order.

**What stays in `CONVERSION_REPORT.txt`.** Every fixed-width report line shape, the matrix row column,
the parent line, the state resource address, and the provenance record. The console change moves no
report bytes, so the goldens do not move.

## Criteria

1. One function states the shape (`container_coverage.console_line(scope, position, identity, fact)`), and
   no other module in `src/` defines a console line or builds the console prefix. A scan module states
   only its fact phrase and its block header, and calls the shape.
2. A test reads `src/` and pins criterion 1, and pins that the scans that keep no console line own no
   console wording (`ownership`, `state_coverage`, `reference_edges`).
3. The shape names no matrix row: the property console line pins a finding by its entry and its fact
   and prints no matrix row name.
4. The fact names captured fields as parsed-object key names, never an XML tag, and the shadow console
   line names the source name only — no path, no record field — while the report line keeps the parent
   line.
5. A run that trips a property finding and a shadow line prints both on the console, one line per
   finding, keyed on the same line number the report row names. A run with no finding in that kind prints
   nothing new.
6. A finding does not change the exit code: the F4.1 gate still decides it, and a WARN still does not
   fail the gate.
7. `CONVERSION_REPORT.txt` bytes are unchanged by the console change, so the report line shapes and the
   goldens stay. The report test pins the unchanged shapes.
8. The new tests call the module functions and compare the run's console with them; they do not restate
   the shape rule as a literal string.
9. `docs/ARCHITECTURE.md` §3.2 states the shape once, names the function that holds it, and stops saying
   the console prints no property or shadow line. `backlog.md` closes the two lines it decides here.
10. `ruff check .` is clean and `python3 -m pytest` passes (baseline 1443 tests).
11. The commit message starts with `Decision:` or `F5.4:` in the `git log` style, uses ASD-STE100, and
   states the shape, the source field, and the migrated console line. The tracking markdown is a second
   commit.

## Result

Met. 1450 tests pass (1443 before) and `ruff check .` is clean.

- The shape is stated in one place, `container_coverage.console_line(scope, position, identity, fact)`,
  and pinned by `tests/test_container_coverage.py::test_the_console_line_shape_is_stated_in_one_place`:
  no other module in `src/` builds the console prefix, `entry_coverage.py` and `shadow_coverage.py` call
  the shape, and the ownership, state and edge scans state no console wording.
- The source field is the parent source name, the minimum actionable part of the record. Pinned by
  `tests/test_shadow_coverage.py::test_the_console_prints_the_shadow_line_and_the_exit_code_is_unchanged`:
  the line names the name, not the path and not a record field, and the report line keeps the parent line.
- The console, before: the container finding line, the summary and gap lines, the gate summary. After: the
  same four finding blocks in the report section order, each printing only when it has a finding. The gap
  line bytes are unchanged, because the existing gap line is already an instance of the shape. The property
  block and the shadow block are new (`Property findings (N):`, `Shadow findings (N):`).
- Two deliberate migrations. The container finding line takes the shape order, so it changed from
  `  - <path> (<position>): <count>` to `  - <position>  <path>  <fact> (<count>)`, and the per-entry
  summary now prints when any finding block has content, not only when there is a gap. The container block
  header moved from `main()` into `container_coverage.console_lines`, so the bytes are unchanged.
- Tests added: `test_container_coverage.py` (the single-shape pin, the doc pin), `test_property_coverage.py`
  (the console block, the parsed-object key name, the no-finding run, the unchanged report bytes),
  `test_shadow_coverage.py` (the console line and its source field, the no-parent run). Each test calls the
  module function and compares the run's console with it.
- No golden changed: the report line shapes are unchanged, so a run writes the same bytes.
