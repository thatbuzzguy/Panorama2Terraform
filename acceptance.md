# Acceptance criteria — F6.10.1: the shape of the write path (the decision)

Feature record: `PLAN.md` Epic 6, `to-do.md` slice 1. This is a decision, not the write path. It names
the two file sets, the default shape, and how the gate reads each set; it writes no directory, so no
output byte changes and no golden changes. The step that writes one directory per unit stays open, and
the print-site rule it applies is already decided (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5, F6.9).

Scope: the shape only. The unit, the directory name, the join key and the one-file-per-codebase rule are
already decided (`docs/CODEBASE_ASSEMBLY.md` §3 rule 3 and rule 5); this slice states which file belongs
to which set, and which set each new file shape belongs to. No new gate rule, no new CLI argument.

## Decisions

### 1. The two file sets

The write path writes one directory per unit the manifest names, and the codebase root.

1. **The unit set** is the files one plan reads, so one directory holds them: the `.tf` files for that
   unit (the resource files, `provider.tf`, `scope.tf`, `imports.tf`, `actions.tf`, `variables.tf`,
   `read_through.tf`), plus the printed form of that unit's site row. `provider.tf` and `variables.tf`
   are per unit, because a unit is one plan and one root (§1 rule 3), so a declaration must have its
   consumer in the same directory (`check_variables` reads both directions).
2. **The codebase root set** is the files that describe the whole codebase, one per run: the four
   records, the five report files, `README.md`, `SOURCE.txt`. The records stay at the root, because the
   edge record needs the whole unit set and a reader cannot find a per-unit file before it knows the
   directory name (§3 rule 5). A report is read by no gate rule, so it cannot be a per-unit file a rule
   would have to read per unit; and one run reads one source, so `SOURCE.txt` is one record file.
3. **The sets are distinct.** No file shape is in both: the block set is the `.tf` files, the data set is
   the four records, and the printed form of the site record is compared and not counted. No `.tf` file
   belongs to the data set, and no record belongs to the block set.
4. **A per-unit file names its unit by the directory it is written in** — the name
   `unit_manifest.directory_name` states. A per-unit file carries no unit name inside it, because the
   unit set is stated once, in the manifest row, and `directory` is the join key. So the gate names a
   per-unit finding by the path from the codebase root, which is the unit the file belongs to.

### 2. Default output, not an opt-in

The write path is default output, with no flag. §8 rule 1 forces it: the committed goldens pin what a
default run emits, so a shape a run writes only when a flag is on cannot be pinned. `name_ref` is the one
place that decides the shape of a reference field (§5 rule 5), so a flag that changed the layout would
give the reference rule two shapes: one for a run that opted in and one for a run that did not. The gate
would also need two readers for the block set. The F5.5 and F6.4 precedent is an opt-in for a block
shape that labels itself, not for the output layout, so it does not apply here.

Consequence: the goldens change. Both committed golden sets move to the per-unit layout, so the golden
pin reads the `.tf` files as paths from the case directory; that reading is pinned now, and the goldens
regenerate with the step that writes the directories, in the same change as the LF byte rule.

### 3. How the gate reads the two sets

1. The block rules read every `.tf` file the run wrote — the unit set — through the one block reader, in
   sorted path order, and a finding names the path from the codebase root. One reader serves today's flat
   run and the split run, so the gate holds no second rule for the layout: for a flat run the path is the
   file name, so the bytes a report names are unchanged.
2. The data rule keeps reading the four records through `parse_rows` at the codebase root, as one rule
   over every unit's rows, so no per-unit record and no second shape rule appears. The rule reads no `.tf`
   file, and it reads no file inside a unit directory.
3. `site.auto.tfvars` is the printed form of the unit's site row: the data rule compares it through
   `render_tfvars` and does not count it, and no block rule reads it. When the split lands, the row's
   `directory` names where the printed form sits.
4. The two counts the report and the console name — the `.tf` files and the data files — name the two
   sets. A new file shape must name which set it belongs to, and the counts change with it.

## Acceptance criteria

1. `docs/CODEBASE_ASSEMBLY.md` §14 states the decided shape in the same style as the rest of the record:
   the unit set, the codebase root set, the default shape and its consequence for the goldens, the gate
   reading, and how a per-unit file names its unit. §14 names the tests that hold what can be pinned, and
   §1 links to §14 instead of splitting the file list.
2. `tests/test_write_path.py` pins the decision without changing a byte:
   - the two sets are distinct, and each shape names the set it belongs to;
   - the block reader reads a `.tf` file inside a unit directory, and a finding names the path from the
     codebase root; for a run that writes no unit directory the path is the file name, so the report bytes
     are unchanged;
   - the data rule reads the records at the codebase root only, so a record inside a unit directory is not
     read, and the rule is one rule over every unit's rows, not one rule per unit;
   - the codebase root and a unit directory hold the declared file sets for the corpus, measured through
     the run, with no file in both sets;
   - no `.tf` file or printed form names a unit directory inside itself, so the path is the only place a
     per-unit file names its unit;
   - no CLI flag names the write path or a unit directory, so the shape is default output;
   - no gate rule reads a file outside the two sets.
3. `tests/test_golden_files.py` reads the golden `.tf` set as paths from the case directory, so the pin
   holds for a golden set that holds unit directories. The committed goldens are byte-identical: no byte
   changes in this slice.
4. `sanity_checks.read_tf_files` reads the block set as the decision states it: every `.tf` file below the
   codebase root, keyed by the path from the root. The existing gate pins, the report counts, the report
   bytes and the exit codes are unchanged for the corpus.
5. `ruff check .` is clean, `pytest` is green, and the change is committed. The goldens, the reports, the
   gate rule set, the report counts and the file sets the corpus run writes are unchanged.
