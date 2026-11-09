# Acceptance criteria — F8.8, the request-set rule in the gate (Phase 8C, path 2)

## Scope

The rule F8.8 states: the request set must agree with the scope the run read.
The join already reports the two directions as data rows, in
`api_requests.unit_findings`. This piece puts a rule in front of those rows, so the
gate decides them, and it lands the path 2 pins for the rules that already read the
files. It belongs to Phase 8C, whose pieces F8.3 and F8.7 landed the other two rules.

F8.8 covers:

- One gate rule in `src/sanity_checks.py`, named `request_set`, that reads the join
  through the owners and reports the findings as a report section.
- The two findings it can make, one for each direction, pinned on both paths.
- The path 2 pins for the rules that already read the files, so the join is tested as
  a join, not as a fixture: each pin runs the pipeline in process with an injected
  producer, and the coverage fact it states is read from the run's ledger.
- The byte rule between the two runs, and the LF rule, in the style of the pins that
  already carry them.
- `docs/API_CONVERSION_PATH.md` §3 states the rule in the present tense and names the
  pins that hold it.

F8.8 does not cover the row set for a cross-response join, which `backlog.md` §2 keeps
open as F8.9: the join reads one response name per fact row, so the facts read from a
fixture and the facts the run recorded are not the same kind of set yet. The rule
decides only what the join can already state. The path 2 read order, which `backlog.md`
§1 keeps open as F8.6, is also F8.9's, and F8.2 keeps the vsys and device-fact scope
facts open.

## The rule, in one sentence

The gate rule checks the request set against the scope set. A unit's facts must match
the request the run made for that unit, and the request set must match the scope rows.

## The criteria

1. **The rule is one owner.** Only `src/sanity_checks.py` decides what the gate does with
   the join's findings: it calls `api_requests.unit_findings(index, ledger)` and turns the
   pairs it gets back into `Finding` objects. It states no merge rule and no membership
   rule, because the join owns both. No other module in `src/` reads the join.
2. **Reads go through the owners.** The rule names a unit and its directory only through
   `unit_manifest.unit_name`, `unit_manifest.directory_name` and `unit_manifest.units`,
   reads the scope side only through `ownership.SOURCE_FIELD` and `api_requests`, and reads
   the cache name only through `source_fetch.cache_name`. It names no table row by hand,
   copies no row from `Corpus`, and does not reach into a private name. `api_requests` stays
   a join: `test_api_path.py` still pins that it names no check, no report section, no
   render, and no name that an owner owns.
3. **Finding 1, the unit side.** A fact that the join and the ledger do not agree on for a
   unit is reported. The file it names is the unit directory, read through
   `unit_manifest.directory_name` and `naming.sanitize`. As measured, the criterion cannot
   name a file position: the fact compares two sets, so `line` is 0 for every join finding,
   which is the shape `check_data_files` already states for a fact about a file as a whole.
   The words are the join's, so the rule states them once.
4. **Finding 2, the run-wide side.** An index entry the run read no rows for names no unit,
   so the fact cannot name a unit directory. It reports with `file=''`, which
   `Finding.render` prints as the root shape `(run)`, the shape `check_terraform` already
   uses for a root fact. The rule states no row set of its own: the pairs come from
   `unit_findings`, so the cross-response half stays open with F8.9.
5. **The findings sort by the data rule.** The report section orders the findings by file,
   then line, then detail, the order `check_data_files` already pins for a data check. A
   byte rule or an LF rule cannot change that order. Measured, the gate order and the join's
   own order differ: the join answers its unit side first in the order `unit_manifest.units`
   states, then the entries in index order, and the gate puts the run-wide facts first.
6. **The rule is a WARN, and it does not change the exit code.** A fact that compares two
   sets is a coverage fact, not a broken output, so the block reports WARN. A WARN never
   changes the exit code, which is the rule `docs/ARCHITECTURE.md` §4.6 already states. The
   gate reports FAIL only for a broken output, so a run that reads the same files through
   different paths exits the same way on both paths.
7. **The rule prints no console line of its own, and prints one line per finding in the
   report section.** The console shape has one owner, `container_coverage`, and the pins that
   hold it say no other module in `src/` states the prefix or the line shape. The gate reads
   the join, so `sanity_checks` states no console line. Measured, the second half cannot hold
   as written: the gate's own `console_summary` prints every finding it reads, so a join
   finding prints there too, in the shape every finding uses. The pin states the shape
   instead: the join prints nothing, and the gate prints the findings it reads.
