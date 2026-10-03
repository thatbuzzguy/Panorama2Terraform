# Acceptance Criteria: F1.2 - Parser unit tests

## Task
Add unit tests for every PanoramaParser parse method. Fixtures are isolated
XML snippets that use the real Panorama config structure.

## Context: bug found while writing fixtures
`parse_virtual_routers` and `parse_logical_routers` return an empty list for
realistic configs. The parser searches `.//template/entry` but Panorama exports
use `<templates><entry>` (different tag name). The device-level path also
misses the real location `.//devices/entry/vsys/entry/network/virtual-router/entry`.
The sample config contains no virtual routers, so this was never exercised.
The README claim "Multi-VR support (tested)" is therefore not supported.

## Acceptance criteria
- [ ] One test per parse method (36 methods), one isolated XML fixture per
      scenario under tests/fixtures/.
- [ ] Fixtures use the real Panorama structure: `<templates><entry>` for
      templates, `devices/entry/vsys/entry/network/...` for per-vsys network
      config, `device-group/entry/pre-rulebase|post-rulebase` for rules.
- [ ] Tests assert the extracted data contract: names, values, member lists,
      types, flags, descriptions.
- [ ] Virtual router and logical router tests use a realistic templates
      structure and a vsys-level structure, and pass (fixes the
      `.//template/entry` path bug in the parser).
- [ ] BGP and OSPF tests cover both the enabled case and the not-enabled
      case (returns None).
- [ ] Address object tests cover ip-netmask, ip-range, fqdn, tags, and the
      skip-reference-only behavior; plus the device-group-overrides-shared
      regression (v4.0.1).
- [ ] Interface tests cover ethernet layer3, vlan, loopback, tunnel, and
      aggregate types.
- [ ] Helper tests cover _get_text and _get_members.
- [ ] All tests pass: `pytest -q`.
- [ ] Lint is clean: `ruff check .`.
- [ ] Sample config output is unchanged (no VRs in the sample, so the parser
      fix must not change the sample output).
