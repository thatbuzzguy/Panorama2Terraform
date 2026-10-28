# Codebase Assembly (design record)

This is the design record for Epic 6 (`PLAN.md`). It states what a full Terraform
codebase needs and what the converter does not do yet. F6.1, F6.2 and F6.3 are
implemented, so their sections name the module and the test that holds them. The rest of
this document is not implemented, so no test pins it. Every statement about the converter
names the module or the test that holds it. Provider facts come from the pinned provider
(2.0.14) and are listed in §12.

## 1. What a codebase is

The converter writes one output directory per run: the `.tf` files, the five report
files, `README.md`, `SOURCE.txt`, the unit manifest `CODEBASE_MANIFEST.json` (§3), the
ownership record `OWNERSHIP.json` (§4), and the edge record `REFERENCE_EDGES.json` (§5).
A codebase is a set of directories that a platform plans and applies, one plan per
directory. Six facts define it:

1. A unit is one declared scope, as [`ARCHITECTURE.md`](ARCHITECTURE.md) §2.2 states
   the four scope facts: a device group, a template, a template stack, or a virtual
   system.
2. One unit owns each entry. A name a parent defines and a child inherits is owned by
   the parent.
3. One unit has one state, because one plan runs against one state.
4. A name another unit defines is a reference, not a value.
5. A unit that creates a scope writes the scope, or the platform creates it by hand.
6. Order between units comes from the references between them.

The codebase boundary and the state boundary are the same boundary: a unit is the
thing one plan can run.

A site unit is the device group and the template the export joins through one device
(the association rule, `ARCHITECTURE.md` §2.4, and
[DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md)). An HA pair is one unit,
because Panorama pushes one template to both members. The two serials are data, not
two units. The shared section and the parent device groups are one unit, because that
unit owns the definitions the child units reference.

## 2. What the converter already gives a codebase

These parts are true today, so a codebase can be built on them.

| Foundation | What it gives a codebase | Owner |
|---|---|---|
| Identity: (device group, vsys, type, name) | The key the state scan uses, and the same data a provider import id holds (§7) | `ARCHITECTURE.md` §2.1 |
| Local name: sanitized name plus the 8-hex identity digest | A resource address that does not move when a unit is regenerated, so a Git diff and an import block stay stable across runs | `ARCHITECTURE.md` §5 and §6 |
| The reference rule | A name defined outside the run stays a plain string. The set of those names is the reference edge list between units (§5) | `ARCHITECTURE.md` §4.3, §5 |
| The policy chain rule | Order inside a unit, and no rule depends on a rule in another unit, so the graph between units stays coarse | `ARCHITECTURE.md` §4.4 |
| The shadow scan | The naming-collision check between a parent scope and a child scope, which is the pre-flight check a codebase needs | `shadow_coverage.py`, `ARCHITECTURE.md` §3.2 |
| The ownership record | The unit that owns a name, so one plan holds one entry and an override resolves through its owner | `ownership.py`, §4 |
| The state scan | The per-unit check that the code and the state agree, offline | `state_coverage.py`, `ARCHITECTURE.md` §3.2 |
| The api producer | One request per scope path and one cached entry per path, so a per-unit run reads one scope | `source_fetch.py`, `ARCHITECTURE.md` §3 |
| The gate, determinism, offline CI | A codebase gate that can run on every unit with no device access | `ARCHITECTURE.md` §4.6, §6 |

§3, §4 and §5 are landed, and §6 is landed for the order data it can state. The gaps are
§7 to §11.

## 3. The unit boundary as data (F6.1, landed)

The converter has no unit directory. `main()` reads one source and writes one output
directory. F6.1 states the unit boundary as data: one row per declared scope in
`CODEBASE_MANIFEST.json`. The rules are in `unit_manifest.py`, and `main()` writes the file.

1. **The unit.** One unit is one combination of the four scope facts (§1 rule 1,
   `ARCHITECTURE.md` §2.2). A unit exists when the ledger has a report row in it, so the
   manifest is built from `entry_coverage.EntryLedger` and adds no parse data. An entry inside
   a config-object entry is a property level (`ARCHITECTURE.md` §3.1), so the parent row's
   count covers it.
