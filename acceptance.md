# Acceptance criteria — F3.5 Multi-vsys (Epic 3)

F3.5 puts the virtual system (vsys) in the data model and in the emitted
`location` block. An object that the export defines under
`devices/entry/<device>/vsys/entry/<vsys>` must land in that virtual system
in the generated Terraform, or be reported when the provider cannot place it
there. No location sub-block comes from memory: every sub-block and field
below is read from `terraform providers schema -json` for 2.0.14.

## What F3.1 and F3.2 already cover (not repeated here)

- Every parse method records `vsys` on every object (F3.1).
- The naming digest and the reference registry key on
  (scope, context, vsys, name) (F3.2).
- Policy chains key on (device group, vsys), so a rule never pivots on a
  rule in another vsys (F3.2).

Remaining gap: `location` never carried vsys, and `vsys_of` reported the
default `vsys1` for entries the export does not place in a vsys, so the
emitter could not tell "shared" from "vsys1".

## Schema facts verified for this task (v2.0.14)

- `location` is a required object. Its sub-blocks differ per resource type.
  The four the converter can use: `device_group { name, panorama_device }`,
  `shared` (empty, or `rulebase` on the four policy-rule types),
  `vsys { name, ngfw_device }`, `template { name, ngfw_device,
  panorama_device, vsys }`.
- Object types (`panos_address`, `panos_address_group`,
  `panos_administrative_tag`, `panos_application_group`,
  `panos_custom_url_category`, `panos_external_dynamic_list`,
  `panos_service`, `panos_service_group`) and the four policy-rule types
  accept `device_group`, `shared`, and `vsys`.
- `panos_security_profile_group` accepts `device_group` and `shared` only.
  A config that sets `location.vsys` fails `terraform validate` with
  "Invalid Attribute Combination" (verified against 2.0.14).
- `panos_zone` and `panos_virtual_router` accept `vsys` and
  `template { …, vsys }`; they have no `device_group` and no `shared`.
- `template` carries `vsys` on `panos_ethernet_interface`,
  `panos_ethernet_layer3_subinterface`, `panos_aggregate_interface`,
  `panos_aggregate_layer3_subinterface`, `panos_loopback_interface`,
  `panos_tunnel_interface`. It does NOT on `panos_vlan_interface`,
  `panos_virtual_router_static_route_ipv4`, `panos_monitor_profile`,
  `panos_ike_gateway`, `panos_ike_crypto_profile`,
  `panos_ipsec_crypto_profile`, `panos_ipsec_tunnel`.
- Terraform does not reject an unknown attribute inside the `location`
  object (verified: `location = { shared = {} }` on `panos_zone`, and
  `template { bogus = "x" }`, both pass `terraform validate`). The schema,
  not `terraform validate`, is the authority on which sub-block a type
  accepts, so the emitter must read the table below.
- `location = { device_group = { name = "Shared" } }` (what the converter
  emits today for shared objects) is schema-valid but names a device group
  called "Shared". The schema's own description of `shared` is "Panorama
  shared object", so `location = { shared = {} }` is the correct output for
  an entry the export defines under `<shared>`.

## Criteria

1. **Honest vsys in the model.** `vsys_of` returns the declared vsys name,
   and `''` when no `<vsys><entry>` ancestor exists. No default `vsys1`.
2. **Source identity in the model.** One parser helper returns the four
   scope facts of an entry: `device_group`, `vsys`, `template` (declared
   template name or `''`), `vsys_device` (the enclosing `devices/entry`
   name or `''`). Every parse method records them, replacing the repeated
   `device_group`/`vsys` pairs.
3. **Identity is unchanged.** The F2.7 + F3.2 digest input stays
   (scope, context, vsys, name) and the reference chain keeps working;
   `''` is a value like any other, so a shared object and a `vsys1` object
   of the same name stay distinct.
4. **Location schema table.** `LOCATION_SCHEMA` in `resource_mapping.py`
   holds, per emitted type, the `location` sub-blocks and their fields that
   the converter may emit (from `device_group`, `shared`, `vsys`,
   `template`). The table is a deliberate subset: the schema also declares
   `ngfw`, `template_stack`, `template_stack_vsys` and `template_vsys` for
   some types, which the converter never uses. A test compares the table
   with the live provider schema: every listed sub-block and every listed
   field must exist in the schema for that type.
5. **Location choice.** `location_block(resource_type, obj)` picks the
   sub-block from the source identity and the table:
   - declared vsys, no declared template, type accepts `vsys` →
     `vsys { name, ngfw_device }`;
   - declared template, type accepts `template` → `template { name }` plus
     `vsys` when the type's `template` declares it and a vsys is declared;
   - otherwise `device_group { name }` for a real device group, `shared`
     for the shared section, and the `template { name = "Shared" }`
     placeholder for template-scoped types with no declared template
     (unchanged; the real template name is F3.6).
   A type that accepts neither `device_group` nor `shared` never receives
   one (criterion 7).
6. **Target device.** `ngfw_device` is emitted when the export names the
   device. `localhost.localdomain` is the PAN-OS placeholder for "this
   device", so it is not a device name: the field is then omitted and the
   resource is listed in the report (criterion 7).
7. **Report what cannot be placed.** Every resource whose declared vsys or
   declared template the emitted location cannot carry is listed in
   `MANUAL_SETUP_REPORT.txt` with the resource type, name, source device
   group/vsys/template, the location that was emitted, and the reason.
   Three cases: the type has no `vsys` sub-block (for example
   `panos_security_profile_group`, `panos_vlan_interface`), the type has no
   `template` sub-block, and the vsys has no target device name.
8. **No invalid location.** No emitted `location` sub-block, and no field
   inside it, is absent from `LOCATION_SCHEMA` for that type. A test checks
   every committed golden block against the table.
9. **Parse paths.** A two-vsys export parses with the right identity on
   every path: sibling vsys entries, objects under a device group, objects
   under `<shared>`, a template that nests a vsys, and the device-level
   network/zone paths. Member lists stay plain names resolved through the
   F3.2 chain.
10. **Tests.** Parser tests for criteria 1-2; emitter tests for criteria
    5-7 (one per branch, plus the report); the schema table test for
    criterion 4; the golden location-shape test for criterion 8; the
    two-vsys fixture test for criterion 9.
11. **Fixtures and goldens.** A fixture covers a named device with two
    vsys, a template that nests a vsys, and the two report cases. The
    kitchen-sink fixture gains the same shapes. Both golden sets are
    regenerated with a reviewed diff, and every changed block is explained
    by criteria 5-7.
12. **Gates:** ruff clean, pytest green, terraform validate green on both
    golden sets.

## Result (2026-10-08)

Criteria 1-3, 5-12 met. Criterion 4 met with the subset direction above.

- Gate: ruff clean; pytest 372 passed; `terraform validate` green on both
  golden sets (4 cases).
- `tests/test_multi_vsys_location.py` (27 tests) covers criteria 1-2, 4-10.
- Two scope decisions, both recorded in `backlog.md`:
  - **`rulebase` is not emitted.** The four policy-rule types declare
    `location.device_group.rulebase` and `location.shared.rulebase`, so a
    pre-rulebase rule *could* name its rulebase. The parser does not yet
    record which rulebase an entry sits in, and the accepted value string
    is unverified (the provider binary carries `pre-rulebase`; it carries
    no `post-rulebase` literal). Emitting a guessed value would move rules.
    The rulebase stays unrecorded and unemitted until that value is
    verified.
  - **Device-aware reference resolution covers device-declared names only**
    (interfaces today). A name no device declared still resolves through
    the F3.2 context chain, which is device-blind by design.
