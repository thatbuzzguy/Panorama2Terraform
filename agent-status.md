# Agent Status

## Current position

Epic 9 (rules as data, one iterated object per rule type) is open: Piece 16, the decision record, Piece 17,
Phase 9A the row shape, Piece 18, Phase 9B the write path, and Piece 19, Phase 9C the iterated block, are complete,
and the next piece is Piece 20, Phase 9D the gate. The pieces are in `to-do.md`, the decisions in `PLAN.md` Epic 9,
and the Piece 19 criteria and measurement in `acceptance.md`. Piece 20 states the gate rule for the block shape
Piece 19 emitted, which is recorded in `acceptance.md` §What Piece 20 reads and in `PLAN.md` Phase 9D: the block's
local name and its `for_each` map name read `rule_data.locals_name`, its `location` equals the `LOCATION_SCHEMA` row,
its field list is the name field plus the table order the matrix row declares, every body field is
`each.value.<field>` under the provider name and the shape word `RULE_ENTRY_FIELDS` states, one block per rule type
per unit, and the map entry keyed by the row `key` holds the values the row names when read through `parse_rows`.

Epic 8 (the second path) is complete with piece F8.10, and Piece 8 closed the finding F8.10 left open. The rules
it landed are in `docs/API_CONVERSION_PATH.md`, the modules are `src/api_requests.py` and `src/api_to_terraform.py`,
and the pins are in `tests/test_api_requests.py`, `tests/test_api_path.py`, `tests/test_unit_manifest.py`,
`tests/test_ownership.py`, `tests/test_provenance.py`, `tests/test_sanity_gate.py`, `tests/test_variables.py`, and
`tests/test_site_data.py`. The completed piece detail is not kept here; the git history holds it.

F8.10 is the agreement pin: for content that holds none of the five facts `docs/API_CONVERSION_PATH.md` §4 names,
path 2 writes the same `.tf` bytes as path 1, and the two reports agree on every field except `line` and `source`.
The pin is `tests/test_api_path.py::test_content_with_no_live_only_fact_writes_the_same_tf_bytes_as_path_1`. The
content lives in the test file (`AGREEMENT` and `AGREEMENT_EXPORT`), so this pin reads no committed response, and
no test calls a network. Measured: 10 `.tf` files byte-for-byte the same,
4 resources, 4 report rows each read through the ledgers, the two source sets disjoint, and the gate reports no
finding for either run, with `request_set` NOT RUN for path 1 and PASS for path 2. The content states no
membership list, because a membership list makes the entry its own scope, so the same entry is read twice.

Piece 8 (2026-11-18) decided that double read. The run reads the membership response and then the entries the
index names, so an entry a membership list names is read twice, once inside the place response and once as the
response its own request made, and the run keeps both answers: each response records its own rows. A parse method
reads the entries at the level its row names, so an entry response answers the entry its own request named, through
`PanoramaParser._section_entries` in `src/panorama_to_terraform.py`, and a membership row answers nothing for an
entry response. Path 2 writes the content of each response it read, so the same entry read twice gives one block
per response and the naming rule's suffix on the second. Measured on `MEMBERSHIP`: 4 responses read, 8 emitted
rows (2 per entry name, each naming its own response), path 2 writes 8 resource blocks against path 1's 4, and the
gate reports nothing for either run. The rule is in `docs/API_CONVERSION_PATH.md` §2.4 and §6; the pins are
`tests/test_api_path.py::test_the_entry_read_answers_the_entry_its_own_request_names`,
`test_an_entry_two_responses_hold_gives_one_block_per_response`, and
`test_the_double_read_agrees_with_the_gate`.

Piece 10 (2026-11-18) closed the six findings the 2026-11-11 audit recorded. The response-set rule reads a content
property of each file: a file in `tests/responses/` has a `response` root, and a file in `tests/fixtures/` is a
Panorama export, so its root is not. `tests/fixtures/api_response.xml` is now `tests/fixtures/export_config.xml`,
the same entries in the export form, and the committed export response holds the same config content. The pair that
was in the corpus sits in the response set under the identity of the request the pins name for it, so the set reads
5 files and `tests/test_api_requests.py`'s `HARNESS` names their requests. The `terraform-gate` CI job runs the
whole test set with the terraform binary present, so the pins that read the provider schema run in CI.
`tests/conftest.py::provider_schemas` skips only for a missing terraform binary and asserts when `terraform init`
returns non-zero. The five pin groups that restated an owner table as a measured count read as derivations from the
table's rows, with the measured number kept in the docstring as a dated measurement. The index rule gained the case
that a directory with no index of its own is named by the root index, so the two `.github/` contribution templates
stay and `README.md` names them. The criteria and the measurement are in `acceptance.md`.

Piece 11 (2026-11-18) landed the `tflint` integration. The gate rule that runs the rule set is
`sanity_checks.check_tflint`, the way `check_terraform` runs `terraform`, and `--tflint` is its flag, so the gate
that runs on every conversion reads no external command and reports the check as NOT RUN. The rule set is data
(`sanity_checks.TFLINT_RULES`), named through `--only`, so no config file restates it, and the rules the gate or the
emitter already state are recorded as `TFLINT_RULES_ALREADY_HELD` with the owner that holds each.
`TFLINT_SEVERITY` maps the tool's three severities to the gate's two, `TFLINT_EXIT_CODES` states the tool's own exit
codes, and a run that answered non-zero with nothing to report is a FAIL finding, so a silence cannot read as a pass.
The check runs once per unit directory the record names and names the directory it ran on. The committed test
material is `tests/tflint/probe.tf` and `tests/tflint/probe.json`, read through `tests/conftest.py`, and
`tests/test_sanity_gate.py::test_the_committed_tflint_output_agrees_with_the_binary` compares the committed answer
with the live answer, so a committed fact cannot drift from the rule it records. The rule is in
`docs/ARCHITECTURE.md` §4.6, the test material set in §1.1, and the file-set answer in `docs/CODEBASE_ASSEMBLY.md`
§14, which answers to no file, so the file inventory is unchanged. The pins that run the binary skip only for a
missing binary and assert on a non-zero run, so the `terraform-gate` CI job, which has the binary, is where they run;
the matrix legs skip them. Four pins changed what they read, and the reasons are in `acceptance.md`.

Piece 12 (2026-11-18) is the last piece of the audit series and is complete. `pyproject.toml` `target-version` now
equals the Python floor, so `ruff check .` enforces the spelling the project writes: the PEP 604 union for an
optional value, the call rule read from `collections.abc`, and `strict` stated at every `zip` call. The findings were
measured at that level on the tree at commit `698c957`, and the 20 `zip` sites were read one at a time before any was
written: `strict=True` at 19, where the two sides are the same set by construction, and `strict=False` at
`tests/conftest.py`, where each rule of a chain is read against the rule before it, so the two sides differ by one by
construction and `strict=True` would refuse a chain of any length. Two pins that read a module's import spelling read
the new spelling, and the reason for each is in `acceptance.md`; no pin is weakened. The criteria, the per-site
decision, and the gate measurement are in `acceptance.md`.

