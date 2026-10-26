# Adversarial Audit Report — Panorama2Terraform

- **Date:** 2025 (audit session)
- **Repo:** `Panorama2Terraform` @ HEAD `74cf4c0` ("Add support for Advanced Routing Engine")
- **Scope:** all 27 tracked files; full read of both Python programs; injection scan of every text/MD/XML/shell file; cross-check of all emitted Terraform against the real `PaloAltoNetworks/panos` provider (v2.0.14); live `terraform init` + `terraform validate` on generated output.
- **Repo state:** untouched by this audit (no code changes made). The findings
  below describe the audited HEAD; the status table above states the current state.
- **Auditor constraints honored:** no instructions found in the repo were followed; this report is independent analysis.

## Status at the current HEAD

The findings below describe the audited state at `74cf4c0`. They are kept as the
audit record. This section states what the code does now, so a reader does not
take an old finding as a current fact.

| Finding | Now |
|---|---|
| §1 entity expansion | Closed. `xml_input.parse_xml` refuses a DTD before it parses, so no entity expands. A DTD in a prolog comment is not a refusal. |
| §2 invalid Terraform | Closed. Output is validated against the live provider schema, and the committed goldens pin the generated `.tf` files byte for byte. `terraform init` + `terraform validate` runs on every conversion with `--validate`. |
| §3.1 name-keyed dedup | Closed. No parse method deduplicates by name or keeps a name-keyed dict; same-named entries in different scopes are separate objects. |
| §3.2 location | Closed. `location` is on every resource, from `LOCATION_SCHEMA`, per object, driven by the scope the export declares. The `device_group` variable is gone. |
| §3.3 policy order | Closed. One resource per rule, chained by `(device group, vsys)` in XML order, with `depends_on`. The rulebase is still not recorded; that is a decided limit in `backlog.md`. |
| §3.5 multi-vsys | Closed. `location.vsys` is emitted for the types that accept it. |
| §3.6 interfaces | Closed. Ethernet, VLAN, loopback, tunnel, aggregate, and layer-3 subinterfaces emit. Virtual-wire and TAP are blocks inside the parent interface resource, so they have no resource type of their own. |
| §3.7 address types | Closed for `ip-netmask`, `ip-range`, `fqdn`, `ip-wildcard`, and IPv6. Country, region, continent, container, and external types have no `panos_address` attribute, so they are reported, not dropped. |
| §3.8 services | Partially by design. The provider accepts one protocol leg, so the converter emits tcp (or udp when tcp is absent) and reports the dropped leg with its ports. Multi-port and ranges emit as one port string. |
| §3.9 comment-only generators | Closed for decryption, PBF, zones, monitor profiles, and VPN. Application override, QoS, log forwarding, zone protection, and tunnel monitor are report-only, each with the reason. `security_profiles.tf` stays a comment inventory because the profile body is not parsed. |
| §3.10 invented references | Closed. No hardcoded `panos_virtual_router.default` and no hardcoded OSPF area. BGP and OSPF are report-only: the provider has no resource that accepts a router ID, AS number, or peer data. |
| §3.11 dependency wiring | Closed. References resolve to resources declared in the same run, and the gate check `references` fails an unresolved one. |
| §3.12 VPN keys | Unchanged by design: the placeholder stays, the report lists the action, and the gate reports it as WARN. |
| §4.1 name collisions | Closed. The local name is the sanitized name plus an 8-hex digest of the source identity; a true duplicate gets a numeric suffix. |
| §4.2 empty names | Closed. An empty name becomes `unnamed`. |
| §4.3 splitter crash on a quoted name | Closed. The splitter compares `entry.get('name')` instead of building an XPath from the name. |
| §4.4 substring template match | Closed. The join rule is the device a device group, a template, and a template stack all list. |
| §4.5 shared merge corruption | Closed. Entries are copied with `copy.deepcopy`, and the merge keeps one entry per name inside a container. |
| §4.6 control characters | Closed. `escape_string` escapes `\t`, `\r`, `\n` and strips the remaining C0 control characters and DEL. The gate check `control_chars` fails a raw control character in a `.tf` file. |
| §4.7 no tests | Closed. `pytest` is the test suite, and CI runs `ruff check .` plus `pytest`, with a job that runs `terraform init` + `terraform validate`. |
| §4.9 committed sample XML | Kept as an exception: the committed XML is the project's own test corpus, and `.gitignore` states the rule and the exception. A real customer export is never committed. |
| §4.10 dead variables | Closed. The provider block consumes the three credential variables, and the gate check `variables` fails a declared variable with no consumer. |
| §6.6 marketing claims | Closed. README and the module docstrings state what the tool does and what it reports, without a coverage or success-rate claim. |

