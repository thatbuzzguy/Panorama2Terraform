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
| Network | `panos_ethernet_interface`, `panos_ethernet_layer3_subinterface`, `panos_virtual_router`, `panos_virtual_router_static_route_ipv4`, `panos_zone`, `panos_monitor_profile` (PBF path monitoring profiles; referenced by PBF rule path monitoring) |
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
`terraform validate`.

## Resource naming

A local resource name is the sanitized PAN-OS name plus an 8-hex digest
of the object's source identity (resource type, defining device group or
template, and name). The name is deterministic: the same object always
gets the same local name, and same-named objects in different device
groups stay distinct. For example:

```hcl
resource "panos_address" "web_server_1_a9a88aa6" {
  name = "web-server-1"
  ...
}
```

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

The following have a v2 provider resource, but the converter captures
only names and entry names — emitting an empty object would create a
misconfigured resource — so they stay in the report until the body
parsing lands (Epic 3):

- Security profile bodies (antivirus, anti-spyware, vulnerability, URL
  filtering, file blocking, WildFire, zone protection)
- Log forwarding profiles
- Schedules

Reports written to the output directory:

- `MANUAL_SETUP_REPORT.txt` - everything above that must be configured
  manually
- `INTERFACE_MIGRATION_REPORT.txt` - interface and IP inventory
- `VPN_MIGRATION_REPORT.txt` - VPN inventory; **pre-shared keys are
  placeholders and must be set before apply**

## Typical outputs

```
provider.tf  variables.tf  README.md
address_objects.tf  address_groups.tf
service_objects.tf  service_groups.tf
tags.tf  custom_url_categories.tf  application_groups.tf  external_lists.tf
security_rules.tf  nat_rules.tf
security_profiles.tf  security_profile_groups.tf
zones.tf  interfaces.tf  virtual_routers.tf
vpn.tf
MANUAL_SETUP_REPORT.txt  INTERFACE_MIGRATION_REPORT.txt  VPN_MIGRATION_REPORT.txt
```

(Only files with content are written; the list above is the union across
all supported inputs.)

## Exporting from Panorama

- **Web UI:** Device -> Setup -> Operations -> save a configuration
  snapshot and extract the XML.
- **CLI:** `show` with `set cli config-output-format xml`.
- **API:** `curl -k -X GET 'https://panorama/api/?type=export&category=configuration&key=KEY' -o config.xml`

## Deploying with Terraform

1. Create `terraform.tfvars` with credentials:

   ```hcl
   panos_hostname = "panorama.example.com"
   panos_username = "admin"
   panos_password = "your-password"
   device_group   = "Production-DG"
   ```

2. `terraform init`
3. `terraform plan` - review every change
4. `terraform apply`

Before deploying: replace placeholder VPN pre-shared keys, review
`MANUAL_SETUP_REPORT.txt`, and adapt interface names to the target
platform (see `INTERFACE_MIGRATION_REPORT.txt`).

## Testing

- `python3 -m pytest` - the full suite: parser and generator unit tests,
  golden byte-for-byte gates, resource-mapping and schema conformance,
  policy order and dependency wiring, robustness, and the F2.8 coverage
  matrix row tests. XML fixtures drive the converter; provider schema
  conformance runs `terraform providers schema -json` against the
  pinned version (skipped when the `terraform` binary or registry
  access is unavailable).
- `tests/test_terraform_validate.py` - `terraform init` + `terraform
  validate` on the sample, kitchen-sink, and crypto-profile-only
  outputs (skipped when the `terraform` binary is absent)
- `ruff check .` - lint

## Documentation

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
