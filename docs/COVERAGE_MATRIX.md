# Coverage Matrix: Provider Resource <-> Panorama XML Element

The machine-readable matrix lives in
[`resource_mapping.py`](../resource_mapping.py) as `COVERAGE_MATRIX`.
These tests enforce it: [`tests/test_coverage_matrix.py`](../tests/test_coverage_matrix.py).

The matrix is the tracked source of truth for **which Panorama XML
element feeds which provider v2 resource type**. It exists so that an
emitter that adds, renames, or drops a resource type can never do so
silently: the drift tests fail when the matrix and the converter
disagree.

## The matrix

One row per emitted provider resource type (20 rows).

| Provider resource | Panorama XML element | Fixture entry | Emitted `name` | Fixture | Output file |
|---|---|---|---|---|---|
| `panos_address` | `address/entry` | `Web-Server-1` | `Web-Server-1` | `address_objects.xml` | `address_objects.tf` |
| `panos_address_group` | `address-group/entry` | `Web-Servers` | `Web-Servers` | `address_groups.xml` | `address_groups.tf` |
| `panos_administrative_tag` | `tag/entry` | `env-prod` | `env-prod` | `tags.xml` | `tags.tf` |
| `panos_application_group` | `application-group/entry` | `web-apps` | `web-apps` | `application_groups.xml` | `application_groups.tf` |
| `panos_custom_url_category` | `custom-url-category/entry` | `blocked-sites` | `blocked-sites` | `custom_url_categories.xml` | `custom_url_categories.tf` |
| `panos_external_dynamic_list` | `external-list/entry` | `threat-ips` | `threat-ips` | `external_lists.xml` | `external_lists.tf` |
| `panos_service` | `service/entry` | `TCP-8080` | `TCP-8080` | `service_objects.xml` | `service_objects.tf` |
| `panos_service_group` | `service-group/entry` | `Web-Services` | `Web-Services` | `service_groups.xml` | `service_groups.tf` |
| `panos_security_policy_rules` | `security/rules/entry` | `Allow-Web-Traffic` | `Allow-Web-Traffic` | `security_rules.xml` | `security_rules.tf` |
| `panos_nat_policy_rules` | `nat/rules/entry` | `Outbound-NAT` | `Outbound-NAT` | `nat_rules.xml` | `nat_rules.tf` |
| `panos_security_profile_group` | `profile-group/entry` | `Strict-Profile` | `Strict-Profile` | `security_profile_groups.xml` | `security_profile_groups.tf` |
| `panos_ethernet_interface` | `ethernet/entry` | `ethernet1/1` | `ethernet1/1` | `interfaces_ethernet.xml` | `interfaces.tf` |
| `panos_ethernet_layer3_subinterface` | `ethernet/entry` | `ethernet1/1` | `ethernet1/1.0` | `interfaces_ethernet.xml` | `interfaces.tf` |
| `panos_virtual_router` | `virtual-router/entry` | `default` | `default` | `virtual_routers.xml` | `virtual_routers.tf` |
| `panos_virtual_router_static_route_ipv4` | `static-route/entry` | `default-gw` | `default-gw` | `virtual_routers.xml` | `virtual_routers.tf` |
| `panos_zone` | `zone/entry` | `trust` | `trust` | `zones.xml` | `zones.tf` |
| `panos_ike_crypto_profile` | `crypto-profiles/ike-crypto-profiles/entry` | `IKE-DEFAULT` | `IKE-DEFAULT` | `ike_crypto_profiles.xml` | `vpn.tf` |
| `panos_ike_gateway` | `ike/gateway/entry` | `IKE-GW-Branch` | `IKE-GW-Branch` | `ike_gateways.xml` | `vpn.tf` |
| `panos_ipsec_crypto_profile` | `crypto-profiles/ipsec-crypto-profiles/entry` | `IPSEC-DEFAULT` | `IPSEC-DEFAULT` | `ipsec_crypto_profiles.xml` | `vpn.tf` |
| `panos_ipsec_tunnel` | `tunnel/ipsec/entry` | `TUN-Branch` | `TUN-Branch` | `ipsec_tunnels.xml` | `vpn.tf` |

