# Usage Guide

This is the technical reference for the two scripts. It states how to run them
and what each output file holds. The rules behind the output are in
[ARCHITECTURE.md](ARCHITECTURE.md); the document index is in
[README.md](README.md).

## What the tool does

The converter reads a Panorama XML configuration export and writes Terraform
configuration for the `PaloAltoNetworks/panos` provider v2 (pinned
`~> 2.0.14`). It also writes reports for configuration that has no v2
resource, so nothing is dropped silently.

The tool is a local file converter. By default it connects to no server, runs no
command, and needs no credentials. Reading from the Panorama API is an explicit
choice (`--source api`), and a run that reads only the cache (`--offline`) needs no
key and connects to no server.

## Requirements

- Python 3.9 or later. Standard library only.
- Terraform 1.0 or later, only for the optional `--validate` check.
- A Panorama XML export.

No installation step. Run the script from the repository. The API source needs no
package: it uses `urllib`, so the https rules below are the tool's own.

## Running the converter

```bash
python3 panorama_to_terraform.py export.xml --output-dir out
```

| Argument | Meaning |
|---|---|
| `input_file` | Panorama XML export. Optional with `--source api` |
| `--source file\|api` | Where the input comes from. Default `file` |
| `--host HOST` | Panorama host for `--source api`. Required with `--source api` |
| `--cache-dir DIR` | Where fetched responses are kept. Default `panorama_cache` |
| `--path /PATH` | Scope path for `--source api`: read one scope instead of the whole config, as `/<container>` or `/<container>/entry/<name>`. The first segment must name a scope container |
| `--parent /PATH` | Parent scope path for `--source api`, read as the second source for the shadow scan. Needs `--path` |
| `--offline` | Read the cache only: no request, no key |
| `--insecure` | Skip certificate verification. Explicit choice, api source only |
| `--state PATH` | Terraform state document read as a reference source (F5.6). Applies to any source kind |
| `--workspace NAME` | The workspace the state document belongs to, so the record names it. Needs `--state` |
| `--data-blocks SCOPE` | A reference scope this run may read through, as a provider data source type. Repeatable, or a comma-separated list. Off by default (F5.5) |
| `--import-blocks` | Write one `import` block per entry the run declares, in `imports.tf`. Off by default (F6.4) |
| `--output-dir DIR` | Output directory. Default `terraform_output` |
| `--max-input-bytes N` | Refuse an input larger than N. Default 67,108,864 (64 MiB) |
| `--validate` | Add the `terraform init` + `terraform validate` check to the post-run gate |

The input check runs before the read allocates and before any file is written.
The tool refuses a DTD, which is the only path an entity expansion or an
external entity takes, and a Panorama export carries none. A refusal names the
file, the limit and the measured size, exits non-zero, and writes nothing.
Raise the size limit only for a trusted file. A fetched response runs the same
checks through the same boundary, and a refusal is written to no cache entry.

### Reading from the API

```bash
export PANOS_API_KEY=...
python3 panorama_to_terraform.py --source api --host panorama --output-dir out
python3 panorama_to_terraform.py --source api --host panorama --offline --output-dir out
python3 panorama_to_terraform.py --source api --host panorama --path /device-group/entry/Production-DG \
  --parent /shared --output-dir out
```

- The key is read from `PANOS_API_KEY`. It is never taken from a command line, so it
  does not appear in a shell history or in a process list, and it never appears in an
  output file or in a cache entry name.
- The request is https only. A redirect that changes the scheme is refused, because
  following it would send the key over a plain connection.
- Each response is stored in `--cache-dir` under the SHA-256 hex of the host and the
  sorted request parameters. The same request finds the same entry, so a repeat run reads
  the cache and sends no request. `--offline` reads the cache only and refuses an entry
  that is not there.
- A stored response is the bytes the parser read, so the report lines name the lines of
  that file. The report names the cache entry as the source, and `SOURCE.txt` records the
  request identity and the entry the run read.
- `--path` reads one scope instead of the whole config, and `--parent` reads the parent scope as
  the second source. Both apply to `--source api` only, and `--parent` needs `--path`: a
  whole-config source holds its own parent, so the tool does not guess which scope a file run
  holds. A path must be `/<container>` or `/<container>/entry/<name>`, and its first segment must
  name a scope container; anything else is an argument error (exit 2). Each scope is its own cache
  entry, because the path is part of the request identity, and `--offline` covers both requests.
