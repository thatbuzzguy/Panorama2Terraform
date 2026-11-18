# Acceptance — `tools/quick_start.sh` and the two command checks (Piece 13)

Criteria set 2026-11-18 for the `backlog.md` Nice-to-Haves item: the demonstration script added
`--validate` when the terraform binary is present and added no flag for the `tflint` rule set, so a
run through the script reported the rule-set check as NOT RUN unless the caller named it. This piece
decides what the script does, and records the decision and the measurement.

Owners: `docs/ARCHITECTURE.md` §4.6 owns the gate rule (the flag gate, NOT RUN, SKIPPED, the
severity and the exit code); `docs/USAGE_GUIDE.md` owns how each script runs, so it owns the
script's stated behavior; `tools/README.md` owns the `tools/` index and names the script;
`tests/test_layout.py` holds the index rule, which reads names and not wording;
`tools/check_documents.py` holds the wording checks; `agent-status.md` and `acceptance.md` hold the
measurement. The script keeps its own comment stating what it adds and why, and states no rule of
the tool.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- A pin measures content or a name, never the wording of a document, so a wording check lives in
  `tools/check_documents.py`, which the test set does not read.
- No pin is weakened or removed. If this piece writes no pin, the reason is recorded here.
- No document states a test count; `agent-status.md` and `acceptance.md` hold the measurement.
- Standard library only; everything stays offline and deterministic. The script is a demonstration,
  so it adds no dependency and reads no tool module.
- The repository root stays clean: the script writes `terraform_example/` in the directory it runs
  from, so the demonstration runs outside the repository root.

## Item 1 — the flag the script adds

**Decision.** The script asks for each gate check that runs an external command when that binary is
present: `--validate` when `terraform` is found, `--tflint` when `tflint` is found. This is the
pattern the script already holds, applied to the second command check. The reason: the gate reports
a check the call did not ask for as NOT RUN, so a run through the script on a machine that has the
rule set reports a check it could have run. Adding the flag makes the demonstration report what it
ran, and keeps the script consistent: it asks for both checks or for neither, and it asks for a
check only when the binary is there.

- AC-1.1: both flags are added by the same kind of test the script already uses (`command -v`), and
  neither flag is added when the binary is absent, so the run still completes on a machine with no
  binary.
- AC-1.2: the script states no second rule of the tool. Its comment states what it adds and why, and
  names `docs/ARCHITECTURE.md` §4.6 as the owner of what a run reports. No gate rule, no severity
  rule, and no exit-code rule is restated as the script's own rule.
- AC-1.3: the script adds no rule the tool enforces, so no gate rule, no module, and no golden
  changes, and the pin count is unchanged.

## Item 2 — the Next steps text

**Decision.** The Next steps text states what the run reports for each command check, and what this
run asked for, so the reader can read `SANITY_REPORT.txt` against the run it came from. The print
names the result for a check the script asked for, NOT RUN for a check it did not ask for, and
SKIPPED for a check asked for by name with no binary, and it points at §4.6 for the rule that
decides these.

- AC-2.1: the text keeps the honest-report wording: a check the script did not ask for is named as
  NOT RUN, never as a pass, and a check it asked for with no binary is named as SKIPPED.
- AC-2.2: the print names what this run asked for, so the report matches the run.
- AC-2.3: the text links to the owner documents (`docs/ARCHITECTURE.md` §4.6 for the gate rule,
  `docs/USAGE_GUIDE.md` for the flags) instead of restating them.
- AC-2.4: the text stays readable as a demonstration print: it names the two command checks and what
  each one reports, and states no rule of its own beyond that.

## Item 3 — pins

Measured 2026-11-18: no pin reads the script. `grep -rn quick_start tests/` answers nothing; the
only mentions of the script are document wording, in `README.md`, `docs/README.md`,
`docs/USAGE_GUIDE.md`, `docs/ARCHITECTURE.md` §1.1, `docs/LICENSING.md`, `tools/README.md`, and the
tracking markdown. The pins that read the flags read the entry point, in `tests/test_sanity_gate.py`:
`test_the_tflint_flag_runs_the_check_on_a_conversion`,
`test_the_tflint_check_reports_not_run_when_the_caller_did_not_ask_for_it`,
`test_validate_flag_runs_the_terraform_check`, `test_validate_without_the_binary_is_skipped_not_failed`,
and `test_tflint_without_the_binary_is_skipped_not_failed`.