Report-only types (`REPORT_ONLY_TYPES`) have no row and can never gain
one without first leaving the report-only set and entering
`EMITTED_TYPES` — the exact-set test enforces both directions.

## Row schema

Each row is a dict with exactly six fields:

| Field | Meaning |
|---|---|
| `resource` | The provider v2 resource type the generator emits. Must be in `EMITTED_TYPES`. |
| `xml_element` | The tag path of the Panorama XML element whose `<entry>` feeds the resource. Scope prefixes (`shared/`, `device-group/entry/`, `vsys/entry/`, `templates/entry/`) vary per export and are not part of the element identity; the tests search the fixture at any scope. |
| `xml_name` | The `<entry name=...>` in the row's fixture that feeds the resource. |
| `emitted_name` | The `name` attribute the emitted resource must carry. Equals `xml_name` except where the converter derives a name: the `.0` layer-3 subinterface is emitted as `ethernet1/1.0` from the `ethernet1/1` entry. |
| `fixture` | The XML fixture under `tests/fixtures/` whose pipeline run exercises the row. |
| `output_file` | The `.tf` file (relative to the output directory) that must contain the resource block. |

## Testing methodology

`tests/test_coverage_matrix.py` enforces the matrix in three
directions, one test per row where noted:

1. **Row set (once).** The row `resource` set is exactly
   `EMITTED_TYPES`: no missing type, no duplicate row, no row for a
   type the converter does not emit. This is the drift guard — an
   emitter change must update the matrix in the same change.
2. **Element grounding (per row).** The row's fixture must exist and
   must contain an element whose tag chain ends in `xml_element`, with
   an entry named `xml_name`. The element column cannot name a
   structure the Panorama export does not actually hold.
3. **Pipeline (per row).** The converter runs end-to-end (CLI,
   subprocess) on the row's fixture. The output must contain a
   `resource "<type>"` block in `output_file` whose body carries
   `name = "<emitted_name>"`. This proves the full parse + generate
   path maps the element to the provider resource, not just the parser
   in isolation.

Implementation notes:

- Per-fixture pipeline runs are cached per test session
  (module-level dict), so a fixture shared by two rows
  (`interfaces_ethernet.xml` feeds both ethernet resource types)
  converts only once.
- A resource block runs from its `resource "..." "..." {` line to the
  first line that is exactly `}` at column 0. Nested object values and
  the `location` block close on indented lines, so the first
  unindented brace is always the block end.
- Tests identify resources by provider type and PAN-OS `name`, never
  by the generated local name (F2.7 hashed local names are
  deterministic but must not be asserted by tests).

### How this project verifies Terraform output

- **Provider schema source.** The panos provider's resource schemas
  come from `terraform providers schema -json`, run by
  `terraform init` against the exact source + version declared in the
  golden `provider.tf` (currently
  `PaloAltoNetworks/panos ~> 2.0.14`). There is no Python package for
  the schema; the conformance tests consume this JSON.
- **Schema conformance.** `tests/test_resource_mapping.py` checks that
  every `EMITTED_TYPES` type exists in the provider schema and that
  every `REPORT_ONLY_TYPES` type is genuinely absent from it.
- **Validation gate.** `tests/test_terraform_validate.py` runs
  `terraform init` + `terraform validate` on three generated outputs:
  the sample config, the kitchen-sink fixture (every resource type),
  and the crypto-profile-only fixture (the standalone `vpn.tf`
  emission path).
- **Golden files.** `tests/golden/sample` and `tests/golden/kitchen_sink`
  pin the converter output byte-for-byte for the two committed cases.
- **Canonical commands.** `python3 -m pytest` runs the full suite
  (requirements.txt pins `pytest==9.1.1`, `ruff==0.16.10`);
  `ruff check .` is the lint gate.

## Maintenance duty

An emitter change that adds, renames, or drops a provider resource
type must update `COVERAGE_MATRIX` in the same change. A new row
needs a fixture (or a new entry in an existing fixture) that contains
the Panorama element with a stable entry name. When the work is done,
all three enforcement directions must pass: row set, element
grounding, and the per-row pipeline test.