- The second source is what the shadow scan reads. A run that reads one device group cannot see the
  parent it inherits from, so an inherited name stays a string. The report lists a child entry whose
  name repeats a parent entry name within the same coverage matrix row, in the shadow section of
  `CONVERSION_REPORT.txt`, with the parent source and the parent line. The section prints only when
  it has a finding, and a finding is an operator action: it does not change the exit code.
- An API response is an envelope (`response/result/config`). The converter reads the
  `config` element inside it, so the conversion is the same as for an export file.

### Reading a state document

```bash
python3 panorama_to_terraform.py export.xml --state production.tfstate --workspace production --output-dir out
```

- The state document is a reference source: the run reads it for two facts and writes no output from
  it, so the generated `.tf` files are unchanged. It applies to `--source file` and `--source api`
  alike, and `--workspace` needs `--state` (exit 2). A state read is a file read, so `--offline` still
  covers the api producer only and no test opens a connection.
- The ownership section lists a run entry the state document already owns. The key is the entry
  identity (matrix row, entry name, and the four declared scope facts) read from the `location` block
  the state holds, so the same name in a different scope is a different object.
- The drift section lists an owned entry with a value this run does not match. Only a property the
  coverage matrix row declares is compared, and only when both sides hold it by the same name, so the
  parse key `tags` and the provider attribute `tag` are not compared. Values print as JSON text, and
  member order is part of the value.
- Both sections print in `CONVERSION_REPORT.txt` after the shadow section, in the order ownership then
  drift, and each prints only when it has a finding. The line names the run entry's source line and
  the state entry's resource address, because a state entry has no source line of its own. Both facts
  are operator actions: the console prints no state line and neither changes the exit code.
- The state document is refused when the bytes are not JSON, when the document is not one object with a
  `resources` array, when a `resources` item is not an object, or when a resource names no `type` or no
  `name`, because the identity key cannot read it. A refusal names the file, exits 1, and writes no
  record. A state document larger than `--max-input-bytes` is refused before the read.
- `SOURCE.txt` records the state source last, in read order, with `-` for the two request fields: it
  references no cache entry, so it prunes nothing.

### Read-through data blocks (opt-in)

```bash
python3 panorama_to_terraform.py export.xml --data-blocks panos_address,panos_zone --output-dir out
```

- Off by default. A run that declares no read-through scope keeps the plain-string rule, so the
  generated `.tf` files and the `README.md` are unchanged.
- `--data-blocks` names a scope the reference rule resolves against, and its provider data source
  must declare `name`. An empty value, a scope outside the reference sets, or a no-name scope is an
  argument error (exit 2).
- A reference that resolves inside the run stays a `.name` reference to the resource. Only a name the
  run cannot resolve becomes one `data` block, one per identity (type, context, vsys, name), in
  `read_through.tf`. The block holds the type, the local name, `name`, and the `location` the
  referrer's identity states, and nothing else.
- Read the file as a plan-time read, not as a stored fact: `terraform plan` asks the device for each
  block, and the plan fails when the entry is not present in the location the block names.
  `terraform validate` cannot check it.
- Every name outside the run becomes a block, including a built-in such as `any`, because no verified
  built-in name table exists. The generated `README.md` labels the run with the declared scopes and
  the block count for that reason.

### Import blocks (opt-in)

```bash
python3 panorama_to_terraform.py export.xml --import-blocks --output-dir out
```

- Off by default. A run that does not declare it writes no `imports.tf`, so the generated `.tf` files
  are unchanged.
- One `import` block per entry the run declares, in one file for the run, in unit order then local-name
  order. Each block states `to` (the block address) and `id` (base64 of the location object plus the
  entry name, the provider shape).
- The block and the id state one fact: the location comes from the same rule the resource block renders
  from, and the local name comes from the same naming rule. `panorama_device` is not stated, because the
  generator emits no device fact.
- A gate rule reads the file (`import_blocks`, §4.6 of [ARCHITECTURE.md](ARCHITECTURE.md)): a block must
  agree with the resource block it names. A wrong type, a wrong local name, a wrong location, or a wrong
  name is a FAIL finding, so the run exits 1.
- The four `*_policy_rules` types write no block, because their import object names the rulebase, the
  position in the live rulebase, and a list of names. Each rule entry is a WARN finding with that reason,
  and a WARN does not change the exit code.

## Quick start script