Piece 13 (2026-11-18) is the last actionable offline piece and is complete. `tools/quick_start.sh`
asks for each gate check that runs an external command when that binary is present, so it passes
`--validate` for terraform and `--tflint` for tflint, and it prints what the run asked for. Its Next
steps text names what `SANITY_REPORT.txt` reports for each command check: the result for a check the
run asked for, NOT RUN for one it did not ask for, and SKIPPED for one asked for by name with no
binary. The script states no rule of the tool: its comment states what it adds and why, and points
at `docs/ARCHITECTURE.md` §4.6, which is the owner of what a run reports. `docs/USAGE_GUIDE.md`
§Quick start script owns how the script runs, so it carries the change; `tools/README.md` names the
file and states no flag, and `README.md` states the converter's flags, so neither changes. No pin
reads the script, and none was written: a pin measures content, and the only content this piece
changes is the script's own text, while the flag behavior is already pinned on the entry point by
the five flag pins in `tests/test_sanity_gate.py`. So the piece is recorded as a dated measurement,
the way `backlog.md` records the provider facts. Measured 2026-11-18 on the committed sample, run
from outside the repository root: with both binaries present the report names `tflint PASS` and
`terraform PASS` for each of the 2 unit directories; with no binary found the script asks for
nothing and the report names both checks as NOT RUN, with the note that names each flag; with one
binary present, the check with the binary names its result and the other names NOT RUN. Every run
exits 0. One document-review finding was recorded during the piece, in `backlog.md`: `README.md`
§Testing states that each module is named once there, and test modules are named twice. Piece 14
closed it.

Piece 14 (2026-11-18) is the last offline-actionable item and is complete, and it closed that
finding. The decision is that the section was wrong and not its rule: 26 of its 81 entries were a
block repeated after the gate area, and each pair states the same facts, so nothing was merged and
each module keeps one row in its own area. The rule stays, and the check that reads it is
`tools/check_documents.py` check 6, because a pin holds a name being present and cannot hold a name
appearing once; the script stays a document-review script that the test set does not read. Measured
before: 81 entries, 55 names, 26 named exactly twice, none three times, so the count the finding
stated did not hold on the current tree. Measured after: 55 entries, each named once, the same 52
test modules, and the check reads the committed README as 26 findings and the fixed README as none.
No pin was added, weakened or removed. The one finding that piece left open is closed by Piece 15.

Piece 15 (2026-11-18) is the last offline-actionable item and is complete, and it closed that
finding. Re-measured 2026-11-18 on the tree at `5c70949`: `tests/test_layout.py` is 78 lines, the
pin `test_the_indexes_name_every_document_under_them` holds 8 asserts, and its AC-4 half is stated
twice, at lines 68 to 72 and at lines 74 to 78, word for word, with the blank line 73 between them,
so the same 22 `src/` modules were read against the same §1 module table text twice on every run.
The two blocks state one fact, so nothing was merged: the second block is removed and the pin keeps
the fact measured once, with the same name, comment, reads and assertion. Measured after: 72 lines,
7 asserts, one AC-4 comment and one read of the table. The decision on the rule is that no rule
states that a pin block is not repeated, and none was written: the Piece 7 rule says a pin measures
content or a name, which says nothing about reading a set twice, and `tools/check_documents.py`
reads documents, not test files, so a repeated block inside a pin is not a finding a check can
print. The piece fixes the instance, not the rule. Nothing offline-actionable remains: what stays in
`backlog.md` needs a fact a live target states.

Piece 16 (2026-11-18) recorded the four Epic 9 decisions and the phase list before any code, and is complete;
the record is in `PLAN.md` Epic 9, and nothing else changed.

Piece 17 (2026-11-18), Phase 9A, is complete at commit `e4ffe7b`. `src/rule_data.py` states the rule row shape
`RULE_ROW_FIELDS` (`directory`, `resource`, `entry`, `key`, `pivot`, `properties`) and the two forms of the same
rows: `render` is the consumed JSON, which is the form a Terraform object reads because Terraform has no CSV
decode function, and `render_csv` is the printed form of the same rows. `parse_rows` reads the data form and
refuses a row that is not the declared shape, including the printed form read as data. `rulebase` is not in the
shape, because the parse records no rulebase fact (F3.5), so no column can name a field the parse cannot capture.
The eight pins are in `tests/test_rule_data.py`, and the criteria are in `acceptance.md`.

What Piece 17 decided while measuring: the property value kinds are string, boolean, list and mapping, because a
PBF rule's `action` is a nested mapping that holds booleans, so the shape cannot declare only strings, and a
number is refused because the rule parse stores no number. `build_rows` reads each declared field through the
recorded object, so a field the parse never stored is a field held with no value and prints no column; measured on
`tests/fixtures/nat_rules.xml`, where 4 rules hold and some rules hold no `destination_translation_*` key at all.
The key's digest half is the row's own unit digest, so `parse_rows` refuses the two halves when they disagree, and
the reader accepts at least four digits rather than exactly four, because a chain longer than 9,999 rules prints a
longer ordinal and a print rule and a read rule cannot contradict each other. `Shared` is read through
`unit_manifest.SHARED_UNIT`, and `vsys1` is the default this grouping needs for a rule the export names no virtual
system for, which is the fact the group keys on and not the parse's honest scope: no pin states that either name is
stated once, so the delegate removes the generator's two literals and no golden byte changes. The key pin plants its
material, because a scan of the committed fixtures found no fixture holding one rule name in two device groups, and
the planted config is read through `xml_input.parse_xml`, the same input door the corpus pins read, and stays out of
the corpus. `TerraformGenerator._policy_rule_chains` delegates to `rule_data.chains`, so the group is stated once,
which the pin reads as no other module defining it.

Piece 18 (2026-11-19), Phase 9B, is complete at commit `eda2d1a`. The rule data pair is written per rule type per
unit inside the unit directory the rows name, and only through `src/write_path.py`: `rule_data.py` holds no writer of
its own, states no path, and the run's write step calls `write_path.unit_path` and `write_path.write_file`, following
the `site_data`, `import_blocks` and `commit_actions` per-unit pattern. One file-name rule and not two:
`rule_data.data_file` and `rule_data.printed_file` read the same coverage matrix row's `output_file`, so the two names
are that row's stem with the `.json` and `.csv` suffixes. The pair is a unit-set file set, because the rows of one
rule type are the rows of one unit: the chain grouping keys on the device group and the virtual system, which are two
of the five unit facts, so the file names its unit only by its directory. Written only when it has content, so the
file set is the units that have rows, not rule types times units. `docs/CODEBASE_ASSEMBLY.md` §14 names the set the
new shape belongs to, `docs/USAGE_GUIDE.md` §Output files names the two forms, the generated `README.md` names them as
files under the §9 rule 9 exception, and the `docs/ARCHITECTURE.md` §1 row for `rule_data.py` states the write half as
the run writing through `write_path.py`. The pins are ten in `tests/test_rule_data.py` and 21 in
`tests/test_write_path.py`; the criteria are in `acceptance.md`.

