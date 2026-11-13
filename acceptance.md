# Acceptance criteria — F8.10, the agreement pin (Epic 8, Phase 8C)

## Scope

One pin: `tests/test_api_path.py::test_content_with_no_live_only_fact_writes_the_same_tf_bytes_as_path_1`, in
group 4 of that module. The pin changes no functional code and states no new rule. It measures that, for content
that holds none of the facts in `docs/API_CONVERSION_PATH.md` §4, path 2 writes the same `.tf` bytes as path 1,
and that the two reports agree on every field except the source each row names and the line inside that source.

## The criteria

1. **The content is named by the pin and lives in the test file.** The committed response set stays at three
   files, which `tests/test_api_path.py::test_the_committed_responses_are_not_corpus_material` pins, so no fourth
   committed response is added. The content is `AGREEMENT` (the two place bodies) and `AGREEMENT_EXPORT` (the
   whole-config read of the same content), read through `_agreement_producer`.
2. **The pin states why the content holds no §4 fact, and measures it on the content.** No `rulebase` element, so
   no rule and no rule to order; no `device` element, so no device entry; no `variable` element; no `predefined`
   element. The measurement reads the element names the content holds in both shapes it is read in, so the claim
   is a measurement on the content rather than an assertion in prose.
3. **Both paths run in process, and path 2 reads no network.** Every response path 2 reads comes from an injected
   producer. Every response is read through `source_fetch.fetch`, never as a file, so the wrapper decision, the
   origin, and the line map are the ones the run holds.
4. **The output is read the way the gate reads it.** `conftest.tf_files` reads through
   `sanity_checks.read_tf_files`, keyed by the path from the output directory. The reports are read through the
   ledgers (`path1.ledger.rows()` and `RunView.rows()`), never by parsing report text.
5. **The path 2 rows are read from the view the run itself built, after the emission.** The values a report row
   carries for the captured object are recorded by the emission, so a view built from a separate read of the same
   content answers nothing. The hook is the shape `conftest.run_pipeline` uses for path 1's parser, and it keeps
   the original function so the run is not read twice.
6. **No new rule.** The pin adds no second naming rule, writer, console line, environment name, path rule,
   response-shape rule, and no test path outside `pyproject.toml`. No test reads the tracking markdown.
7. **The gate reads the same file set for both runs and reports nothing for either.** `request_set` is NOT RUN for
   path 1, which holds no index, and PASS for path 2. `terraform` is NOT RUN for both, because this pin does not
   run terraform. Green means no finding for either run.
8. **The gate stays green.** `ruff check .` is clean, and `python3 -m pytest` passes with no skips. No existing
   pin is weakened.

## Out of scope

- The membership list. The content states none, because a membership list makes the entry its own scope: the index
  names it, path 2 reads the entry twice (the membership read and the entry read), writes the same address in two
  blocks with `_2` names, and `request_set` reports a finding. That is a finding for
  `docs/API_CONVERSION_PATH.md` §2.4 and §6, recorded in `backlog.md`.
- The five facts in §4. They stay blocked on a live target.
- The report files. The pin compares rows through the ledgers, not report text, and states no rule that the
  report files agree.

## Measured results (2026-11-13)

Criterion 1 and 2. The content holds two entries: `Office-FW` in `device-group` with the address `10.0.0.7`, and
`HQ-Networks` in `templates` with the address `10.0.0.9`. The element names it holds, measured in both shapes, are
`address`, `config`, `device-group`, `entry`, `ip-netmask`, `panorama`, `response`, `result`, `templates`. None of
the four §4 element names is present.

Criterion 3 and 5. Path 2 read two responses, one per place: `device-group` and `templates`; a request for
`template-stack` answers nothing. The index holds 2 entries, which are the two places. Path 1 read one response,
the whole-config read of the same content. Both runs read through `fetch`, and the responses landed in the cache
directories the runs wrote, not in the committed response set. Path 1's source is not per-scope; path 2's two
parts are.

Criterion 4 and 7. The file set agrees: 10 `.tf` files, byte-for-byte the same, 4 resources, and the gate counts
agree for both runs (10 files, 2 data files, 4 resources). Each report holds 4 rows. The rows agree on every
field, and the keys that differ are `line` and `source` for all four rows. The printed entry line agrees apart
from the position. The path 1 lines are 7, 9, 14, 16; the path 2 lines are 5, 7, 5, 7. The two source sets are
disjoint: path 1 names one response
(`241cbc8980537850768efb4f106eaf6665bbc113a5ecd7c9fbd42449f200d34f.xml`), path 2 names two
(`181d42732d20ea918cb4ea333000da9280a02de1e818ee6d26300cf4b98d759c.xml` and
`de9bdaf007529c7a6ad27da998b86d8643720bbf7d20e704219ef0adb50c0ec0.xml`). The gate reports no finding for either
run. `request_set` is NOT RUN for path 1 and PASS for path 2, and `terraform` is NOT RUN for both.

Criterion 8. Gate before: `ruff check .` clean, 1,650 pins, no skips. Gate after: `ruff check .` clean, 1,651 pins,
no skips. `tests/test_api_path.py` reads 29 pins before and 30 after. The only file the piece changed is
`tests/test_api_path.py`.
