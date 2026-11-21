# The Codebase Across Several Runs (design record)

This is the design record for Epic 11, feature id `F11.x`. Nothing here is built, so every rule below is a
design rule pending a pin. The pins this document names are pins that already hold and that the new rules
must not change. When a piece lands, its pins live in the module that owns its rule, and this document names
the test module that holds them.

The converter runs today as one run over one source and writes one output directory. A codebase that several
runs write into needs three facts stated as data that a single run cannot state: which scopes a run read, which
units the run built, and which units the codebase already holds. This document states the levels the output
sits in, the read-set rule, the merge rule, and the boundary a run may not cross.

## 1. The levels

The output keeps three levels, and one layer that names what a run covers.

1. **The codebase root** — the level that persists across runs. It holds the four records as codebase state
   (§3), the reports as the last run's printed view, `README.md`, and `SOURCE.txt` as the run's own record.
2. **The unit** — one directory, one plan, one state, one declared scope (`CODEBASE_ASSEMBLY.md` §1). The
   level is unchanged. A unit directory is already self-contained: `provider.tf` and `variables.tf` are
   unit-set files, so a plan reads its declarations in its own root, and no unit file needs another unit's
   file. That is what lets a unit written by one run sit beside a unit written by another.
3. **The unit's files** — unchanged (`CODEBASE_ASSEMBLY.md` §14).

The layer a multi-run codebase adds is **the run's read set and write set**: the scopes the run read, and the
units the run built. A run writes files for the units it built, and writes nothing for a unit it read only
through the codebase record (§6).

Three facts already hold, and they are the reason no new naming rule or identity rule is needed:

- The directory name is the §5 shape applied to the unit identity, so it does not move when an unrelated unit
  is added (`tests/test_unit_manifest.py::test_a_directory_name_does_not_move_when_an_unrelated_unit_is_added`).
  A unit written by a later run takes the same directory the first run gave it.
- A local resource name is the §5 shape applied to the source identity, so a targeted run writes the same
  address for the same entry as the run that wrote it first, and an import block stays valid across runs.
- A name another unit owns stays a plain string, because one plan runs against one root and one state
  (`CODEBASE_ASSEMBLY.md` §5 rule 5). So a unit directory needs nothing from another unit directory.

## 2. The run's read set

1. **The selection names the read set, not what the run writes.** A run that reads a whole export cannot
   select: the whole export is one source, and the run's unit set is the units the ledger names
   (`unit_manifest.units`), so a filter that dropped units from that set would give the unit rule two shapes.
   For a file source, targeted conversion is the splitter's one file per device group plus `--parent` for the
   ancestor (`docs/DEVICE_GROUP_SPLITTING.md`).
2. **The selection is a scope path**, read through `container_coverage.is_scope_path`, the one scope path
   definition, so no second path rule appears. It applies to the api source, the way `--path` and `--parent`
   do. A selection that names no unit in the run's read set is an argument error (exit 2), the way `--path` is,
   and it writes no file.
3. **The targeted read set is the selected scope plus the membership facts its unit identity needs.** The
   index states no merge rule and reads no membership of its own, so the run reads the membership container for
   each identity fact a selection cannot state on its own. A name the selection excludes is not an index entry,
   so the join reports no finding for it.
4. **An ancestor the run reads as a reference source names no unit**, the `--parent` rule already pinned
   (`tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency`). The run builds rows for
   its own units and reads the ancestor for the ownership rule.
5. **The run's unit set and the codebase's unit set are two facts, read through two rules.** The run's set is
   `unit_manifest.units`, the set that names the directories the run writes. The codebase's set is the merged
   manifest read through `unit_manifest.parse_rows`. Neither module counts units a second way.
6. **A targeted run writes the same unit bytes as a full run writes for that unit**, for content that names no
   read-through name. With a read-through scope declared, a name the codebase owns and the run did not read
   becomes a `data` block, because the run read no unit that declares it. The run labels itself in the
   generated `README.md`, the F5.5 rule, so the exception is stated and not guessed.