`quick_start.sh` runs the converter on the committed sample export
(`sample_panorama_config.xml`) and prints the next steps. It is a demonstration,
not part of the converter. It adds `--validate` when the terraform binary is
present, so the gate runs the terraform check when it can.

## Running the splitter

The splitter is optional pre-processing. It writes one XML file per device
group.

```bash
python3 split_device_groups.py export.xml --output-dir split_output
```

| Argument | Meaning |
|---|---|
| `input_file` | Panorama XML export |
| `--output-dir DIR`, `-o DIR` | Output directory. Default `split_configs` inside the input file's directory |
| `--max-input-bytes N` | The same input check as the converter |

How the splitter joins a device group to a template is in
[DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md). The splitter writes XML,
so it has no `.tf` output and no gate run.

## Output files

The converter writes a file only when it has content.

| File | Content |
|---|---|
| `provider.tf` | Provider block, wired to the three credential variables |
| `variables.tf` | The three credential variables (`panos_hostname`, `panos_username`, `panos_password`) plus the site variables the run printed (F6.6). Written after the emitters, so it declares only what the run consumed |
| `scope.tf` | The six scope objects the export declares: device group, the device-group parent record, template, template stack, template variable, and virtual system. Written by every run that has a scope entry, before the object files, in the F3.9 level order (F6.5) |
| `address_objects.tf`, `address_groups.tf`, `service_objects.tf`, `service_groups.tf`, `tags.tf`, `custom_url_categories.tf`, `application_groups.tf`, `external_lists.tf` | Object resources |
| `security_rules.tf`, `nat_rules.tf`, `decryption_rules.tf`, `pbf_rules.tf` | Policy rules, one resource per rule, chained in XML order |
| `security_profile_groups.tf` | Profile group resources |
| `security_profiles.tf` | Inventory only: names and descriptions, with the resource name the emitter would use |
| `interfaces.tf`, `zones.tf`, `virtual_routers.tf`, `monitor_profiles.tf`, `vpn.tf` | Network and VPN resources |
| `read_through.tf` | One `data` block per name a reference needed and the run did not read. Written only for a run that declares `--data-blocks` (F5.5) |
| `imports.tf` | One `import` block per entry the run declares, as `to` and `id`: the block address, and base64 of the location object plus the entry name. Written only for a run that declares `--import-blocks` and has a block to write (F6.4) |
| `README.md` | Deployment steps for the generated directory |
| `SOURCE.txt` | One record per source the run read, as `field: value` data: kind, name, path, scope, request, cache_entry, size, and the SHA-256 hex of the parsed bytes |
| `MANUAL_SETUP_REPORT.txt` | Report-only configuration, plus a section for a container no parse method reads |
| `INTERFACE_MIGRATION_REPORT.txt` | Interface and IP inventory |
| `VPN_MIGRATION_REPORT.txt` | VPN inventory and the pre-shared key actions |
| `CONVERSION_REPORT.txt` | One line per entry the parse read, plus the gap section, the property section, the shadow section for a run that declares a parent source, the repeated-name section for a name the ownership rule cannot decide, the reference-cycle section for two units that reference each other, and the state ownership and drift sections for a run that declares a state source |
| `SANITY_REPORT.txt` | The post-run gate result |
| `CODEBASE_MANIFEST.json` | One row per unit (one declared scope), as data: the four scope facts, the directory name, the entry count, and the names the unit references from outside itself. Written only when it has content (F6.1) |
| `OWNERSHIP.json` | One row per entry the coverage matrix covers, as data: the matrix row, the entry name, the source, the four scope facts, the declaring unit's directory, the owning unit's directory, what the rule can say about the entry, and the `disable_override` flag as the parse read it. Written only when it has content (F6.2) |
| `REFERENCE_EDGES.json` | One row per reference pair, as data: the referrer unit, the target unit, the matrix row, and the entry name. Written only when it has content (F6.3) |
| `SITE_DATA.json` | One row per site that names a value, as data: the unit directory and the variable names with their values. Written only when it has content (F6.6) |
| `site.auto.tfvars` | The `.tfvars` written from the site data rows, one line per variable in name order (F6.6). Terraform loads a `*.auto.tfvars` file automatically, so `terraform.tfvars` stays the operator's own file for the credentials |

The interface report, the VPN report, and the conversion report share one grouping
rule: one section per scope the export declares (device group, then the template or
the device), and the shared section is named `Shared`. The rule is in
[ARCHITECTURE.md](ARCHITECTURE.md) §4.5. The manual report is organised by object
kind instead, so it does not name the scope on each line; that is recorded in
[`../backlog.md`](../backlog.md).

