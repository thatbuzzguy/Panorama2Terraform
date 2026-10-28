# Acceptance Criteria — F6.1 The unit boundary as data (the codebase manifest)

A unit is one declared scope (`docs/CODEBASE_ASSEMBLY.md` §1). F6.1 states the unit as data:
one manifest row per declared scope, with the four scope facts, the directory name, the entry
count, and the names the unit references from outside itself.

The rows come from the ledger `entry_coverage.py` already writes, so F6.1 adds no parse data.
The reference names come from the reference rule (`docs/ARCHITECTURE.md` §4.3), recorded at the
site that applies it. F6.1 writes no directories: it names the directory a later feature writes.

The three open decisions in `to-do.md` are decided here, before the code.

## Decision 1 — the directory naming rule

1. The directory name is `sanitize(unit name) + '_' + 8-hex digest of the unit identity`, in the
   `ARCHITECTURE.md` §5 shape. The sanitizing rule is §5's rule, used through
   `TerraformGenerator.sanitize_name`; no second sanitizing rule exists.
2. The unit identity is the four scope facts in the `container_coverage.SCOPE_FACT_KEYS` order,
   joined by `|`. This is the same identity the state scan keys on (`state_coverage.py`), so the
   parent enters the directory name through the digest, the way a local name carries its context.
3. The digest is always present, not only on a collision. Reason: a collision-only rule makes one
   unit's name depend on the other units in the run, so adding an unrelated scope moves an
   existing directory. The digest makes the name depend on the unit alone, which is the same
   reason §5 puts the digest in a local name, and a codebase directory must not move when a unit
   is regenerated (`docs/CODEBASE_ASSEMBLY.md` §2).
4. The unit name is the deepest declared scope name, in the level order the F3.9 rule states
   (device group, then template, then device). The virtual system is the innermost scope the
   export declares, so it names the unit when the export declares one. `Shared` names the shared
   section (the F3.9 rule already names it `Shared`). `localhost.localdomain` names no device
   (F3.5), so a unit whose deepest level is the placeholder takes the scope above it.
5. Pinned by `tests/test_unit_manifest.py`, which calls the generator's `sanitize_name` and does
   not define a sanitizing rule of its own.

## Decision 2 — the manifest data shape

1. The manifest is data, so a document describes its fields and never restates a row
   (`docs/README.md` rule). Standard library only: the `json` module (`backlog.md`, F5.2).
2. One row per unit, one JSON object, with the fields in this fixed order:

   | Field | Value |
   |---|---|
   | `unit` | the unit name Decision 1 states. The four facts alone do not name the shared section, so the row states the name |
   | `device_group` | the declared device group, `""` when the export declares none |
   | `vsys` | the declared virtual system, `""` when the export declares none |
   | `template` | the declared template, `""` when the export declares none |
   | `vsys_device` | the device that owns the entry, `""` when the export declares none |
   | `directory` | the directory name Decision 1 states |
   | `entry_count` | the number of report rows in the unit (`docs/ARCHITECTURE.md` §3.2) |
   | `references` | the names the unit references from outside itself, as a JSON array, sorted |

3. A fact is read from the ledger row, so it states what the export declares. `Shared` in
   `device_group` is the parse fallback, not a declared device group (F3.9), so it is not a fact
   value; the shared unit is the unit whose four facts are empty.
4. Row order: sorted by the four facts in the `SCOPE_FACT_KEYS` order, which is the identity
   order, so the sort is a total order and does not depend on document order. Fields print in the
   declared order, not alphabetically.
5. Bytes: `json.dumps(rows, indent=2)` with one trailing newline, ASCII output, so two runs on the
   same bytes write the same bytes.
6. The manifest reads back as data: `parse_rows` reads a manifest file, and a row that is not the
   declared shape is a refusal, as `provenance.parse_record` refuses a line that is not a field.

## Decision 3 — one manifest file per codebase

1. One file per run: `CODEBASE_MANIFEST.json` in the output directory, one row per unit.
2. Reasons:
   - a reader cannot find a per-unit file before it knows the directory name, and the directory
     name is the fact the manifest decides;
   - F6.1 writes no directories, so a per-unit file would sit outside the shape it names;
   - the project's record shape is one file that holds one record per thing the run read, and the
     prune rule reads a record file, not one record (`backlog.md`, F5.3 and F5.4);
   - the set of units is a run fact: a per-unit file cannot state the set, and the edge list
     (F6.3) needs the whole set.
3. A plain run writes it. The tool writes data an orchestrator reads
   (`docs/CODEBASE_ASSEMBLY.md` §13), and the unit boundary is a fact of every run, so no CLI flag
   is needed. The file is written only when it has content, following the existing rule; a run
   that read no entries writes no manifest, and an input refusal writes no manifest, like every
   other refusal.
4. The manifest is not a gate check, and no new gate rule is added. It writes no `.tf` byte, so
   the gate rules, the report bytes, and the exit codes are unchanged (input refusal 1, argument
   error 2).

## AC-1 The unit and its rows

1. A unit is one combination of the four scope facts, as `docs/ARCHITECTURE.md` §2.2 states them.
   A unit exists when the ledger has a report row in it, so a declared scope the parse read is a
   unit, and the scope entry itself is one of its rows.
2. `entry_count` counts the ledger report rows of the unit. An entry inside a config-object entry
   is a property level (§3.1), so it is not counted here; the parent row's count covers it.
3. F6.1 names the directory; it does not write one.
4. A declared template stack is not one of the four facts, so the manifest names no stack unit
   today. The limit is recorded in `backlog.md`.

## AC-2 The reference names

1. A reference name is recorded by `TerraformGenerator.name_ref` at the site that applies the
   reference rule, so no second resolution rule exists. The recorded names are the names the rule
   resolved outside the run: a name that stayed a plain string, or a name that became a
   read-through `data` block (F5.5).
2. A name the run declares is not recorded, including a name two devices declare: the F3.6 rule
   keeps it plain because the referrer is ambiguous, not because the name is outside the run. The
   edge list (F6.3) is the feature that names the other unit, so the manifest keeps one fact:
   outside the run.
3. The name is recorded with the referrer's four scope facts, through the F3.9 rule, so
   `Shared` names the shared unit. A name is stored once per unit, and the row prints the names
   sorted.
4. The referrer's facts decide the unit, not the call-site context, because a contextless call
   site (the VPN objects) resolves through the shared chain while the referrer sits in a declared
   scope.
5. Every recorded reference name belongs to a unit the ledger rows show. Pinned on the corpus.

## AC-3 The no-change rule

1. The generated `.tf` files are byte-identical to the committed goldens for both golden cases.
2. The files a run writes are the F5.5 output set plus the manifest file: the four reports,
   `README.md`, `SOURCE.txt`, `SANITY_REPORT.txt`, the `.tf` files, and `CODEBASE_MANIFEST.json`.
   No report file gains a field, a name, or a line that the manifest states.
3. The gate reads `.tf` files only, so a data file in the output directory is not a gate input,
   and `CHECK_ORDER` is unchanged.
4. The exit codes are unchanged: 0 when the gate reports no FAIL finding, 1 for an input refusal,
   2 for an argument error.

## AC-4 Gates and determinism

1. The gates do not change: `ruff check .` clean, `pytest` green, both golden sets
   byte-identical, report and record determinism pinned, every test offline.
2. Two runs with the same arguments on the same bytes write the same manifest bytes: the rows are
   sorted by the identity, and the reference names are sorted.
3. The manifest writes no timestamp and no path, so its bytes depend only on the input.
4. Every test runs offline.
