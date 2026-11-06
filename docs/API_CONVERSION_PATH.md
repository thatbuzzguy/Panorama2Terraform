# The API-only conversion path (Epic 8)

The design record for the second conversion path. It states what that path reads, what it may
decide, and what it must not state twice. No rule here is enforced yet, so each rule names the
module and the test that will hold it. When a piece lands, this document states the rule in the
present tense and names the pin.

Path 1 reads one declared source: a file, or the whole-config API export
(`docs/ARCHITECTURE.md` §3). Path 2 reads only responses, and it reads one response per scope
instead of one response for the whole config. It is parallel: it shares the tables, the naming
rule, the write path, and the gate with path 1, and it shares no input producer.

## 1. The two paths

| Part | Path 1 (export) | Path 2 (api) |
|---|---|---|
| Input | one declared source: a file, or one whole-config response | the request set: one response per scope |
| Scope set | the scopes the source holds | the scopes the membership responses name |
| Report position | the source line | the line inside the response the request made |
| Parse methods | the same methods | the same methods, run once per response |
| Tables | `resource_mapping.py`, `container_coverage.py` | the same tables |
| Naming rule | `naming.py` | the same rule |
| Write path | `write_path.py` | the same single writer |
| Gate | `sanity_checks.py` | the same rules, plus the response join |

Rule 1: path 2 states no second version of any part of that table. The pins that read the `src/`
set read path 2's modules with the other modules, so a second naming rule, a second writer, or a
second console line in path 2 fails CI. The pins are `tests/test_write_path.py`,
`tests/test_variables.py`, `tests/test_container_coverage.py`, and
`tests/test_site_data.py::test_the_module_defines_no_second_naming_rule`.

Rule 2: path 2 changes no path 1 rule. A table row that path 2 needs must be a row both paths
read, so the coverage matrix, the container table, and the entry ledger stay one set.

## 2. The request set

**2.1 The accepted request shapes.** Path 2 accepts three shapes, and one response shape per
request shape (the rule `source_fetch.py` already states for the first two):

| Shape | Request | Response element the run reads |
|---|---|---|
| whole-config export | `type=export&category=configuration` | the `config` element under `result` |
| per-scope read | `type=config&action=get&path=<scope path>` | the element the path names |
| device fact | `type=op&cmd=<command>` | the element the command names |

The op shape is new, so the wrapper rule needs one accepted shape for it before path 2 can read a
device fact. `container_coverage.SCOPE_PATH_ROOTS` is the one definition that validates a scope
path, so a request for `predefined` needs a decision inside that definition, not a second
definition. `tests/test_source_fetch.py` gains the op-shape pins, and the existing pins that read
the `src/` set must still pass unchanged.

**2.2 The scope set is read, not guessed.** Path 2 builds its scope set from the membership
responses it read, through the same four membership lists `parse_associations` reads
(`docs/ARCHITECTURE.md` §3, rule 3). Two levels, no more: one request per scope container, then
one request per scope entry that those containers name. Path 2 makes no request for a scope the
run did not read, and it guesses no scope. `api_requests.py` states this rule, and
`tests/test_api_requests.py` pins it.

**2.3 One response per request, checked against the request that made it.** A response is
accepted only when the element it holds is the element its own request names, and the entry name
inside it agrees with the scope index. This is the F5.4 wrapper rule read with the scope index, so
the join is checked rather than assumed. `tests/test_source_fetch.py` pins the shape, and
`tests/test_api_requests.py` pins the join with the index.

**2.4 The request set is not one tree.** Path 2 never assembles one tree from many responses,
because the line map, the entry ledger, and the parent walk are keyed on the source that was
parsed. Each response is its own `ParsedSource` with its own line map, and each parse method runs
over the response that holds its container. The report row names the source that holds the entry,
which `tests/test_entry_coverage.py::test_every_row_names_the_source_that_holds_the_entry` already
pins. A run that reads N scopes has N sources, so its report names the response the entry came
from. `tests/test_api_path.py` pins that a merged tree is not built.

**2.5 The record holds one record per request the run read.** The eight fields and the fixed order
are unchanged (`docs/ARCHITECTURE.md` §3.3). The `scope` field names the path the request declared,
and the `request` field names the key-free identity of that request. The prune action reads the
record file the same run wrote, so a run that read N scopes protects N entries. No new field is
needed. `tests/test_provenance.py::test_the_record_file_holds_one_record_per_source_read` is the
pin that grows.

## 3. The join to the codebase model

- **The unit set.** `unit_manifest.units` is still the one unit rule, so path 2 states no second
  unit rule. Path 2 adds one fact the join can read: the scope the run read for a unit. A unit with
  no request, and a request that answers no unit, is a finding. `tests/test_api_path.py` pins both
  directions, and `tests/test_unit_manifest.py` keeps the join rule.
- **The source field on the ownership row.** `OWNERSHIP.json` already names the source for each
  entry, so path 2 writes the same row shape with a response name instead of a file name, and
  `tests/test_ownership.py` keeps it.
