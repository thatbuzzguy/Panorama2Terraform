# Acceptance Criteria — F6.2 Ownership as data

Status: complete and committed (`44496dd`). The criteria below are the record of what F6.2 accepted.

`docs/CODEBASE_ASSEMBLY.md` §1 rule 2 states the fact a codebase needs: one unit owns each entry.
F5.4 (`shadow_coverage.py`) reports the case where a child entry repeats a parent entry name, but it
reports a naming collision, not an owner. F6.2 turns that fact into data and decides the owner rule
for a repeated name. The rules are in `ownership.py`, and `main()` writes the file.

F6.2 adds no parse fact. It reads the row set `entry_coverage.py` already builds, the repeated-name
key `shadow_coverage.py` already uses, the unit identity `unit_manifest.py` already defines, and the
identity key `state_coverage.py` already keys on. F6.2 writes no directory: it names the unit F6.1
names.

The four open decisions in `to-do.md` are decided here, before the code.

## Decision 1 — where the ownership fact lives

1. A second data file: `OWNERSHIP.json` in the output directory, one row per entry the coverage
   matrix covers.
2. Reasons:
   - ownership is a per-entry fact. `unit_manifest.py` rule 4 pins one row per unit, so a per-entry
     fact cannot be a manifest field without breaking that pin;
   - a per-unit file cannot exist yet: F6.1 names the directory and writes none, so a per-unit file
     would sit outside the shape it names;
   - the project's data shape is one file that holds one record per thing the run read
     (`SOURCE.txt`, `CODEBASE_MANIFEST.json`), and the set of entries is a run fact;
   - the row set is the F4.4 scan scope, read through the report row, so the same rule that names a
     matrix row names an ownership row.
3. A plain run writes it. The tool writes data an orchestrator reads
   (`docs/CODEBASE_ASSEMBLY.md` §13), so no CLI flag is needed. The file is written only when it has
   content, following the existing rule; an input refusal writes no file.
4. A row names a unit by its directory, through `unit_manifest.directory_name`, so `OWNERSHIP.json`
   and `CODEBASE_MANIFEST.json` join on the manifest's `directory` field. The module defines no
   second naming rule: it takes `TerraformGenerator.sanitize_name` as an argument, the way
   `unit_manifest.build_rows` does.
5. The file is not a gate input: the gate reads `.tf` files only (`ARCHITECTURE.md` §4.5), so a data
   file cannot change a gate result or a golden byte.

## Decision 2 — the owner of a repeated name

1. **Rule 1, unchanged** (`docs/CODEBASE_ASSEMBLY.md` §4 rule 1): an entry the export declares
   inside a unit belongs to that unit. The row states the declaring unit, and the entry identity is
   the matrix row, the entry name, and the four scope facts — `state_coverage.ownership_key`, read
   through `unit_manifest.facts_of`, so no second identity key appears.
2. **A name a unit uses but does not declare is not owned by that unit.** A member list, a reference
   string, and a reference pointer (`<entry>` with only `<id>`) hold a name without declaring an
   object, so they write no ownership row. The reference rule (`ARCHITECTURE.md` §4.3) stays the only
   place that names a use.
3. **Two entries are one object only when the export can place them in one inheritance chain.** The
   chain is the shared unit (the four facts empty) and the units whose declared fact is a device
   group. A name in a template, a virtual system, or a device is a different object in each unit
   (`ARCHITECTURE.md` §2.1), so each unit owns its own entry.
4. **The owner is the ancestor entry** — the entry in the unit the other unit inherits from, as §1
   rule 2 states it. The export states the relation in two cases only: the shared unit, and the
   parent source the run declares with `--parent` (the F5.4 rule). The device-group `parent` field is
   not captured (the bookkeeping gap in `backlog.md`), so the rule cannot name an ancestor for two
   device groups in one source.
5. **`disable_override` does not choose the owner.** Verified against provider 2.0.14
   (`terraform providers schema -json`) and the provider docs: the flag is cleared by default, so a
   descendant may override; when it is set, the entry in its own location is the definition and no
   descendant device group may override it. So the flag names the entry that cannot be overridden.
   A descendant entry that carries the same name while its definition names the flag cannot be an
   override, so the export contradicts itself: that is an operator action.
6. **What the rule can say, per entry** (`kind`):
   - `declared` — one entry declares the name, or the units cannot sit in one chain, so this entry's
     unit owns it;
   - `definition` — this entry owns the name for a group that sits in one chain;
   - `override` — this entry repeats a name another entry owns, so the codebase resolves it as a
     reference to `owner`;
   - `ambiguous` — the rule names no owner for this entry.