2. **The unit name.** The deepest scope the export declares names the unit, in the F3.9 level
   order. `Shared` names the unit whose four facts are empty, because the four facts alone
   cannot name the shared section. `localhost.localdomain` names no firewall (F3.5), so the
   placeholder never names a unit, and `Shared` in `device_group` is the parse fallback (§2.2),
   so it never enters an identity.
3. **The directory name.** `sanitize(unit name) + '_' + 8-hex digest of the unit identity`, in
   the `ARCHITECTURE.md` §5 shape, and the digest is always present. A collision-only rule
   would make one unit's name depend on the other units in the run, so an unrelated scope would
   move an existing directory. The module takes the §5 rule as an argument, so no second naming
   rule exists. Pinned by
   `tests/test_unit_manifest.py::test_the_directory_name_is_the_sanitized_name_plus_the_digest`,
   `::test_the_manifest_defines_no_second_sanitize_or_naming_rule`,
   `::test_a_name_that_sanitizes_to_nothing_keeps_the_shape`, and
   `::test_a_directory_name_does_not_move_when_an_unrelated_unit_is_added`.
4. **The row shape.** The row is data, so a document describes its fields and never restates a
   row (the `docs/README.md` rule). Fields print in the declared order, the rows sort by the
   identity, the reference names are sorted, and no field states a timestamp or a path.
   `parse_rows` reads a written file back, and a row that is not the declared shape is a
   refusal, the way `provenance.parse_record` refuses a line that is not a field. The two order
   fields `rank` and `after` print after the F6.1 fields (§6 rule 1).
5. **One file per codebase run.** The edge list (§5) needs the whole set of units, and a reader
   cannot find a per-unit file before it knows the directory name, so one file holds one row per
   unit. `CODEBASE_MANIFEST.json` is written only when it has content, following the rule for the
   report files, and the CLI takes no flag for it. The three data files are the manifest (one row
   per unit), the ownership record (one row per entry), and the edge record (one row per pair), so
   no file states the unit set twice, which is why the order lives on the manifest row.
6. **The reference names.** The reference rule records them (`ARCHITECTURE.md` §4.3), keyed by
   the referrer's four scope facts, so a row states the names a unit references from outside
   itself. This module resolves no name.

The manifest names the directory; F6.1 writes no directory. A data file cannot change an
existing output byte, so the `.tf` goldens, the report bodies, the gate inputs, and the exit
codes are unchanged. Pinned by `tests/test_unit_manifest.py`, including
`::test_one_row_per_combination_of_the_four_facts`,
`::test_the_rows_are_sorted_by_the_identity_not_by_document_order`,
`::test_the_manifest_round_trips_as_data`,
`::test_a_row_that_is_not_the_declared_shape_is_refused`,
`::test_the_reference_names_are_recorded_for_the_referrers_facts`,
`::test_the_gate_reads_no_data_file`, and `::test_two_runs_write_the_same_bytes`.

The decision this section asked for is settled: the manifest is a data file, not a section of
the conversion report. §4 is landed; the edge list (§5) follows. The template stack is a
scope container (`container_coverage.SCOPE_CONTAINERS`), but it is not one of the four facts, so
no stack unit is named today; this is recorded in `backlog.md`.

## 4. Ownership as data (F6.2, landed)

The converter now states the ownership fact as data: `OWNERSHIP.json`, one row per entry the
coverage matrix covers. `state_coverage.py` still reports which entries another workspace already
owns; that is a state fact, not this fact. The rules are in `ownership.py`, and `main()` writes the
file.

1. **The declaring unit, and no second naming rule.** An entry the export declares inside a unit
   belongs to that unit (§1 rule 2). The row names the unit by its directory, so `OWNERSHIP.json`
   and `CODEBASE_MANIFEST.json` join on `directory`. The identity is `state_coverage.ownership_key`
   read through `unit_manifest.facts_of`, and the module takes `TerraformGenerator.sanitize_name` as
   an argument, the way `unit_manifest.build_rows` does.
2. **A name a unit uses but does not declare is not owned by that unit.** A member list, a
   reference string, and a reference pointer (`<entry>` with only `<id>`) hold a name without
   declaring an object, so they write no row. `ARCHITECTURE.md` §4.3 stays the only place that names
   a use.
