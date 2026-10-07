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
  - Dual-protocol (tcp+udp) service objects keep tcp only; the udp definition is dropped (pinned by F1.6 edge fixture).
- Policy rules do not record which rulebase (pre, post, or shared) they came from. F2.5 chains are ordered per device group across all rulebases, which matches PAN-OS evaluation order for a single rulebase but mixes rulebases when a device group has both pre- and post-rules. Tracking the rulebase per rule (and chaining within one rulebase) lands after F3.1.
- Security profile bodies are not parsed (antivirus, anti-spyware, vulnerability, URL filtering, file blocking, WildFire, zone protection). The v2 provider has resources for them, but emitting empty profile objects would silently create misconfigured resources. F2.9 decision (2026-10-04): the names and descriptions go to `MANUAL_SETUP_REPORT.txt` with the reason; real emission waits for the Epic 3 profile parsing.
- Schedules: `panos_schedule` exists in v2, but only entry names are parsed (day/time ranges not captured) and v2.0.14 has no monthly schedule support. F2.9 decision (2026-10-04): report entry; revisit when schedule parsing lands.
- IPsec tunnel monitor profiles have no v2 resource: `panos_monitor_profile` is the PBF path monitoring profile (`network/profiles/monitor-profile`), a different PAN-OS object — verified in the provider/pango source. F2.9 decision (2026-10-04): report entry.
- F3.1 legacy context conventions (kept so the pre-F3.1 name digests stay stable): the six security profile categories are declared with an empty context (their objects carry `device_group` + `vsys` identity, but the digest context is '' until F3.6), and template-scoped objects (zones, interfaces, VRs, LR, VPN) use `template` (absent until F3.6) as context. F3.2 put `vsys` in the digest for every type, so these categories now hash (scope, '', vsys, name); F3.6 (template-aware parsing) should unify these to the true defining DG/template and regenerate the affected goldens with a reviewed diff.
- Reference resolution order (F3.2, acceptance-recorded): the keyed chain is (referrer context, referrer vsys), then (Shared, referrer vsys), then (contextless, referrer vsys), then the flat first-declaration index. The flat index is not vsys-aware, so a name that exists only in another vsys still resolves through it. This keeps the F2.6 behavior for call sites that pass no vsys (template-scoped types). A strict per-vsys rule would break those sites; it stays as recorded until F3.6 gives them a real context.

## Out of Scope

- Live Panorama API integration.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.
- Deeper post-run checks (beyond F4.1): parse the generated HCL and cross-check object counts against the input (round-trip; needs the F4.3/F4.4 coverage data); `tflint` integration.

## Notes on Already-Completed Work

- F3.8 (safe XML input) is implemented: both scripts reject DTDs before parsing (F1.7). If F3.8 is promoted, only `defusedxml` or the size limit remains.
- F2.4 (emitter rewrite) also fixed two F1.6 extraction gaps: dynamic address group filters are serialized from the structured `<filter>` XML, and IPv6 address objects (`<ipv6>`, `<ipv6-range>`) are parsed and emitted.

## Design Decisions (Epic 3 planning)

- Policy chains key on (device group, vsys) since F3.2. Each chain anchors
  at `where = "last"`, so a vsys boundary restarts the chain; a rule never
  pivots on, or depends on, a rule in another vsys.
- The `location` block does not carry vsys yet (v2 `location` has no vsys
  sub-block for object types). vsys in `location` is F3.5 work.

## Design Decisions (Epic 4 planning)

- The conversion report (F4.3) keys on logical entries — an `<entry name>` plus its properties — not physical lines; one entry spans many lines in the XML. The reported line number is the entry's opening tag.
- The coverage matrix (F4.4, former F2.8) is a permanent maintenance duty: every emitter change must keep the property matrix honest, or `CONVERSION_REPORT.txt` silently lies. F4.3/F4.4 include a test that an unmarked element read fails CI for this reason.
- The parser extraction gaps listed above will surface in the F4.2/F4.3 reports; fix each gap when the report confirms it in a fixture, rather than fixing them speculatively now.