7. **The ambiguous case is a report finding**, one line per entry, in `CONVERSION_REPORT.txt`, after
   the shadow section and before the state sections. The section prints only when it has a finding,
   and a finding is an operator action, so it does not change the exit code (the F4.1 gate still
   decides it). The console prints no ownership line, following the rule for the property and shadow
   findings. A finding is printed for:
   - an entry whose group sits in one chain but whose relation the export does not state;
   - an entry whose group names `disable_override` on an entry that cannot be the ancestor;
   - an `override` entry whose definition names `disable_override`, so the override cannot exist.
8. **Intended change to `CONVERSION_REPORT.txt`**: the new section. The report bytes for a fixture
   with a finding change; every other report byte is unchanged. Measured on the corpus, three fixtures
   have a finding group, giving seven groups and twelve finding lines
   (`tests/fixtures/edge_dup_names_across_dgs.xml`, `tests/fixtures/ownership_override.xml`,
   `tests/fixtures/report_grouping.xml`), and no fixture has a false positive. The `.tf` goldens, the
   gate inputs, and the exit codes are unchanged.

## Decision 3 — the service `disable-override` leg

1. Extract it in `parse_service_objects` and emit it in `generate_service_objects`. `panos_service`
   declares `disable_override` in the pinned schema, and `tests/test_coverage_matrix.py` requires a
   declared property to be a key the emitter reads, so the `panos_service` row gains the property at
   the same time the emitter reads it.
2. Report-only is not accepted. The F4.4 rule says a field the parse captures is either printed or
   reported as unread. A report-only choice would leave the ownership rule reading a field the tool
   admits it drops, and the corpus test would then have to pin a new finding for every service entry
   that carries the flag. Emitting keeps one rule: a captured field is an emitted field.
3. The emitted line is the same shape `panos_address` writes: `disable_override = "yes"`, the string,
   not a bool (verified 2.0.14). The field prints after `description`, the order the address emitter
   uses.
4. The goldens do not change: no committed fixture holds a service entry with `disable-override`, so
   the line appears only for a run that reads one. `tests/fixtures/ownership_override.xml` is the new
   fixture that pins the extraction and the emitted line. It produces no property finding, because the
   emitter reads the field it captures, and it is the fixture that supplies the measured
   `panos_service` `disable_override` read
   (`tests/test_property_coverage.py::test_measured_reads_equal_the_declared_properties`).
5. The pinned provider schema declares `disable_override` for 25 resource types. The coverage matrix
   names the property for two rows: `panos_address` (extracted since F3.4) and `panos_service`, which
   this feature adds. For a row that does not name the property the rule states `unknown`, so the row
   does not claim a value the parse did not read. The extraction gap for the parsed types that can
   carry the flag stays in `backlog.md`: `panos_address_group`, `panos_administrative_tag`,
   `panos_application_group`, `panos_custom_url_category`, `panos_external_dynamic_list`,
   `panos_security_profile_group`, `panos_service_group`.

## Decision 4 — the row shape, the order, and determinism

1. The row is data, so a document describes its fields and never restates a row (`docs/README.md`
   rule). Standard library only: the `json` module (`backlog.md`, F5.2).
2. One row per entry in the scan scope, with the fields in this fixed order:

   | Field | Value |
   |---|---|
   | `type` | the coverage matrix row that covers the entry, or `""` for its name. The matrix row is the key the property scan and the shadow scan use |
   | `entry` | the entry name |
   | `source` | the source the entry sits in, by its report value (F4.2 rule 6), never the path |
   | `device_group` | the declared device group, `""` when the export declares none |
   | `vsys` | the declared virtual system, `""` when the export declares none |
   | `template` | the declared template, `""` when the export declares none |
   | `vsys_device` | the device that owns the entry, `""` when the export declares none |
   | `directory` | the declaring unit's directory name (`unit_manifest.directory_name`) |
   | `owner` | the owning unit's directory name, `""` when the rule names no owner |
   | `kind` | one of `declared`, `definition`, `override`, `ambiguous` |
   | `override` | `yes`, `no`, or `unknown`: the flag as the parse read it. `no` is the default when the entry carries no value; `unknown` when the matrix row does not declare the property |

3. The four fact fields are `unit_manifest.FACT_KEYS`, so the row joins to the manifest row and no
   second fact order appears.
