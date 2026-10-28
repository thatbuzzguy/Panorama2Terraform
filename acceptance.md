# Acceptance Criteria — F6.3 The reference between units

Status: complete (2026-10-28). The four decisions below are the acceptance record for this feature, and
every criterion below is pinned by `tests/test_reference_edges.py`.

`docs/CODEBASE_ASSEMBLY.md` §1 rules 4 and 6 state the two facts a codebase needs: a name another unit
defines is a reference, and order between units comes from the references between them. F6.1 names the
unit (`unit_manifest.py`) and F6.2 names the unit that owns each entry (`ownership.py`), so a reference
can now name two units instead of one name. F6.3 turns the recorded reference names into an edge list,
states the acyclic rule, and writes the unit order as data.

F6.3 adds no parse fact. It reads the names `TerraformGenerator.name_ref` records at the sites that
apply the reference rule (`ARCHITECTURE.md` §4.3), the ownership rows `ownership.py` builds, the unit
identity and the directory name `unit_manifest.py` defines, and the F3.9 scope grouping rule. It resolves
no name, writes no `.tf` byte, and writes no directory.

Measurable after the run: the corpus writes seven edge rows in three fixtures. The two fixtures measured
before the code write five (`tests/fixtures/kitchen_sink.xml` three, `tests/fixtures/multi_device_templates.xml`
two), and `tests/fixtures/reference_cycle.xml` writes the two that form the cycle. One cycle finding, no
false positive, no report byte for any other fixture, and both golden `.tf` sets byte-identical.

## Decision 1 — where the edge fact lives

1. **A third data file: `REFERENCE_EDGES.json`, one row per edge.** An edge is a pair fact, so it cannot
   be a manifest field (`unit_manifest.py` rule 4 pins one row per unit) and it cannot be an ownership row
   (`ownership.py` rule 1 pins one row per entry). A per-unit file is still refused, because F6.1 names the
   directory and writes none.
2. **The row holds one edge the data can name.** A row states the referrer unit, the target unit, the
   matrix row, and the entry name. A name that no unit in the run declares writes no edge row, because the
   pair does not exist: that name is already stated in the manifest's `references` field, so no second
   place states a reference name.
3. **Fields, in this fixed order.**

   | Field | Value |
   |---|---|
   | `referrer` | the unit that uses the name, by its directory |
   | `target` | the unit that owns the name, by its directory |
   | `type` | the coverage matrix row that covers the target entry |
   | `entry` | the reference name |

4. **The join.** `referrer` and `target` join to `CODEBASE_MANIFEST.json` on the manifest's `directory`
   field, the F6.2 rule. `type` plus `entry` join to `OWNERSHIP.json`, which is the only place that names
   the declaring entry and its owner. The module defines no naming rule and no identity key: it takes
   `TerraformGenerator.sanitize_name` as an argument, the way `unit_manifest.build_rows` and
   `ownership.build_rows` do, and it reads the unit identity through `unit_manifest.facts_of`.
5. **The target unit is the owner, not the declaring unit** (`ownership.py` rule 5). A name several units
   declare inside one inheritance chain has one owner, so it gives one edge row. A name that several units
   declare as separate objects gives one row per owner, which is the ambiguous-device case already recorded
   in `backlog.md` (`ARCHITECTURE.md` §4.3 rule 1).
6. **Self-reference exclusion.** A row whose target is the referrer writes no row. An edge is a fact
   between two units, and a unit cannot come before itself.
7. **Row order and bytes.** Fields print in the declared order, not alphabetically. Rows sort by the four
   fields in field order, which is a total order a reader can reproduce from the file. One row per pair, so
   no row repeats. No field states a timestamp or a path, so two runs on the same bytes write the same
   bytes. `parse_rows` reads a written file back as data and refuses a row that is not the declared shape:
   an undeclared field, a missing field, a value that is not a name, or a row that names fewer than two
   units. This is the same rule `unit_manifest.parse_rows` and `provenance.parse_record` hold.