- **The order rule.** The three bases `CODEBASE_ASSEMBLY.md` §6 states do not read the input
  shape, so path 2 writes the same order. `tests/test_reference_edges.py` is unchanged.
- **The gate.** Every existing gate rule reads the files the run wrote, so path 2 output is read by
  the same rules. Path 2 adds one rule: the request set must agree with the scope the run read. Its
  position in `sanity_checks.CHECK_ORDER` is a decision inside that module, not a second order. The
  round-trip cross-check reads the run's ledger, so path 2 must feed the same ledger through the
  same `mark` rule. `tests/test_round_trip.py` and `tests/test_sanity_gate.py` gain the path 2
  pins.
- **The credential rule.** `CODEBASE_ASSEMBLY.md` §11 is the owner, and `source_fetch.py` is the
  only `src/` module that states the environment name. Path 2's entry point must not state it, so
  `tests/test_variables.py::test_the_generated_block_names_the_environment_the_fetch_layer_reads`
  holds it for path 2 too.

## 4. The facts only a live target states

These are the facts an export cannot carry. Path 1 cannot state them, and path 2 cannot read them
offline, so each one stays blocked until a committed response shows its shape. Each fact names the
request shape that gives it, and each is recorded in `backlog.md` while it is blocked.

| Fact | Request shape | What it unlocks | Blocked on |
|---|---|---|---|
| rulebase per rule | per-scope read under a `pre-rulebase` or `post-rulebase` path | the four `*_policy_rules` types, and the import block for a rule entry | the accepted value string, verified against a live target (F3.5) |
| rule position | the same request, read in document order | the import position for a rule entry | the rulebase value above |
| device serial | the device fact shape | `target`, and `ngfw_device` as a value the run can print | an accepted op response shape, and a committed response |
| per-device template variable override | the device fact shape | the per-serial value `panos_template_variable` cannot carry | a response that shows how a device states it |
| built-in name table | a `predefined` read | the read-through rule can skip a built-in name such as `any` | `SCOPE_PATH_ROOTS` decision, and a committed response |

For the rulebase, path 2 has one advantage path 1 does not: the request path names the rulebase,
so the value is a request fact and not a guess. The rule is that the parse records the rulebase
only from the request that read the entry, and no parse method reads it off the element.

## 5. Offline proof

- Path 2 reads no network in a test. The producer is injected, as `tests/test_source_fetch.py`
  does today, so Goal 1 holds for path 2.
- The committed responses are one file per request shape, and each one names the request identity
  that produced it, so a test can run `fetch()` through the injected producer and read the same
  bytes the record names.
- A run that reads only committed responses writes byte-identical output between two runs, the same
  rule the corpus pins for path 1.
- For content that holds none of the facts in §4, path 2 writes the same `.tf` bytes as path 1 on
  the same fixture. The report files do not agree, because the report names the source. This is the
  pin that keeps the two paths honest to each other: `tests/test_api_path.py`.

## 6. What path 2 does not close

Path 2 is an input mechanism. It does not close a parse gap, so these stay where they are:

- The security profile bodies, the schedules, the regions, and the application filter properties:
  an export already holds these containers, so path 2 adds nothing. They stay in `backlog.md`.
- A value the parse cannot carry. A live device does not return a private key or a password hash,
  so the reference-only rule (`docs/ARCHITECTURE.md` §4.6, `VALUE_VARIABLES`) is unchanged.
- The state write path, the orchestrator, the Day 1 device bootstrap, and the plan: out of scope
  (`backlog.md`, Out of Scope).
- The PAN-OS version matrix: a device fact is version dependent, and version matrix testing is out
  of scope.

## 7. Modules path 2 adds

`src/` is one flat namespace, so both modules import their siblings by plain name, and each is
named in the `docs/ARCHITECTURE.md` §1 table when it lands.

| Module | Role | Rule it keeps |
|---|---|---|
| `api_requests.py` | the scope index and the request set | the set is read from the membership responses, in sorted order, one entry per scope, and every response is checked against the request that made it |
| `api_to_terraform.py` | the path 2 entry point | the run order, the arguments, the exit codes, and no rule restated. It reads `PanoramaParser`, `TerraformGenerator`, `unit_manifest`, `sanity_checks`, and `write_path` |

Both modules write no file except through `write_path.py`, and neither states the environment name.

## 8. Piece order

1. The accepted request shapes, including the op shape, and the `SCOPE_PATH_ROOTS` decision for
   `predefined` (§2.1). Nothing else in path 2 can be written before this decision.
2. The scope index, read from the membership responses (§2.2), and the response-to-index join
   (§2.3).
3. The offline harness: one committed response per request shape, the injected producer, and the
   rule that no test calls a producer (§5).
4. The run over many sources: the parse methods per response, the report position, and the record
   per request (§2.4, §2.5).
5. The unit join, and the ownership source field (§3).
6. The gate: the request-set rule, and the path 2 pins for the rules that already read the files
   (§3).
7. The entry point: the arguments, the run order, the exit codes, and the generated `README.md`
   label that names which path wrote the codebase.
8. The live facts in §4, in the order the table names them, each gated on its own condition.
