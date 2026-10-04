# Acceptance Criteria — F2.6: Dependency wiring

## Goal
Terraform must apply objects in an order that satisfies PAN-OS
references. Every name attribute that points at an object exported by
this generator must be a Terraform reference (`<resource>.name`) when
the target is declared in the same output. Names that point at objects
outside the export (built-ins such as `any` or `service-ftp`, or
objects not in the export) must stay plain name strings (brown-field).
The old `unique_resource_name` fallback declared phantom resources and
emitted references to resources that `terraform validate` rejects; it
must be gone.

## Definition of Done
1. **Single safe reference resolver.**
   `TerraformGenerator.name_ref(name, scopes, key=None)` returns an
   `HclRef` of `scope.<local>.name` when `(scope, key)` was declared in
   this run, else the plain `name`. Scope order sets precedence
   (object before group). `key` is the registry key when it differs
   from the PAN-OS name (VPN composite keys).
2. **Unsafe fallback removed.**
   `unique_resource_name` is removed. VPN reference sites use the safe
   resolver; an undeclared VPN object emits a plain name (brown-field),
   never a reference to an undeclared resource.
3. **Wired reference sites** (every name list and name attribute):
   - Address group `static` -> address, then address group
   - Address `tags` -> administrative tag
   - Service group `members` -> service, then service group
   - Security rule `source_zones` / `destination_zones` -> zone
   - Security rule `source_addresses` / `destination_addresses` ->
     address, then address group
   - Security rule `services` -> service, then service group
   - NAT rule `source_zones`, `destination_zone`, `source_addresses`,
     `destination_addresses` -> zone / address scopes
   - NAT rule `service` -> service, then service group
   - NAT `interface_address.interface` -> ethernet interface, then
     layer-3 subinterface
   - Zone `network` members -> ethernet interface, then layer-3
     subinterface
   - Virtual router `interfaces` -> ethernet interface, then layer-3
     subinterface
   - Layer-3 subinterface `parent` -> ethernet interface
   - IKE gateway `local_address.interface` -> ethernet interface, then
     layer-3 subinterface
   - IKE gateway `ike_crypto_profile` -> IKE crypto profile
   - Tunnel `auto_key.ike_gateway` -> IKE gateway
   - Tunnel `auto_key.ipsec_crypto_profile` -> IPsec crypto profile
4. **Not wired (intentional).**
   Rule `applications` (built-in PAN-OS app names, no managed scope),
   zone protection and interface management profiles (F3 scope, and the
   profile bodies are comment-only so a reference would dangle),
   security profile group members (profiles are not emitted as
   resources), `tunnel_interface`, PBF / decryption / app-override
   rules (comment-only emitters).
5. **Emit order.**
   `main()` emits ethernet interfaces before zones and virtual routers
   so their `.name` lookups resolve at emission time.
6. **Tests.**
   - New `tests/test_dependency_wiring.py` (CLI run + structural
     regexes, matching the existing suite style) with fixture
     `tests/fixtures/dependency_wiring.xml`:
     - mixed managed / unmanaged member lists emit a reference plus a
       plain string in one list
     - address / address-group name collision resolves to the address;
       service / service-group collision resolves to the service
     - zone membership, virtual router interfaces, subinterface parent,
       and NAT translation interface are wired
     - an undeclared tunnel gateway emits a plain name (regression: the
       old code emitted a reference to an undeclared resource)
     - invariant: every `<type>.<local>.name` reference emitted
       anywhere in the generated output resolves to a resource
       declared in that same output
   - `tests/test_robustness.py` migrates the two
     `unique_resource_name` tests to `declare_resource_name` +
     `name_ref`.
7. **Goldens.**
   `sample` and `kitchen_sink` regenerate. Changed files are limited to
   the wired emitters (group lists, rule lists, zone/VR interface
   lists, subinterface parent, VPN unchanged). `terraform validate`
   passes on both.
8. **Docs.**
   README "Dependency wiring" note; to-do.md, PLAN.md,
   agent-status.md updated; backlog notes that mention
   `unique_resource_name` updated; commit.

## Gate
- `ruff check .` clean
- `pytest` green (terraform validate gates run when terraform exists)
- `terraform validate` green on the sample, kitchen-sink, and
  dependency-wiring generated outputs