8. **A plain run writes it.** The tool writes data an orchestrator reads
   (`docs/CODEBASE_ASSEMBLY.md` §13), so no CLI flag is needed, and the file is written only when it has
   content, following the rule for the report files and the two data files. The file is not a gate input:
   the gate reads `.tf` files only (`ARCHITECTURE.md` §4.5), so `CHECK_ORDER` is unchanged.

## Decision 2 — the mechanism that resolves a name another unit owns

1. **The data block is the codebase rule for a name outside the run.** F5.5 chose it
   (`ARCHITECTURE.md` §4.7), it is the only mechanism built today, and the gate rule `data_blocks` already
   reads it. A run that declares no read-through scope keeps the plain string, so a plain run writes the
   same `.tf` bytes as before.
2. **The choice for a name inside the run stays open.** A `data` block cannot resolve such a name, because
   the target unit declares the entry in its own root: one plan runs against one state
   (`docs/CODEBASE_ASSEMBLY.md` §1 rule 3). The mechanism must be that unit's outputs, through a remote
   state data source or a platform output, and the generator writes no outputs. So F6.3 states the edge and
   the order, and the outputs rule stays in `backlog.md`.
3. **The reference fact stays one fact.** `name_ref` records one fact: the name resolved outside the run.
   It is not split into "outside the run" and "ambiguous inside the run", because the edge record states the
   other unit when the ownership rule can name one, and the two cases are told apart by whether an edge row
   exists for the name. No second vocabulary appears, so no second resolution rule appears.
4. **Names the rule resolved inside the run are not edges.** They are references inside one root, which is
   what the generator emits today. The split of those names across unit directories is the write path and
   the import block decision (`backlog.md`), so F6.3 does not read them.

## Decision 3 — the cycle rule and where it prints

1. **The edge graph must be acyclic** (`docs/CODEBASE_ASSEMBLY.md` §6 rule needed). Two units that
   reference each other cannot be put in a plan order, so a cycle is a finding.
2. **A cycle is an operator action, not a broken output.** It prints in `CONVERSION_REPORT.txt` in its own
   section, after the repeated-names section and before the state sections, grouped by the F3.9 scope rule
   the way the other finding sections print. The console prints no cycle line, and it does not change the
   exit code, which the F4.1 gate decides.
3. **The section prints only when it has a finding.** One line per cycle, reported once. A cycle is read
   from its smallest unit in the identity order, so the same edge set produces the same lines. The line
   shape is fixed: `cycle`, the units in walk order, the names on each hop, the reason.
4. **A self-reference cannot be a finding**, because rule 1 of Decision 1 excludes the row, so the smallest
   possible cycle is two units.
5. **A unit in a cycle cannot be ranked**, so its order row states `rank` as 0 (Decision 4), and the cycle
   section names it.
6. **New report bytes**: the new section is the only report change, and only for a fixture with a cycle.
   `tests/fixtures/reference_cycle.xml` is the fixture that pins it: two edges, one finding, no false
   positive across the corpus.

## Decision 4 — the unit order as data

1. **The order lives on the manifest row**, as two added fields, because the manifest is the place that
   names each unit (`unit_manifest.py` rule 4). A fourth data file that lists directories would be a second
   place that states the unit set, which `tests/test_unit_manifest.py::test_the_manifest_is_one_file_for_the_codebase`
   pins. This is a shape change to the manifest row: the eight F6.1 fields keep their declared order, and
   `rank` and `after` are added at the end.

   | Field | Value |
   |---|---|
   | `rank` | the position in the plan order, from 1. `0` for a unit in a cycle, which cannot be ordered |
   | `after` | the units this unit must be planned after, by their directory, sorted |

2. **Three rules produce `after`** (`docs/CODEBASE_ASSEMBLY.md` §6), read through the module that holds each
   fact, so no second rule appears:
   - **the ancestor before the child**: the owner unit before the unit that carries an `override` of a name
     it owns (`ownership.py` rule 4);
   - **the shallower scope before the deeper scope inside it**: the scope object before the config inside it
     (§6 rule 2). F6.5 writes no scope object, so this rule orders the units, not blocks: the device group
     unit before the template unit inside it, before the device unit inside it, in the F3.9 level order.
     A container that the manifest does not name adds no dependency;
   - **the reference edge**: the target unit before the referrer unit.
