# Coverage Matrix: Provider Resource <-> Panorama XML Element

The machine-readable matrix lives in
[`../src/resource_mapping.py`](../src/resource_mapping.py) as `COVERAGE_MATRIX`.
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

One row per emitted provider resource type (40 rows: 34 before F7.8, plus the six routing-profile filter
containers, of which the six scope rows F6.5 added are part of the 34). The table below shows the
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
| `panos_aggregate_layer3_subinterface` | `aggregate-ethernet/entry/layer3/units/entry` | `ae1.101.20` | `ae1.101.20` | `interfaces_other.xml` | `interfaces.tf` |
| `panos_virtual_router` | `virtual-router/entry` | `default` | `default` | `virtual_routers.xml` | `virtual_routers.tf` |
| `panos_virtual_router_static_route_ipv4` | `static-route/entry` | `default-gw` | `default-gw` | `virtual_routers.xml` | `virtual_routers.tf` |
| `panos_zone` | `zone/entry` | `trust` | `trust` | `zones.xml` | `zones.tf` |
| `panos_ike_crypto_profile` | `crypto-profiles/ike-crypto-profiles/entry` | `IKE-DEFAULT` | `IKE-DEFAULT` | `ike_crypto_profiles.xml` | `vpn.tf` |
| `panos_ike_gateway` | `ike/gateway/entry` | `IKE-GW-Branch` | `IKE-GW-Branch` | `ike_gateways.xml` | `vpn.tf` |
| `panos_ipsec_crypto_profile` | `crypto-profiles/ipsec-crypto-profiles/entry` | `IPSEC-DEFAULT` | `IPSEC-DEFAULT` | `ipsec_crypto_profiles.xml` | `vpn.tf` |
| `panos_ipsec_tunnel` | `tunnel/ipsec/entry` | `TUN-Branch` | `TUN-Branch` | `ipsec_tunnels.xml` | `vpn.tf` |
| `panos_device_group` | `device-group/entry` | `Edge-FW` | `Edge-FW` | `scope_objects.xml` | `scope.tf` |
| `panos_device_group_parent` | `device-group/entry` | `Edge-FW` | `Edge-FW` | `scope_objects.xml` | `scope.tf` |
| `panos_template` | `templates/entry` | `Edge-Networks` | `Edge-Networks` | `scope_objects.xml` | `scope.tf` |
| `panos_template_stack` | `template-stack/entry` | `Edge-Stack` | `Edge-Stack` | `scope_objects.xml` | `scope.tf` |
| `panos_template_variable` | `variable/entry` | `edge-tag` | `edge-tag` | `scope_objects.xml` | `scope.tf` |
| `panos_vsys` | `vsys/entry` | `edge-vsys` | `edge-vsys` | `scope_objects.xml` | `scope.tf` |
| `panos_filters_access_list_routing_profile` | `network/routing-profile/filters/access-list/entry` | `ACL-Filter` | `ACL-Filter` | `filter_containers.xml` | `filters.tf` |
| `panos_filters_as_path_access_list_routing_profile` | `network/routing-profile/filters/as-path-access-list/entry` | `ASPath-Filter` | `ASPath-Filter` | `filter_containers.xml` | `filters.tf` |
| `panos_filters_prefix_list_routing_profile` | `network/routing-profile/filters/prefix-list/entry` | `Prefix-Filter` | `Prefix-Filter` | `filter_containers.xml` | `filters.tf` |
| `panos_filters_community_list_routing_profile` | `network/routing-profile/filters/community-list/entry` | `Community-Filter` | `Community-Filter` | `filter_containers.xml` | `filters.tf` |
| `panos_filters_bgp_route_map_routing_profile` | `network/routing-profile/filters/route-maps/bgp/bgp-entry/entry` | `RouteMap-Filter` | `RouteMap-Filter` | `filter_containers.xml` | `filters.tf` |
| `panos_filters_route_maps_redistribution_routing_profile` | `network/routing-profile/filters/route-maps/redistribution/redist-entry/entry` | `Redist-Filter` | `Redist-Filter` | `filter_containers.xml` | `filters.tf` |

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
| `emitted_name` | The `name` attribute the emitted resource must carry. Equals `xml_name` except where the converter derives a name: the `.0` layer-3 subinterface is emitted as `ethernet1/1.0` from the `ethernet1/1` entry. For `panos_device_group_parent` the provider declares no `name`, so the value is the entry name carried by the field `entry_coverage.name_field` states. |
| `fixture` | The XML fixture under `tests/fixtures/` whose pipeline run exercises the row. |
| `output_file` | The `.tf` file name that must contain the resource block. The run writes it inside the unit directory the manifest row names (§14), so a test reads the parts that name it, keyed by the path from the output directory. |
| `emitter` | The `TerraformGenerator` method names that read this row's properties. Usually one method. Two names appear when a report writer reads a property the `.tf` emitter does not, which is the case for `panos_address`: the manual setup report prints a report-only address row from the same parsed object. |
| `properties` | The keys of the parsed object that the row's emitters read. The entry name and the five scope facts are not properties: they are the row identity (§2.2 of [`ARCHITECTURE.md`](ARCHITECTURE.md)), so they are not listed here. |

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