8. **The rule reports NOT RUN when it has no index.** `run_checks` cannot build an index,
   because the index is the run order's set, so a call that is missing the index or the ledger
   reports NOT RUN with a note, the same shape `check_round_trip` uses for a call without a
   ledger. `main()` still passes no index, because the path 2 entry point (F8.9) is what will
   pass the index it builds.
9. **The position.** `request_set` sits after `round_trip` and before `control_chars`. The
   reason is the order `tests/test_round_trip.py` pins: `round_trip` sits immediately after
   the data rule, and `terraform` sits last, so the new rule takes the next position after
   `round_trip`. That pin is migrated, not dropped, and the order has one owner.
10. **The pins run the pipeline in process.** A path 2 pin reads a fact from a real run
    because a fact from a run must come from the run's ledger, and `run_script` loses the
    ledger with the process. So each pin calls `run_pipeline`, injects the producer, and
    passes the index built from the response the run read. Path 1 cannot produce a join
    finding, because it reads no request, so every join pin is a path 2 pin. Measured, the
    "same findings on both paths" half is: the same bytes read through both paths write the
    same files and the same rule results for every rule that reads the files, `request_set`
    excepted, and both paths exit the same way.
11. **The byte rule and the LF rule between two runs.** Two pins hold them on this path, in
    the style of `tests/test_round_trip.py`: two runs on the same content write the same
    files and report the same findings, and the report file is LF bytes through `write_path`.
    Measured, a finding names no byte order of its own: the byte rule is the rule that two
    runs on the same bytes write the same bytes.

## The pins that hold these criteria

In `tests/test_sanity_gate.py`:

- `test_the_gate_checks_the_join_through_the_owners` — criteria 1 and 2.
- `test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report` —
  criterion 3, as measured, and the report section.
- `test_the_run_wide_findings_print_through_the_join` — criterion 4.
- `test_the_join_findings_sort_by_the_data_rule` — criterion 5.
- `test_the_join_prints_no_console_line_and_stays_a_warn` — criteria 6 and 7, as measured.
- `test_the_rule_reports_not_run_when_the_gate_has_no_index` — criteria 8 and 12.
- `test_two_runs_read_the_same_files_and_report_the_same_findings` — criteria 10 and 11.
- `test_a_path_2_run_and_a_path_1_run_report_the_same_findings` — criteria 10 and 11, as
  measured, and the exit code on both paths.

In `tests/test_round_trip.py`:

- `test_the_cross_check_reads_the_join_ledger_on_a_path_2_run` — the path 2 run, where the
  cross-check compares the block set with the join's own rows through the same ledger and
  names the same unit.

The pins that already exist are migrated where the new rule changes what they see: the order
pin in `tests/test_data_file_gate.py`, and the pin in `tests/test_sanity_gate.py` that reads
the set of results on a path 1 run, which now reads `request_set` as NOT RUN. The shared path
2 run and the injected producer live in `tests/conftest.py`, because both files read the same
run.

## Result

Measured on the committed response set (the whole-config export, the only committed response),
against a baseline of 1629 pins:

- The run reads 7 join rows: 3 on the unit side and 4 on the entry side, so every pair is a
  fact that does not agree.
- Every join finding is WARN, the report section reports `WARN (7)`, the exit code is 0 on both
  paths, and `report.failed` is False.
- `line` is 0 for every join finding; the unit side names the unit directory, and the entry side
  names no file and prints as `(run)`.
- The gate order puts the 4 run-wide findings first, then the 3 unit findings sorted by the data
  rule's key; the join's own order is units first, then entries.
- The cross-check reports nothing on that run, because the join's rows and the block set agree.
  Planting one `panos_address` block for the unit the join names gives exactly one cross-check
  finding, and both rules name the same unit.
- Two path 2 runs on the same content write the same files, and the report bytes are identical
  and LF only.

## Checks

- `python3 -m pytest` passes with no skips. The baseline count is 1629, and the new count is
  recorded in `agent-status.md` when the piece lands.
- `ruff check .` reports no finding.
- The tool imports only the standard library, and the tests run offline with injected
  producers.
- One owner document per rule, no document restates a table row by row, and no document states
  a test count.

## Commit

- `acceptance.md` is overwritten with this page and committed as its own commit, in the style
  of the F8.7 acceptance commit.
- The piece's commit message records the sub-feature history in ASD-STE100: the rule, the two
  directions, the position, the severity and exit-code decision, the console-line decision,
  the new pins, and the documents updated.