## 3. The four records as codebase state

1. **The root records are state, not run output.** A run that writes into an existing codebase reads each
   record through the module that owns its shape (`parse_rows`), and merges by row identity. A record with no
   existing file is the run's own set, so the first run writes the bytes the rules state today and the committed
   goldens are unchanged.
2. **The merge rule, stated once, in `codebase_state.py`.** The run's rows replace the codebase's rows for the
   units the run built. The rows for the units the run did not build stay as the record states them. The module
   defines no row shape, no reader, no identity key, no naming rule, no writer, no path rule, and no console
   line: it reads each shape through its own module's `parse_rows`, the identity through
   `state_coverage.ownership_key` and `unit_manifest`, and the writer through `write_path.py`.
3. **The merge key is each record's own join key**, so no second key appears: the manifest on `directory`, the
   ownership record on `directory` and (`type`, `entry`), the edge record on `directory`, the site record on
   `directory`. A record the reader cannot read as its declared shape is a refusal, the rule `parse_rows`
   already states.
4. **The order rule runs over the merged set**, because `rank` and `after` are facts about the codebase and not
   about a run. So `rank` can move for a row the run did not build. That is not a name change: the directory
   name is a pure function of the unit identity, so an address in a state document and an import block stay
   stable while the plan order moves.
5. **Determinism reads the existing record as an input.** Two runs on the same inputs — the same sources and the
   same existing records — write the same bytes. A run that merges the same record twice writes the same bytes,
   because the rows sort by identity and the run order does not decide the merge.
6. **The reports and `SOURCE.txt` stay per run.** A run fact cannot be accumulated without a timestamp, which
   the record rule refuses, so the root reports are the last run's printed view and `SOURCE.txt` names the last
   run's sources. The codebase therefore holds no record of which run produced which unit; the operator reads
   that through git. The consequence for `--prune-cache` is recorded in `backlog.md`.
7. **The codebase-level view is the merged records.** No fifth root-set file states the unit set a second time,
   which is the rule `CODEBASE_ASSEMBLY.md` §3 rule 5 and §14 hold. The run's report gains one section, §7.

## 4. Ownership, edges and order across runs

1. **The existing records are a reference source**, read the way the state document is read: the run writes no
   fact it cannot read from a source, and it gains the facts the record holds. The run reads them before it
   builds the ownership rows, so the ownership rule and the order rule run over the merged set. The step is in
   `generate_run`, which states no rule the owners state.
2. **The ownership chain gains one source.** `ownership.parent_map` reads the declared parent source, the
   parent fact the parse captures, and the codebase's existing rows. A targeted run that reads no parent can
   still name the ancestor for a name the codebase already owns, so `kind` answers `definition` or `override`
   through the record instead of naming no owner. No second key and no second grouping rule appear.
3. **The edge set can name a unit the run did not read**, through the join `reference_edges.py` already states
   on `directory` and (`type`, `entry`). So a stack unit built by a targeted run is ranked after the template
   units the codebase holds, and `after` names a unit another run wrote.
4. **A name the run uses whose owner neither the run nor the record names** keeps the plain-name rule and writes
   no edge row, the rule `reference_edges.py` rule 1 already states.
5. **The run states no `kind` for a row it read from the record.** The kind is what the run read for its own
   entries; a row the run did not build keeps the kind the run that wrote it stated. A kind the rule cannot
   decide is still a finding, and a finding still does not change the exit code.
6. **The move fact.** An entry the codebase owns and the run reads with different scope facts is a finding read
   through `state_coverage.ownership_key` and the join on `directory`. The tool states the move, not a rename:
   the identity changes, so the local name and the import id change with it, and a plan against the live config
   shows a destroy and an add. It needs a fixture that shows one entry placed in a different scope than the
   record names, so it stays in `backlog.md`.

## 5. The gate for a partial run