`SANITY_REPORT.txt` is written on every run, by the gate, not only when it has a
finding. `SOURCE.txt` is written on every completed run, because a run always reads a
source. The other reports are written only when they have content.

### The provenance record

`SOURCE.txt` is one record per source the run read, in read order, separated by one blank line,
written as data: the main source, then a declared parent source, then a state source. A run that
reads one source writes one record, and the bytes are the same as the single-record rule before it:

```text
kind: api
name: 6cf3d2e1....xml
path: panorama_cache/6cf3d2e1....xml
scope: whole-config
request: panorama?category=configuration&type=export
cache_entry: 6cf3d2e1....xml
size: 24658
sha256: 9b1c...
```

- `kind`, `name`, `path` name the bytes you can reopen. `path` is the path the run received,
  so a record written from another directory names a different path.
- `scope` names the scope the source holds: `whole-config` when the producer declares none, or the
  declared path (`device-group/entry/Production-DG`, no leading slash) for a per-scope run. A run
  with a declared parent writes a second record for it, so each record names the source the shadow
  line prints. A state source names the workspace the run declared, or `whole-config` when it
  declares none.
- `request` and `cache_entry` are the key-free request identity and the entry it names, for
  an api source. A file source and a state source write `-` for both, so a state record references
  nothing and prunes nothing. The record never names the API key.
- `size` and `sha256` are measured on the bytes the input door parsed, so the record names
  the bytes the report lines describe, not a file that changed after the run.
- The rule lives in `provenance.py`, and the report bodies keep the rule that a report names
  the source name only, never the path
  ([ARCHITECTURE.md](ARCHITECTURE.md) §3.3). The label the report bodies use is `Source:`.

### The unit manifest

`CODEBASE_MANIFEST.json` is one row per unit, where a unit is one combination of the four scope
facts. It is written as data, in identity order, so a tool reads it and a document does not
restate a row. Ten fields, in this order: `unit`, `device_group`, `vsys`, `template`,
`vsys_device`, `directory`, `entry_count`, `references`, `rank`, `after`.

```json
[
  {
    "unit": "Production-DG",
    "device_group": "Production-DG",
    "vsys": "",
    "template": "",
    "vsys_device": "localhost.localdomain",
    "directory": "production_dg_f7597196",
    "entry_count": 17,
    "references": [
      "any",
      "service-http"
    ]
  }
]
```

- `unit` names the unit. It is the deepest scope the export declares. `Shared` names the unit whose
  four facts are empty, and `localhost.localdomain` names no firewall, so the scope above it names
  the unit.
- `directory` is the sanitized unit name plus the 8-hex digest of the unit identity. The digest is
  always in the name, so a name does not move when an unrelated scope is added. F6.1 names the
  directory; it does not write one.
- `entry_count` counts the ledger rows for the unit, including the entry that defines the scope. An
  entry inside a config-object entry is a property level, so the parent row's count covers it.
- `references` names the names this unit references from outside itself, in sorted order. A name the
  run declares is not one.
- `rank` is the position in the plan order, from 1, and `after` names the units this unit must be
  planned after, in sorted order. Three bases produce `after`: the unit that owns a name before the
  unit that overrides it, the shallower scope before the deeper scope inside it, and the target unit
  before the referrer unit. A unit in a reference cycle cannot be ordered, so it states `rank` as 0
  and the cycle prints in the report. `reference_edges.py` fills the two fields; the rule that
  `rank` starts at the units with no dependency, in identity order, is the reason the order is
  deterministic.
- Two runs on the same bytes write the same bytes, because the rows sort by the identity, the names
  are sorted, and no field states a path or a timestamp.
- The rule lives in `unit_manifest.py`, and `parse_rows` reads a written file back as data, so a row
  that is not the declared shape is a refusal ([ARCHITECTURE.md](ARCHITECTURE.md) §3.4). The file is
  written only when it has content, and the CLI takes no flag for it.

### The ownership record

`OWNERSHIP.json` is one row per entry the coverage matrix covers. Ownership is a per-entry fact, so
this file holds one row per entry while the manifest holds one row per unit, and the two join on
`directory`. Eleven fields, in this order: `type`, `entry`, `source`, `device_group`, `vsys`,
`template`, `vsys_device`, `directory`, `owner`, `kind`, `override`.