A row that names `disable_override` names a property the pinned provider declares
for its type. Nine rows name it: `panos_address` (F3.4), `panos_service` (F6.2),
and the seven the parse reads through `_get_text` (F4.4). One
helper states the print shape for all nine,
`TerraformGenerator.emit_disable_override`: the string, printed after the entry's
descriptive field, or after `name` when the block prints no descriptive field, and
only when the value is `yes` or `no`, so an entry with no value prints nothing. The
row set against the provider is pinned by
`tests/test_resource_mapping.py::test_the_flag_rows_are_the_types_the_provider_declares_it_for`,
and the shape by `tests/test_ownership.py::test_the_seven_emitters_print_the_flag`.

The six scope rows (F6.5) add two facts the other rows do not state:

- The sub-block a scope row places itself in comes from `SCOPE_PLACEMENT`, and each key it names is a
  scope fact, so a row declares no property for it (`entry_coverage.NON_FIELD_KEYS`).
  `panos_template_variable` is the row with two possible sub-blocks, `template` and `template_stack`, so
  the emitter reads the fact the export declares to choose between them (F6.10.5).
- The device-group row declares `parent`, and the device-group block prints none: the provider has
  no `parent` attribute for `panos_device_group`, so the value reaches the output through the parent
  record the same entry feeds. The shape test excludes that property, because it is printed by another
  block (`tests/test_scope_objects.py::PRINTED_BY_ANOTHER_BLOCK`).
- `resource_mapping.SCOPE_SHAPE` states the provider shape of each property the row prints at
  the block's own level (`devices` is a list of objects, `templates` a list of strings, `type` an
  object), so the emitter cannot print a string where the provider takes an object. Pinned by
  `tests/test_scope_objects.py::test_scope_shape_is_the_provider_shape` against the live provider
  schema, and `::test_scope_shape_covers_the_properties_the_rows_declare` against the rows.

The row is the part of the cross-source shadow scan key the scan compares (F5.4): a child entry name
that repeats a parent entry name is a finding only when both entries are covered by the same row, so
the same name under a different row is not a shadow. The rest of the key is the declared scope facts, and
the key rule is the one `ARCHITECTURE.md` §3.2 states. Pinned by
`tests/test_shadow_coverage.py::test_the_matrix_row_is_the_key_not_the_name_alone`, and the scan
scope is the same rule (`::test_the_scan_scope_is_the_f4_4_rule`).

The row is the key of the state scan too (F5.6). A state entry has no container path, so the row is
the one `MATRIX_BY_RESOURCE` keys by the resource type, and the property list is the list drift
compares, on both sides. The scan scope rule holds on both sides: an entry no row covers is not a
finding, and a state resource whose type has no row is not in the index. Pinned by
`tests/test_state_coverage.py::test_the_matrix_row_is_the_same_table_the_property_scan_uses` and
`::test_the_scan_scope_is_the_f4_4_rule_on_both_sides`.