3. **Self-references are excluded twice, by the same rule**: an edge whose target is the referrer writes no
   row (Decision 1 rule 6), so `after` never names the unit itself.
4. **Ties and determinism.** A unit with no dependency is ranked in the identity order, which is the order
   the manifest rows already print, so `rank` is deterministic and does not depend on document order. Two
   runs on the same bytes write the same bytes. `after` is sorted.
5. **A declared parent source names no manifest unit** (a unit exists when the run's ledger has a row in
   it), so the order graph reads only units the manifest names. An edge row can name a parent-source
   directory, and the order row states nothing about it.
6. **The tool can emit the order; it cannot enforce it** (§13). The platform plans in the order the data
   states.

## AC-1 The edge row and the join

1. One row per edge, one row per pair, no repeated row. Across the corpus the edge set is the five rows
   Decision 1 measures, plus the two rows the new fixture adds: seven rows. Pinned as a measured set.
2. `referrer` equals the referrer unit's directory in the manifest, and `target` equals an ownership row's
   `owner` field, so both join to `CODEBASE_MANIFEST.json` on `directory` and the pair joins to
   `OWNERSHIP.json` on (`type`, `entry`).
3. A name no unit in the run declares writes no edge row, and the name is still stated in the manifest's
   `references` field.
4. `parse_rows` reads a written file back as the rows it wrote, in field order, and refuses a row that is
   not the declared shape, including a row that names one unit instead of two.

## AC-2 The reference fact stays one fact

1. The edge set comes from the names `name_ref` recorded at the sites that applied the rule. The module
   resolves no name and records no name, so no second resolution rule exists.
2. Self-reference exclusion, pinned on a name a unit declares and references: no row.
3. A target that is an owner gives one row for the group; a name several units own gives one row per owner.
4. The `.tf` goldens are byte-identical: F6.3 writes no `.tf` byte.

## AC-3 The acyclic rule

1. `tests/fixtures/reference_cycle.xml` produces two edges and one cycle finding, in the new report section,
   in the fixed position, grouped by the F3.9 rule.
2. No false positive: the corpus produces no cycle finding.
3. The section prints only when it has a finding; a cycle does not change the exit code, and the console
   prints no cycle line.
4. A unit in a cycle states `rank` as 0, and every other unit keeps a rank that respects its dependencies.

## AC-4 The unit order

1. Parent before child: pinned on `ownership_override.xml`, where an override entry's unit comes after the
   unit that owns the name.
2. Scope before config: pinned on `multi_device_templates.xml`, where a device unit inside a template comes
   after the device group unit that declares it, in the F3.9 level order.
3. Edges: pinned on `kitchen_sink.xml`, where the target unit comes before the referrer unit.
4. `after` never names the unit itself; a unit with no dependency states `after` as an empty list.
5. Ties follow the identity order, so `rank` is a total order for an acyclic graph.
6. `parse_rows` validates the two added fields (`rank` as a count, `after` as a list of directories).

## AC-5 The report section, the console, and the exit code

1. The new section prints after the repeated-names section and before the state sections, grouped by the
   F3.9 rule, and only when it has a finding.
2. No report names the data file or restates a row, and no report line prints a field name.
3. The console prints no cycle line. The exit codes are unchanged: 0 when the gate reports no FAIL finding,
   1 for an input refusal, 2 for an argument error. A refusal writes no edge file.

## AC-6 Gates and determinism

1. The gates do not change: `ruff check .` clean, `pytest` green, both golden `.tf` sets byte-identical,
   report and record determinism pinned, every test offline.
2. Two runs with the same arguments on the same bytes write the same bytes, for the edge file and for the
   manifest.
3. The gate reads `.tf` files only, so `CHECK_ORDER` is unchanged and no data file is a gate input.
   `tests/test_unit_manifest.py::test_the_manifest_is_one_file_for_the_codebase` asserts the data file set,
   so that assertion names three data files with this feature.
4. A run that writes no edge and no order writes no edge file, following the content rule; the manifest is
   written when it has rows, as before.
5. Every test runs offline, and the CLI takes no flag for the edge file, so `--help` is unchanged.