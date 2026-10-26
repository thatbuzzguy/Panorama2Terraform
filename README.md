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

## Quick start

```bash
python3 panorama_to_terraform.py your_export.xml --output-dir terraform_output

cd terraform_output
terraform init
terraform validate
```

Every run ends with a static gate (see [Post-run sanity gate](#post-run-sanity-gate)):
it checks the files it wrote, writes `SANITY_REPORT.txt`, and exits non-zero
when a check fails. Add `--validate` to run `terraform init` + `terraform
validate` in the same run.

Split a Panorama export into one XML file per device group:

```bash
python3 split_device_groups.py your_export.xml --output-dir split_output
```

## Requirements

- Python 3.9+ (standard library only)
- Terraform 1.0+ for the validate gate
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
[`resource_mapping.py`](resource_mapping.py) and
[`docs/RESOURCE_MAPPING.md`](docs/RESOURCE_MAPPING.md).

The provider-resource <-> Panorama-XML-element coverage matrix — one
row per emitted type with the XML element, fixture, and expected name,
enforced by `tests/test_coverage_matrix.py` — is in
[`COVERAGE_MATRIX`](resource_mapping.py) (machine-readable) and
[`docs/COVERAGE_MATRIX.md`](docs/COVERAGE_MATRIX.md) (table + method).

## Dependency wiring

Name attributes that reference an object exported by the same run are
emitted as Terraform `.name` references (for example
`source_addresses = [ panos_address_group.web_servers.name ]`), so
`terraform apply` orders the resources deterministically. Names that
point outside the export — built-in PAN-OS names such as `any`,
`application-default`, or `service-ftp`, or objects in other tenants —
stay plain strings. The converter never declares a resource just to
make a reference work, so the output always passes
`terraform validate`. The resolution order is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.3.

## Resource naming

A local resource name is the sanitized PAN-OS name plus an 8-hex digest
of the object's source identity: resource type, defining device group,
template or owning device, virtual system (vsys), and raw name. The name
is deterministic: the same object always gets the same local name, the
name does not depend on emission order, and same-named objects in
different device groups, virtual systems, templates, or firewalls stay
distinct. Two firewalls that both declare `ethernet1/1` are two resources
with two locations, not one resource and a numeric suffix. The full rule
is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5. For example:

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
[`LOCATION_SCHEMA`](resource_mapping.py), the verified v2.0.14 shape per
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

- BGP (router, peer groups, peers)
- OSPF (router, areas, interfaces)
- Application filters
- Application override rules
- QoS profiles
- IPsec tunnel monitor profiles (note: `panos_monitor_profile` is the
  PBF path monitoring profile, a different PAN-OS object)

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

Reports written to the output directory:

- `MANUAL_SETUP_REPORT.txt` - everything above that must be configured
  manually
- `INTERFACE_MIGRATION_REPORT.txt` - interface and IP inventory
- `VPN_MIGRATION_REPORT.txt` - VPN inventory; **pre-shared keys are
  placeholders and must be set before apply**
- `CONVERSION_REPORT.txt` - one line per entry the parse read: source line,
  object type, entry name, destination, detail, and the fields it captured;
  the file names the input file name, not its path

Both migration reports are grouped by the scope the export declares: device
group first, then the template or the device the entry sits in, then the
object kind inside the section. A section names only the scope the export
states, so the same interface or gateway name on two device groups appears
once under each, and an entry the export places nowhere is the shared
section, named `Shared`. The rule is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.5.

## Typical outputs

```
provider.tf  variables.tf  README.md
address_objects.tf  address_groups.tf
service_objects.tf  service_groups.tf
tags.tf  custom_url_categories.tf  application_groups.tf  external_lists.tf
security_rules.tf  nat_rules.tf  decryption_rules.tf  pbf_rules.tf
security_profiles.tf  security_profile_groups.tf
zones.tf  interfaces.tf  virtual_routers.tf  monitor_profiles.tf
vpn.tf
MANUAL_SETUP_REPORT.txt  INTERFACE_MIGRATION_REPORT.txt  VPN_MIGRATION_REPORT.txt
SANITY_REPORT.txt
```

(Only files with content are written; the list above is the union across
all supported inputs. The kitchen-sink fixture exercises the full set,
and `tests/test_golden_files.py` pins the exact file names and bytes.)

## Exporting from Panorama

- **Web UI:** Device -> Setup -> Operations -> save a configuration
  snapshot and extract the XML.
- **CLI:** `show` with `set cli config-output-format xml`.
- **API:** `curl -k -X GET 'https://panorama/api/?type=export&category=configuration&key=KEY' -o config.xml`

## Safe input

Both scripts read the input through one check (`xml_input.py`) and refuse
input they cannot parse safely before they allocate for it and before they
write any file:

- **Size.** The read is capped at 64 MiB (`--max-input-bytes N`). A
  Panorama export this project has seen is three orders of magnitude
  smaller, and `xml.etree` builds the whole document in memory, so an
  unbounded read is a memory denial of service.
- **A DTD.** A DTD is the only way an entity expansion ("billion laughs")
  or an external entity (XXE) reaches `xml.etree`, and a Panorama export
  never carries one. The check asks the parser, not a text search, so it
  also holds for a UTF-16 export, where a `<!DOCTYPE` text search sees
  nothing. A `<!DOCTYPE` that only appears in a prolog comment is legal
  input and is not a refusal.

A refusal names the file, the limit and the measured size, exits
non-zero, and writes no output. Raise the limit only for a trusted file.
The converter is standard-library only by design: `defusedxml` would close
the DTD class but not the size class, so it is not a reason to add a
dependency.

## Deploying with Terraform

1. Create `terraform.tfvars` with credentials (do not commit it):

   ```hcl
   panos_hostname = "panorama.example.com"
   panos_username = "admin"
   panos_password = "your-password"
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
what you receive, not what the generator intended.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every resource block carries `location` | FAIL |
| `references` | every `.name` reference resolves to a resource declared in the same run | FAIL |
| `variables` | every declared variable has a `var.` consumer | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder (the VPN key `***CHANGE_ME***`) is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

A WARN does not fail the run: a placeholder is correct output that still needs
an action before apply. A FAIL finding exits 1. A SKIPPED check never changes
the exit code, so a run on a machine without terraform still reports the checks
it could not run. The rules are stated once in `sanity_checks.py`; the tests
call that module instead of restating them. The gate is described in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4.6.

## Testing

- `python3 -m pytest` - the full suite: parser and generator unit tests,
  golden byte-for-byte gates, resource-mapping and schema conformance,
  policy order and dependency wiring, robustness, the F2.8 coverage
  matrix row tests, and the F2.10 no-dead-variable checks. XML fixtures drive the converter; provider schema
  conformance runs `terraform providers schema -json` against the
  pinned version (skipped when the `terraform` binary or registry
  access is unavailable).
- `tests/test_terraform_validate.py` - `terraform init` + `terraform
  validate` on the sample, kitchen-sink, and crypto-profile-only
  outputs (skipped when the `terraform` binary is absent)
- `tests/test_sanity_gate.py` - the post-run gate: every check detects its
  violation, no fixture trips a false positive, the report is byte-identical
  between two runs, and the exit code follows the findings
- `ruff check .` - lint

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - data model, parse pipeline,
  emit pipeline, and the naming rules
- [`docs/MIGRATION_GUIDE.md`](docs/MIGRATION_GUIDE.md) - migration workflow
- [`docs/USAGE_GUIDE.md`](docs/USAGE_GUIDE.md) - technical reference
- [`docs/RESOURCE_MAPPING.md`](docs/RESOURCE_MAPPING.md) - v2 mapping rationale
- [`docs/COVERAGE_MATRIX.md`](docs/COVERAGE_MATRIX.md) - coverage matrix, row schema, and test methodology
- [`docs/DEVICE_GROUP_SPLITTING.md`](docs/DEVICE_GROUP_SPLITTING.md) - splitter notes

## License

This project is **dual-licensed**:

- **AGPL v3** - free for open source use (see [LICENSE-AGPL](LICENSE-AGPL))
- **Commercial** - for proprietary use (see [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL))

## Additional resources

- [Palo Alto Terraform Provider](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [PAN-OS API documentation](https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api)