3. **The row scope is the F4.4 rule, read through the report row**, so the scan adds no second
   scope rule: an entry a matrix row covers whose destination writes an object. A property level, a
   skipped entry, and a report-only entry write no row.
4. **Two entries are one object only when the export can place them in one inheritance chain:** the
   shared unit, and the units whose declared fact is a device group. A name in a template, a virtual
   system, or a device is a different object in each unit (`ARCHITECTURE.md` §2.1), so each unit
   owns its own entry.
5. **The owner is the ancestor entry** (§1 rule 2). The export states the relation in two cases
   only: the shared unit, and the parent source the run declares with `--parent` (the F5.4 rule).
   The device-group `parent` field is not captured (the bookkeeping gap in `backlog.md`), so the
   rule cannot name an ancestor for two device groups in one source.
6. **`disable_override` does not choose the owner.** It names the entry no descendant may override,
   so a second entry with the same name contradicts the flag and is an operator decision. The value
   is the string the parse read, and the row states `unknown` for a matrix row that does not name the
   property (`backlog.md`), and for a declared parent source, which the run reads as entry names and not
   as objects.
7. **What the rule can say per entry** is `kind`: `declared`, `definition`, `override`, `ambiguous`.
   The case the rule cannot decide is a report finding, in its own section after the shadow section
   and before the state sections. A finding is an operator action, so it does not change the exit
   code, which the F4.1 gate decides, and the console prints no ownership line.

Pinned by `tests/test_ownership.py`, including
`::test_one_row_per_entry_the_matrix_row_covers`,
`::test_a_name_a_unit_uses_but_does_not_declare_writes_no_row`,
`::test_the_ancestor_entry_owns_the_name`,
`::test_two_device_groups_have_no_stated_relation`,
`::test_a_name_in_two_units_that_cannot_be_one_chain_is_two_objects`,
`::test_the_declared_parent_source_is_the_ancestor`,
`::test_the_flag_on_the_definition_makes_the_repeat_a_finding`,
`::test_the_flag_on_a_descendant_names_no_owner`,
`::test_the_findings_are_grouped_by_the_f3_9_scope_rule`, and
`::test_a_finding_does_not_change_the_exit_code_and_the_console_prints_no_line`.

The decision this section asked for is settled. The service leg is closed: the parse captures
`disable-override` for a service entry and the emitter prints it, so the `panos_service` matrix row
names the property
(`tests/test_ownership.py::test_the_service_row_names_the_property_the_emitter_reads`). The edge list
(§5) is the next gap, and it now has the owner fact to build on.

## 5. The reference between units as data (F6.3, landed)

The converter now states the pair as data: `REFERENCE_EDGES.json`, one row per edge. The rules are
in `reference_edges.py`, and `main()` writes the file.

1. **The edge set is the names the reference rule recorded** (`TerraformGenerator.name_ref`,
   `ARCHITECTURE.md` §4.3), so the module records no name and resolves no name. A name the rule
   resolved inside the run is a reference inside one root, not an edge between units, so it writes
   no row. A name no unit in the run declares writes no row either: the pair does not exist, and
   that name is already stated in the manifest's `references` field, the only place that states a
   reference name.
2. **The target unit is the owner**, the `owner` field of the ownership row for (`type`, `entry`),
   not the declaring unit (§4 rule 5). A name several units declare as separate objects gives one
   row per owner, which is the ambiguous-device case in `ARCHITECTURE.md` §4.3 rule 1.
3. **Self-reference exclusion.** A row whose target is the referrer writes no row, because an edge
   is a fact between two units and a unit cannot come before itself. The same rule keeps a unit out
   of its own `after` (§6 rule 3).
4. **The row shape, and the join.** `referrer` and `target` name units by their directory, so the
   row joins to `CODEBASE_MANIFEST.json` on `directory` and to `OWNERSHIP.json` on (`type`,
   `entry`). Fields print in the declared order, rows sort by the four fields in field order, one
   row per pair, no timestamp and no path. `parse_rows` reads a written file back and refuses a row
   that is not the declared shape, including a row that names one unit instead of two. The module
   defines no naming rule and no identity key: it takes `TerraformGenerator.sanitize_name` as an
   argument, the way `unit_manifest.build_rows` and `ownership.build_rows` do.

