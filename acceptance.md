# Acceptance criteria — F6.10.3: the directory write

Feature record: `PLAN.md` Epic 6, `to-do.md` slice 1 of the F6.10 slices. The shape is decided
(`docs/CODEBASE_ASSEMBLY.md` §14, F6.10.1) and the print-site rule runs per unit (F6.10.2), so this slice
is the step that turns the manifest `directory` field into a real directory per unit the manifest names.

Scope: the write path, the gate rules that read the file sets, and the goldens. No new gate rule, no new
CLI argument, no new naming rule, no new reference rule, no new unit rule.

## Decisions

### 1. The write path

1. **One function writes bytes.** `write_path.py` is the only place a run writes a file, so the LF rule is
   enforced once: `open(..., 'w')` writes `os.linesep`, so a run on a Windows desktop writes CRLF and the
   golden byte rule stops holding (`ARCHITECTURE.md` §6). `newline='\n'` forces LF, and the rule is stated
   in `docs/ARCHITECTURE.md` §6, where the project states the byte rule.
2. **Two path builders, one per set.** The unit set is written inside the directory the manifest row
   names; the codebase root set is written at the codebase root. A writer names which builder it uses, so
   no module builds a path for a file it does not own.
3. **A per-unit file names its unit only by its directory.** The write path states no unit inside a file,
   and no unit-set file name names a unit. The path is the only place a file states the unit it belongs
   to, so a gate finding for a per-unit file names the path from the codebase root.

### 2. Which unit a block belongs to

The unit is read through `unit_manifest.facts_of` at the emitter, and the directory name through
`unit_manifest.directory_name`, so the generator states no unit rule and no directory rule. The run's unit
set is `unit_manifest.units(ledger)` — the ledger rule the manifest already states — so a unit the manifest
names gets a directory even when the run writes no `.tf` block inside it.

### 3. The single-unit case

A run that names exactly one unit writes one unit directory: the same rule, one time. There is no flat
shape and no exception path. `tests/golden/single_unit/` is the golden case that shows it, measured from a
real run on a fixture that names one unit.

### 4. The gate

1. The block rules read every `.tf` file below the codebase root through `read_tf_files`, keyed by the path
   from the root, so a finding names the unit directory the file is in. This is unchanged from F6.10.1, and the
   pin changed because the committed goldens now hold unit directories.
2. The data rule stays one rule that reads the four records at the root through `parse_rows`, over the rows
   of every unit. Its printed-form half compares each unit's file against `render_tfvars` for that unit's
   row.
3. The plan check runs on one directory, so it runs once for each unit directory the manifest names. It
   names no file: each finding names the directory it ran on. A missing terraform binary or no provider
   cache is still SKIPPED, so the suite stays offline.

## Acceptance criteria

1. A run writes one directory per unit `unit_manifest.units` names, and the directory holds the unit set:
   the per-type `.tf` files, `provider.tf`, `scope.tf`, `imports.tf`, `actions.tf`, `variables.tf`,
   `read_through.tf`, and the printed form `site.auto.tfvars` of that unit's row. The codebase root holds
   the root set: the four records, the report files, `README.md`, `SOURCE.txt`. Pinned in
   `tests/test_write_path.py` and `tests/test_unit_manifest.py`.
2. Every file names exactly one set, and the LF rule is in the one write function: the scan of the tool's
   modules finds no other writer, and the bytes a run writes hold no `CR`. Pinned in
   `tests/test_write_path.py`.
3. `tests/test_write_path.py::test_no_unit_directory_is_written_yet` is replaced by the pin that names the
   directory the run writes, so the test states what the step does.
4. A gate finding for a per-unit file names the path from the codebase root, and the report counts name the
   two sets: the `.tf` files the reader read (below the root) and the four records at the root. The pinned
   counts for the sample run are re-measured from a real run.
5. The plan check runs once per unit directory and stays offline-skippable; the report names the directory
   it ran on.
6. Both committed golden sets move to the per-unit layout, as paths from the case directory, and the
   single-unit case is added. Every golden is the output of a real run (`python3 panorama_to_terraform.py
   <source> --output-dir <dir>`), never edited by hand. The bytes of one unit's blocks are the bytes the
   same run wrote before, because the per-unit file holds that unit's blocks in the order the run read
   them.
7. A test that reads the `.tf` set reads it as the gate reads it: keyed by the path from the output
   directory. A test that pins one file's content reads the parts that name that file, in path order, so a
   run that names two units is not read as one file.
8. Two runs on the same bytes write the same bytes, including the per-unit layout and the LF rule
   (`ARCHITECTURE.md` §6).
9. The rules that stay: `naming.py` is the one naming rule; `TerraformGenerator.name_ref` is the one
   reference rule; no per-unit file states a path in its bytes; the data rule reads no file inside a unit
   directory; no rule reads a report, `README.md` or `SOURCE.txt`; no flag names the layout; the exit codes
   are unchanged.
10. `docs/CODEBASE_ASSEMBLY.md` §14 states the landed write path, `docs/ARCHITECTURE.md` §6 states the LF
   rule, and no other document restates them. `README.md` states the output shape as the run writes it.
11. `ruff check .` is clean, `python3 -m pytest` is green, and the change is committed with an ASD-STE100
    message that starts `F6.10.3:`.
