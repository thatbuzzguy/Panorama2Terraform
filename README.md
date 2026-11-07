# Panorama to Terraform Converter

Converts a Palo Alto Panorama XML configuration export into Terraform
configuration for the **Palo Alto Networks panos provider v2** (pinned to
`~> 2.0.14`), plus plain-text migration reports for the configuration
that has no v2 resource.

## What it does

1. Parses the Panorama export (device groups, shared objects, templates,
   vsys).
2. Emits provider-v2 Terraform resources, each carrying the required
   `location` argument.
3. Writes reports for configuration with no v2 resource so nothing is
   silently dropped.
4. Writes the site values as data and the `.tfvars` the platform reads from it, so a site change is a
   `.tfvars` change and not a code change. The device name a resource block prints is a variable
   reference, and the tool names no value the run did not print (F6.6).

## Quick start

```bash
python3 src/panorama_to_terraform.py your_export.xml --output-dir terraform_output

cd terraform_output/<unit directory>     # one directory per unit the manifest names
terraform init
terraform validate
```

Every run ends with a static gate (see [Post-run sanity gate](#post-run-sanity-gate)):
it checks the files it wrote, writes `SANITY_REPORT.txt`, and exits non-zero
when a check fails. Add `--validate` to run `terraform init` + `terraform
validate` in the same run, once for each unit directory the manifest names. A unit is one plan against one
state, so a plan runs inside the unit directory.

Split a Panorama export into one XML file per device group:

```bash
python3 src/split_device_groups.py your_export.xml --output-dir split_output
```

Read a Terraform state document as a reference source, so the report names which entries another
workspace already owns and which owned value this run does not match:

```bash
python3 src/panorama_to_terraform.py your_export.xml --state production.tfstate --workspace production
```

The state document writes no output, so the generated `.tf` files are the same as without it; the
report gains two sections. The rule is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §3.2.

Read a name the run cannot resolve as a provider data source instead of a plain string, for scopes
you declare:

```bash
python3 src/panorama_to_terraform.py your_export.xml --data-blocks panos_address,panos_zone
```

A run that declares no read-through scope keeps the plain-string rule. A run that declares one
writes `read_through.tf`, one `data` block per name it cannot resolve, and labels itself in the
generated `README.md`, because a `data` block resolves at plan time and the plan fails when the
entry is not present in the location the block names. The rule is in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §4.7.

Write one `import` block per entry, so the first plan for a directory reads
`N to import, 0 to add, 0 to change, 0 to destroy` for the entries the parse models:

```bash
python3 src/panorama_to_terraform.py your_export.xml --import-blocks
```

Off by default. A run that declares it writes `imports.tf`, one block per entry, in unit order then
local-name order. Each block states `to` and `id`, and `id` is base64 of the location object plus the
entry name, built from the same data the resource block uses. A gate rule reads the file and refuses a
block that does not agree with the resource block it names. The four `*_policy_rules` types write no
block, because their import object names the rulebase, the position, and a list of names; each rule
entry is a WARN finding. The rule is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §4.8.

## Requirements

- Python 3.9+ (standard library only)
- Terraform 1.14+ for the validate gate (an `action` block is 1.14 syntax)
- A Panorama XML export

## Generated resources (provider v2)

| Area | Resources |
|---|---|
| Objects | `panos_address`, `panos_address_group`, `panos_administrative_tag`, `panos_application_group`, `panos_custom_url_category`, `panos_external_dynamic_list`, `panos_service`, `panos_service_group` |
| Policy | `panos_security_policy_rules`, `panos_nat_policy_rules`, `panos_decryption_policy_rules`, `panos_pbf_policy_rules` (one resource per rule; per-device-group chains in XML order — the first rule anchors at the end of the rulebase, each later rule is placed directly after the previous one and depends on it) |
| Profiles | `panos_security_profile_group` |
| Network | `panos_ethernet_interface`, `panos_ethernet_layer3_subinterface`, `panos_vlan_interface`, `panos_loopback_interface`, `panos_tunnel_interface`, `panos_aggregate_interface`, `panos_aggregate_layer3_subinterface`, `panos_virtual_router`, `panos_virtual_router_static_route_ipv4`, `panos_zone`, `panos_monitor_profile` (PBF path monitoring profiles; referenced by PBF rule path monitoring) |
| VPN | `panos_ike_crypto_profile`, `panos_ike_gateway`, `panos_ipsec_crypto_profile`, `panos_ipsec_tunnel` (proxy-ids merged into the tunnel) |

The mapping and rationale are in
[`src/resource_mapping.py`](src/resource_mapping.py) and
[`docs/RESOURCE_MAPPING.md`](docs/RESOURCE_MAPPING.md).

The provider-resource <-> Panorama-XML-element coverage matrix — one
row per emitted type with the XML element, fixture, and expected name,
enforced by `tests/test_coverage_matrix.py` — is in
[`COVERAGE_MATRIX`](src/resource_mapping.py) (machine-readable, 34 rows) and
[`docs/COVERAGE_MATRIX.md`](docs/COVERAGE_MATRIX.md) (table + method).

## Dependency wiring

Name attributes that reference an object the referrer's own unit declares are
emitted as Terraform `.name` references (for example
`source_addresses = [ panos_address_group.web_servers.name ]`), so
`terraform apply` orders the resources deterministically. A name another unit in
the run declares, and a name that points outside the export — built-in PAN-OS
names such as `any`, `application-default`, or `service-ftp`, or objects in
other tenants — stay plain strings, because one plan runs against one root and
one state. The converter never declares a resource just to
make a reference work, so the output always passes
`terraform validate`. The resolution order is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.3.

A run may opt in to `data` blocks for the names it cannot resolve
(`--data-blocks`), one block per name, in `read_through.tf`. That is a
plan-time read, so the run is labelled in the generated `README.md`.
The rule is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.7.

## Resource naming

A local resource name is the sanitized PAN-OS name plus an 8-hex digest
of the object's source identity: resource type, defining device group,
template or owning device, virtual system (vsys), and raw name. The name
is deterministic: the same object always gets the same local name, the
name does not depend on emission order, and same-named objects in
different device groups, virtual systems, templates, or firewalls stay
distinct. Two firewalls that both declare `ethernet1/1` are two resources
with two locations, not one resource and a numeric suffix. One name rule
serves both block kinds, so a read-through `data` block takes the name the
object would have had as a resource. The full rule is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5. For example:

```hcl
resource "panos_address" "web_server_1_11f477f4" {
  name = "Web-Server-1"
  ...
}
```

## Location blocks

Provider v2 places every resource with the required `location` argument,
and the sub-blocks one type accepts differ from the next. The converter
takes the choice from the source scope the export declares and from
[`LOCATION_SCHEMA`](src/resource_mapping.py), the verified v2.0.14 shape per
emitted type. The branch order is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.2:

| Source of the entry | Emitted location |
|---|---|
| Inside a device group | `device_group = { name = "<device group>" }` |
| Inside `<shared>` | `shared = {}` |
| Inside a virtual system | `vsys = { name = "<vsys>", ngfw_device = "<firewall>" }` |
| Inside a template | `template = { name = "<template>" }`, plus `vsys` where that type declares the field |
| Inside a device, on a type with no virtual system (an interface, a virtual router, a VPN object) | `ngfw = { ngfw_device = "<firewall>" }` |
| Nothing in the export places it | `template = { name = "Shared" }` placeholder, reported |

`localhost.localdomain` is the PAN-OS placeholder for "this device", so it
is never written as `ngfw_device`.

Three limits are reported in `MANUAL_SETUP_REPORT.txt` instead of being
dropped silently: a declared vsys, template, or device group the resource
type cannot carry (for example `panos_security_profile_group` has no `vsys`
sub-block), a vsys location whose export names no target firewall
(`ngfw_device` is omitted), and a template location the converter had to
guess, which is listed with the templates the entry's own device takes.

## Report-only configuration

The following have no v2 provider resource. The converter keeps their
data visible in `MANUAL_SETUP_REPORT.txt` instead of emitting it:

- Application filters
- Application override rules
- QoS profiles
- IPsec tunnel monitor profiles (note: `panos_monitor_profile` is the
  PBF path monitoring profile, a different PAN-OS object)

Routing is not in that list, because BGP, OSPF and OSPFv3 print as the `protocol` object on
`panos_virtual_router` (`docs/ARCHITECTURE.md` §4.9). The report names only the routing entries the object
cannot express: a peer no peer group names it, an interface outside an area, a choice value the mapping does
not state, and a `range` entry that states neither `advertise` nor `suppress`. A routing level the shape table
does not state is not read, so the `ospfv3` timer, BFD, graceful-restart and export-rule levels, and the `ospf`
fields outside `area` and `auth_profile` stay out of the output. The filter containers are the routing kind the
provider declares as its own resource, so each entry prints in `filters.tf` through `FILTER_SHAPE`
(`docs/ARCHITECTURE.md` §4.10). Those open levels are recorded in [`backlog.md`](backlog.md).

The following have a v2 provider resource, but the converter cannot emit
the whole object — emitting a partial one would create a misconfigured
resource — so the missing part stays in the report:

- Security profile bodies (antivirus, anti-spyware, vulnerability, URL
  filtering, file blocking, WildFire, zone protection)
- Log forwarding profiles
- Schedules
- Address objects whose type has no `panos_address` attribute (location
  type: country, region, continent, container; external type). Every
  other address type emits, including `ip-wildcard` and IPv6.
- The second protocol leg of a service that defines both tcp and udp:
  `panos_service` accepts one leg, so the tcp leg emits and the udp leg is
  listed with its ports

Data files and reports are the codebase root set: one file per run, written at the output directory root. Each
is written only when it has content; `SOURCE.txt` is written on every completed run, because a run always reads
a source. The other files are the unit set, and the run writes one directory per unit the manifest names
([`docs/CODEBASE_ASSEMBLY.md`](docs/CODEBASE_ASSEMBLY.md) §14):

- `SOURCE.txt` - what the run read, as `field: value` data, one record per source read: the
  source kind, the name, the path, the scope, the request identity, the cache entry, the size,
  and the SHA-256 hex of the bytes the input door parsed ([`src/provenance.py`](src/provenance.py))
- `CODEBASE_MANIFEST.json` - one row per unit (one declared scope), as data: the five scope facts,
  the directory name, the entry count, and the names the unit references from outside itself
  ([`src/unit_manifest.py`](src/unit_manifest.py)). Every run writes it when it has content
- `OWNERSHIP.json` - one row per entry a coverage matrix row covers, as data: the matrix row, the
  entry name, the source, the five scope facts, the declaring unit, the owning unit, what the owner
  rule can say about the entry, and the `disable_override` flag as the parse read it
  ([`src/ownership.py`](src/ownership.py)). Every run writes it when it has content, and the two data files
  join on the unit directory
- `REFERENCE_EDGES.json` - one row per reference pair, as data: the unit that uses a name another unit
  owns, the unit that owns it, the coverage matrix row, and the entry name
  ([`src/reference_edges.py`](src/reference_edges.py)). Every run writes it when it has content, and the row
  joins to the manifest on the unit directory and to the ownership record on (`type`, `entry`)
- `SITE_DATA.json` - one row per site that names a value, as data: the unit directory and the variable
  names with their values ([`src/site_data.py`](src/site_data.py)). Every run writes it when it has content, and the
  row joins to the manifest on the unit directory. The values are the pairs the emitter recorded when it
  applied the value-to-variable table ([`src/resource_mapping.py`](src/resource_mapping.py) `VALUE_VARIABLES`)
- `site.auto.tfvars` - the `.tfvars` written from the site data rows, one file per unit inside the directory
  that row names, one line per variable in name order
  ([`src/site_data.py`](src/site_data.py)). Terraform loads a `*.auto.tfvars` file automatically, so
  `terraform.tfvars` stays the operator's own file for the values the tool cannot read, and for the key, which
  the tool never writes ([docs/CODEBASE_ASSEMBLY.md](docs/CODEBASE_ASSEMBLY.md) §11). Written
  only when it has content. The gate rule `data_files` reads the record through `parse_rows` and compares
  the printed form with `render_tfvars`; the printed form is not one of the four data files, so the report
  count names only the records. A name the table records with no value for it writes no row and no line:
  `target` is such a name, because the export states a device as a hostname, so no serial reaches the parse, and
  `hostname` is the same case, because the export states no host (§11). The operator supplies both values
  ([`docs/CODEBASE_ASSEMBLY.md`](docs/CODEBASE_ASSEMBLY.md) §9 rule 8)
- `scope.tf` - The scope objects the export declares: one `resource` block per scope entry for
  `panos_device_group`, `panos_device_group_parent`, `panos_template`, `panos_template_stack`,
  `panos_template_variable`, and `panos_vsys`, written by every run that has a scope entry, before the
  object files, and in the F3.9 level order ([`src/resource_mapping.py`](src/resource_mapping.py)
  `SCOPE_LEVEL_ORDER`). A device membership prints as the list of objects the provider takes, and the
  PAN-OS "this device" placeholder names no firewall, so it never enters a printed list
  ([`docs/CODEBASE_ASSEMBLY.md`](docs/CODEBASE_ASSEMBLY.md) §8)
- `imports.tf` - one `import` block per entry the run declares, as `to` and `id`
  ([`src/import_blocks.py`](src/import_blocks.py)). Written only for a run that declares `--import-blocks` and
  has a block to write, and the gate rule reads it because it is a `.tf` file
- `actions.tf` - the commit and push actions: one block per action the pinned schema declares, for each unit the
  manifest names, and each block names the fact its own unit selects
  ([`src/commit_actions.py`](src/commit_actions.py)). Written by every run that has such a unit, as the last `.tf` file,
  and the push block prints after the commit block for the same unit and shares its address. A unit whose fact no
  filter and no push type can name writes no block, and the file is written only when it has content
  ([`docs/CODEBASE_ASSEMBLY.md`](docs/CODEBASE_ASSEMBLY.md) §10). The push block states no `devices`, because the
  tool names no serial, so the provider pushes to all devices in the target
- `MANUAL_SETUP_REPORT.txt` - everything above that must be configured
  manually, plus a section for a container no parse method reads
  ([`src/container_coverage.py`](src/container_coverage.py))
- `INTERFACE_MIGRATION_REPORT.txt` - interface and IP inventory
- `VPN_MIGRATION_REPORT.txt` - VPN inventory; **pre-shared keys are
  placeholders and must be set before apply**
- `CONVERSION_REPORT.txt` - one line per entry the parse read: source line,
  object type, entry name, destination, detail, and the fields it captured;
  a section for a captured field no output read, for an entry a coverage matrix
  row covers ([`docs/COVERAGE_MATRIX.md`](docs/COVERAGE_MATRIX.md)); a section for a child entry
  name that repeats a parent entry name, for a run that reads a declared parent source
  ([`src/shadow_coverage.py`](src/shadow_coverage.py)); a section for a repeated name the ownership rule cannot
  decide ([`src/ownership.py`](src/ownership.py)); two sections for an entry another workspace already
  owns and for an owned value this run does not match, for a run that reads a declared state document
  ([`src/state_coverage.py`](src/state_coverage.py)); the file names the input file name, not its path
  ([`src/entry_coverage.py`](src/entry_coverage.py))

The three grouped reports are grouped by the scope the export declares: device
group first, then the template or the device the entry sits in, then the
object kind inside the section. A section names only the scope the export
states, so the same interface or gateway name on two device groups appears
once under each, and an entry the export places nowhere is the shared
section, named `Shared`. The rule is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.5.

## Typical outputs

The run writes two sets. The codebase root holds one file per run: the four records, the report files,
`README.md` and `SOURCE.txt`. Every other file is the unit set, and the run writes one directory per unit the
manifest names, holding that unit's `.tf` files and the printed form of that unit's site row
([`docs/CODEBASE_ASSEMBLY.md`](docs/CODEBASE_ASSEMBLY.md) §14).

```
<output directory>                     (the codebase root set)
  CODEBASE_MANIFEST.json  OWNERSHIP.json  REFERENCE_EDGES.json  SITE_DATA.json
  README.md  SOURCE.txt
  CONVERSION_REPORT.txt  SANITY_REPORT.txt  MANUAL_SETUP_REPORT.txt
  INTERFACE_MIGRATION_REPORT.txt  VPN_MIGRATION_REPORT.txt

  <unit directory>/                    (one directory per unit the manifest names)
    provider.tf  variables.tf          (the names the run declares: the host, the values the run printed,
                                        and the names it holds no value for. `provider.tf` reads
                                        `var.hostname` for every unit and `var.target` for a unit that
                                        names a device, F6.6, F6.10.4, §11)
    scope.tf
    address_objects.tf  address_groups.tf
    service_objects.tf  service_groups.tf
    tags.tf  custom_url_categories.tf  application_groups.tf  external_lists.tf
    zones.tf  interfaces.tf  virtual_routers.tf  filters.tf  monitor_profiles.tf
    security_profiles.tf  security_profile_groups.tf
    vpn.tf
    security_rules.tf  nat_rules.tf  decryption_rules.tf  pbf_rules.tf
    read_through.tf  imports.tf        (opt-in: --data-blocks, --import-blocks)
    actions.tf                         (the commit and push actions per unit, the last .tf file written)
    site.auto.tfvars                   (the printed form of that unit's site row)
```

(Only files with content are written; the list above is the union across
all supported inputs. The kitchen-sink fixture exercises the full set, and
`tests/test_golden_files.py` pins the exact `.tf` paths and bytes, read as paths from the case directory. A
per-unit file names its unit only by its directory, so a gate finding names the path from the codebase root.)

## Exporting from Panorama

- **Web UI:** Device -> Setup -> Operations -> save a configuration
  snapshot and extract the XML.
- **CLI:** `show` with `set cli config-output-format xml`.
- **API:** `curl -k -X GET 'https://panorama/api/?type=export&category=configuration&key=KEY' -o config.xml`

The converter can also read the API response itself (`--source api --host panorama`),
which fetches over https and keeps a cached copy. The response is an envelope
(`response/result/config`), so the fetch layer normalises the root to the `config` element
before the parse. A cached entry lets a later run work with `--offline`, which needs no
key. The key is read from the environment, never from a command line, and the generated codebase reads the same
environment at plan time ([docs/CODEBASE_ASSEMBLY.md](docs/CODEBASE_ASSEMBLY.md) §11). `--path` reads one scope
instead of the whole config, and `--parent` declares the parent scope the run reads as a second
source, which is what the shadow scan reads ([`src/shadow_coverage.py`](src/shadow_coverage.py)); both
apply to the api source only. The arguments are in
[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md); the rules are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §3.

## Safe input

Both scripts read the input through one boundary (`xml_input.py`) that runs the two
checks on the bytes a producer hands, and refuses input it cannot parse safely before
it parses it and before it writes any file:

- **Size.** The read is capped at 64 MiB (`--max-input-bytes N`), and the same limit
  applies to the bytes a producer hands. A
  Panorama export this project has seen is three orders of magnitude
  smaller, and `xml.etree` builds the whole document in memory, so an
  unbounded read is a memory denial of service.
- **A DTD.** A DTD is the only way an entity expansion ("billion laughs")
  or an external entity (XXE) reaches `xml.etree`, and a Panorama export
  never carries one. The check asks the parser, not a text search, so it
  also holds for a UTF-16 export, where a `<!DOCTYPE` text search sees
  nothing. A `<!DOCTYPE` that only appears in a prolog comment is legal
  input and is not a refusal.

A refusal names the source, the limit and the measured size, exits
non-zero, and writes no output. For a file it names the path; for a producer with no
file behind it it names the source (F5.1). Raise the limit only for a trusted input.
The input boundary is standard-library only by design: `defusedxml` would close the DTD
class but not the size class, so it is not a reason to add a dependency to the boundary.

The api producer hands its response bytes through the same boundary, so a response over the
limit or carrying a DTD is refused with the same words, and a refused response is never
written to the cache. The https rules for that producer are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §3.

The state producer hands its bytes through the same boundary (F5.6), so a state document over the
limit is refused before the read, with the same words. Only the parse step is chosen by the kind:
a JSON document has no prolog, so the DTD check reaches no DOCTYPE and a `<!DOCTYPE` inside a JSON
value is legal input. A state document the identity key cannot read is refused as an input refusal
(exit 1), and a refusal writes no record.

## Deploying with Terraform

1. Set the key in the environment the provider reads at plan time
   ([docs/CODEBASE_ASSEMBLY.md](docs/CODEBASE_ASSEMBLY.md) §11), and create `terraform.tfvars` for the names the
   tool declares and cannot fill (do not commit it):

   ```hcl
   hostname = "panorama.example.com"   # every unit
   target   = "0123456789"             # a unit that plans against a device (F6.10.4)
   ```

2. `terraform init`
3. `terraform plan` - review every change
4. `terraform apply`

Before deploying: replace placeholder VPN pre-shared keys, review
`MANUAL_SETUP_REPORT.txt`, and adapt interface names to the target
platform (see `INTERFACE_MIGRATION_REPORT.txt`).

## Post-run sanity gate

Every conversion runs a static gate on the output it wrote, then prints a
summary and writes `SANITY_REPORT.txt`. The gate reads the files, so it reports
what you receive, not what the generator intended. It reads the `.tf` files for
the block rules and the four data files for the data rule, and the summary names
both counts. The round-trip cross-check is the one exception to that boundary,
because its fact compares two sets: the `.tf` block set it read, and the entry
set the run's ledger read. It reads no report and no data file, and a call with
no ledger reports the check as NOT RUN, so the rules that read only the files are
unchanged. The rule is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.6,
and `tests/test_round_trip.py` pins it.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every `resource` and `data` block carries `location` | FAIL |
| `data_blocks` | every `data` block matches the `DATA_SOURCE_SCHEMA` row for its type | FAIL |
| `import_blocks` | every `import` block agrees with the `resource` block it names: the type, the local name, the entry name, and the location | FAIL; WARN for a rule type the shape cannot state |
| `scope_blocks` | a name inside a scope block's `location` names a scope the run declares, by the type that defines it | FAIL |
| `actions` | every `action` block matches its `ACTION_SCHEMA` row inside `config` and names one unit | FAIL |
| `protocol_object` | every `protocol` object on a `panos_virtual_router` block matches the `PROTOCOL_SHAPE` row for its level, prints as a field, and states the one key a row selects | FAIL |
| `filter_blocks` | every filter container block matches the `FILTER_SHAPE` row for its level, states the one key a row selects, and an element inside a `[` container states the name the row reads as the entry name | FAIL |
| `certificate_blocks` | every certificate block matches the `CERTIFICATE_SHAPE` row for its level, states the entry name through the one naming rule, states the one key a row selects, prints a `sensitive` field as the variable reference, and an element inside a `[` container states the name the row reads as the entry name | FAIL |
| `references` | every `.name` reference resolves to a block declared in the same run, by kind | FAIL |
| `variables` | every declared variable has a `var.` consumer, and every `var.` consumer names a variable the run declares | FAIL |
| `data_files` | every data file reads as its declared rows, and the data agrees with the naming rule, the joins, the order rule, and its printed form | FAIL |
| `round_trip` | the `.tf` block set agrees with the entry set the run's ledger read, per unit and row, where the entry side counts only the entries `entry_coverage.EntryLedger.destination` answers as `emitted`, so an entry the run reports is not counted | WARN, or NOT RUN |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder (the VPN key `***CHANGE_ME***`) is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

A WARN does not fail the run: a placeholder is correct output that still needs
an action before apply, and a cross-check finding names a coverage fact, not a
broken output, so a count that does not agree keeps the exit code with the rules
that read the files. A FAIL finding exits 1. A SKIPPED check never changes
the exit code, so a run on a machine without terraform still reports the checks
it could not run. The rules are stated once in `sanity_checks.py`; the tests
call that module instead of restating them. One block reader serves every block
kind the gate reads, including `import` blocks, which it reads through `to`. The
reader keys each `.tf` file by the path from the codebase root, so a finding names the unit directory the file
is in, and the `terraform` check runs once per unit directory the manifest names, so each result names the
directory it ran on. The
gate is described in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.6.

## Testing

- `python3 -m pytest` - the full suite: parser and generator unit tests,
  golden byte-for-byte gates, resource-mapping and provider-schema
  conformance, policy order, dependency wiring, robustness, the coverage
  matrix row tests, the container-table parity tests, the entry-mark tests,
  and the no-dead-variable checks. XML fixtures drive the converter; schema
  conformance runs `terraform providers schema -json` against the pinned
  version (skipped when the `terraform` binary or registry access is
  unavailable).
- `tests/test_terraform_validate.py` - `terraform init` + `terraform
  validate` on the sample, kitchen-sink, and crypto-profile-only
  outputs (skipped when the `terraform` binary is absent)
- `tests/test_sanity_gate.py` - the post-run gate: every check detects its
  violation, no fixture trips a false positive, the report is byte-identical
  between two runs, and the exit code follows the findings
- `tests/test_container_coverage.py` - the container table and the code stay
  in step: no parse method without a row, no row naming a path the method
  does not read
- `tests/test_entry_coverage.py` - every parse method that reads entries
  marks them, so the per-entry report cannot lie
- `tests/test_source_fetch.py` - the api producer: bytes handed to the shared door,
  the response wrapper, the key-free cache name, `--offline`, the https rules, and the
  key from the environment. No test calls the network, and the committed response set is read through
  an injected producer
- `tests/test_api_requests.py` - the scope index and the response-to-request join (`api_requests.py`): the four
  membership lists as the container table rows, the scope set read from the membership responses, the sorted
  one-entry-per-scope order, the join checked against the request that made the response, and the offline
  harness: one committed response per request shape, each named by the request identity that produced it, read
  through the injected producer, and read as data by the record
- `tests/test_api_path.py` - the run over many sources: one response is one source with its own line map, the
  section-to-response join, the parse method running over the response that holds its container, the report
  position as the line inside that response, the row naming the source that holds the entry, and the predefined
  read
- `tests/test_shadow_coverage.py` - the cross-source shadow scan: the per-scope shape in the
  scan, the shadow fact (the key is `state_coverage.ownership_key` read with the facts the parent row
  declares, so it names the parent scope), the report section and its line shape with the parent entry
  field, one finding per parent entry, the report order, the console line, the CLI argument rules, and the
  offline run reading both cache entries
- `tests/test_provenance.py` - the provenance record (`SOURCE.txt`): the fields, the record
  read back as data, one record per source the run read, the `Source:` label for both sources,
  the rule that a cache entry is not pruned while a written record references it, and the record
  byte rule between two runs
- `tests/test_state_input.py` - the state producer: the two byte checks on the state bytes, the entry
  shape a scan can read, the document refusals, the record facts, the CLI argument rules, and the
  offline run that calls no producer
- `tests/test_state_coverage.py` - the state scan: the ownership key, the drift rule, the two report
  sections and their line shapes, the rule that a state read is not an output read, the exit code, and
  the record read back with no new field
- `tests/test_data_source_schema.py` - the data source table against the live provider schema: the rows,
  the required `location` and `name`, the 22 rows that declare no `name`, and the pin between
  `DATA_SOURCE_SCHEMA` and `LOCATION_SCHEMA`
- `tests/test_data_blocks.py` - the read-through data blocks: the one block reader for every block kind,
  the gate rule for a `data` block, the kind rule for a reference, the opt-in emit path (a run that
  declares nothing writes the golden bytes), the CLI argument rules, the report rule, the generated
  `README.md` label, and the byte rule between two runs
- `tests/test_unit_manifest.py` - the unit as data (`CODEBASE_MANIFEST.json`): one row per declared
  scope, the directory naming rule, the row shape read back as data, the reference names recorded by
  the reference rule, the no-change rule for the `.tf` goldens, the report bodies, the gate inputs,
  and the exit codes, and the byte rule between two runs
- `tests/test_reference_edges.py` - the reference between units as data (`REFERENCE_EDGES.json`): one
  row per pair, the join to the manifest and to the ownership record, the rule that the module
  resolves no name, self-reference exclusion, the acyclic rule and the report section, the unit order
  and its three bases, the gate inputs, the exit codes, and the byte rule between two runs
- `tests/test_import_blocks.py` - the import blocks (`imports.tf`): the id encoding and its inverse, the
  agreement gate rule and each violation type, the rule that the corpus writes no finding, the decision
  for the four `*_policy_rules` types, the rule that the block and the id come from one location rule and
  one naming rule, the order, and the byte rules between two runs and for a run that declares nothing
- `tests/test_scope_objects.py` - the scope objects (`scope.tf`): one block per scope entry, the level
  order and the document order, the file written before the config inside it, the file written only when
  it has content, emission as the default with no flag, the name field for the parent record, the value
  shape against the live provider schema and against the rows that declare it, the device membership as
  the objects the provider takes, the placeholder device never entering a printed list, the placement rule
  and the skipped entry, each violation type of the gate rule, and the byte rule between two runs
- `tests/test_site_data.py` - the site as data (`SITE_DATA.json`) and the `.tfvars` written from it: the
  value-to-variable table against `LOCATION_SCHEMA`, the row shape read back as data, the join to the manifest
  on the unit directory, the `.tfvars` bytes for a string and for a list, the device-name rule at the print
  site, the declaration set, both directions of the variable gate rule, the corpus rows, the rule that the
  corpus trips neither, the gate inputs, the report bodies, the rule that the module defines no second naming
  rule, and the byte rule between two runs
- `tests/test_data_file_gate.py` - the gate rule that reads the four data files (`data_files`): the file set
  the gate reads, the `CHECK_ORDER` position, each finding, the row ordinal as the finding position, the rule
  that each row shape is read through its own module, the truth across the corpus, and the byte rule between
  two runs
- `tests/test_round_trip.py` - the cross-check (`round_trip`): the `.tf` block set read through the one gate
  reader and the entry set read through the run's ledger, the join through the one scope rule and the one unit
  rule, one finding per unit and row where the two counts do not agree, the position the reader read, the WARN
  severity, the NOT RUN result when the caller passes no ledger, the rows that enter no count, the findings the
  corpus reports, and the byte rule between two runs
- `tests/test_write_path.py` - the write path (`write_path.py`): the two file sets and the rule that every file
  names one set, the one function that writes bytes and forces LF, the two path builders, the rule that no module
  of the tool writes a file outside it, the reader key as the path from the codebase root, the plan check that
  runs once per unit directory and names the directory it ran on, the rule that no flag names the layout, the
  golden set read as paths from the case directory, the single-unit case, and the byte rule between two runs
- `tests/test_commit_actions.py` - the commit action per unit (`actions.tf`): one block per unit the
  manifest names, the fact its own unit selects, the unit that writes no action, the address that answers
  the names inside the block, the order, the file written only when it has content, each violation type of
  the gate rule, the field inside `config`, the one field mapping and the one answer table and the one level
  rule, `ACTION_SCHEMA` against the live provider schema, the Terraform minimum, and the byte rule between
  two runs
- `tests/test_protocol_object.py` - the `protocol` object on `panos_virtual_router`: the shape table against
  the live provider schema, the print shape (`protocol = { ... }`, not a block), the one-of mapping, the body of
  a chosen level read from inside the chosen element, the peer inside its peer group, the interface inside its
  area, the entry the file cannot express, a sensitive field as
  the variable reference, `VALUE_VARIABLES` as the one shape owner, each violation type of the gate rule, and
  the byte rule between two runs
- `tests/test_filter_containers.py` - the six routing-profile filter containers: `FILTER_SHAPE` against the live
  provider schema, the 14 rows that state an exactly-one choice and the gate refusing two of them or none, the
  row scope that stops at a `match` or `set` row, the six `CONTAINER_TABLE`,
  `COVERAGE_MATRIX`, `EMITTED_TYPES` and `LOCATION_SCHEMA` entries with `FILTER_TYPES` as the one decision owner,
  the parse read and the print, the path-keyed input spellings with every pair grounded by a fixture entry and
  read from a real run, and each violation type of the gate rule
- `tests/test_build_kitchen_sink.py` - the fixture assembler (`tools/`): the read rule read on the committed
  bytes, so a hostile fixture is skipped by rule and not by name and the tool's decision agrees with `xml_input`
  for every committed fixture; the rule that the tool names no fixture except its own record, writes no file,
  and is a generator rather than a pin on the record; the three merge cases; the byte rule between two runs; and
  the rule that the tool reads the corpus and not the committed response set
- `ruff check .` - lint

Run counts are not stated here. They change with every feature and are
recorded in the git history and in `agent-status.md`.

`tests/` is flat: the test files sit beside the three sets `fixtures/`, `golden/`, and `responses/`, and
`tests/conftest.py` is the one shared helper file and the one place the path to each set is built. A committed
API response is not a Panorama export, so it lives in `tests/responses/` and is not corpus material: the scan
and the fixture assembler read the corpus only. `pyproject.toml` `testpaths = ["tests"]` keeps discovery at the root, and
`pythonpath = ["src"]` is the only place a test path is stated, so a test imports a tool module by name.
The rule is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §1.1.

## Documentation

The full index is [`docs/README.md`](docs/README.md). Each rule lives in one
document; the others link to it.

- [`docs/USAGE_GUIDE.md`](docs/USAGE_GUIDE.md) - how to run each script and
  what each output file holds
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - data model, parse pipeline,
  emit pipeline, and the naming rules
- [`docs/RESOURCE_MAPPING.md`](docs/RESOURCE_MAPPING.md) - v2 mapping rationale
- [`docs/COVERAGE_MATRIX.md`](docs/COVERAGE_MATRIX.md) - coverage matrix, row
  schema, and test methodology
- [`docs/MIGRATION_GUIDE.md`](docs/MIGRATION_GUIDE.md) - migration workflow,
  including the multi-VR case
- [`docs/DEVICE_GROUP_SPLITTING.md`](docs/DEVICE_GROUP_SPLITTING.md) - the
  splitter and how it joins a device group to a template
- [`docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md`](docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md) -
  logical routers
- [`docs/VPN_ROUTING_CONFIG_EXAMPLES.md`](docs/VPN_ROUTING_CONFIG_EXAMPLES.md) -
  input shapes the parser reads
- [`docs/DUAL-LICENSING-EXPLAINED.md`](docs/DUAL-LICENSING-EXPLAINED.md) - the
  two license options

Example input and example output are in [`examples/`](examples/), and its index is
[`examples/README.md`](examples/README.md): the committed sample input, the pointer to the pinned golden
sample, and a real report from the kitchen-sink fixture.

The developer scripts are in [`tools/`](tools/), and its index is
[`tools/README.md`](tools/README.md): the quick start script and the fixture corpus builder.

## Repository layout

The layout rule is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §1.1, which is the owner document. The
root holds `AGENTS.md`, the readme indexes (this file, [`docs/README.md`](docs/README.md),
[`examples/README.md`](examples/README.md), and [`tools/README.md`](tools/README.md)), the
tracking markdown ([`PLAN.md`](PLAN.md), [`backlog.md`](backlog.md), [`to-do.md`](to-do.md),
[`acceptance.md`](acceptance.md), [`agent-status.md`](agent-status.md)), the two license files
([LICENSE-AGPL](LICENSE-AGPL) and [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL)), and the two tool-config files
([`pyproject.toml`](pyproject.toml), which states the layout rules, and
[`requirements.txt`](requirements.txt), the pinned development tools). `docs/` holds every other
document, `tests/` holds every test, `src/` holds the tool's modules, `tools/` holds the developer scripts,
and `examples/` holds the sample input and the two example text files. The canonical sample output is the
golden set `tests/golden/`, so `terraform_output/` is only the default value of `--output-dir` and holds no
committed sample.

## License

This project is **dual-licensed**:

- **AGPL v3** - free for open source use (see [LICENSE-AGPL](LICENSE-AGPL))
- **Commercial** - for proprietary use (see [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL))

The summary of the two options, including the network copyleft rule, is in
[`docs/DUAL-LICENSING-EXPLAINED.md`](docs/DUAL-LICENSING-EXPLAINED.md).

## Additional resources

- [Palo Alto Terraform Provider](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [PAN-OS Advanced Routing](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-networking-admin/advanced-routing)

The converter reads a declared source. By default it reads a file and calls no server.
Reading the PAN-OS API export is an explicit choice (`--source api`), and `--offline`
reads the cache only, so a run that calls no server still produces the same bytes.
