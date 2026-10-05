# Acceptance criteria — F2.9: Real resources or explicit reports

The comment-only `.tf` generators and the report-less name/description
captures are replaced by one of:

1. a real provider v2.0.14 resource, emitted with full parsed data, or
2. an explicit entry in `MANUAL_SETUP_REPORT.txt` naming the item, the data
   that was captured, and the reason it is not emitted.

No output may remain "comment-only Terraform" and no captured item may be
dropped silently.

## Emits real v2 resources

| Panorama area | v2 resource | Emission model |
|---|---|---|
| Decryption rules | `panos_decryption_policy_rules` | one resource per rule, chained per device group in XML order (F2.5 position semantics: first rule `where = "last"`, later rules `where = "after"`, `directly = true`, pivot = previous Panorama rule name, `depends_on` on the previous rule's resource) |
| PBF rules | `panos_pbf_policy_rules` | same per-rule chain model |
| PBF path monitoring profiles | `panos_monitor_profile` | one resource per profile, template-scoped location (default "Shared" template, same convention as the other template-scoped types) |

Field mapping (verified against the v2.0.14 schema and provider source):

- Decryption: `from` -> `source_zones`, `to` -> `destination_zones`,
  `source`/`destination` -> `source_addresses`/`destination_addresses`,
  `source-user` -> `source_user`, `category` -> `category`,
  `service` -> `services` (declared services become `.name` references,
  F2.6), `profile` -> `profile`, `log-setting` -> `log_setting`,
  `log-start` -> `log_success`, `log-end` -> `log_fail`,
  `description` -> `description`, `disabled` -> `disabled`.
  The v2 `action` is an enum (`no-decrypt` | `decrypt` |
  `decrypt-and-forward`) and the inspection mode is a separate
  `type { <key> = {} }` block (`ssl-forward-proxy` -> `ssl_forward_proxy`,
  `ssl-inbound-inspection` -> `ssl_inbound_inspection`,
  `ssh-proxy` -> `ssh_proxy`). Modern PAN-OS exports carry both; legacy
  PAN-OS 9 exports put the mode in the `action` field instead — those map
  to `action = "decrypt"` plus the matching `type` block.
- PBF: `from/zone` -> `from { zone = [...] }`, `source` ->
  `source_addresses`, `source-user` -> `source_users`,
  `destination` -> `destination_addresses`, `application` ->
  `applications`, `service` -> `services`,
  `action/forward` -> `action { forward = { nexthop = { ip_address = "..." },
  egress_interface = "..." } }` with optional
  `monitor = { ip_address, profile, disable_if_unreachable }`,
  `action/discard` -> `action { discard = {} }`,
  `action/no-pbf` -> `action { no_pbf = {} }`,
  `action/forward-to-vsys` -> `action { forward_to_vsys = "vsysN" }`,
  `enforce-symmetric-return` -> `enforce_symmetric_return { enabled = true }`,
  `schedule` -> `schedule`, `description` -> `description`,
  `disabled` -> `disabled`.
- PBF path monitoring profile (`network/profiles/monitor-profile`):
  `action` -> `action` (v2 enum `wait-recover` | `fail-over`),
  `interval` -> `interval` (int), `threshold` -> `threshold` (int).
  The v2 schema has no `description` attribute, so none is emitted.

## Goes to MANUAL_SETUP_REPORT.txt

| Panorama area | v2 resource exists? | Report reason |
|---|---|---|
| Application override rules | No | no v2 resource; rule details listed |
| QoS profiles | No | no v2 resource; profile and class details listed |
| IPsec tunnel monitor profiles | No | no v2 resource. `panos_monitor_profile` manages the PBF path monitoring profile (`network/profiles/monitor-profile`), a different PAN-OS object — verified in the provider/pango source |
| Schedules | Yes (`panos_schedule`) | only the entry names are parsed; the day/time ranges are not captured, and v2.0.14 has no monthly schedule support |
| Log forwarding profiles | Yes (`panos_log_forwarding_profile`) | only name/description are parsed; the `match_list` body is not captured, and an empty profile would be a misconfigured object |
| Zone protection profiles | Yes (`panos_zone_protection_profile`) | only name/description are parsed; the SIP/UDP/TCP/ICMP/DNS options body is not captured; real emission needs profile parsing (Epic 3) |

The six comment-only `.tf` files (`application_override_rules.tf`,
`qos_profiles.tf`, `tunnel_monitor_profiles.tf`, `schedules.tf`,
`log_settings.tf`, `zone_protection_profiles.tf`) are no longer written.

## Bookkeeping

- `resource_mapping.py`: `EMITTED_TYPES` gains the three new types;
  `REPORT_ONLY_TYPES` gains the three no-v2-resource types (app override,
  QoS, IPsec tunnel monitor — the report-only names must not exist in the
  v2 schema, so the IPsec tunnel monitor is named
  `panos_tunnel_monitor_profile`); a new `NOT_EMITTED_TYPES` dict names
  the three types that have a v2 resource but are intentionally not
  emitted (log forwarding, zone protection, schedules), each with the
  reason; `COVERAGE_MATRIX` gains one row per new emitted type.
- Drift guards: every `REPORT_ONLY_TYPES` name must be absent from the
  provider schema; every `NOT_EMITTED_TYPES` name must be present (the
  inverse test); the coverage-matrix exact-set test covers the new rows.
- Fixtures: `decryption_rules.xml` gains a legacy-shape rule;
  `pbf_rules.xml` gains the full action set and a path-monitoring block;
  new `pbf_monitor_profiles.xml` covers both action enum values;
  `kitchen_sink.xml` gains a PBF path monitoring profile and a PBF
  path-monitoring block.
- Kitchen-sink golden regenerated: `monitor_profiles.tf` added, the six
  comment-only `.tf` files removed, decryption and PBF goldens updated.
- `terraform validate` passes on the sample, the kitchen sink, and the
  new fixture outputs (legacy decryption action, PBF monitor block, both
  monitor-profile action values).