The remaining open items are in [`backlog.md`](backlog.md).


---

## Executive Summary

| Area | Verdict |
|---|---|
| Prompt injection / hidden instructions / behavior manipulation | **NONE FOUND** |
| Malicious behavior (network, exec, eval, exfiltration) | **NONE FOUND** — pure local XML→text converter |
| Core function (valid Panorama→Terraform) | **BROKEN** — output fails `terraform validate` against the provider it pins |
| Complex import scenarios (multi-DG, multi-vsys, ordered policy) | **STRUCTURALLY UNSUPPORTED** — silent data loss + policy reordering |
| Marketing claims ("100% success on production data", "95%+ coverage") | **CONTRADICTED BY EVIDENCE** |
| Licensing | AGPL v3 dual-license — legal review required before internal/SaaS use |
| Recommendation | **DO NOT USE for a real migration** until the generator is rewritten against the real v2 provider schema and CI validates output |

---

## 1. Injection / Behavior-Change Scan (CLEAN)

Scans performed, all negative:

- Zero-width / bidi-override / invisible Unicode characters in every file
- Base64/hex blob heuristics (≥200 chars) in every file
- AI-directed imperatives ("ignore previous", "as an AI", "don't tell the user", "secretly", "override instructions", etc.) across `.py`, `.md`, `.txt`, `.xml`, `.sh`
- Dynamic code execution: `subprocess`, `socket`, `urllib`, `requests`, `eval(`, `exec(`, `__import__`, `compile(` — **none**
- Full import inventory of both scripts: only `xml.etree.ElementTree`, `argparse`, `os`, `json`, `re`, `pathlib`, `typing`, `sys`, `traceback`
- `quick_start.sh`: benign (checks python3, runs converter on sample, prints next steps)
- `.github/workflows/python-tests.yml`: benign (py_compile + `--help`)

**Conclusion: no attempt to change AI/agent behavior or inject instructions exists in the repo.**

### One security-relevant property (low severity)

`xml.etree.ElementTree` (used in both scripts) **does expand internal DTD entities** — verified: a 4-level nested entity chain expanded to 10⁴ chars; a full billion-laughs (depth 9) would be ~10¹⁰ chars → memory DoS. Only exploitable if someone parses a hostile "Panorama export". Hardening option: `defusedxml` or a custom parser that rejects DTDs.

---

## 2. CRITICAL: Generated Terraform Is Invalid (Show-Stopper)

### Evidence (reproducible)

```bash
python3 panorama_to_terraform.py sample_panorama_config.xml --output-dir /tmp/tf_out
cd /tmp/tf_out
terraform init -backend=false      # installs paloaltonetworks/panos v2.0.14 (per pin)
terraform validate
```

Result on the repo's own **tiny** sample (7 addresses, 3 groups, 3 services, 3 sec rules, 2 NAT rules):

```
24 errors:
  15  Error: Invalid resource type
        - 4x "panos_address_object"
        - 4x "panos_nat_rule_group"
        - 6x "panos_security_rule_group"
        - 6x "panos_service_object"
   5  Error: Unsupported argument   ("static_value" x3, "services" x1, "description" x1)
   4  Error: Missing required argument ("location")
```

(Errors behind "Invalid resource type" hide further attribute errors; real-world configs fail far more.)

### Root cause

