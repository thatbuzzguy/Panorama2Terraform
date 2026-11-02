# Acceptance criteria — F6.9: the outputs rule for a name another unit owns

Feature record: `PLAN.md` Epic 6. The piece taken from `to-do.md` is the decision the reference edge
rule (`docs/CODEBASE_ASSEMBLY.md` §5 rule 5) left open: the mechanism that resolves a name another
unit in the run owns. This is a decision, not a module. It writes no byte, changes no gate rule, and
adds no file, so no golden changes. The write path that splits the output per unit directory stays
open and is no longer gated by an open decision.

Scope: the mechanism only. The pair is already data on the edge row, the order rule is already the
plan order the data states, and the `data` block stays the rule for a name outside the codebase
(F5.5). This feature decides what the write path prints for a name inside the codebase that belongs
to another unit.

## Decisions

### 1. The mechanism is the plain name the reference rule already returns

`name_ref` is the one place that decides the shape of a reference field. For a codebase run, the rule
resolves inside one unit: a name the unit declares stays a `.name` reference, and a name another unit
declares is outside that unit, so the rule returns the plain name string. The provider reads the name
as the value, and Panorama resolves an object name through its own inheritance at commit time (the
F5.5 fact), so the plain name is correct output. The single-unit case is the flat run today, so a
plain run writes the same bytes as before, and the goldens are unchanged.

### 2. Order carries existence

The tool cannot enforce order (§13), but the order rule already ranks the owner unit before the
referrer unit through the edge, so the platform plans the owner first and the object exists when the
referrer applies. No plan-time read of another unit's state is needed, so no remote-state data source
appears. The `references` gate rule needs no change, because no `.name` reference crosses a unit
boundary.

### 3. No outputs block and no remote-state data source

The tool writes no `outputs` block and reads no remote-state data source, because the state backend is
out of scope, a module is a standard a person writes, and the tool's part is the data a module
consumes. The `data` block stays the mechanism for a name the run cannot attribute to a unit in the
codebase (`ARCHITECTURE.md` §4.7). The pair reaches the write path only as data, through the edge
record, so no second rule decides which name crosses a unit.

### 4. The consequence for the write path

When the write path splits the output per unit, `name_ref` runs per unit, so the names that the flat
chain resolves across scopes in today's single flat run become plain names. The recorded set is the
pair set, so the edge record and the manifest `references` field grow to name every cross-unit use,
and the corpus pin lists change with that step. The decision names the rule; the positive half prints
bytes only when that step lands, so today the negative half is pinned.

## Acceptance criteria

1. `docs/CODEBASE_ASSEMBLY.md` §5 rule 5 states the decision and names the test that holds it; §14
   step 4 no longer names the rule as open.
2. `reference_edges.py` rule 6 states the same rule and links the decision, so the module docstring
   and the design record agree, and no module defines an outputs writer or reads remote state.
3. `tests/test_reference_edges.py` pins the negative half:
   `test_the_mechanism_defines_no_writer_and_no_reader`. The positive half is
   held by the existing pins: the plain-name rule in `tests/test_data_blocks.py` and
   `tests/test_robustness.py`, the pair in `tests/test_reference_edges.py`, and the order in the
   order group of the same file.
4. The open item leaves `backlog.md`; `to-do.md` keeps the write path as the open step with the print
   site it must apply, `PLAN.md` records the landed decision, and `agent-status.md` states the fact
   and the pin-list consequence named in decision 4.
5. `ruff check .` is clean, `pytest` is green, and the change is committed. No byte changes: the
   goldens, the reports, the gate, and the file sets are unchanged.

## Results

1. Met. `docs/CODEBASE_ASSEMBLY.md` §5 rule 5 states the decision and names the pin; §14 step 4 states
   the rule as decided, so the write path has no open decision.
2. Met. `reference_edges.py` rule 6 states the same rule and names the pin. The scan reads the tool's own
   modules, so the citation cites the group and the test name rather than the mechanism words: a source
   that names a forbidden word cannot be scanned. No module defines an outputs writer or reads remote
   state.
3. Met. `tests/test_reference_edges.py` group 7 pins the negative half through
   `test_the_mechanism_defines_no_writer_and_no_reader`: the scan of the tool's modules, the gate's block
   kinds, the corpus run file set, and the block reader for an `output` block. The positive half is the
   existing pins, unchanged.
4. Met. The open item left `backlog.md`; `to-do.md` keeps the write path as the open step with the print
   site it applies; `PLAN.md` records the landed rule; `agent-status.md` states the fact and the pin-list
   consequence.
5. Met. `ruff check .` is clean and `pytest` is green: 1245 tests, one more than before, and the added
   test is the pin. No byte changed: the goldens, the reports, the gate rule set, the report counts and
   the file sets are unchanged. Committed as F6.9.
