# Acceptance criteria — F3.4 Full object types (Epic 3)

F3.4 parses and emits every address and service shape the provider v2.0.14
models, and reports the shapes it does not model. No attribute is taken from
memory: every shape below is verified against the live schema
(`terraform providers schema -json`) and the pango source (the XML element
names the provider reads).

## Schema facts verified for this task (v2.0.14)

- `panos_address` attributes: `name`, `description`, `tags`,
  `disable_override`, `location`, and one value attribute per address type:
  `ip_netmask`, `ip_range`, `ip_wildcard`, `fqdn`. There is no attribute for
  a location-type address (no country, region, continent, or container), so
  location entries cannot be emitted. `disable_override` is a **string**
  taking `"yes"` or `"no"` (not a bool — `terraform validate` rejects
  `true`).
- `panos_external_dynamic_list` attributes: `name`, `location`,
  `disable_override` (string, as above), and a `type` object with the seven
  sub-shapes `domain`, `imei`, `imsi`, `ip`, `predefined_ip`,
  `predefined_url`, `url`. The fields each sub-shape models differ:
  - `predefined_ip`, `predefined_url`: `url`, `description`, `exception_list`;
  - `imei`, `imsi`, `ip`, `url`: the above plus `certificate_profile` and
    `recurring`;
  - `domain`: the above plus `expand_domain` (bool) — domain only.
  Every non-predefined sub-shape also takes `auth` (credential material —
  never captured, see criterion 7).
  Recurring keys: `daily { at }`, `five_minute`, `hourly`,
  `monthly { at, day_of_month }`, `weekly { at, day_of_week }`.
- `panos_service` attributes: `name`, `description`, `tags`,
  `disable_override`, `location`, and `protocol`. The `protocol` object
  *declares* `tcp` and `udp`, but the provider accepts **one leg only**: a
  config that sets both fails `terraform validate` with "Invalid Attribute
  Combination … one (and only one) of" (verified against 2.0.14). Each leg
  takes `destination_port`, `source_port`, and `override` (tcp:
  `halfclose_timeout`, `timeout`, `timewait_timeout`; udp: `timeout`), all
  timeouts are numbers.
- XML element names (pango source): `address/entry` reads `ip-netmask`,
  `ip-range`, `ip-wildcard`, `fqdn`, `tag`, `description`,
  `disable-override`; `service/entry` reads `protocol/{tcp,udp}` with
  `port`, `source-port`, `override>yes` (export shape
  `override/yes/<timeout>`), `tag`, `description`; EDL entries are
  `external-list/entry` with `type/<key>`.

## Criteria

1. **Address type coverage.** `parse_address_objects` reads every
   schema-modeled value element, including `ip-wildcard`, plus `tag`,
   `description` and `disable-override`. The entry's `type` attribute is
   recorded as `declared_type` when the export carries it. The emitter writes
   `disable_override` as the `"yes"`/`"no"` string the schema takes.
2. **Address types with no v2 attribute.** An entry with no modeled value
   element and other content (a location-type entry: country, region,
   continent, container) is captured generically and classified as
   report-only. It is not emitted as an empty `panos_address` resource.
3. **Report.** Report-only address entries appear in `MANUAL_SETUP_REPORT.txt`
   with the entry name, device group, the captured fields, and the reason
   (`panos_address` has no attribute for that type).
4. **EDL type coverage.** `parse_external_lists` covers all seven v2
   sub-shapes and the schema-verified fields (`url`, `description`,
   `exception_list`, `expand_domain`, `certificate_profile`, `recurring` with
   all five keys and their values). The emitter writes only the fields the
   chosen sub-shape models (`EDL_SUBSHAPE_FIELDS`); a field it cannot model
   stays as a NOTE comment, so the output stays valid.
5. **Service shapes.** `parse_service_objects` captures both protocol legs
   (a dual-protocol object loses nothing in the parse model), `source_port`,
   the `override/yes` timeouts, and `tag` members. Multi-port values
   (`80,443`) pass through as the `destination_port` string.
6. **Dual-protocol services.** The emitter writes the primary leg (tcp wins,
   then udp) so the resource stays valid, keeps the dropped leg as a NOTE
   comment in the HCL, and lists it in `MANUAL_SETUP_REPORT.txt` with the
   object name, scope, the leg that was dropped and its captured values.
7. **Credentials.** EDL `auth` (username/password) is not emitted: writing
   credential material into generated HCL is not acceptable. The gap is
   recorded in `backlog.md`.
8. **Naming and references.** The F2.7 + F3.2 contract holds: digest input is
   (scope, context, vsys, name); service `tags` resolve through `name_ref` in
   the referrer's (context, vsys) pair; no dangling references.
9. **Tests.** A test per new shape: ip-wildcard parse and emit;
   disable_override emit; location entry classified and reported; EDL
   sub-shape and field coverage; EDL fields a sub-shape lacks; dual-protocol
   parse keeps both legs and the emit keeps one; multi-port pass-through;
   source_port and override emit; service tags emit and reference resolution.
   `COVERAGE_MATRIX` gains rows only for newly emitted types (none:
   `panos_address`, `panos_service`, `panos_external_dynamic_list`
   already have rows).
10. **Goldens** regenerated for both sets with a reviewed diff.
11. **Gates:** ruff clean, pytest green, terraform validate green.