```json
[
  {
    "type": "panos_address",
    "entry": "Printer-Pool",
    "source": "ownership_override.xml",
    "device_group": "Branch-DG",
    "vsys": "",
    "template": "",
    "vsys_device": "localhost.localdomain",
    "directory": "branch_dg_ddec9c8a",
    "owner": "shared_be5be69f",
    "kind": "override",
    "override": "no"
  }
]
```

- `type` is the matrix row that covers the entry, the same key the property scan and the state scan
  use.
- `source` is the report value of the source the entry sits in, never its path.
- `directory` names the unit the export declares the entry inside, and `owner` names the unit that
  owns the name. The two are the same value for an entry that is not an override. `owner` is empty
  when the rule names no owner.
- `kind` is what the rule can say about an entry: `declared` (one entry, or units that cannot sit in
  one inheritance chain), `definition` (this entry owns the name), `override` (this entry repeats a
  name another entry owns, so the codebase resolves it as a reference to `owner`), `ambiguous` (the
  rule names no owner).
- `override` is the `disable_override` flag as the parse read it: `yes`, `no`, or `unknown` when the
  matrix row does not declare the property. The flag names the entry no descendant may override, so it
  does not choose the owner; it makes a repeated name an operator decision.
- Two runs on the same bytes write the same bytes, because the rows sort by the identity and then by
  the source, and no field states a path or a timestamp.
- The rule lives in `ownership.py`, and `parse_rows` reads a written file back as data, so a row that
  is not the declared shape is a refusal ([ARCHITECTURE.md](ARCHITECTURE.md) §3.5). The file is written
  only when it has content, and the CLI takes no flag for it.

A name the rule cannot decide prints in `CONVERSION_REPORT.txt`, in its own section after the shadow
section and before the state sections. A finding is an operator action, so it does not change the exit
code, which the gate decides.

### The reference edge record

`REFERENCE_EDGES.json` is one row per reference pair. An edge is a fact between two units, so it
cannot be a manifest field (one row per unit) or an ownership row (one row per entry), and this file
holds one row per pair. Four fields, in this order: `referrer`, `target`, `type`, `entry`.

```json
[
  {
    "referrer": "fw_a_example_com_4daa3d43",
    "target": "fw_b_example_com_f80a1db9",
    "type": "panos_ethernet_interface",
    "entry": "ethernet1/2"
  }
]
```

- `entry` is a name the reference rule resolved outside the run. `referrer` is the unit that used it.
  A name the rule resolved inside the run is a reference inside one root, so it writes no row, and a
  name no unit in the run declares writes no row: that name is already in the manifest's `references`
  field.
- `target` is the unit that owns the name, which is the `owner` field of the `OWNERSHIP.json` row for
  (`type`, `entry`), not the unit that declared it. `type` is the same matrix row the property scan
  and the state scan use.
- `referrer` and `target` join to `CODEBASE_MANIFEST.json` on `directory`, and (`type`, `entry`) joins
  to `OWNERSHIP.json`, so the record states no path and no second identity key.
- A row whose target is the referrer writes no row, because a unit cannot come before itself.
- Two runs on the same bytes write the same bytes, because the rows sort by the four fields in field
  order and no field states a path or a timestamp.
- The rule lives in `reference_edges.py`, and `parse_rows` reads a written file back as data, so a row
  that is not the declared shape is a refusal ([ARCHITECTURE.md](ARCHITECTURE.md) §3.6). The file is
  written only when it has content, and the CLI takes no flag for it.

A pair that closes a cycle prints in `CONVERSION_REPORT.txt`, in its own section after the
repeated-name section and before the state sections, one line per cycle, read from its smallest unit.
Two units that reference each other cannot be put in a plan order, so the order they cannot have is
the finding. A cycle is an operator action, so it does not change the exit code, which the gate
decides, and the console prints no cycle line. The tool emits the order as data; the platform plans
in that order.

### The site data record

`SITE_DATA.json` is one row per site that names a value, and `site.auto.tfvars` is the same data in the
form Terraform reads. A site is a unit, so the record joins to the manifest and holds one row per site. Two
fields, in this order: `directory`, `variables`.

```json
[
  {
    "directory": "fw_2_example_com_5cef6fb6",
    "variables": {
      "fw_2_example_com": "fw-2.example.com"
    }
  }
]
```

```
# site.auto.tfvars, written from the row above
fw_2_example_com = "fw-2.example.com"
```