`panorama_to_terraform.py:2056` pins `version = "~> 2.0.7"` (provider **v2**), but the code emits a **v1-style / partly invented schema**. The v2 provider renamed resources, made `location` **required** on every resource, and nested many attributes into blocks.

### Mismatch table (verified against provider docs + validate output)

| Code emits (line ref) | Real v2 resource | Other defects |
|---|---|---|
| `panos_address_object` (gen: `generate_address_objects`, ~2104) | `panos_address` | uses `value`+`type`; real: `ip_netmask` / `ip_range` / `fqdn` / `ip_wildcard` |
| `panos_service_object` (~2169) | `panos_service` | flat `protocol`+`destination_port`; real: nested `protocol = { tcp = { destination_port = "80" } }` |
| `panos_security_rule_group` (~2380) | `panos_security_policy_rule(s)` | `position_keyword = "bottom"` + singular `rule {}`; real: `position = { where = ... }` + `rules = [...]` list |
| `panos_nat_rule_group` (~2440) | `panos_nat_policy_rule(s)` | `original_packet {}` block doesn't exist in that form |
| `panos_bgp`, `panos_bgp_peer`, `panos_bgp_peer_group` (~3001) | split into `panos_bgp_*_routing_profile` resources | **do not exist in v2** |
| `panos_ospf`, `panos_ospf_area`, `panos_ospf_area_interface` (~3062) | `panos_ospf_*_routing_profile` resources | **do not exist in v2** |
| `panos_static_route_ipv4` (~2741) | `panos_virtual_router_static_route_ipv4` | not a v2 name |
| `panos_layer2_subinterface` (~2793) | `panos_ethernet_layer3_subinterface` (or layer2 handling inside `panos_ethernet_interface`) | not a v2 name |
| `panos_ipsec_tunnel_proxy_id_ipv4` (~3247) | no such resource (proxy-id lives inside `panos_ipsec_tunnel`) | not a v2 resource |
| `panos_ethernet_interface` (~2761) | name OK | emits `mode`, `static_ips`, `management_profile`; real: nested `layer3 = { ipv4 = { ip_address = [...] } }` |
| `panos_ike_gateway` (~3170) | name OK | flat `peer_address_type`/`pre_shared_key`/`auth_type`; real: nested `peer_address{}`, `authentication{}`, `protocol{}` |
| `panos_ike_crypto_profile` (~3127) | name OK | `dh_groups`/`authentications`/`encryptions`/`lifetime_hours`; real: `dh_group`/`hash`/`encryption`/`lifetime{}` |
| `panos_ipsec_tunnel` (~3222) | name OK | `type = "auto-key"`, `ak_ike_gateway`; real: nested `auto_key { ... }` |
| **ALL resources** | — | **missing required `location` block** (device_group / shared / vsys) |

### Marketing contradiction

README.md:307, 453-455 claims *"Production-tested on 133,000-line config with 10,000+ objects"*, *"95%+ coverage"*, *"100% success rate on production data"*. The Python script "succeeding" (not crashing) is evidently what was measured — the Terraform output does not validate.

---

## 3. Complex-Import Gaps (multi-DG / multi-vsys / ordered policy)