| Field | Value |
|---|---|
| `referrer` | the unit that uses the name, by its directory |
| `target` | the unit that owns the name, by its directory |
| `type` | the coverage matrix row that covers the target entry |
| `entry` | the reference name |

5. **The mechanism that resolves a name is not data here.** A name outside the run resolves through
   the `data` block, which is the codebase rule F5.5 chose (`ARCHITECTURE.md` §4.7), and the gate
   rule `data_blocks` reads it. A name another unit in the run owns cannot resolve through a `data`
   block, because that unit declares the entry in its own root and one plan runs against one state
   (§1 rule 3): the mechanism must be that unit's outputs, and the generator writes no outputs. The
   outputs rule stays open in `backlog.md`. A plain run writes the same `.tf` bytes as before,
   because the module writes no `.tf` byte.
6. **The reference fact stays one fact.** `name_ref` records one fact: the name resolved outside the
   run. It is not split into two kinds, because the edge row states the other unit when the
   ownership rule can name one, and the two cases are told apart by whether an edge row exists. A
   name the flat index resolves is not an edge: its split across unit directories is the write path
   and the import-block decision (§7), which is recorded in `backlog.md`.

The decision this section asked for is settled: the edge list is a data file, not a report section,
and it is written only when it has content. `tests/test_reference_edges.py` pins it, including
`::test_the_record_is_one_row_per_edge_the_data_can_name`,
`::test_the_row_joins_to_the_manifest_and_to_the_ownership_record`,
`::test_a_name_no_unit_declares_writes_no_row_and_stays_in_the_manifest`,
`::test_the_module_resolves_no_name_and_records_no_name`,
`::test_a_self_reference_writes_no_row`, and `::test_the_golden_tf_bytes_are_unchanged`.

The acyclic rule, which this section asked for, is §6.

## 6. The unit order as data (F6.3, landed)

Order inside a unit is pinned (`ARCHITECTURE.md` §4.1). Order between units is now data on the
manifest row, because the manifest is the file that names each unit (§3 rule 5).

1. **The two fields.** `after` names the units a unit must be planned after, by their directory,
   sorted; `rank` is its position in the order, from 1, and 0 for a unit that cannot be ordered.
   `unit_manifest.py` states the row shape; `reference_edges.order` fills the two fields, because
   the order comes from the rules this section states.
2. **The three bases**, each read through the module that holds the fact, so no second rule appears:
   - **the parent before the child**: the owner unit before the unit that carries an override of a
     name it owns (§4 rule 5), which is also the fact the shadow scan reads in read order
     (`ARCHITECTURE.md` §3.2);
   - **the shallower scope before the deeper scope inside it** (§1 rule 6, and §8 for the scope
     object a resource needs): the device group unit before the template unit inside it, before the
     device unit inside it, in the F3.9 level order. A container the manifest does not name adds no
     dependency, and a declared parent source names no unit, because a unit exists when the run's
     ledger has a row in it;
   - **the reference edge**: the target unit before the referrer unit.
3. **Ties, and the acyclic rule.** A unit with no dependency is ranked in the identity order, which
   is the order the manifest rows already print, so `rank` is deterministic. A cycle is a finding:
   two units that reference each other cannot be put in a plan order. A finding is an operator
   action, so it does not change the exit code, which the F4.1 gate decides, and the console prints
   no cycle line. The report prints one line per cycle in its own section, after the repeated-names
   section and before the state sections, grouped by the F3.9 rule, and a cycle is read from its
   smallest unit so one cycle is reported once. A unit in a cycle keeps `rank` 0, and the section
   names it.
4. **The graph is unit level only**, never rule level, because the rule that a policy chain never
   crosses a virtual system or a device group already holds (`ARCHITECTURE.md` §4.4).
5. **The tool emits the order; it cannot enforce it** (§13). The platform plans in the order the
   data states.