What Piece 18 decided while measuring: no gate rule reads the pair in this piece, because the data rule keeps reading
the four records at the codebase root as one rule over the rows of every unit and reads no file inside a unit
directory, so the report's two counts do not move and the gate that reads the rule rows through the declared shape is
Piece 20. The printed half of the pair is not the printed form the data rule compares, which stays with
`site.auto.tfvars`, so `rule_data.parse_rows` still refuses the printed form read as data. The write step states no
type table and no join table: the four types come from `import_blocks.rule_types`, the parse answer for one type is the
`PARSE_ORDER` entry for the parse method `container_coverage.CONTAINER_TABLE` names for that matrix row, read through
`entry_coverage.row_detail`, and the join is the `directory` column. `policy_order.xml` names five unit directories
while its three chains name three of them, so the pin reads the three chains as the units that have rows and not as
the whole file set. Because `tests/test_write_path.py::test_a_record_module_renders_rows_and_writes_no_file` forbids a
`def write...` in a record module, the writing cannot sit in `rule_data.py`, which is what the write-path rule means
in practice. The pins derive the two names through `rule_data` and the matrix row, so no pin restates a file-name rule
and no pin reads a private module constant.

Piece 19 (2026-11-19), Phase 9C, is complete at commit `14e5b92`. The four rule generators print one `for_each`
block per rule type per unit, and the block reads the `locals` map that is the printed form of that unit's rows, so a
row value is stated once in the file and the block body prints only `each.value.<field>`. One name rule and not three:
the map name and the block's local name read the same matrix row's `output_file` stem through `rule_data.locals_name`,
which is the stem `data_file` and `printed_file` read with the `.json` and `.csv` suffixes. The entry states the name
field first through `entry_coverage.name_field` and then the row's fields in table order, and a field the recorded
object holds with no value prints `null`, because one field list serves every instance. Reference columns record
whether a name resolved inside the unit, read through `name_ref` at the map site; a `VALUE_VARIABLES` column prints
`var.<name>`. `depends_on` drops, `position` prints `where = "last"` for every instance, and `pivot` stays a row
column the block does not read, because instances inside one block create in the key order, which is the XML order
inside a chain. `rule_data` gains `printed_keys`, the only reader of the printed map and a reader of its keys only,
and the cross-check's block side for the four rule rows reads it, so the gate states no reader for the map. The pins
retargeted are the shared rule-block parser and chain check in `tests/conftest.py`, then `tests/test_policy_order.py`
8, `tests/test_real_or_report.py` 5, `tests/test_edge_cases.py` 19, `tests/test_dependency_wiring.py` 11,
`tests/test_coverage_matrix.py` 211, `tests/test_round_trip.py` 34, `tests/test_property_coverage.py` 33,
`tests/test_golden_files.py` 91, `tests/test_import_blocks.py` 32, `tests/test_sanity_gate.py` 110,
`tests/test_data_file_gate.py` 21, and one new pin in `tests/test_rule_data.py`, now 11. The six rule goldens move,
from a real run, and the sample run's resource count moves 20 to 17.

What Piece 19 decided while measuring: `rules = [ each.value ]` cannot be the printed shape, because `terraform
validate` refuses it - the provider marks `rules[0].name` required and cannot read it through a dynamically-typed
`each.value` (measured 2026-11-19 in the offline validate harness, Value Conversion Error, Target Type:
provider.SecurityPolicyRulesResourceRulesObject), so the entry enumerates its fields and one table holds the name and
the shape word for each, with `RULE_ENTRY_READERS` naming the reader for a field whose provider object key is the row
value. The reader is tried before the empty-value check, because a reader can derive the shape from another field: the
legacy decryption `action` carries the inspection mode. `destination_zone` is the one row field the parse records as
one value through `xml_input._get_text` while the provider declares `['list','string']`, so the entry prints the
one-member list. NAT `service` is one string, so a member list prints `null` plus the `# NOTE:` line that names the
members, which is the never-drop rule, and the `# NOTE:` lines print inside the entry before the field line they
explain, so the printer prints entries field by field rather than one `hcl_value` call per entry. The cross-check's
finding wording for a rule row is `the ledger reads N entries, the reader reads M entries in the map the block reads`,
and `position` is a helper inside the rule's source slice. Measured on the corpus after the retarget the four rule
rows read clean, so the corpus table in `tests/test_round_trip.py` names no rule row and the fact count stays 19 on 8
fixtures, 3 + 15 + 1 by category. `check_location_present` reads only `resource`, `data`, `import` and `action`
blocks, so a `locals` block raises no finding, and `check_references` resolves references inside the map.

The licensing rule is in `docs/LICENSING.md`, the owner document: the fork source, the two holders, the split
measured through `git blame`, and the scope of each grant. `LICENSE-COMMERCIAL` is the upstream author's grant, so
it covers the upstream parts only, and this project grants no commercial terms for its own contributions. The word
"non-commercial" is not used as a license name, because AGPL v3 permits commercial use and §10 does not allow an
extra non-commercial condition on a derivative work, so the choice reads as "AGPL v3 only".

Test count: `python3 -m pytest` reads 1,697 pins in 52 test modules: no skips when the tflint binary
is present, and 4 skips for the missing binary when it is absent, because the pins that run the rule
set skip only for a missing binary. The count is the same before and after Piece 12, so no pin was
added, removed, or weakened. Piece 13 adds no pin, and the count is 1,697 in 52 modules before and
after it, read from the per-module collection counts. Piece 14 adds no pin, and the count is the
same 1,697 in 52 modules before and after it, read the same way. Piece 15 adds no pin, removes no
pin and weakens no pin, and reads the same count before and after it: the change removes one
duplicate assert inside the index pin, and a pin is the test function, not an assert. Piece 17 adds 8 pins and one
test module, so the count reads 1,705 pins in 53 modules: 1,701 pass and the same 4 skip for the missing `tflint`
binary, measured 2026-11-18 on the tree at commit `e4ffe7b`, with `ruff check .` clean and `ruff format --check .`
clean on the 102 Python files. Piece 18 adds 3 pins and no test module, so the count reads 1,708 pins in 53 modules:
1,704 pass and the same 4 skip for the missing `tflint` binary, measured 2026-11-19 on the tree at commit `eda2d1a`.
Piece 19 adds 1 pin and no test module, so the count reads 1,709 pins in 53 modules: 1,705 pass and the same 4 skip
for the missing `tflint` binary, measured 2026-11-19 on the tree at commit `14e5b92` in 292.16 s, with `ruff check .`
clean and `ruff format --check .` clean on the 102 Python files and `check_documents` reporting no finding; no pin was
weakened, and every retargeted pin still measures content.
`ruff check .`
is clean at the level `pyproject.toml` states and `ruff format --check .` is clean on the 100 Python
files. `tests/test_api_path.py` reads 33 pins (30 before Piece 8). `tests/test_sanity_gate.py` reads
110 pins, 11 more than the 99 it read before Piece 11. `pyproject.toml` sets `addopts = "-q"`, so a
second `-q` suppresses the summary line; the count is read from the per-module collection counts.

