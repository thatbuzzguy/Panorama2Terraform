# Codebase Assembly (design record)

This is the design record for Epic 6 (`PLAN.md`). It states what a full Terraform
codebase needs and what the converter does not do yet. F6.1 is implemented, so its rules
name the module and the test that holds them. The rest of this document is not
implemented, so no test pins it. Every statement about the converter names the module or
the test that holds it. Provider facts come from the pinned provider (2.0.14) and are
listed in §12.

## 1. What a codebase is

The converter writes one output directory per run: the `.tf` files, the five report
files, `README.md`, `SOURCE.txt`, and the unit manifest `CODEBASE_MANIFEST.json` (§3).
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
| The reference rule | A name defined outside the run stays a plain string. The set of those names is the reference edge list between units (§6) | `ARCHITECTURE.md` §4.3 |
| The policy chain rule | Order inside a unit, and no rule depends on a rule in another unit, so the graph between units stays coarse | `ARCHITECTURE.md` §4.4 |
| The shadow scan | The naming-collision check between a parent scope and a child scope, which is the pre-flight check a codebase needs | `shadow_coverage.py`, `ARCHITECTURE.md` §3.2 |
| The state scan | The per-unit check that the code and the state agree, offline | `state_coverage.py`, `ARCHITECTURE.md` §3.2 |
| The api producer | One request per scope path and one cached entry per path, so a per-unit run reads one scope | `source_fetch.py`, `ARCHITECTURE.md` §3 |
| The gate, determinism, offline CI | A codebase gate that can run on every unit with no device access | `ARCHITECTURE.md` §4.6, §6 |

The gaps are §3 to §11.

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
   refusal, the way `provenance.parse_record` refuses a line that is not a field.
5. **One file per codebase run.** The edge list (§6) needs the whole set of units, and a reader
   cannot find a per-unit file before it knows the directory name, so one file holds one row per
   unit. `CODEBASE_MANIFEST.json` is written only when it has content, following the rule for the
   report files, and the CLI takes no flag for it.
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
the conversion report. Ownership (§4) and the edge list (§6) follow. The template stack is a
scope container (`container_coverage.SCOPE_CONTAINERS`), but it is not one of the four facts, so
no stack unit is named today; this is recorded in `backlog.md`.

## 4. Gap — ownership as data

Today the ownership fact is a report fact: `state_coverage.py` reports which entries
another workspace already owns. A codebase needs the ownership stated before the run, so
one unit owns one entry.

Rules needed:

1. An entry the export declares inside a unit belongs to that unit.
2. A name the export does not declare inside the unit is not owned by the unit, even
   when the unit uses it. `shadow_coverage.py` states the fact for the case where a
   child entry repeats a parent entry name.

The open decision is the override case. Panorama resolves a repeated name through
inheritance at commit time, so a repeated name is one object on the device and two
entries in the export. `panos_address` declares `disable_override`, and the parse
extracts it for an address but not for a service (`backlog.md`, F3.4). Until the rule
names the owner, two units can both claim the same object, and two states can both try
to change it.

## 5. Gap — the reference between units

For a name outside the run, the converter keeps a plain string
(`ARCHITECTURE.md` §4.3). A codebase needs that name to resolve at plan time, in one of
two ways:

1. A provider data source (F5.5): one `data` block per outside name. It resolves at
   plan, costs one API call per block, and fails at plan when the name does not exist,
   so a read-through run must be labelled in the generated `README.md`.
2. The state of another unit (a remote state data source, or a Terraform Cloud output).
   It costs no API call, but a unit must export outputs, and the generator writes no
   outputs today.

Decision needed: which one is the codebase rule. F5.5 chose the data block for a single
run (implemented, `ARCHITECTURE.md` §4.7), and that choice is the base for the codebase
rule. The remote state route needs a new rule for outputs, which the gate does not read
today.

A reference is also a dependency. A `data` block does not order two units, so the order
comes from §6.

## 6. Gap — order between units

Order inside a unit is pinned (`ARCHITECTURE.md` §4.1). Order between units comes from
three facts:

1. The parent device group before the child, because the shadow scan needs the parent
   read first (`ARCHITECTURE.md` §3.2).
2. The scope object before the config inside it, because a resource cannot be placed in
   a device group or a template that does not exist (§8).
3. The reference edges: unit A before unit B when B references a name A defines.

The generator already knows which names resolve inside the run and which do not, so the
edge list can come from data the parse holds. The tool can emit the edge list; it cannot
enforce the order, because enforcement is the platform's job (§13).

Rule needed: the edge graph must be acyclic. Two units that reference each other are a
finding, and a finding is an operator action, so it does not change the exit code
(`ARCHITECTURE.md` §4.6, and the F4.3 rule in `backlog.md`).

The rule that a policy chain never crosses a virtual system or a device group already
holds (`ARCHITECTURE.md` §4.4), so the graph is unit level only, never rule level.

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
3. The ownership assignment (§4), after the override decision.
4. The import blocks (§7). The single-unit case does not need the ownership rule, so this
   can land before §4. The rule types need the rulebase decision.
5. The scope objects (§8).
6. The site data layer (§9).
7. The commit action (§10), last, because it needs the gate rule for an action block and
   the Terraform minimum decision.

The smallest useful increment is one unit: one directory, one manifest row, one set of
import blocks, and a plan that shows zero change. A codebase is that shape repeated across
the declared scopes.
