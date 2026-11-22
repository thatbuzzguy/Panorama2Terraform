# Acceptance — criteria for Piece 11B.3 (2026-11-22)

Piece 11B.3: ownership, edges and the plan order read over the merged record set, so an edge row and an `after`
fact can name a unit another run wrote (`docs/MULTI_RUN_CODEBASE.md` §4 rules 3, 4 and 5). Baseline `f3f2b78`.
Offline, committed fixtures only, no network.

## Criteria

1. **The measurement is taken first, through the record modules.** For a pair of committed fixtures — the first
   run as the codebase, the second as the second run — every record is read back through its own `parse_rows` and
   merged through `codebase_state.merge_rows`. Per record, the measurement records whether a row names a unit the
   second run built, a unit the first run built, or only its own units. The order rule is recorded for the same
   pair both ways: the run's own row set, and the merged row set. Nothing is decided before the measurement.
2. **Single-owner constraints.** `codebase_state.py` is the only merge rule and the only join key (`JOIN_KEYS`,
   `merge_rows`); `unit_manifest.units` is the only unit rule; `reference_edges.py` defines no reader of the
   membership tables and no fact order of its own, and takes the row sets as arguments; `LEVEL_KEYS` and the
   membership basis (`docs/TEMPLATE_STACK_DEPLOYMENT.md` §2) gain no second basis; the acyclic rule and its report
   section stay single; `ownership.py`'s decision, its seven emitters, and the `disable_override` rule do not
   change.
3. **Out of scope.** `sanity_checks.py`, the exit-code behaviour, the two two-set rules, and the plan check
   (Piece 11B.4). Phase 11C is out of scope. Committed goldens stay unchanged unless the measurement shows the rule
   genuinely changes them; any moved golden is regenerated from a real run in the same commit.
4. **One pin per stated fact**, in the module that owns the rule: `tests/test_reference_edges.py`,
   `tests/test_ownership.py`, `tests/test_unit_manifest.py`, `tests/test_codebase_state.py`. Every pin is grounded
   on committed runs read through `parse_rows` and `tests/conftest.py`, never on a hand-built row. No test module
   imports another test module; a fact more than one test module reads is stated once in `tests/conftest.py`.
5. **No second rule of any kind:** no second naming rule, console line, writer, environment name, path rule, join
   key, membership basis, or order rule. The `src/` scans must read every module unchanged.
