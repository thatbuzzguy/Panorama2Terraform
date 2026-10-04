# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.

## Tech Debt

- `.gitignore` consistency: `*.xml` is ignored, yet `sample_panorama_config.xml` is committed (audit §4.9).
- No input size limit on XML files. DTD rejection (F1.7) removes the entity-expansion DoS, but a multi-GB well-formed file still allocates memory. A size limit is a product decision (pair with F3.8).
- Parser extraction gaps found by F1.2 unit tests (each silently drops data; fix lands with the Epic 2/3 rewrites):
  - Application filter `description` is not extracted.
  - Service object tags are not extracted.
  - Schedule `description` is not extracted.
  - Security rule profile group references are not extracted.
  - NAT rule `service` in member-list form is captured as whitespace text; only text form works.
  - Ethernet subinterfaces (`ethernet.1.10`) are not parsed as individual interfaces; only vlan and aggregate subunits are.
  - Dual-protocol (tcp+udp) service objects keep tcp only; the udp definition is dropped (pinned by F1.6 edge fixture).
- Stale narrative docs still show v1-era output (type names and file layout): `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md`, `docs/MULTI_VR_MIGRATION_GUIDE.md`, `docs/MULTI_VR_QUICK_ANSWER.md`, `examples/example_terraform_output.txt`. Refresh when the output stabilizes (F2.11 territory).
- Policy rules do not record which rulebase (pre, post, or shared) they came from. F2.5 chains are ordered per device group across all rulebases, which matches PAN-OS evaluation order for a single rulebase but mixes rulebases when a device group has both pre- and post-rules. Tracking the rulebase per rule (and chaining within one rulebase) lands with the F3.1 keyed model.
- `declare_resource_name` accepts a `context` argument but the identity key is `(scope, name)`; uniqueness comes from the per-scope taken set. A reference via `unique_resource_name` resolves to the first declaration. If F3.1 removes name deduplication, same-named objects in different device groups need a context-keyed registry so references resolve to the defining object.
- Security profile bodies are not parsed (antivirus, anti-spyware, vulnerability, URL filtering, file blocking, WildFire, zone protection). The v2 provider has resources for them, but emitting empty profile objects would silently create misconfigured resources. Requires parser work first (F2.9 decision).

## Out of Scope

- Live Panorama API integration.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.

## Notes on Already-Completed Work

- F3.8 (safe XML input) is implemented: both scripts reject DTDs before parsing (F1.7). If F3.8 is promoted, only `defusedxml` or the size limit remains.
- F2.7 (collision-safe naming) has a foundation: `TerraformGenerator.declare_resource_name` (context-aware declarations) and `unique_resource_name` (references) keep resource names unique per type and context (F1.7, refined in F2.4). The hash-of-source-path refinement remains with F2.7.
- F2.4 (emitter rewrite) also fixed two F1.6 extraction gaps: dynamic address group filters are serialized from the structured `<filter>` XML, and IPv6 address objects (`<ipv6>`, `<ipv6-range>`) are parsed and emitted.