- `variables` is the variable name with its value. The name is the naming rule applied to the value
  ([ARCHITECTURE.md](ARCHITECTURE.md) §5), so the row states the value once: `fw-2.example.com` becomes
  `fw_2_example_com`. A name is the mapping result, so a row cannot state a name the run did not print.
- `directory` joins to `CODEBASE_MANIFEST.json`, so the record states no path and no second unit rule, and
  `variables` cannot be a manifest field, because a manifest row holds one unit and names no value.
- A value comes from the table `resource_mapping.VALUE_VARIABLES`, which states what the emitter prints for
  each location field. Only `ngfw_device` prints as `var.<name>`, because the device is the value a codebase
  changes per site ([CODEBASE_ASSEMBLY.md](CODEBASE_ASSEMBLY.md) §9). A run that names no value writes neither
  file, so the sample output is unchanged.
- `site.auto.tfvars` prints one line per variable, in name order across the file, and one line for a name two
  rows state. Terraform loads a `*.auto.tfvars` file automatically, so `terraform.tfvars` stays your own file
  for the credentials, which the tool never writes.
- `parse_rows` reads a written file back as data and refuses a row that is not the declared shape, including a
  variable name that is not the naming-rule shape of its string value
  ([ARCHITECTURE.md](ARCHITECTURE.md) §3.7). A value that is neither a string nor a list is a refusal, and so
  is a name two rows state with two different values.
- The rows keep the identity order, the names inside a row sort, and no field states a path or a timestamp, so
  two runs on the same bytes write the same bytes.
- Neither file is a gate input, because the gate reads `.tf` files, and both are written only when they have
  content. The CLI takes no flag for them: the table is the default output.

## Post-run sanity gate

Every conversion runs the gate on the files it wrote, prints a summary, and
writes `SANITY_REPORT.txt`. The gate reads the files, so it reports what you
receive, not what the generator intended.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every `resource` and `data` block carries `location` | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type (the type, the `location` sub-block and its fields, and `name` when the row declares one) | FAIL |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | every declared variable has a `var.` consumer, and every `var.` consumer names a variable this run declares (F6.6) | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder (the VPN key `***CHANGE_ME***`) is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

One block reader serves every block kind the gate reads, so a `data` block is checked
by the same reader as a `resource` block, and the same fact is not reported twice: the
missing `location` block is the `location_present` finding for both kinds. The
`data_blocks` rule is the only check that reads the shape of a `data` block, because
`terraform validate` accepts an unknown `location` sub-block and drops it silently. A
WARN does not fail the run. A FAIL finding exits 1. A SKIPPED check never
changes the exit code. The rules live in `sanity_checks.py` and are stated in
[ARCHITECTURE.md](ARCHITECTURE.md) §4.6.

Exit codes: 0 when the gate reports no FAIL finding, 1 when a check fails or
the input is refused. A coverage gap or an unaccounted entry is an operator
action, so it does not change the exit code.

## Reading the generated Terraform

Four things explain the shape of the output:

- **Naming.** A local resource name is the sanitized PAN-OS name plus an 8-hex
  digest of the source identity, so the same name in two device groups, virtual
  systems, templates or firewalls is two resources. The rule is in
  [ARCHITECTURE.md](ARCHITECTURE.md) §5.
- **Location.** Each resource carries the `location` block the source scope
  states, in the shape the provider declares for that type. The branch order is
  in [ARCHITECTURE.md](ARCHITECTURE.md) §4.2.
- **References.** A name the same run declares is emitted as a `.name`
  reference, so apply order follows the dependency. A name outside the export
  stays a plain string, unless the run declares a read-through scope, in which case
  it becomes one `data` block the plan reads
  ([ARCHITECTURE.md](ARCHITECTURE.md) §4.7). The resolution order is in
  [ARCHITECTURE.md](ARCHITECTURE.md) §4.3.
- **Site values.** The device name in a `location` block prints as `var.<name>`, because the table
  `resource_mapping.VALUE_VARIABLES` maps that field to a variable (F6.6). A site change is a `.tfvars`
  change, not a code change, so replacing hardware changes one line in `site.auto.tfvars` instead of every
  resource inside the template. Every other location field prints as the value the source states.

## Deploying the generated configuration

1. Create `terraform.tfvars` with the credentials. Do not commit it. The tool writes `site.auto.tfvars`
   from `SITE_DATA.json`, and Terraform loads it automatically, so put the credentials in
   `terraform.tfvars` and leave the site values in the file the tool wrote.
