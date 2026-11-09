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
3. **Finding 1, the unit side.** A fact that is in the run's ledger for a unit, or in the
   join's response row for that unit, but not in both, is reported. The line it names is the
   file that carries the fact, and the file it names is the unit directory. When one side is
   empty the finding says so, in the words the join already uses: 'no response row', or
   'the ledger has the fact and the response row does not'.
4. **Finding 2, the run-wide side.** A scope row for a unit that is not in the response set,
   and a response name that has no scope row, are reported through the join. The rule reports
   the run-wide half in the report block with `file=''`, the same shape `check_terraform`
   uses for the root block. The rule states no row set of its own: the pairs come from
   `unit_findings`, so the cross-response half stays open with F8.9.
5. **The findings sort by the data rule.** The report section orders the findings by file,
   then line, then detail, the order `check_data_files` already pins for a data check. A
   byte rule or an LF rule cannot change that order.
6. **The rule is a WARN, and it does not change the exit code.** A fact that compares two
   sets is a coverage fact, not a broken output, so the block reports WARN. A WARN never
   changes the exit code, which is the rule `docs/ARCHITECTURE.md` §4.6 already states. The
   gate reports FAIL only for a broken output, so a run that reads the same files through
   different paths exits the same way on both paths.
7. **The rule prints nothing in the console summary, and prints one line in the report
   section.** The console shape has one owner, `container_coverage`, and the pins that hold
   it say no other module in `src/` states the prefix or the line shape. The gate reads the
   join, so `sanity_checks` states no console line. This is the decision F8.7 left open in
   `backlog.md` §2, and it closes it: the findings print in the report only.
8. **The rule reports NOT RUN when it has no index.** The gate cannot build an index, because
   no module in `src/` imports `api_requests` yet, so a call without one reports NOT RUN with
   a note, the same shape `check_round_trip` uses for a call without a ledger.
9. **The position.** `request_set` sits after `round_trip` and before `control_chars`. The
   reason is the order `tests/test_round_trip.py` pins: `round_trip` sits immediately after
   the data rule, and `terraform` sits last, so the new rule takes the next position after
   `round_trip`. That pin is migrated, not dropped, and the order has one owner.
10. **The pins run the pipeline in process.** A path 2 pin reads a fact from a real run
    because the acceptance says a fact from a run must come from the run's ledger. So each
    pin calls `run_pipeline`, injects the producer, and passes the join's index built from
    the fixture. A fixture-only pin is allowed only for the pair a real run cannot make, and
    the pin says what it is.
11. **The byte rule and the LF rule between two runs.** Two pins hold them on this path, in
    the style of `tests/test_round_trip.py`: the byte rule says a finding names the bytes
    that carry the fact, and no finding names a byte order the run did not read; the LF rule
    says the report file is LF bytes, and the same run through the other path reports the
    same findings.

## The pins that hold these criteria

In `tests/test_sanity_gate.py`:

- `test_the_gate_checks_the_join_through_the_owners` — criterion 2.
- `test_a_fact_that_the_join_and_the_ledger_do_not_agree_on_prints_in_the_report` —
  criterion 3, both directions.
- `test_the_run_wide_findings_print_through_the_join` — criterion 4.
- `test_the_join_findings_sort_by_the_data_rule` — criterion 5.
- `test_the_join_prints_no_console_line_and_stays_a_warn` — criteria 6 and 7.
- `test_the_rule_reports_not_run_when_the_gate_has_no_index` — criterion 8.
- `test_a_path_2_run_and_a_path_1_run_report_the_same_findings` — criteria 10 and 11,
  the byte rule between two runs, and the LF rule on the report file.
- `test_two_runs_read_the_same_files_and_report_the_same_findings` — criteria 6, 10 and 11,
  the byte rule between two runs on both sides of the join.

The pin list at the top of `tests/test_sanity_gate.py` names the new pins, and the pins that
already exist are migrated where the new rule changes what they see: the pins that check the
order, the set of results on a path 1 run, the kitchen-sink gate report, and the sample
summary line. `tests/test_round_trip.py` keeps the order pins, the exit-code pins, and the
byte-rule pins, and gains the path 2 pins for the rules that already read the files, so the
cross-check is tested as a reader of the files and as a reader of the join together.

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