Pinned by `tests/test_reference_edges.py`, including
`::test_the_cycle_fixture_produces_two_edges_and_one_finding`,
`::test_no_corpus_fixture_produces_a_cycle_finding`,
`::test_a_unit_in_a_cycle_states_no_rank`,
`::test_the_parent_unit_comes_before_the_unit_that_overrides_its_name`,
`::test_the_shallower_scope_comes_before_the_deeper_scope_inside_it`,
`::test_the_edge_target_comes_before_the_referrer`,
`::test_a_declared_parent_source_adds_no_dependency`,
`::test_the_gate_reads_no_data_file_and_check_order_is_unchanged`, and
`::test_two_runs_write_the_same_bytes`. `tests/fixtures/reference_cycle.xml` is the fixture that
pins a cycle; no other fixture in the corpus produces one.

## 7. Gap — binding the codebase to the live config

The provider import id is the base64 JSON of the location plus the name, verified in
§12. The generator already writes the same location block, and the local name is already
stable across runs (`ARCHITECTURE.md` §5, §6), so an import block can come from the same
data as the resource block. The tool can write one `imports.tf` per unit with no new
identity data.

Rules needed:

1. An import block must agree with the resource block it names: the same type, the same
   local name, and the same location. The gate reads resource blocks only
   (`ARCHITECTURE.md` §4.6), so this is a new gate rule.
2. For the four `*_policy_rules` types, the import object names the rulebase, the
   position, and a list of names (§12). The position must be the position the live
   config holds, not the create-time position the generator emits: the first rule of a
   chain anchors at `where = "last"` (`ARCHITECTURE.md` §4.4), which is not the position
   of a rule that already exists. So a rule import block needs the position the export
   states, and the rulebase decision in `backlog.md` (F3.5) gates it.
3. The first plan for a unit should read `N to import, 0 to add, 0 to change,
   0 to destroy`. That holds only for entries the parse models. The per-entry report
   (`ARCHITECTURE.md` §3.2) names the entries that cannot reach zero change, and the
   property gaps in `backlog.md` are the list of what can make a plan show a change. The
   state scan (F5.6) is the offline check for the zero-change half.

## 8. Gap — the scope objects

The pinned schema has a resource for each scope a codebase needs:
`panos_device_group`, `panos_device_group_parent`, `panos_template`,
`panos_template_stack`, `panos_template_variable`, `panos_vsys` (§12). The container
table marks `parse_device_groups` and `parse_associations` as `bookkeeping` rows, so no
scope is emitted, and a new site cannot be created by an apply.

Rule needed: emit the scope objects, or state that the platform creates them by hand. A
codebase that creates a new site must emit them. This needs new `EMITTED_TYPES` entries,
new coverage matrix rows, and an emitter, all written from the schema, not from memory
(`resource_mapping.py` rule).

`panos_template_variable` is the provider shape for the template variables a codebase
wants as Terraform variables. The export holds the defaults, so a generated module
cannot take a template variable as a `var.` value until the value-to-variable mapping is
data (§9).

## 9. Gap — the site data layer and the device name

A codebase separates the standard from the site. The tool writes values inline, so a
site change is a code change.

Rules needed:

1. The device name comes from a variable, not a literal.
   `tests/golden/kitchen_sink/zones.tf` writes `ngfw_device = "fw-2.example.com"` as a
   literal. When hardware is replaced, the serial changes, and a literal changes every
   resource in that template. A variable reference keeps the change to one line. The
   provider's `target` argument names one NGFW serial (§12), so a unit that owns one
   firewall needs it as a variable too.
2. One data file per site, and the tool writes the `.tfvars` for it. The format stays
   JSON, because the project keeps the standard library only (`backlog.md`, F5.2); YAML
   needs a third-party package.
3. The value-to-variable mapping is a table, so it must be data and pinned the way
   `LOCATION_SCHEMA` is. Today the mapping is a choice inside each emitter.

The tool cannot derive a module from an export: a module is a standard a person writes.
The tool can write the data file a module consumes. The gate rule that every declared
variable has a `var.` consumer (`ARCHITECTURE.md` §4.6) already stops a generated file
from declaring a variable it does not use.

## 10. Gap — commit and push

The pinned schema declares two actions: `panos_commit` and `panos_push_to_devices`
(§12). `panos_commit` can commit one device group, one template, or one template stack,
so a commit can stay inside one unit. The provider does not commit as part of a resource
change: the commit is out of band (the provider docs state that Terraform has no native
commit support), so an action block or an outside step is the commit path.