2. Replace the placeholder VPN pre-shared keys.
3. Read `MANUAL_SETUP_REPORT.txt` and configure those items by hand.
4. Check interface names against the target platform
   (`INTERFACE_MIGRATION_REPORT.txt`).
5. `terraform init`, then `terraform plan`, then `terraform apply`. Review the
   plan before you apply it.

## Troubleshooting

| Symptom | Cause and action |
|---|---|
| `ParseError: not well-formed` | The export is truncated or invalid. Export again from Panorama. |
| `Error: ... larger than the limit` | The input exceeds `--max-input-bytes`. Raise the limit only for a trusted file. |
| `Refused: input declares a DTD` | The file is not a Panorama export. Do not disable the check; obtain the export again. |
| Gate FAIL on `references` | A `.name` reference points at a resource this run did not declare. Read `SANITY_REPORT.txt`; the converter never declares a resource to make a reference work. |
| Gate FAIL on `variables` | A declared variable has no `var.` consumer, or a `var.` consumer names a variable this run does not declare. The run declares the three credential variables plus the site variables it printed (F6.6). Read `SANITY_REPORT.txt` |
| Gate WARN on `placeholders` | Expected. A VPN pre-shared key is a placeholder, and you must set it before apply. |
| Duplicate local resource names | A true duplicate of the same identity. The generator adds a numeric suffix so the output stays valid HCL. Two different identities never need it. |
| `terraform validate` reports an unknown `location` sub-block | The gate checks presence only, not shape. Read `LOCATION_SCHEMA` in `resource_mapping.py`; `terraform validate` accepts an unknown sub-block and drops it silently. |
| Apply fails with "not found" | The referenced object exists in another tenant, so the converter left the name as a plain string. Create it, or point the provider at the right device group. |
| Splitter prints "No device groups found" | The export came from a firewall, not Panorama. Run the converter on it directly. |
| Splitter copies no template | No device appears in both the device group and the template. The splitter prints the fact. Fix the export, or copy the template section by hand. |

## Extending the converter

Add a type in this order, so the tests cannot drift:

1. Add the type to `EMITTED_TYPES` in `resource_mapping.py`, and to
   `LOCATION_SCHEMA` with the sub-blocks the provider schema declares.
2. Add a `COVERAGE_MATRIX` row with the XML element, the fixture entry, the
   expected emitted name, the fixture, and the output file.
3. Add the parse method, and mark each entry it reads. Add the container-table
   row in `container_coverage.py`.
4. Add the generator method.
5. Add or extend a fixture, and the row test. Run `python3 -m pytest` and
   `ruff check .`.

An emitter change that skips step 2 fails `tests/test_coverage_matrix.py`. A
parse method that reads entries without marking them fails
`tests/test_entry_coverage.py`.

## Limitations

The limits are recorded in [`../backlog.md`](../backlog.md) and in
[RESOURCE_MAPPING.md](RESOURCE_MAPPING.md). The main ones:

- BGP, OSPF, application filters, application override rules, QoS profiles, and
  IPsec tunnel monitor profiles have no v2 resource.
- Security profile bodies, log forwarding profiles, and schedules are captured
  only as name and description, so they are reported, not emitted.
- Address types with no `panos_address` attribute (country, region, continent,
  container, external) are reported.
- A service that defines both tcp and udp emits one leg, because the provider
  accepts one.
- Rulebase (pre, post, shared) is not recorded, so a device group with both
  pre- and post-rules chains across them.
- `location.template_stack` is never emitted, and a template that targets two
  devices keeps interface names as strings.
- The state scan compares only a property the matrix row declares that both sides hold by the same
  name, because no rule maps a parse key to a provider attribute name, so the parse key `tags` and
  the provider attribute `tag` are not compared. The state source is read only: a run reports what a
  state document holds and never writes one.

## License

The project is dual-licensed: AGPL v3 for open source use, and a commercial
license for proprietary use. The terms are in
[DUAL-LICENSING-EXPLAINED.md](DUAL-LICENSING-EXPLAINED.md), and the license
texts are `LICENSE-AGPL` and `LICENSE-COMMERCIAL`.

## Additional resources

- [Palo Alto Terraform provider](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [PAN-OS API documentation](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-panorama-api)
- Testing and linting: `python3 -m pytest`, `ruff check .`