1. **The block rules read the whole codebase.** They read every `.tf` file below the codebase root in sorted
   path order, so they read a unit another run wrote, the same way they read a file a person wrote. A finding
   names the path from the codebase root, which is the unit the file belongs to.
2. **The data rule reads the merged records as the codebase set**, and it can verify a row the run did not
   build, because the naming rule, the joins and the order rule are pure functions of the identity. Its
   printed-form half compares each unit's file inside the directory that row names, including the units the run
   did not write.
3. **The two rules that read two sets read the run's unit set.** `round_trip` reads the block set against
   `unit_manifest.units(ledger)`, which for a partial run names only the run's units, so a unit the run read no
   rows for enters no count. `request_set` reads the join against the run's index, which names only the scopes
   the run read. A call that passes no ledger or no index reports the rule as NOT RUN, unchanged.
4. **The plan check and the rule-set check run once per unit directory the run wrote**, and each result names
   the directory it ran on. For a full run the two sets are the same set, so the pins that hold today are
   unchanged.
5. **No gate rule reads a report, `README.md` or `SOURCE.txt`**, unchanged, so the run's report section adds no
   gate rule and no file.

## 6. What a run writes into an existing codebase

1. **The codebase is the output directory.** `--output-dir` names it, so no module gains a path rule, the write
   path keeps two builders, and no third file set appears.
2. **The run writes what it built and deletes nothing.** A unit the run read only through the record is
   untouched. A unit the run no longer has content for keeps the files an earlier run wrote, because the tool has
   no delete rule; that boundary is recorded in `backlog.md`.
3. **The tool owns every file it writes**, and `terraform.tfvars` stays the operator's own file
   (`CODEBASE_ASSEMBLY.md` §11). The run reports the units it wrote (§7); the byte difference between two runs is
   read through git, because the tool holds no record of what it wrote before, which is the rule `AGENTS.md`
   states for a historical record.

## 7. The run's report section

One section, in `CONVERSION_REPORT.txt`, after the sections the report rule already orders:

- it names the units the run built, and the codebase units the run did not read, grouped by the F3.9 scope rule,
  so no module states a second grouping rule;
- it names a unit by its name, not by its directory, so the report keeps the rule that it names the input name
  and no path;
- it prints only when the codebase holds a unit the run did not read, so a run that built the whole codebase
  writes the report bytes it writes today and the golden reports hold;
- its content is read through `unit_manifest`, so the report names the sets and states no row field the records
  already state.

The console prints no line for it: the console prints one line per finding, and the run's unit set is not a
finding.

## 8. Module ownership

| Rule | Owner module | Test module that holds the pins |
|---|---|---|
| The run's read set, the selection shape, the excluded names | `container_coverage.py` for the path shape, `api_requests.py` for the read set, `panorama_to_terraform.py` (`shared_arguments` and `shared_checks`) for the argument | `tests/test_api_requests.py` |
| The run's unit set, the codebase unit set, the report section shape | `unit_manifest.py` | `tests/test_unit_manifest.py` |
| The merge rule | `codebase_state.py`, named in `docs/ARCHITECTURE.md` §1 when it lands | `tests/test_codebase_state.py` |
| The ownership chain read through the record | `ownership.py` | `tests/test_ownership.py` |
| The cross-run edge and the order over the merged set | `reference_edges.py` | `tests/test_reference_edges.py` |
| The gate for a partial run | `sanity_checks.py` | `tests/test_sanity_gate.py` |
| The write boundary, and the rule that the run deletes nothing | `write_path.py` | `tests/test_write_path.py` |
| The run's report section | `entry_coverage.py` for the report rule, `unit_manifest.py` for the sets | `tests/test_reports.py` |

## 9. What stays blocked

The items that need a fact the tool cannot read offline are in `backlog.md`: the selection for a `vsys` or a
device unit, which needs the fact that names which device the run read; the stale-file boundary; the move fact,
which needs a fixture; and the `--prune-cache` consequence for a codebase that several runs write into.