1. **Hierarchical model flattened → silent data loss.** ~40 parsers dedup by name with first-wins `seen_names` (e.g., `panorama_to_terraform.py:535-549`). Panorama legally allows same-named rules/objects in different device groups (e.g. `Default-Deny` per DG) — all but the first are **dropped silently**.
2. **Device-group association lost.** `variable "device_group"` is emitted (line ~2094) but **never used by any resource**; no `location` block is generated. Everything would land in `shared`, defeating per-DG migration.
3. **Policy order destroyed.** All rules get `position_keyword = "bottom"` (lines 2391, 2451); no position/pivot chain; pre-rulebase and post-rulebase (lines 539-540) merged into one flat list. PAN-OS is first-match — reordering allow/deny changes security posture.
4. **Per-DG object overrides collapse** (name-keyed dicts, last-wins; e.g., `parse_address_objects` ~308-377).
5. **Multi-vsys not represented at all.**
6. **Interfaces:** only physical `ethernet` emitted (line 2770 `if iface['type'] != 'ethernet': continue`). **VLAN, loopback, subinterfaces, virtual-wire, TAP, aggregate are all dropped** from .tf output.
7. **Address types:** only `ip-netmask`/`ip-range`/`fqdn` (lines ~340-360). **IPv6, ip-wildcard, external, location silently dropped.**
8. **Services:** only first `tcp` OR `udp`, single port (lines ~460-478); multi-port, ranges, tcp+udp lost.
9. **Placeholder "coverage":** decryption, PBF, app-override, zone-protection, log-settings, QoS, tunnel-monitor generators emit comment-only files (lines 2505-2640).
10. **Hardcoded assumptions / silent TODOs:** BGP/OSPF reference `panos_virtual_router.default` unconditionally (lines 3011, 3026, 3039, 3072, 3084, 3097 — breaks unless a VR is literally named `default`); OSPF interface area hardcoded as `ospf_area = "0.0.0.0"  # Adjust to correct area` (line 3098).
11. **No dependency wiring:** no `depends_on` between objects; references are bare name strings → nondeterministic apply ordering → "not found" failures.
12. **VPN keys:** pre-shared keys emitted as `***CHANGE_ME***` placeholders (by design, documented) — fine only if the user actually replaces them.

---

## 4. Code Rough Spots / Concrete Bugs

| # | Bug | Location | Evidence |
|---|---|---|---|
| 1 | `sanitize_name` collisions: `Web-Server-1`, `Web_Server_1`, `web server 1`, `WEB.SERVER.1` → all `web_server_1` → duplicate resource blocks | `panorama_to_terraform.py:2028` | reproduced; 5 distinct names → 2 resource names |
| 2 | All-special/empty names → empty resource name `resource "..." "" {}` (invalid HCL) | same fn; `sanitize_name("///") == ''` | reproduced |
| 3 | `split_device_groups.py` **crashes** (`SyntaxError: invalid predicate`, unhandled) on a DG name containing `'` — f-string XPath | `split_device_groups.py:61` (`dg_xpath`), `:106` (`template_xpath`) | reproduced with `DG-O'Hare` |
| 4 | Fragile template matching by substring: `device_group_name.lower() in t_name.lower()` | `split_device_groups.py:110-117` | code read |
| 5 | `<shared>` merge logic appends nested `.//entry` nodes into the first-seen container — can corrupt nesting | `split_device_groups.py:75-100` | code read |
| 6 | `escape_string` doesn't escape `\r` / control chars | `panorama_to_terraform.py:2039` | code read |
| 7 | Entity-expansion DoS on hostile XML (see §1) | both scripts, `ET.parse` | reproduced 10⁴-char expansion |
| 8 | **No tests** — CI runs only `py_compile` + `--help`; nothing validates generated Terraform | `.github/workflows/python-tests.yml` | this is why finding §2 shipped |
| 9 | `.gitignore` ignores `*.xml` ("Customer data - DON'T commit") yet `sample_panorama_config.xml` is committed | `.gitignore`, `git ls-files` | minor hygiene inconsistency |
| 10 | `variables.tf` defines `panos_hostname/username/password` as `sensitive = true` but nothing consumes them (provider block has them commented out) | `panorama_to_terraform.py:2049-2103` | dead config surface |

---

## 5. Risks of Using This Tool

1. **Silent data loss in a security-critical migration** (dropped per-DG rules, lost policy order, dropped VLANs/IPv6). A user who hand-fixes the validate errors and applies would end up with a **wrong security posture** (reordered allow/deny, missing rules) that may appear to work.
2. **False confidence** from README claims ("100% success", "production-tested") — contradicted by direct evidence.
3. **AGPL v3 copyleft:** internal/SaaS use without the commercial license requires publishing source + modifications over the network. Legal review required. (See `LICENSE-AGPL`, `LICENSE-COMMERCIAL`, `docs/DUAL-LICENSING-EXPLAINED.md`.)
4. **Supply chain:** clean — no network/exec paths; no exfiltration vector.
5. **Operational:** VPN keys, OSPF areas, and several profile types require manual follow-through that is easy to miss.