Full-suite time, measured 2026-11-13: 325.4 s, 364.6 s and 364.9 s on three runs of the same set (5
min 25 s to 6 min 05 s). Measured pin time 335.2 s, collection 0.6 s, `ruff check .` 0.1 s. The
recorded run when the test set held 663 pins took 35 s, so the growth is the corpus pins and the
pins that run `terraform`. The slowest part is `tests/test_terraform_validate.py` at 121.4 s, then
`tests/test_sanity_gate.py` at 49.9 s (34.0 s of it in the three pins that run the gate with the
terraform binary), then the corpus pins at 79.8 s. The Piece 7 runs, measured 2026-11-16, took 4 min
24 s and 6 min 25 s for the same set. The Piece 8 run, measured 2026-11-18, passed 1,688 pins in
305.56 s. The Piece 10 run, measured 2026-11-18, passed 1,686 pins in 313.68 s, with `ruff check .`
at 0.015 s, `ruff format --check .` at 0.011 s, and `python3 tools/check_documents.py` at 11.09 s.
The Piece 11 run, measured 2026-11-18, passed 1,697 pins in 280.97 s with the tflint binary present
and in 286.45 s with it absent, where the four pins that run the rule set skip for the missing
binary. The Piece 12 run, measured 2026-11-18 with the binary present, passed the same 1,697 pins in
52 modules in 273.21 s at the new level, against 339.42 s for the same set read on the tree at
commit `698c957` in a detached worktree; `python3 tools/check_documents.py` reports no finding for
either tree. The Piece 13 run, measured 2026-11-18 with the tflint binary present, passed the same
1,697 pins in 52 modules in 335.42 s, with `ruff check .` clean at `py310`, `ruff format --check .`
clean on the 100 Python files, and `python3 tools/check_documents.py` reporting no finding. The
demonstration run through the script on the committed sample takes 3.29 s with both binaries present
and 0.26 s with neither, measured 2026-11-18 from `/tmp/opencode/piece13`, so the script writes no
file in the repository root. The Piece 14 run, measured 2026-11-18 on the final tree with the tflint
binary present, passed the same 1,697 pins in 52 modules in 360.33 s, with `ruff check .` clean at
`py310`, `ruff format --check .` clean on the 100 Python files, and `python3 tools/check_documents.py`
reporting no finding, read at 6.20 s after the final document edits. The same set passed in 299.71 s
on the run before the final document wrapping, so the wrapping changed no pin. The Piece 15 run,
measured 2026-11-18 on the final tree with this piece's change and the tflint binary present, passed
the same 1,697 pins in 52 modules in 258.53 s, with `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 100 Python files, and `python3 tools/check_documents.py`
reporting no finding, read at 6.54 s after the final document edits. The same set measured 263.54 s
before the final document edits and 271.38 s on the tree before the change. The Piece 17 run, measured 2026-11-18 on the tree at commit `e4ffe7b` with the
`tflint` binary absent, passed 1,701 pins and skipped the same 4 in 320.31 s, with `ruff check .`
clean at `py310`, `ruff format --check .` clean on the 102 Python files, and
`python3 tools/check_documents.py` reporting no finding, read at 12.15 s. `tests/test_rule_data.py`
reads 8 pins. The piece changes no golden, fixture, response or tflint file, so the pins that name
the printed sets and the golden bytes read the same as before. The Piece 18 run, measured 2026-11-19 on the final
tree at commit `eda2d1a` with the `tflint` binary absent, passed 1,704 pins and skipped the same 4 in 507.48 s,
against 280.70 s for the same set read on the tree before the final document edits, with `ruff check .`
clean at `py310`, `ruff format --check .` clean on the 102 Python files, and
`python3 tools/check_documents.py` reporting no finding, read at 23.20 s after the final document edits.
`tests/test_rule_data.py` reads 10 pins and `tests/test_write_path.py` reads 21, against the 8 and 20 it read before
the piece. The piece changes no golden, fixture, response or tflint file, because the golden set is the `.tf` set and
the records and the reports are not in it, so the golden bytes and the report counts read the same as before.

Gate size, decided 2026-11-13: no smaller default gate is adopted. The measured subset that drops the pins that
call `terraform` runs in 203.0 s (44% of the full run), and the subset that drops the corpus pins runs in about
285 s, and each saves time by dropping the pins that carry the promise, so neither can be the gate a result claim
comes from. The full run stays the default gate, and the plan check pins and the corpus pins stay inside it;
nothing is removed from the full run. A smaller run is a working loop on one area only, as an explicit
command-line selection, followed by the full run before a result is recorded or the work is committed. It is
recorded in the report and in `docs/ARCHITECTURE.md` §1.1, and not in the tests, because the suite states no marks
and a mark would make the smaller set the default. A smaller gate does not change the result: every pin in each
subset passes, and the full run passes.

The shared test definitions are in `tests/conftest.py`, so a test module reads them there instead of
defining its own copy, and no test module imports another test module (`docs/ARCHITECTURE.md` §1.1).
What landed: the rule-block parser and the chain check that `tests/test_policy_order.py` and
`tests/test_real_or_report.py` share, the terraform binary, the golden set path, and the resource-
line patterns. The pattern decision came from measurement against the goldens and the corpus run
output: the shapes the test set held before answer the same 414 matches, and no resource line lacks
the trailing brace, so the difference was the capture groups only. `tests/conftest.py` therefore
states two named patterns as data, both requiring the block brace, each with the rule it serves:
`RESOURCE_RE` answers the resource type for the pins that read the emitted type set, and
`RESOURCE_ADDRESS_RE` answers the type and the local name for `tests/test_dependency_wiring.py`,
which reads `findall` as pairs. The measurement and the decision are recorded in the comment at the
patterns and in `acceptance.md`. The pin count is unchanged, so no pin was weakened.

The CI gate reads the Python floor as 3.10, and the matrix legs are 3.10, 3.11, 3.12 and 3.13. The
3.9 leg is dropped, not moved to an older runner image, because two facts make it unusable:
`actions/setup-python` has no hosted build for 3.9 on Ubuntu 26.04, the image `ubuntu-latest` names
from November 2026, and `requirements.txt` pins `pytest==9.1.1`, which requires 3.10. Each leg is a
minor version, never an exact patch, because the build manifest for 26.04 holds only the newest
patches for the older minors. `pyproject.toml` states the floor, and `README.md` and
`docs/USAGE_GUIDE.md` state the same value. `target-version` now equals that floor, so the lint gate
enforces the spelling the project writes: the PEP 604 union for an optional value, the call rule
read from `collections.abc`, and `strict` stated at every `zip` call. No pin reads the workflow
file, and the workflow states no level of its own, so the CI legs read `pyproject.toml`; the legs
start at 3.10, so no leg runs a Python below the level the gate enforces.

The pieces that stay blocked on a fact the tool cannot read offline are in `backlog.md`: the path 2
live facts in `docs/API_CONVERSION_PATH.md` §4, the four `*_policy_rules` types, a config entry
inside a stack, the EDL `certificate_profile` field, and the profile-name report column. The audit
series is complete with Piece 12, and Pieces 13 to 15 are the last offline-actionable pieces, so no
actionable slice is left open: what stays in `backlog.md` needs a fact a live target states.

Piece 3 (pins that measure nothing) is complete. The five findings the 2026-11-11 audit recorded in
`backlog.md` are fixed, each by making the pin read the material its own rule names, and no pin failed when it
started measuring content, so no new finding is recorded. What landed: `tests/conftest.py` states the three
definitions more than one module reads — the `.tf` read shape `tf_bytes` (keyed by the path from the case
directory, because the run writes one directory per unit), the input read rule `input_refusal`
(`xml_input.check_bytes`, then the parse), and the accepted corpus set `corpus_fixtures()`. No test module states
the hostile-fixture name rule, so the 18 read sites in 12 test modules read the accepted set, and no corpus pin
needs a guard because an accepted fixture cannot fail the parse. The four golden byte pins, the actions corpus
pin, the two response-set length pins, and the five order pins now measure content; the order pins state the
document order `docs/ARCHITECTURE.md` §4.4 states and each asserts the uniqueness rule the name-keyed read
depends on. The pin count is 1,651 before and after, so no pin was added, removed, or weakened. The acceptance
criteria and the measurement are in `acceptance.md`. Gate after, measured 2026-11-13: `ruff check .` clean,
`python3 -m pytest` passes with no skips, 1,651 pins in 293.0 s.

Piece 4 (the parse set reads what its rows state) is complete, committed 2026-11-13. The five findings the
2026-11-12 audit recorded for the parse set are closed, and one part of the last finding stays open in
`backlog.md` with owner `_protocol_field`: a `number` text the value rule cannot read has no report. What landed:
`tag` is read for every interface kind through one rule, `_interface_tag`, and both address shapes through one
rule, `_list_values`; `zone` and `virtual_router` are gone from the interface object, and `parent` is a field only
for the kinds whose row declares it; every entry name guard records the entry it skips, and
`_list_names` is the one guard the rule does not reach; `parse_schedules` skips a nameless recurring child through
the record, so the writer joins only the names it kept; `_parse_router` records an entry at the level the shape
table states no row for; `value_shape` reads a signed integer back as `number`. The criteria and the measurement
are in `acceptance.md`. Gate after: `ruff check .` clean, `python3 -m pytest` passes with no skips, 1,659 pins in
270.21 s, against 1,651 in 334.6 s before the piece. Counts by module: `tests/test_interfaces.py` 8 to 10,
`tests/test_entry_coverage.py` 29 to 32, `tests/test_property_coverage.py` 31 to 33,
`tests/test_protocol_object.py` 45 to 46; two pins in `tests/test_parse_network.py` changed what they assert, and
its count is unchanged at 24. No pin was weakened.

Piece 5 (naming and printing state one rule) is complete, committed 2026-11-15. The eight findings the
2026-11-12 audit recorded for naming and printing are closed, each by stating the rule once in its owner module
and pinning it with a test that measures the content of a run. What landed: `generate_virtual_routers` passes the
route's own name to `declare_block_name`, so one name is digested once and the declaration index holds the name a
reference reads; `naming.UNNAMED` is the one statement of the fallback word, read by `unit_manifest` and
`declare_block_name`; `site_data.record_pair` is the one statement of the pair rule, so a second source for one
name is a refusal; `hcl_value` states that the row order is the print order at every level, so the two `sorted()`
calls are gone and `parse_filter_containers` reads `FILTER_PATHS`; `xml_input.CONTROL_CHARS` is the read layer's
statement of the control-character rule, the state door refuses one in a value, and `escape_string` keeps only the
escape shapes; `xml_input.read_text` owns the whitespace rule and the six value helpers read it, with an absent
element answering `None`; `UnitText` keeps its own once record per file; and the placeholder marker is stated once
as `resource_mapping.PLACEHOLDER_TEXT`, printed only for a `reference_only` field the export cannot carry, with the
gate rule reading it through the owner. `pre_shared_key` is dropped from the `COVERAGE_MATRIX` row for
`panos_ike_gateway`, because the parse holds no value for it.

Five pins are source scans rather than content reads, each with the reason stated in `acceptance.md`: the two
"stated once" rules (items 2 and 8), which no run can show because two statements of one word print the same
string, the "no print site states a second order" rule (item 4, two pins), which content cannot show for the
certificate rows, and the "the read layer owns the rule" decision (item 5), which no run can show because a state
value never reaches a `.tf` file. Each of those items keeps a content pin as well. Measured against the code
before the change, 28 of the 1,673 pins fail: 23 pins and the five `tests/test_real_or_report.py` pins, which
stop the run at their collection because they read a constant the table did not state. The pins that measure the
rule and cannot fail before the change are recorded in `acceptance.md`, each with the reason.

Gate after, measured 2026-11-15: `ruff check .` clean, `python3 -m pytest` passes with no skips, 1,673 pins in
258.2 s, against 1,659 in 270.2 s before the piece. Three goldens moved: the kitchen-sink `filters.tf` and
`virtual_routers.tf`, and the filter-container golden's `filters.tf`. The criteria, the pin changes, the pins that
fail before the change, and the counts by module are in `acceptance.md`.

Piece 6 (the splitter reads the owners' rules, and the error rule names its kinds) is complete, committed
2026-11-15. The six findings the 2026-11-12 audit recorded for `src/split_device_groups.py` and the error rule are
closed, each by reading the rule through its owner. What landed: the splitter serializes the tree to text and writes
it through `write_path.write_file`, so the byte rule and the `LF` rule cover the split files and the text ends with
the final line the single writer states, and the writer scan now reads the element-writer shape; the file name is
`naming.variable_name` applied to the device-group name, and two names that read to one file name are refused as an
input-layer refusal with no file written, because a numbering would depend on the order the entries appear in; the
splitter's tables are keyed by the source line the read layer records, so one entry produces one row and the join
answers each entry's own devices in source line order; the shared merge dedupes the pair (path, name) at the level
the path names and keeps each entry at its own path; the dead branch and its troubleshooting row are gone, because
the extraction takes the row it was given; and `is_refusal` names only `xml_input.UnsafeInputError` and
`ET.ParseError`, so a plain `ValueError` keeps the shape `failed()` states and `refused()` lost the branch that
could no longer fire and its `read_name` argument.

Two pins are source scans, each with the reason `acceptance.md` states: the writer scan cannot show which writer
wrote a file, because an element writer can produce the same bytes for the same tree, and a branch that cannot fire
cannot be shown by a run at all. Each of those items keeps a content pin as well. Measured against the code before
the change, 23 of the pins fail, and the same 23 pass after it (`/tmp/opencode/piece6/before`). The pins that
measure a claim and cannot fail before the change are recorded in `acceptance.md`, each with the reason.

Gate after, measured 2026-11-15: `ruff check .` clean, `python3 -m pytest` passes with no skips, 1,687 pins in 51
modules in 355.14 s, against 1,673 pins in 50 modules in 258.2 s before the piece. Counts by module:
`tests/test_split_device_groups.py` is new at 12, `tests/test_write_path.py` 19 to 20, `tests/test_safe_input.py`
36 to 37; the other four modules are unchanged. No pin was weakened.

Piece 7 (the indexes and the documents agree with measurement) is complete, committed 2026-11-16. The findings the
2026-11-11 audit recorded for the indexes, the documents, and the pins that read documents are closed. What landed:
the `docs/ARCHITECTURE.md` §1 module table names all 22 `src/` modules, with `commit_actions.py` as a row; the test
set is named by the root index, which names every test module, `tests/conftest.py` and the files the response set
holds, so `tests/` keeps no index of its own; four document claims took the real pin names; the counts
the documents state are measured at commit `ac7609e` or stated as derived from the table, and `README.md` states no
counts and links to the owner documents; the index rule has one pin,
`tests/test_layout.py::test_the_indexes_name_every_document_under_them`, and the wording checks moved to
`tools/check_documents.py`; three pins became redundant with the tool and were removed, one in
`tests/test_api_requests.py` and two in `tests/test_container_coverage.py`, and the two pins that read
`backlog.md` keep their facts as data; each row shape has one name (`SITE_ROW_FIELDS`, `ACTION_ROW_FIELDS`,
`IMPORT_ROW_FIELDS`, `MATRIX_ROW_FIELDS`). Decision 1 records that no pin in the test set reads document wording,
with the reason.

Gate after, measured 2026-11-16: `ruff check .` clean, `python3 -m pytest` passes 1,685 pins in 52 modules with no
skips in 4 min 24 s, against 1,687 pins in 51 modules before the piece (3 pins removed with the wording checks, 1
index pin added). `python3 tools/check_documents.py` reports no finding. No pin was weakened. Two findings stay open
in `backlog.md`: the two `.github/` template files sit outside every index, and the pins that state the fixture set
as a fixed number.

Piece 9 (`ruff format` as a gate, the `backlog.md` Nice-to-Haves item) is complete, committed 2026-11-16. What
landed: the one-time format pass over the Python files — 22 modules in `src/`, 49 in `tests/`, 2 in `tools/` — with
ruff's default double-quote style and no `pyproject.toml` change; ten string literals over the 120-line limit
split by hand, with the value unchanged; eight pins that read the single-quote spelling of a module source,
retargeted to the double-quote spelling the pass enforces, one of which reads the hex spelling ruff normalizes
(`chr(0x7F)` in `tests/test_sanity_gate.py`); and `tools/check_documents.py` reading each notice's file total at
the commit `docs/LICENSING.md` names, so a format pass cannot move a document fact. The gate adoption is the CI
step and the documents that state the gate: `README.md` §Testing, `docs/ARCHITECTURE.md` §1.1,
`docs/COVERAGE_MATRIX.md`, `docs/USAGE_GUIDE.md`, `PLAN.md` §Current State, and `tools/README.md`. No pin reads the
CI workflow file, so the gate is stated and not pinned.

Gate after, measured 2026-11-16 at commit `7df0570`: `ruff check .` clean, `ruff format --check .` clean,
`python3 -m pytest` passes 1,685 pins in 52 modules with no skips in 333.87 s, and
`python3 tools/check_documents.py` reports no finding. The same set passes in 305.95 s on the tree that carries
these edits, with no finding. The pin count is unchanged, so no pin was weakened. One
finding was recorded and closed inside the piece: the format commit alone reports 2 findings from
`tools/check_documents.py`, because a notice's file total was read from the working tree, while the document
measures at commit `ac7609e`.

Next: piece 8, the membership entry read (`to-do.md`).


## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A document that names a test names a test that exists.
- A pin measures content or a name, never the wording of a document. A wording check is a document review, so it
  lives in `tools/check_documents.py`, which the test set does not read.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record is not kept in the markdown. The git history is the record, and the
  markdown states the current state.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.
- Completed epic, phase, feature and task detail is removed from the tracking markdown after
  the work is committed; `AGENTS.md` states the rule.

## Watch for the shape tables and the write path

- `state_coverage.ownership_key` is the one identity key rule, so the shadow scan, the ownership order and the
  state scan read their keys through it and no module states a second key. The key names the parent scope for a
  shadow, so the report line names which parent entry the child repeats, and the parent entry stays in the
  report, because the console shape names one identity.
- The console line shape is stated in one place, `container_coverage.console_line` (`docs/ARCHITECTURE.md`
  §3.2), so a scan states its fact phrase and its block header and calls it. A finding kind that prints on
  the console must fit the four parts: one position, one identity, one fact. A source named on a console
  line is the source name, never the path, and a fact that compares two entries or two units prints in the
  report only.
- The captured part of a report line is stated in one place, `entry_coverage.captured_part`, so `entry_line` and
  `gap_fact` print the same words for the same finding. `PRINTS_VALUE_KINDS` names which kinds print a value, and
  it must stay data: no writer branch may decide the shape per kind. `NAMES_NO_FIELD_KINDS` is the matching data set
  for the kinds that name no field, so a `bookkeeping` row states the row identity only, because the fact its row
  records is the relation the entry carries no value for. A row that prints a value must carry the
  captured object through `row_for`, because `fields` holds the names only, and the value shape is
  `report_value`. A read through the recorded object is what the property scan counts, so a rule that prints a
  value is a rule about a read, and the pin that holds it must run the pipeline, not build a row by hand. A kind
that names field names must name only fields a read reaches: for a `nested-block` row the print is the only
output its entry reaches, so the names come from the read record, and for a `bookkeeping` row no read reaches a
field, because the fact the row records is a relation the entry carries no value for
(`docs/COVERAGE_MATRIX.md` §1, pinned by
`tests/test_property_coverage.py::test_the_nested_block_line_names_only_the_fields_the_emitter_reads` and
`tests/test_property_coverage.py::test_the_bookkeeping_line_names_no_field_for_the_membership_entry_it_marks`).
- The write path landed (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per
unit the manifest
    names, and the codebase root holds the root set. A new file shape must name which set it
  belongs to, and the
  report counts, the console line and the tests that read the file set change with it.
- `unit_manifest.units` is the run's unit set, so a rule that names a unit for a directory, an
owner, or an
    edge reads it through that one function. A unit exists only when the ledger has a row in
  it, and the fact
    order is the identity join, so a new fact changes every digest and every golden in the same
  commit.
- `VALUE_VARIABLES` is the single shape owner and `sensitive = true` is the `REFERENCE_ONLY`
row's rule alone, so a
new shape word must be read in the table and not by a name list. F7.7: a reference-only name
can be the §5 name
of the entry that holds the field, so the pin that reads the declaration set walks the fixture
through the
table (`tests/test_variables.py::_reference_names`). The test that pins the declaration set
reads the
    names the table records with no value (`tests/test_variables.py`), and the test that pins
the report rule carves
    the `README.md` file-inventory exception. A change to a shape word moves both pins in the
same commit.
- A rule that pins an absence by scanning module sources cannot read a source that names the words it
  forbids, so a scan reads the tool's own modules, and the test name and the module docstring carry no
  forbidden word. The writer scan reads the `src/` set and excludes `src/write_path.py` (the single writer);
  `tests/conftest.py` is the test harness, so it sits outside the set. The pin for the outputs rule is group 7
  of `tests/test_reference_edges.py`; the pins for the file shape are `tests/test_write_path.py`.
- The fixture assembler is a generator, not a pin, so no document or test may claim that its output is the
  committed fixture. Its read rule is the two F3.8 checks read on the committed bytes, so a hostile fixture is
  skipped by rule and not by name, and the tool names no fixture in its source except its own record. `tools/`
  is not on the test path, so `tests/test_build_kitchen_sink.py` reads the tool's functions through `importlib`
  on the path `tests/conftest.py` builds once, and the tool writes no file, so a run cannot change the record the
  goldens read.
- The block reader in `sanity_checks.py` serves every kind, and the same field reader serves
the fields inside a
    container value and the elements of a list value, so a new block shape uses them rather
than writing a second
  reader. The round-trip cross-check reads the block set through it with `kinds = ('resource',)`, so it states
  no reader of its own. Its fact compares two sets, so its finding is a coverage fact and prints no console
  line: it is a WARN, the decision `entry_coverage.PROPERTY_RULE` already states for a gap, and the exit code
  stays with the rules that read the files.
- A test that reads the `.tf` set reads it as the gate reads it, keyed by the path from the
output directory, so
    a run that names two units is not read as one file. A plan check that runs writes a
`.terraform` cache inside
  the directory it ran on, so a pin that reads a corpus run uses a copy of it.
- A plan check reads the directory the plan runs on, so a validate pin runs `sanity_checks.check_terraform` once per
  unit directory the manifest record names, never at the codebase root, where no configuration file sits. A value the
  provider constrains in its code, not in the schema JSON, is not data the gate can read, so it stays outside the
  static rules and the plan check reports it (`docs/ARCHITECTURE.md` §4.6), and a fixture a plan pin reads states the
  accepted value.
- A field reader must read at the block's own level and stop at the closing quote, or a
  sub-block field or an escaped quote answers for the block's field. Both are pinned in
  `tests/test_import_blocks.py`, and the scope rule reads at the block's own level through the
  same reader, which takes the sub-block it reads as an argument (the action rule reads inside
  `config`). The same reader also tells a quoted value from a `var.` reference, so no second
  rule decides the shape of a field.
- `PROTOCOL_SHAPE` is the one table for the `protocol` object, `FILTER_SHAPE` is the one table for the filter
  containers, which sit outside it, and `CERTIFICATE_SHAPE` is the one table for the two certificate containers
  (F7.14). A level either table does not state is not read. A new routing level needs a table row before an
  emitter, a gate rule or a report can read it, and `SHAPE_TO_SCHEMA` is the one pin between a table word and the
  schema word for all three tables. A parse method states a path and never spells a field name:
  `_protocol_field_name` and `_protocol_xml_name` are the two rules; `XML_NAME_EXCEPTIONS` is the protocol table's
  exception map, and `FILTER_XML_NAME_EXCEPTIONS` is the filter table's map, keyed by the container path because
  one idea spells two ways in two containers. All three shape tables are the same row shape read as `resource_mapping.ShapeTable`,
  so the readers and the gate helpers take the table as an argument and state no table name in their finding
  wording, and one helper group (`_shape_level_findings`, `_shape_field_findings`, `_shape_choice_findings`) serves
  all three. A level the export holds as entries states its row as `string_list`, so the walk reads it as a `[`
  value and each element as an entry, which is the certificate profile's `certificate` row. `_parse_router` builds the `protocol` dict from the fields the `protocol` row states, and
  `parse_filter_containers` builds each entry dict from the fields its own row states, so the level names are the
  table's names in both. Field order is the table order, so the order a row states is the order the block
  prints, and a row change that moves the order moves the goldens. A level that holds no entry has no container row, so the property scan measures nothing
  for it and the matrix row stays grounded by the table. An entry inside an entry is not in the scan scope unless a
  row names the path with the `entry` segment the parent entry is: the certificate profile's list objects are that
  case, because the field the profile row names is also the spelling of the `certificate` section row, so the row
  that holds the `entry` segment wins by length and the profile row measures them. Every other entry inside an entry
  is grounded by the table instead.
  `_protocol_areas` is the area rule the two OSPF levels share, `_protocol_branch` walks the
  segments between a
    level dict and an entry level, `_protocol_entries` fills a `string_list` level, `_protocol_entry_level` (F7.10)
fills an entry level the row states as a field, because its entries live under the element the field names, and
  `_protocol_body` fills the
    three shapes a level dict cannot hold: the choice the export states by presence, the
  entries inside the level,
    and the entries inside an `object` field. An entry can hold its own choice, so
  `_protocol_body` takes the entry
    as the element that holds it, and it reads an entry as a direct child, so an entry inside
  an entry belongs to
    the level the field names. A presence choice states exactly one alternative, and the choice level is not
  required, so a level that states no choice element prints nothing for it while an element that states none is a
  report row. A choice level can state its alternatives as values, in which case `_protocol_choice` reads the
  value from the element the choice lives under and the print writes it as the reader read it. A `member_list`
  field is read by `_protocol_level`, because its members are values, so no level row stands under it and the
  walk never enters it: `sanity_checks.SHAPE_READS_AS` states which word the reader reads each specialization as,
  and `SHAPE_LEVELS` states which words name a level the walk enters. A parse method that reads a container
  reads only the level its own row states, which `entry_coverage.covering_row` decides. A row that states leaf
  fields only is the walk's stop point, so a field inside it is a gate finding: the redistribution entry's
  `match` and `set` rows are that case, and the six levels inside them are in `backlog.md`. A `sensitive` field
  cannot name itself, so `_protocol_fields` carries the name of the entry that holds the level: an entry names
  itself, and a level inside an entry prints the reference the entry that holds it names. F7.12: `selects` is the
  one place a row states a choice the provider reads as exactly one, so the level or the entry states one of the
  keys `selects` names, and the gate reads that rule at the level the walk enters and at each entry of a
  `string_list` row through `_shape_choice_findings`. The two rows that state it are `peer_address`, where the
  choice is the whole value, and the `ospfv3` auth profile entry, where the choice is two of the entry's fields.
  The three filter levels `terraform validate` refuses to hold more than one (`source_address`, `prefix`, and the
  redistribution entry's `bgp`) state their alternatives as fields and no `selects`, so the choice rule reads
  nothing for a filter block; that decision is in `backlog.md`.
- The parse method that takes the router element is named in the test helpers that call it for
each router:
    `tests/test_entry_coverage.py::_parse_every` and `tests/test_multi_vsys_location.py`. A new
  level method
  must be added there, or the corpus checks run no method for it.
- A container row that moves from `report` to `emitted` changes the property scan scope, the per-entry report,
  and the `.tf` goldens together, so it cannot be a print-only change. A moved row must be `emitted` with the
  provider type in its note, because the matrix row and the report both read the note. A row must also name the
  type the emitter prints for the entries in that container, so the matrix element names an entry inside the
  container the row names: a shape the emitter reaches through a name fact is not a container the row can
  state, and no entry measures such a row.
- `SCOPE_PLACEMENT` and the location sub-block are one fact: a new scope type needs both the
  placement key and the `SCOPE_ANSWER` entry, and the emitter reads the placement key as the
  location, so a new row cannot place itself in a scope it does not name. A config type has no
  `template_stack` sub-block, so a config entry inside a stack writes no block and is a finding
  recorded in `backlog.md`.
- The entry name is never a property. A row whose provider type declares no `name` reaches the
  block through `entry_coverage.name_field`; no emitter, gate rule, or test should state the
  field again.
- One place decides the shape of a value: `resource_mapping.VALUE_VARIABLES`, read at the print
  site. A new field a table row maps must be read by the emitter, the gate and the `.tfvars`
  writer through the same table, and the table must cover every field `LOCATION_SCHEMA`
  declares.
- The §5 naming rule lives in `naming.py`. No module may define a second one;
  `TerraformGenerator.sanitize_name` is a delegate and the data modules take the rule as an
  argument.
- One place decides the shape of a reference field: `TerraformGenerator.name_ref`, read at the
 print site.
    The mechanism for a name it cannot resolve is the plain name it returns, so a write path
  that runs the
  rule per unit changes the corpus pin lists, not the rule.
- The import position for the four `*_policy_rules` types must be the position the live config
    holds, and the F3.5 rulebase decision gates it. No block is written for a rule entry until
  both
  land.
- The generated `README.md` names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, and it
names
    `target` as a fact the tool names as a variable. It states no row, no value, no mapping
  result, no count,
  no path and no timestamp, so the report rule holds for the site record with the README as the
  file-inventory exception (`tests/test_site_data.py`).
- Actions need Terraform 1.14 or later; the committed goldens now declare it, so a change to
the
  minimum is a golden change.
- The credential rule has one statement and one owner document, `docs/CODEBASE_ASSEMBLY.md` §11, so every other
  document links to it. `source_fetch.py` is the only tool module that states the environment name, and the pin
  `tests/test_variables.py::test_the_generated_block_names_the_environment_the_fetch_layer_reads` holds both halves:
  the generated block names that name, and no other `src/` module states it. `VALUE_VARIABLES` decides the shape, so
  the host is an `operator_supplied` row and no name list decides a provider argument or a marking.
- The prune action reads the record file the run wrote, because the record directory is the output directory
  and `SOURCE.txt` is a codebase root-set file. `provenance.prune` decides through `prunable_entries` and
  builds no path, so no path rule for a record directory can appear in the module that owns the record. A state
  record references nothing, so it prunes nothing and protects nothing, and the action reads a record file, not
  one record. `--prune-cache` is an opt-in flag that gates the step; it names no part of the layout, so the
  no-flag scan holds, and it cannot change what the gate counts or the exit code the gate decides.
- One place answers a destination: `entry_coverage.EntryLedger.destination`, in the order the per-entry fact on
  the recorded object, the destination `mark` recorded, the container table row. `mark` states no destination of
  its own, so a call site that states `destination='report'` for a report-only entry restates a fact the entry
  already holds. The fact is read through `RecordingDict.value()`, so the decision records no property use and
  the order of `mark` and the field cannot change the answer; `mark_skipped` records no object, so a skipped
  entry answers through the mark. The cross-check counts only `emitted` rows, so an entry the run reports enters
  no count.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests
  run
  the pipeline in process. The round-trip cross-check reads the run's ledger as an argument, so its
  pins run the pipeline in process too, and a `run_checks` call that passes no ledger reports the check
  as NOT RUN rather than guessing a count.
- A cycle test needs two units that each declare a name the other one uses, because the rule
  resolves a
  name only inside the unit that declared it (`tests/fixtures/reference_cycle.xml`).
- The splitter (`src/split_device_groups.py`) reads the rules its owners state and defines none of its own: the
  single writer for the bytes of a split file, `naming.py` §5 for the file name, and the source line as the identity
  of an entry for its three tables. It owns its own output path, so it names no builder from `write_path.py`, and the
  writer scan reads the element-writer shape so no module can add a writer of its own. A file name two entries read
  to is a refusal, not a numbering, because a numbering depends on the order the entries appear in (§6). The shared
  merge dedupes the pair (path, name) at the level the path names, so an entry stays at its own path and one name at
  two depths is two entries.
- The LF rule is a byte rule, so the goldens and the no-change tests change with the write
  path. The rule is in
  the one write function, and `docs/ARCHITECTURE.md` §6 states it.

- Path 2 (Epic 8) adds `api_requests.py` and `api_to_terraform.py`, and both are read by the pins that
  scan the `src/` set: the writer scan, the environment-name scan, the console-line scan, and the
  second-naming-rule scan. So path 2 states no second rule of any kind, and each new path 2 rule names
  the module that holds it and the test that pins it. Its rules are in `docs/API_CONVERSION_PATH.md`.