**Decision: no pin for the script.** A pin measures content, and the only content this piece changes
is the script's own text, so a pin for it would read the wording of a shell script, which is what the
rule puts in `tools/check_documents.py`. A content pin would have to run the script, and its answer
depends on the binaries on the machine: the script's decision is "add the flag when the binary is
present", so a pin that runs the script either depends on the environment or measures the environment
instead of the script. The facts the script would be pinned for — that a run which asks for nothing
reports NOT RUN, that a run which asks for a check with no binary reports SKIPPED, and that a run
which asks for a check with the binary present reports its result per unit directory — are already
pinned on the entry point by the five pins above. The script adds no rule the tool enforces, so there
is nothing new for a pin to measure. What this piece records is the demonstration as a dated
measurement, the way `backlog.md` records the provider facts.

- AC-3.1: no existing pin is weakened, removed, or narrowed.
- AC-3.2: the pin count is recorded before and after, and expected unchanged.

## Item 4 — the documents that state the script's behavior

- AC-4.1: `docs/USAGE_GUIDE.md` §Quick start script is the owner of how the script runs, so it states
  what the script now adds and links to §4.6 for what a run reports.
- AC-4.2: `tools/README.md` names the file and states no flag and no behavior beyond what the script
  is for, so it does not change; the index rule (`tests/test_layout.py`) reads names, so it cannot
  move.
- AC-4.3: `README.md` states the converter's flags and not the script's, so it does not change.
  `docs/ARCHITECTURE.md` §1.1 names the script as a demonstration and §4.6 owns the gate rule, so
  neither changes: the gate rule stays in one place.
- AC-4.4: `docs/LICENSING.md` reads the license split at the commit it names, so the script edit
  cannot move a count there. No license document changes.
- AC-4.5: `tools/check_documents.py` reports no finding after the document edits.

## Item 5 — the demonstration measurement

The script runs offline on the committed sample, so the demonstration is measured on the committed
material with no network, from outside the repository root (`/tmp/opencode/piece13`, so the root
stays clean and `terraform_example/` is written there and not in the tree). Measured 2026-11-18, four
runs of the same script on `examples/sample_panorama_config.xml`, each with exit 0. The sample run
writes 2 unit directories, so a command check that runs reports one result per unit directory.

| Binary found | What the script asks for | The two command checks in `SANITY_REPORT.txt` |
|---|---|---|
| both | `--validate --tflint` | `tflint PASS` per directory, `terraform PASS` per directory |
| neither, through a `PATH` that resolves `python3` and `dirname` only | none | both NOT RUN, each with the note naming its flag |
| terraform only | `--validate` | `tflint NOT RUN`, `terraform PASS` per directory |
| tflint only | `--tflint` | `tflint PASS` per directory, `terraform NOT RUN` |

The run time is 3.29 s with both binaries and 0.26 s with neither, so the demonstration stays a quick
run. No check that did not run is named as a pass, which is AC-2.1. The static checks and the counts
are the same for every run (`14 .tf files, 2 data files, 20 resources`, `request_set NOT RUN` because
path 1 read no request), so the flags change only the two command checks.

## Gate

Run in order, with no parallel runner: `ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`. Conservative threads.

Before, on the committed tree at `35f8023`: 1,697 pins in 52 test modules (`pytest --collect-only -q`,
read as the per-module counts because `pyproject.toml` sets `addopts = "-q"`). The recorded run for
that tree is 273.21 s with tflint 0.66.0 present, in `agent-status.md`. `ruff check .` is clean at
`py310`, `ruff format --check .` is clean on the 100 Python files, and `python3
tools/check_documents.py` reports no finding. The script is not a Python file, so neither ruff gate
reads it, and no pin reads it.

After, measured 2026-11-18 on the tree with this piece's edits, in that order, with tflint 0.66.0
present: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 100 Python files,
1,697 pins in 52 modules, all pass, no skips, 335.42 s, and `python3 tools/check_documents.py`
reports no finding. The count is unchanged, so no pin was added, removed, or weakened (AC-3.1 and
AC-3.2), and the document check was run again after the document edits and reports no finding
(AC-4.5).

One document-review finding was recorded during this piece and stays open in `backlog.md`, with the
measurement: `README.md` §Testing states that each module is named once there, and 24 test modules
are named twice. It is a wording finding, so it lives in the tracking documents and not in a pin.
