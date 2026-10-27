# Coverage Matrix: Provider Resource <-> Panorama XML Element

The machine-readable matrix lives in
[`../resource_mapping.py`](../resource_mapping.py) as `COVERAGE_MATRIX`.
These tests enforce it: [`../tests/test_coverage_matrix.py`](../tests/test_coverage_matrix.py).

The matrix is the tracked source of truth for **which Panorama XML
element feeds which provider v2 resource type**. It exists so that an
emitter that adds, renames, or drops a resource type can never do so
silently: the drift tests fail when the matrix and the converter
disagree.

The table below is the matrix as it reads today. Do not maintain it by
hand. Read the table from code, or let the row-set test fail:

```bash
python3 -c "import resource_mapping as rm; [print(r) for r in rm.COVERAGE_MATRIX]"
```

The document index is in [README.md](README.md).

## The matrix

One row per emitted provider resource type (28 rows). The table below shows the
six identity fields; the Row schema section names the other two, which are too
long to read in a table. Read a whole row from the command at the top of this
document.

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
| `panos_decryption_policy_rules` | `decryption/rules/entry` | `Decrypt-HTTPS` | `Decrypt-HTTPS` | `decryption_rules.xml` | `decryption_rules.tf` |
| `panos_pbf_policy_rules` | `pbf/rules/entry` | `PBF-Forward` | `PBF-Forward` | `pbf_rules.xml` | `pbf_rules.tf` |
| `panos_security_profile_group` | `profile-group/entry` | `Strict-Profile` | `Strict-Profile` | `security_profile_groups.xml` | `security_profile_groups.tf` |
| `panos_monitor_profile` | `profiles/monitor-profile/entry` | `PM-Branch` | `PM-Branch` | `pbf_monitor_profiles.xml` | `monitor_profiles.tf` |
| `panos_ethernet_interface` | `ethernet/entry` | `ethernet1/1` | `ethernet1/1` | `interfaces_ethernet.xml` | `interfaces.tf` |
| `panos_ethernet_layer3_subinterface` | `ethernet/entry` | `ethernet1/1` | `ethernet1/1.0` | `interfaces_ethernet.xml` | `interfaces.tf` |
| `panos_vlan_interface` | `vlan/units/entry` | `10` | `vlan.10` | `interfaces_other.xml` | `interfaces.tf` |
| `panos_loopback_interface` | `loopback/units/entry` | `1` | `loopback.1` | `interfaces_other.xml` | `interfaces.tf` |
| `panos_tunnel_interface` | `tunnel/units/entry` | `1` | `tunnel.1` | `interfaces_other.xml` | `interfaces.tf` |
| `panos_aggregate_interface` | `aggregate-ethernet/entry` | `ae1` | `ae1` | `interfaces_other.xml` | `interfaces.tf` |
| `panos_aggregate_layer3_subinterface` | `aggregate-ethernet/entry` | `ae1.101` | `ae1.101` | `interfaces_other.xml` | `interfaces.tf` |
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

Each row is a dict with exactly eight fields:

| Field | Meaning |
|---|---|
| `resource` | The provider v2 resource type the generator emits. Must be in `EMITTED_TYPES`. |
| `xml_element` | The tag path of the Panorama XML element whose `<entry>` feeds the resource. Scope prefixes (`shared/`, `device-group/entry/`, `vsys/entry/`, `templates/entry/`) vary per export and are not part of the element identity; the tests search the fixture at any scope. |
| `xml_name` | The `<entry name=...>` in the row's fixture that feeds the resource. |
| `emitted_name` | The `name` attribute the emitted resource must carry. Equals `xml_name` except where the converter derives a name: the `.0` layer-3 subinterface is emitted as `ethernet1/1.0` from the `ethernet1/1` entry. |
| `fixture` | The XML fixture under `tests/fixtures/` whose pipeline run exercises the row. |
| `output_file` | The `.tf` file (relative to the output directory) that must contain the resource block. |
| `emitter` | The `TerraformGenerator` method names that read this row's properties. Usually one method. Two names appear when a report writer reads a property the `.tf` emitter does not, which is the case for `panos_address`: the manual setup report prints a report-only address row from the same parsed object. |
| `properties` | The keys of the parsed object that the row's emitters read. The entry name and the four scope facts are not properties: they are the row identity (§2.2 of [`ARCHITECTURE.md`](ARCHITECTURE.md)), so they are not listed here. |