Rules needed:

1. One action block per unit, and no action that names a scope another unit owns.
2. The gate reads resource blocks only (`ARCHITECTURE.md` §4.6), so an `action` block is
   not checked today. A codebase that emits actions needs a gate rule that reads them.
3. Actions need Terraform 1.14 or later (§12), which is newer than the provider's own
   minimum. The committed goldens declare no Terraform minimum, so a codebase that emits
   actions needs one.

## 11. Gap — credentials and the provider block

`generate_variables` declares `panos_hostname`, `panos_username`, and
`panos_password`, and `generate_provider_config` uses them. The fetch rule
(`ARCHITECTURE.md` §3) is: the key comes from the environment only and never reaches a
generated file. A codebase should use the same rule for the provider: the host per unit
as a variable, the key through `TF_VAR_PANOS_API_KEY`, and no credential literal in a
generated file.

Decision needed: keep the generated username/password provider block as an operator
template, or make the generated provider block read the key. One rule, stated once, must
cover both the fetch layer and the generated provider block.

## 12. Provider facts, verified 2026-10-27

Measured against provider 2.0.14 through `terraform providers schema -json`, and the
provider docs:

- 128 resource schemas and 128 data source schemas, and 2 action schemas:
  `panos_commit` and `panos_push_to_devices`.
- No resource registers a device, defines an HA pair, sets a management interface, or
  holds an auth key. The provider can name a device (`location.ngfw_device`,
  `panos_device_group.devices`) and nothing else about a device. So the Day 1 bootstrap
  (serial registration, HA grouping, management IP, DNS and NTP, admin account) stays
  outside the codebase. This is a forced boundary, not a preference.
- A resource exists for each scope: `panos_device_group` (`parent`, `devices`,
  `templates`), `panos_device_group_parent`, `panos_template` (`default_vsys`),
  `panos_template_stack` (`devices`, `templates`), `panos_template_variable`, and
  `panos_vsys`.
- The import id is base64 JSON of the location plus the name. For the four
  `*_policy_rules` types the import object names the rulebase, the position, and a list
  of names. No resource schema declares an `id` attribute, so the import id is the
  encoded object, not a stored attribute.
- Actions need Terraform 1.14 or later. The provider needs Terraform 1.8 or later.
- Provider arguments include `api_key` (environment `PANOS_API_KEY`) and `target` (one
  NGFW serial), and the local inspection mode (`config_file`, `panos_version`), which
  reads a config file with no server. No rule in this project uses local inspection mode,
  and a plan in that mode cannot show drift, so it is not a replacement for the state
  scan.

## 13. The tool and the platform boundary

The tool stays a generator. It writes data an orchestrator reads: the manifest, the edge
list, the import blocks, and the `.tfvars`. It runs no plan, no apply, and no commit, and
it manages no secrets. The orchestrator (Terragrunt, Terraform Cloud, GitHub) is the
platform, and the platform is not this repository's job. This keeps the rules the project
already holds: standard library only, no network in a test, no credential in a generated
file, and a run with no network passes CI.

## 14. What it would take, in order

1. F5.5, because the reference mechanism decides itself: the data block is the first
   mechanism a codebase can use, and the gate rule for a `data` block is the gate rule
   the codebase needs.
2. The unit manifest (§3), because ownership, edges, and import blocks all need the unit.
   No new parse data is needed. Landed as F6.1.
3. The ownership assignment (§4), after the override decision. Landed as F6.2.
4. The reference edge list (§5) and the unit order (§6), because both need the unit and the owner.
   Landed as F6.3. The outputs rule for a name another unit owns is still open in `backlog.md`.
5. The import blocks (§7). The single-unit case does not need the ownership rule. The rule types need
   the rulebase decision.
5. The scope objects (§8).
6. The site data layer (§9).
7. The commit action (§10), last, because it needs the gate rule for an action block and
   the Terraform minimum decision.

The smallest useful increment is one unit: one directory, one manifest row, one set of
import blocks, and a plan that shows zero change. A codebase is that shape repeated across
the declared scopes.
