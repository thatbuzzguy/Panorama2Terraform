# Acceptance criteria — piece 1, the test set reads one shared definition

## Scope

`tests/conftest.py` is the one shared helper file and the one place the path to each test set is built
(`docs/ARCHITECTURE.md` §1.1). This piece moves into that file the four definitions the test set holds more
than once, and makes the eight test modules named below read them through it. No functional code of the tool
changes, and no new rule is stated.

The findings are the import rule violation, the second definitions, and the path builder, measured
2026-11-11 and recorded in `backlog.md`.

## The criteria

1. **No test module imports another test module.** The two helpers `tests/test_real_or_report.py` reads from
   `tests/test_policy_order.py` (`_check_chain_semantics` and `_rule_blocks`, line 33) move to `tests/conftest.py`
   and are read from there by both modules. The mechanism that lets a test module import a test module is not
   added back: no `conftest.py` import of a test module, no plugin, no path entry. The rule is stated in
   `docs/ARCHITECTURE.md` §1.1 and `to-do.md` §Rules the layout keeps.
2. **One pattern for the resource line, stated as data with the rule it serves.** `RESOURCE_RE` is defined four
   times today, and the four patterns are not the same. Each pattern shape is measured against the goldens and the
   corpus run output before the decision is taken (see Measurement). A pattern is stated once in `tests/conftest.py`
   when one pattern answers for all four definitions; two named patterns are stated there when a difference is real,
   each with the rule it serves. A pin must not pass because a merged pattern is broader, so the narrower shape is
   not dropped: the block brace stays required by every pattern stated here, and a pattern that cannot serve a
   consumer keeps its own name.
3. **One `TERRAFORM`.** The terraform binary is resolved once, in `tests/conftest.py`, and read from there by
   `tests/test_dependency_wiring.py`, `tests/test_sanity_gate.py`, and `tests/test_terraform_validate.py`. No module
   resolves it a second time, so no module keeps its own skip rule for a missing binary.
4. **One place builds the golden set path.** `tests/test_golden_files.py` reads `GOLDEN_DIR` through
   `tests/conftest.py` instead of building it with `Path(__file__)`. Its header note states where the goldens live:
   inside the unit directory the run wrote, not at the case root (`docs/CODEBASE_ASSEMBLY.md` §14), so the
   regeneration step copies the whole tree. `pyproject.toml` stays the only place a test path is stated
   (`testpaths`, `pythonpath`), and no module builds a second path rule.
5. **The gate stays green.** `ruff check .` is clean, and `python3 -m pytest` passes with no skips. No existing pin
   is weakened, and no pin is changed to read a definition it cannot measure. A pin that measures nothing is a
   failure, so the pins that read these definitions must still read the same material.

## Out of scope

- The pins that pass without measuring anything (`backlog.md`, the empty-set pins, the guarded vacuity, the
  self-referential pin). They are piece 2.
- The import rule has no pin that reads `tests/`, so this piece is a code change, not a pin repair. Adding a scan
  of the test set for cross-test-module imports is not part of this piece.
- The hostile-fixture exclusion, the dict insertion order, the `tests/` index, and the document pin claims, which
  are other pieces of this series.

## Measurement (before, 2026-11-13)

Gate before: `ruff check .` clean, no skips. The pin count is recorded in `agent-status.md`. `terraform` is
present (`/usr/bin/terraform`), Python 3.12.3.

The three pattern shapes the four `RESOURCE_RE` definitions hold, measured against the committed goldens and the
output of a corpus run:

- corpus: 71 fixtures, 69 accepted, 2 refused by the F3.8 read rule (`hostile_billion_laughs.xml`,
  `hostile_xxe.xml`); `hostile_bad_control_char.xml` passes `check_bytes` and the parse refuses it
  (`not well-formed (invalid token)`, line 13), so its run writes no `.tf` file and enters no count.
- goldens: 87 `.tf` files; corpus run output: 584 `.tf` files.
- matches: 414 for each of the three shapes, so the brace requirement answers the same match set on the measured
  material, and 0 resource lines lack the trailing brace.
- the difference is the capture groups: the one-group pattern answers 42 distinct type values, the two-group
  pattern answers 262 distinct (type, local name) pairs, so `findall` returns a different shape and
  `tests/test_dependency_wiring.py::_declared` cannot be served by a one-group pattern.

Decision, from that measurement: `tests/conftest.py` states two named patterns as data, both requiring the block
brace — the block line with the type group, and the same line with the local name captured — each with the rule it
serves. The measurement is recorded in the comment at the patterns.

## Measured results (after, 2026-11-13)

`ruff check .` is clean, and `python3 -m pytest` passes with no skips. The pin set is the same as before, so no
pin was weakened and no pin was changed to read a definition it cannot measure. The pin count is recorded in
`agent-status.md`.

### The time the gate takes

The full suite was run once for the time, and the slow cases were confirmed from the per-pin durations of the same
run. The pin count is not stated here.

- Full run: 325.4 s, 364.6 s and 364.9 s (5 min 25 s to 6 min 05 s). Measured pin time 335.2 s, collection 0.6 s,
  `ruff check .` 0.1 s; the rest is the session fixtures `tests/conftest.py` builds once. The recorded run when the
  test set held 663 pins took 35 s.
- Slowest module: `tests/test_terraform_validate.py`, 121.4 s. Each pin runs `terraform init` and the plan check
  once per unit directory (`docs/ARCHITECTURE.md` §4.6), so the time is the number of unit directories times the
  provider. The `multi_device` and `kitchen_sink` cases hold it.
- Second: `tests/test_sanity_gate.py`, 49.9 s, of which 34.0 s is the three pins that run the gate with the
  terraform binary.
- The corpus pins and the pins that read every fixture: 79.8 s. These are the pins that show the tool reports
  nothing wrong across the 584 `.tf` files a corpus run writes.
- Slowest single pins: 32.3 s (`test_terraform_validate.py`, `multi_device`), 31.1 s (`test_property_coverage.py`,
  the measured reads), 27.1 s (`test_terraform_validate.py`, `kitchen_sink`), 26.7 s (`test_sanity_gate.py`, the
  kitchen sink gate with `--validate`), then the corpus pins between 10 s and 15 s each.
- `tests/conftest.py` reads the provider schema once for the set, 2.2 s.

### Decision on a smaller default gate

No smaller default gate is justified, and none is added. The measured subset that drops the pins that call
`terraform` runs in 203.0 s, which is 44% of the full run; the subset that drops the corpus pins runs in about
285 s. Both save time by dropping the pins that carry the promise, so neither can be the gate a result claim comes
from: the plan check pins prove the emitted blocks are valid Terraform, and the corpus pins prove the tool reports
nothing wrong across the corpus. The full run stays the default gate, and the slower part stays inside it.

A smaller run is allowed only as a working loop on one area, stated as an explicit command-line selection, and it
must be followed by the full run before a result is recorded or the work is committed. It is recorded in this
report and in `docs/ARCHITECTURE.md` §1.1, and not in the tests: the suite states no marks, a skipped pin proves
nothing, and a mark would make the smaller set the thing a developer runs by default.

The smaller gate does not change the result. Every pin in each subset passes, and the full run passes. It changes
only what a run proves, so a claim taken from a partial run is not a result.
