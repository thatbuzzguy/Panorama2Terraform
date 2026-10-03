# Acceptance — F2.2: Resource mapping (old emitted name -> real v2 resource)

## Facts established (verified against provider v2.0.14, 128 resource types)
- Of the 28 emitted types, **15 are missing** from v2 (not 13 — the audit
  list omitted `panos_application_filter` and `panos_external_list`; the
  F1.4 test split of 15 type-XFAIL / 13 type-XPASS confirms 15).
- 13 types already exist in v2 (they still need `location` + attribute
  fixes — F2.3/F2.4).

## Mapping decisions (the 15 missing)
| Old emitted type | v2 target | Kind |
|---|---|---|
| `panos_address_object` | `panos_address` | rename |
| `panos_service_object` | `panos_service` | rename |
| `panos_static_route_ipv4` | `panos_virtual_router_static_route_ipv4` | rename |
| `panos_security_rule_group` | `panos_security_policy_rules` | rename (container, ordered `rules`) |
| `panos_nat_rule_group` | `panos_nat_policy_rules` | rename (container, ordered `rules`) |
| `panos_external_list` | `panos_external_dynamic_list` | rename (url/recurring/description dropped, F2.9 report) |
| `panos_layer2_subinterface` | `panos_ethernet_layer3_subinterface` | rename (parent/tag derived from `.unit` name) |
| `panos_ipsec_tunnel_proxy_id_ipv4` | inside `panos_ipsec_tunnel` | merge into `auto_key.proxy_id[]` |
| `panos_application_filter` | none | report only (v2 `panos_application` is a different concept) |
| `panos_bgp` | none | report only (v2 has only 6 specialized BGP profiles) |
| `panos_bgp_peer` | none | report only |
| `panos_bgp_peer_group` | none | report only |
| `panos_ospf` | none | report only (v2 has only 4 specialized OSPF profiles) |
| `panos_ospf_area` | none | report only |
| `panos_ospf_area_interface` | none | report only |

## Changes
1. `resource_mapping.py` (repo root): `RESOURCE_MAPPING` dict, old type ->
   v2 type, or `None` for report-only. The single source of truth for F2.4.
2. `docs/RESOURCE_MAPPING.md`: the human-readable table with rationale.
3. `tests/test_resource_mapping.py`:
   - mapping keys == the 28 emitted types (parsed from goldens);
   - every non-`None` target exists in the v2.0.14 schema;
   - every `None` entry is genuinely absent from the schema (guards
     against report-only masking a real resource);
   - shares the `provider_schema` fixture moved to `conftest.py`
     (test_schema_conformance.py refactored to use it).
4. Docs correction: "13 missing" -> "15 missing" in PLAN.md and
   agent-status.md (the F1.4 note mis-copied the audit's undercount).

## Gate
- ruff clean.
- Full pytest suite green with the same split (106 passed, 46 xfailed,
  13 xpassed) plus the new mapping tests passing.

## Non-goals
- No emitter changes (F2.3/F2.4).
- No attribute-level rewrites (F2.4).