Every row is measured through a corpus entry. `panos_aggregate_layer3_subinterface` was the row that showed
the table limit: `parse_interfaces` reaches an aggregate subinterface with the same relative pattern it uses
for the ethernet shape, so the container table names that container
(`network/interface/aggregate-ethernet/entry/layer3/units`), and the longest match covers the entry inside an
aggregate entry. The element column states the same container, plus the entry inside it, so the entry the
element test reads is the entry the scan measures. `ae1.101` is an aggregate entry whose name carries a unit,
so the group row covers it, and the emitter reaches the subinterface type for it through the name rule.
Pinned by
`tests/test_property_coverage.py::test_the_scan_measures_an_aggregate_subinterface_through_the_aggregate_row`,
and the parity test now names one row with no read of its own: `panos_device_group_parent`.

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
  emitter reads. The cross-check reads the same scope through `matrix_row_for`, so the
  rule about a read keeps one owner and one reader (`ARCHITECTURE.md` §4.6). It reads the
  destination per entry through `entry_coverage.EntryLedger.destination`, which answers a
  destination in one place, so an entry the run reports enters no count even when the row
  that covers its container is an `emitted` row.
  `tests/test_round_trip.py::test_an_entry_the_run_reports_is_not_counted` holds that, and
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`
  holds the scan scope, which the destination rule is not. A field gap
  in a container with no rule is recorded in [`../backlog.md`](../backlog.md).
  A container outside the scan scope is honest only when the output that reaches its entry reads the
  field, because no finding can name a container with no row. Four shapes state that, one per kind.
  A `report` container is honest only when its report section reads the field it prints through the
  captured object, because that section is the only output for the entry. Five pins hold the rule, one per
  container, in `tests/test_property_coverage.py`:
  `::test_the_report_reads_the_application_filter_description_it_prints` (the provider declares no
  `panos_application_filter`, so the report prints the description),
  `::test_the_report_reads_the_schedule_description_it_prints` (`panos_schedule` declares no
  description, so the report prints it),
  `::test_the_security_rule_row_measures_the_profile_group_the_emitter_prints` (the row names
  `profile_group`, and the emitter prints it as `profile_setting = { group = [ ... ] }`, the shape the
  pinned provider declares),
  `::test_the_nat_service_is_read_in_both_export_forms` (`service` is a string, so one member is the
  value the field can hold, and more than one member prints the `# NOTE:` line that names them), and
  `::test_the_report_reads_the_application_override_fields_it_prints` (the provider declares no
  `panos_application_override_rule`, so the report prints `description` and `destination_addresses`).
  The shape of that line is stated once, as `OVERRIDE_REPORT_FIELDS` in `src/panorama_to_terraform.py`:
  the line prints the fields it reads through the captured object in that order, and a field the entry
  carries no value for prints nothing (F4.3 rule 3).

  A `count-only` container has no report section, so the per-entry report line is the only output its
  entry reaches. The line is honest only when it prints the value of each field it names, read through the
  captured object, in the sorted field order the report already uses (`entry_coverage.captured_fields`
  states that order), and a field the entry carries no value for prints nothing (F4.3 rule 3). One pin
  holds the rule, on `tests/fixtures/regions.xml`:
  `::test_the_report_line_reads_the_region_addresses_it_prints` (`parse_regions` keeps `addresses`, so the
  line prints `captured: addresses=[US, CA, MX]`). Measured 2026-11-04 against the pinned provider, none of
  the 128 resources or the 128 data sources names a region, and `panos_address` declares no `region`
  attribute, so no emitter can read a region field and the row cannot become an `emitted` row: the report
  line is the only output a region entry can reach. `entry_coverage.gap_fact` reads the same captured part,
  so the console fact names the same words the report line names.

  A `nested-block` container has no matrix row either, so the per-entry report line is the only output its entry
  reaches, and the line is honest only when it names the fields the print reads through the captured object.
  `parent` is not one of those fields. Measured 2026-11-04 against the pinned provider, three resource types
  declare a `parent` attribute: `panos_ethernet_layer3_subinterface`, `panos_aggregate_layer3_subinterface`, and
  `panos_device_group_parent`. `panos_ethernet_interface`, the type the virtual-wire block prints, declares no
  `parent`, so no line of that block can print a parent. `parent` is therefore a fact of the parent entry, not a
  property of the child, and the child's own name states the parent part (`ethernet1/4.1` is unit `1` of
  `ethernet1/4`), which the `name` line prints as the row identity. So `parse_interfaces` records no `parent`
  value for a `nested-block` entry, and the line names the fields the print reads: `comment` (the printed line),
  `mode` (the block key), and `type` (the type from `INTERFACE_RESOURCE_TYPES`). `parent` stays a captured
  property for the kinds whose row declares it, where the emitter reads it through the child object and prints
  `parent = <parent entry>.name`. One pin holds this shape, on `tests/fixtures/interfaces_ethernet.xml`:
  `::test_the_nested_block_line_names_only_the_fields_the_emitter_reads`.

  A `bookkeeping` container has no matrix row and no captured object, because the fact its row records is
  a relation between an entry and the membership container that lists it. So its entry line names no field:
  the entry carries no value for a relation, the row states the relation in its detail column
  (`association table`, and the five scope facts), and the line prints `captured: name only`, because the
  membership entry contributes only its name, which is the row identity (`entry_coverage.NON_FIELD_KEYS`).
  The value of the relation belongs to the entry that owns the membership container, so a `bookkeeping`
  field is honest only when that owning entry is covered by an `emitted` row whose emitter reads the list
  through that entry's captured object. Where the owning entry's row declares no field for the list, the
  parse method keeps no value for it, because no output can read it. The association itself is read as a
  table, by the location rule (`template_of`, `device_of`) and by the manual report section that names the
  templates a device takes, so it can never be a captured field. Measured 2026-11-04 with a run on
  `tests/fixtures/multi_device_templates.xml`: `parse_device_groups` keeps `devices` and `templates` for
  `Office-FW`, the device group block prints both, and the entry line names them; each membership entry the
  association row covers carries nothing, so its line prints `captured: name only`. One pin holds this
  shape, on that fixture:
  `::test_the_bookkeeping_line_names_no_field_for_the_membership_entry_it_marks`, and the part of the line
  is the data set `entry_coverage.NAMES_NO_FIELD_KINDS`.

   F7.11 completed the six `PROTOCOL_SHAPE` entry rows the router reads, so the router row declares
   a property for each field those rows state, and the scan measures each entry that states them.
   A level inside an entry is not a measured entry: the entry that holds it is, so the fields inside
   the level count as properties of that entry. An interface entry sits inside an area entry, so its
   section path holds an `entry` segment a row path cannot match, and the two interface rows stay
   grounded by the table. Pinned by
   `tests/test_property_coverage.py::test_the_scan_measures_the_six_rows_and_not_a_level_inside_an_entry`.

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
  `terraform init` + `terraform validate` on five generated outputs:
  the sample config, the kitchen-sink fixture (every resource type),
  the crypto-profile-only fixture (the standalone `vpn.tf`
  emission path), the two-device fixture (the `location.ngfw` placement), and the filter fixture (the
  `filters.tf` blocks, read through `sanity_checks.check_terraform` on each unit directory the manifest names).
- **Golden files.** `tests/golden/sample`, `tests/golden/kitchen_sink`, `tests/golden/single_unit` and
  `tests/golden/filter_containers` pin the converter output byte-for-byte for the four committed cases.
- **Canonical commands.** `python3 -m pytest` runs the full suite
  (requirements.txt pins `pytest==9.1.1`, `ruff==0.16.10`);
  `ruff check .` is the lint gate.