4. Row order: sorted by the identity key `state_coverage.ownership_key(type, entry, facts)`, then by
   `source`, because two sources can state the same identity. The sort is a total order and does not
   depend on document order. Fields print in the declared order, not alphabetically.
5. Bytes: `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, no timestamp and no
   path, so two runs on the same bytes write the same bytes.
6. `parse_rows` reads a written file back as data, and refuses a row that is not the declared shape:
   an undeclared field, a missing field, a value that is not a name, a `kind` outside the declared
   set, or an `override` outside the declared set. This is the same rule `unit_manifest.parse_rows` and
   `provenance.parse_record` hold.

## AC-1 The row scope

1. A row is a report row that a matrix row covers, and whose destination writes an object
   (`emitted`). An entry inside a config-object entry is a property level (§3.1), so it writes no row;
   the parent row's count covers it.
2. A skipped entry (no name, or a reference pointer that carries only `<id>`) and a report-only entry
   write no row: the export did not declare an object there.
3. A name a unit uses but does not declare writes no row (Decision 2 rule 2). Pinned on a member list
   and on a reference pointer.
4. The scan reads a captured value through `entry_coverage.RecordingDict.value`, so the ownership scan
   is not an output read and cannot move a property finding (the F5.6 rule, reused).

## AC-2 The declaring unit and the join

1. Every row's four facts equal the unit the export declares the entry in, read through
   `unit_manifest.facts_of`, and every row's `directory` equals that unit's directory in the manifest.
2. Pinned across the fixture corpus: every ownership row belongs to a manifest unit.
3. For a sole entry, `kind` is `declared` and `owner` equals `directory`.

## AC-3 The owner rule

1. `edge_dup_names_across_dgs.xml`: two device groups declare `web`. The export states no relation
   between them, so each row is `ambiguous` and `owner` is `""`.
2. A name in two virtual systems, two templates, or two devices is two objects: each row is `declared`
   and `owner` equals `directory`. Pinned on `kitchen_sink.xml` and `multi_device_templates.xml`.
3. A shared entry and a device-group entry with the same name: the shared entry is `definition` and
   its unit owns the name; the device-group entry is `override`. Pinned on the new fixture.
4. A declared parent source is the ancestor, so the parent entry is `definition` and the run entry is
   `override`. Pinned with the two-source fixtures `scope_parent.xml` and `scope_child.xml`, read with
   the same row rule as the shadow scan.
5. The flag on the ancestor entry keeps the ancestor as the owner, and the repeated descendant entry
   is a finding. The flag on a descendant entry names no owner for the name, so the group is
   `ambiguous`.
6. `override` is `no` for an entry whose row declares the property and carries no value, and `unknown`
   for a row that does not declare it.
7. No false positive on the corpus: the seven groups in three fixtures named by Decision 2 rule 8 are
   the whole set. Pinned as a measured set.

## AC-4 The service leg

1. `parse_service_objects` captures `disable_override` for a service entry.
2. `generate_service_objects` emits `disable_override = "yes"` for it, as a string.
3. The `panos_service` coverage matrix row declares `disable_override`, and the emitter reads it.
4. The committed goldens are byte-identical. The new fixture's emitted line is pinned by the test, not
   by a golden.

## AC-5 The report finding

1. The section prints only when it has a finding, after the shadow section and before the state
   sections, grouped by the F3.9 scope rule, the way the other finding sections print.
2. The line shape is fixed: line, object type, entry name, matrix row, the reason. The section names a
   source by its report value, never by its path.
3. A finding does not change the exit code, and the console prints no ownership line.
4. The report bytes for the fixtures with a finding change as Decision 2 rule 7 states. No other
   report body, field, or line changes, and no report names the data file.

## AC-6 Gates and determinism

1. The gates do not change: `ruff check .` clean, `pytest` green, both golden `.tf` sets
   byte-identical, report and record determinism pinned, every test offline.
2. Two runs with the same arguments on the same bytes write the same bytes.
3. The exit codes are unchanged: 0 when the gate reports no FAIL finding, 1 for an input refusal,
   2 for an argument error. A refusal writes no ownership file.
4. The file set a run writes gains one data file: `OWNERSHIP.json`. The gate reads `.tf` files only,
   so `CHECK_ORDER` is unchanged. `tests/test_unit_manifest.py::test_the_manifest_is_one_file_for_the_codebase`
   asserts the file set, so that assertion changes with this feature: it names both data files instead
   of one.
5. Every test runs offline.
