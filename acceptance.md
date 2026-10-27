# Acceptance Criteria — F4.4 Property-level coverage (current task)

Scope: the coverage matrix moves from type level to property level. Each row names the
properties its emitter reads. A property the parse captured but no output reads is a gap,
and the conversion report prints that gap. The two report lines that state the property
scan as if it already exist change in this pass, with the two BGP and OSPF report defects.

The record of the previous task (F5.1) is in the git history.

Out of scope for this task:

- The entry-mark rule and the section rule are unchanged. `container_coverage` still
  reports only the section level; a property level stays inside a config-object entry.
- The cross-source shadow report (F5.4) and the ownership drift report (F5.6). Both need
  this feature, neither is part of it.
- `.tf` output bytes. A property gap is reported, not emitted, so both golden sets stay
  byte-identical.

## AC-1 — Each matrix row names its properties

1. Every row in `resource_mapping.COVERAGE_MATRIX` gains `emitter` and `properties`, so a
   row holds eight fields: `resource`, `xml_element`, `xml_name`, `emitted_name`,
   `fixture`, `output_file`, `emitter`, `properties`.
2. `emitter` names the generator method that writes the row's output, and `properties`
   lists the entry keys that output reads for this container. A key that names the object
   or places it (`name`, the four scope facts) is not a property, so `properties` uses the
   same key set as `entry_coverage.NON_FIELD_KEYS` excludes.
3. `emitter` may name two methods when the row has two output paths: the `.tf` emitter and
   the report writer that prints the row when the entry takes the other path. The row for
   `panos_address` is the case: `generate_address_objects` writes the resource, and
   `generate_manual_setup_report` prints a report-only entry.
4. `tests/test_coverage_matrix.py` pins the row shape: every row has the eight fields,
   `emitter` names a method on `TerraformGenerator`, and `properties` is not empty.

## AC-2 — Parity between a row and what the output reads

1. The pipeline records, for each entry object, the property keys an output reads from it.
   The record starts after the parse, so a key the parse method read off the XML element is
   not a property the output used.
2. For every matrix row, `properties` equals the recorded key set for the corpus entries of
   that container. A key the output reads that the row does not name fails the test, and a
   property the row names that no output reads fails it too.
3. Every property a row names appears as a key read in one of its `emitter` methods,
   checked on the source (the same style as the entry-mark rule in
   `tests/test_entry_coverage.py`).

## AC-3 — The property scan and its report section

1. A captured property that is not in the row's `properties` is a finding. The scan runs on
   the entries a matrix row covers, in report order, and `CONVERSION_REPORT.txt` prints one
   line per finding with the scope path, the object type, the entry name, and the properties
   the parse captured but no output read.
2. Scan scope is the entries a matrix row covers. An entry in a report, inventory,
   bookkeeping, count-only, or nested-block destination has no matrix row, so the scan does
   not report it; those field gaps stay in `backlog.md`. A property entry inside a
   config-object entry is in scope when its container maps to a matrix row.
3. A finding is an operator action, not a broken output: the exit code is still decided by
   the F4.1 gate, and no `.tf` byte changes.
4. Report order is fixed (source line, then object type, then entry name), so the same input
   produces the same bytes.
5. The committed corpus has findings. `tests/test_property_coverage.py` pins them by name,
   so a new finding cannot appear without a test change. The properties recorded for the
   corpus are the ones AC-2 pins.

## AC-4 — The two report lines that name the property scan

1. `entry_coverage.summary_lines` no longer prints `(F4.4 covers each one)`. It states the
   scan: the property entries counted, and the findings the scan reported.
2. `container_coverage.render_section` no longer prints `Field-level coverage is F4.3`. It
   names the property scan as the section that owns a property level.
3. Both lines state what the code does now, and no other report wording changes.

## AC-5 — BGP and OSPF report defects, in the same pass

1. `parse_bgp` and `parse_ospf` read one path each. `.//network/virtual-router/entry/protocol/...`
   already matches a router under a device, so the second pattern is dropped, and the §3.4
   one-path rule holds for this pair. A router under a device is read once and printed once.
2. Each BGP and OSPF record carries the four scope facts and the router name, so the manual
   report groups those two sections with the F3.9 rule and names the router. Same rule, one
   implementation: `TerraformGenerator._report_scope_path`.
3. BGP `redist-rules` are printed. The capture exists, so the report prints the rule name and
   the address family; the decision closes the backlog item that said "print them, or stop
   capturing them".
4. BGP peer-group `export-nexthop` and `import-nexthop` are printed in the peer group line,
   so a captured property has an output.

## AC-6 — Gate

1. `ruff check .` clean, `pytest` green.
2. Both golden sets byte-identical.
3. Report output is deterministic for the same input (the report determinism tests still
   pass), and the committed example report is unchanged except for the sections AC-3 and
   AC-4 add.
4. Exit codes unchanged: a run with property findings still exits 0, and the F4.1 gate still
   decides the exit code.

## Documents to update

`docs/COVERAGE_MATRIX.md` (row schema and the property level), `docs/ARCHITECTURE.md` §2.4
and §3.1 and §3.4, `README.md`, `backlog.md` (the closed items), `to-do.md`,
`agent-status.md`.