The property list is what makes the row a property-level statement, and two tests
keep it honest:

- `tests/test_coverage_matrix.py::test_declared_property_is_a_key_the_emitter_reads`
  checks each declared property against the emitter source, so a row cannot name a
  property its emitter does not read. The check follows `self.<helper>()` calls,
  because an emitter that reads through a helper is still the row's emitter.
- `tests/test_property_coverage.py::test_measured_reads_equal_the_declared_properties`
  measures the keys the corpus outputs read from the entries each row covers, and
  fails when a row declares a property no output reads. A property captured but not
  read is a finding, not a declaration: the report prints it (§3.2).

The row is also the key of the cross-source shadow scan (F5.4): a child entry name that
repeats a parent entry name is a finding only when both entries are covered by the same row,
so the same name under a different row is not a shadow. Pinned by
`tests/test_shadow_coverage.py::test_the_matrix_row_is_the_key_not_the_name_alone`, and the scan
scope is the same rule (`::test_the_scan_scope_is_the_f4_4_rule`).

One row has no corpus entry to measure: `panos_aggregate_layer3_subinterface`,
because the container table maps an aggregate subinterface to the ethernet
subinterface row. That row is grounded by the emitter check only, and the table
limit is recorded in [`../backlog.md`](../backlog.md).

## Testing methodology

`tests/test_coverage_matrix.py` enforces the matrix in five directions, one test per
row where noted:

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
   path maps the element to the provider resource, not the parser in
   isolation.
4. **Row shape (per row).** A row holds the eight fields of the Row schema, the
   emitter names are real `TerraformGenerator` methods, and `properties` is a
   non-empty tuple of names
   (`::test_row_names_its_emitter_and_properties`).
5. **Property grounding (per row).** Each declared property appears as a string key
   inside the row's emitter, or inside the generator helper that emitter calls
   (`::test_declared_property_is_a_key_the_emitter_reads`).

The measured read sets are pinned separately, in
`tests/test_property_coverage.py`, because that check needs a whole pipeline run: the
scan records which keys an output reads from a captured object, so it cannot run inside
one parse method.

Two levels sit beside the matrix:

- **Container level.** `container_coverage.CONTAINER_TABLE` holds one row per
  parse method, with the container it reads and the destination its entries
  take. `tests/test_container_coverage.py` keeps the table and the code in
  step. The rule and the destination kinds are in
  [`ARCHITECTURE.md`](ARCHITECTURE.md) §3.1.
- **Property level.** Each row names the properties its emitter reads (Row schema
  above). A property the parse captured but no output read is a finding, and the
  per-entry report prints those findings in their own section
  ([`ARCHITECTURE.md`](ARCHITECTURE.md) §3.2). The scan scope is the entries a matrix
  row covers, so a report, inventory, bookkeeping, count-only, or nested-block
  container is not a finding: it has no row, and only a row can name the properties an
  emitter reads. Those field gaps are recorded in [`../backlog.md`](../backlog.md).

## Maintenance duty

An emitter change that adds, renames, or drops a provider resource
type must update `COVERAGE_MATRIX` in the same change. A new row
needs a fixture (or a new entry in an existing fixture) that contains
the Panorama element with a stable entry name. An emitter change that
reads a property, or stops reading one, must update that row's
`properties` in the same change, because the parity test measures the
run rather than restating the row. When the work is done, all five
enforcement directions must pass: row set, element grounding, the
per-row pipeline test, row shape, and property grounding.

## How this project verifies Terraform output

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