---

## 6. Recommendations / Next-Session Tasks

Priority order:

1. **Add a CI gate that runs `terraform init` + `terraform validate`** on the generated sample output. (Blocks any of the §2 class of bugs.) Requires a `provider` config with dummy env vars; use `terraform validate` (no plan/apply).
2. **Rewrite the generator against real v2 provider schemas:**
   - Correct resource type names (see §2 table)
   - `location = { device_group = { name = ... } }` (or `shared = {}`) on **every** resource, driven by where the object came from in the XML
   - Correct nested blocks (`protocol{}`, `layer3{}`, `auto_key{}`, `position{}`)
   - Order-preserving policy emission: one `rules = [...]` list per (DG, rulebase) in original XML order, or `position = { where = "after", pivot = ... }` chains
   - `depends_on` wiring or reference via `.name` attributes where the provider supports it
   - Collision-safe resource naming (suffix on hash of source path/DG, not just name)
3. **Fix the splitter** (`split_device_groups.py`): quote-safe XPath (iterate and compare `get('name')` instead of f-string XPath), correct shared-merge, real tests.
4. **Expand parsers** for IPv6/wildcard/external addresses, multi-port services, VLAN/loopback/subinterfaces, per-DG rule variants (key by `(device_group, rulebase, name)`).
5. **Replace placeholders** (decryption, PBF, app-override, QoS, log-settings) with real resources or explicit "not exported — manual" reports with a checklist.
6. **Remove/soften marketing claims** in README until validated; replace "success rate" with test evidence.
7. **Harden XML parsing** (reject DTDs / use `defusedxml`) if untrusted inputs are in scope.
8. **Legal:** route AGPL/commercial dual-licensing through counsel before internal adoption.

---

## 7. Appendix — Key Reproduction Commands

```bash
cd /home/ryan/external/Panorama2Terraform

# A. Full pipeline + validation (finding §2)
python3 panorama_to_terraform.py sample_panorama_config.xml --output-dir /tmp/tf_out
cd /tmp/tf_out && terraform init -backend=false && terraform validate

# B. Name collision (finding §4.1)
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('p2t','panorama_to_terraform.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
g = m.TerraformGenerator('/tmp/x')
print([g.sanitize_name(n) for n in ['Web-Server-1','Web_Server_1','web server 1','WEB.SERVER.1']])
"

# C. Splitter crash on quoted DG name (finding §4.3)
# Create a config XML containing: <entry name="DG-O'Hare"> ... then:
python3 split_device_groups.py <that>.xml   # -> SyntaxError: invalid predicate (unhandled)

# D. Entity expansion (finding §1)
# 4-level nested internal DTD entities -> ElementTree expands to 10^4 chars in ~1ms
```

### Provider resource cross-check (v2.0.14, 128 resources)

Missing from provider but emitted by code:
`panos_address_object`, `panos_service_object`, `panos_security_rule_group`, `panos_nat_rule_group`, `panos_bgp`, `panos_bgp_peer`, `panos_bgp_peer_group`, `panos_ospf`, `panos_ospf_area`, `panos_ospf_area_interface`, `panos_static_route_ipv4`, `panos_layer2_subinterface`, `panos_ipsec_tunnel_proxy_id_ipv4`.

Names that DO exist (but with wrong attributes/missing `location`):
`panos_address_group`, `panos_administrative_tag`, `panos_application_group`, `panos_custom_url_category`, `panos_ethernet_interface`, `panos_ike_crypto_profile`, `panos_ike_gateway`, `panos_ipsec_crypto_profile`, `panos_ipsec_tunnel`, `panos_security_profile_group`, `panos_service_group`, `panos_virtual_router`, `panos_zone`.

Provider docs source used for verification:
`https://github.com/PaloAltoNetworks/terraform-provider-panos` → `docs/resources/*.md` (branch `main`).

---

*End of report. Repo left unmodified.*