6. **The gate runs single-threaded**: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`. Counts are read from the per-module collection counts.
7. **A fact that cannot be stated from committed material is recorded as a condition in `backlog.md`** and the
   piece is reported open for that fact.

## Measured (2026-11-22)

Taken through the record modules themselves, on committed fixtures, single-threaded.

- `tests/fixtures/kitchen_sink.xml` as the codebase, `tests/fixtures/address_objects.xml` as the second run: the
  manifest 11 rows against 1 give 11, ownership 61 against 5 give 62, edges 9 against 0 give 9, site 3 against 0
  give 3. The second run writes no edge row and no site row, so those two merged sets are the codebase's own rows.
- Corpus pair scan, 59 accepted-fixture pairs: 178 merged ownership keys are stated by both runs, and no pair gives
  a merged ownership row whose `owner` names a unit only the other run built, so the owner rule has nothing to pin
  across two runs. 59 pairs where the merged ownership set names an edge the second run's own rows cannot.
- Pin pair `tests/fixtures/address_groups.xml` (codebase) + `tests/fixtures/security_rules.xml` (second run):
  manifest 1 against 2 give 3, ownership 2 against 3 give 5. Over the run's own rows the edge set is empty; over
  the merged rows it names `('production_dg_6ce3cc69', 'shared_45ca31c3', 'panos_address_group', 'Web-Servers')`, a
  pair whose target is a unit the second run did not build. Over the run's own rows the order ranks those units 1
  and 2 with an empty `after`; over the merged rows `shared_45ca31c3` ranks 1, `shared_a6577c11` ranks 2 with
  `after` naming `shared_45ca31c3`, and `production_dg_6ce3cc69` ranks 3 with `after` naming `shared_45ca31c3`. The
  cross-run `after` entry comes from the edge basis: the level basis alone names no dependency for that pair.
- Cycle pair `tests/fixtures/reference_cycle.xml` (codebase) + `tests/fixtures/address_objects.xml` (second run):
  manifest 2 against 1 give 3, ownership 4 against 5 give 9, edges 2 against 0 give 2, site 2 against 0 give 2. The
  acyclic rule reads the merged set and reports the cycle, grouped by the merged manifest row of the unit the cycle
  is read from, a unit the second run did not build; both cycle units keep `NO_RANK` over the merged set, and the
  second run's own unit ranks 1. No accepted pair gives a cycle whose two halves come from two runs: 0 across the
  59 pairs.
- Membership basis: only `template-stack/entry/templates` joins outside the container that names it, and the
  committed corpus holds exactly 3 such facts (`kitchen_sink.xml` Branch-Stack to FW-Template,
  `multi_device_templates.xml` Branch-Stack to HQ-Networks, `scope_objects.xml` Edge-Stack to Edge-Networks). Every
  fixture declares the membership name itself, so no committed pair can state a membership row whose two sides come
  from two runs. Recorded as a condition in `backlog.md`.
- `ownership.py`'s decision and its findings half read the report fields (`chain`, `from_parent`, `reason`, `line`,
  `container`), which `parse_rows` refuses, so they read only the rows a run decided and cannot be read over a
  merged set. Recorded as a condition in `backlog.md`.

## Decision

The modules already take the row sets as arguments, so reading a merged set through them states no new rule. The
only change in `src/` is the wording of the rules that say "the run" for a rule that answers for the rows it is
given. The pins state the measured behaviour. `codebase_state.py` and `unit_manifest.py` are unchanged.

## Pins added

Six pins, one per stated fact, in the module that owns the rule, each grounded on a committed run read through
`parse_rows` and `tests/conftest.py` and none building a row by hand:

- `tests/test_reference_edges.py::test_an_edge_row_can_name_a_unit_the_run_did_not_build` — the join between two row
  sets, read on the pin pair.
- `tests/test_reference_edges.py::test_the_order_rule_reads_the_merged_set` — `rank` and `after` over the merged rows,
  with the cross-run `after` entry read through the edge basis and the level basis named on its own.
- `tests/test_reference_edges.py::test_the_acyclic_rule_reads_a_finding_from_a_unit_the_run_did_not_build` — the walk
  reads the edge rows it is given, and the finding is grouped through the manifest row of a unit the second run did
  not build.
- `tests/test_reference_edges.py::test_the_edge_rule_and_the_order_rule_read_the_row_sets_they_are_given` — the
  single-owner constraint: `codebase_state.py` holds `JOIN_KEYS`, `join_key` and `merge_rows`, `unit_manifest.units`
  is the only unit rule, `LEVEL_KEYS` is the only level basis, and `reference_edges.py` takes the row sets as
  arguments and calls no rule an owner states.
- `tests/test_ownership.py::test_the_owner_rule_reads_the_group_the_merged_set_can_state` — the group the merged set
  can hold from both runs, read through the join key with no second grouping rule.
- `tests/test_ownership.py::test_a_merged_row_keeps_the_kind_the_run_that_wrote_it_stated` — rule 5, read through
  `parse_rows` and the record's own order rule.

No pin was needed in `tests/test_unit_manifest.py`, and no pin moved in `tests/test_codebase_state.py`: the unit rule
and the join key are unchanged, and the read-back the three modules read moved to `tests/conftest.py` as the fact
more than one test module reads (`record_rows`, `run_records` and `JOIN_RECORDS`, read through
`sanity_checks.DATA_FILES` and `codebase_state.JOIN_KEYS`), so `tests/test_codebase_state.py` reads it from there with
its pin assertions unchanged. No test module imports another test module.

## Gate (measured 2026-11-22, single-threaded)

`ruff check .` clean at `py310`, `ruff format --check .` clean on the 108 files it reads (81 Python files,
27 markdown files), `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,778 pins
with the same 4 `tflint` skips — 1,782 pins in 54 test modules, 6 more than the 1,772 pins Piece 11B.2 measured, in
352.23 s. Read through the per-module collection counts: `tests/test_reference_edges.py` collects 43 (39 before, the
4 new pins), `tests/test_ownership.py` collects 42 (40 before, the 2 new pins), `tests/test_unit_manifest.py` 41 and
`tests/test_codebase_state.py` 10, both unchanged. `terraform` is present, so the pins that read the live provider
schema ran, and the 4 skips are the `tflint` pins in `tests/test_sanity_gate.py`. `src/` holds 24 modules, which is
the count `docs/LICENSING.md` states. No committed golden changed.

The piece is open for the three facts it could not state from committed material, recorded as conditions in
`backlog.md`: the membership row whose two sides come from two runs, the cycle whose two halves come from two runs,
and the ownership findings and ancestor half, which reads facts `parse_rows` does not read back.
