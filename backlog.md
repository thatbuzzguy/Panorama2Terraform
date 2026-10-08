# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.

## Tech Debt

- `.gitignore` consistency: `*.xml` is ignored, yet `sample_panorama_config.xml` is committed (audit §4.9).
- No input size limit on XML files. DTD rejection (F1.7) removes the entity-expansion DoS, but a multi-GB well-formed file still allocates memory. A size limit is a product decision (pair with F3.8).
- Parser extraction gaps found by F1.2 unit tests (each silently drops data; fix lands with the Epic 2/3 rewrites):
  - Application filter `description` is not extracted.
  - Schedule `description` is not extracted.
  - Security rule profile group references are not extracted.
  - NAT rule `service` in member-list form is captured as whitespace text; only text form works.
  - Service object `disable-override` is not extracted (the address parser
    extracts it since F3.4; the service parser does not).
- Service objects with both tcp and udp legs cannot be emitted whole. The v2
  `panos_service` schema declares `protocol.tcp` and `protocol.udp`, but the
  provider accepts one leg only: a config with both fails `terraform
  validate` with "Invalid Attribute Combination" (verified against 2.0.14,
  F3.4). F3.4 decision: emit the tcp leg (udp when tcp is absent), keep the
  dropped leg as a `# NOTE:` comment and a `MANUAL_SETUP_REPORT.txt` entry.
  A future release could offer a two-object split as an opt-in.
- External dynamic list `auth` (username/password) is not parsed. Writing
  credential material into generated HCL is not acceptable (F3.4). An EDL
  that authenticates to its fetch URL needs the credentials configured by
  hand; the converter cannot express them safely. Revisit only with an
  explicit secret-manager design (e.g. a `var.` reference, never a literal).
- Policy rules do not record which rulebase (pre, post, or shared) they came from. F2.5 chains are ordered per device group across all rulebases, which matches PAN-OS evaluation order for a single rulebase but mixes rulebases when a device group has both pre- and post-rules. F3.5 confirmed the provider can express it: `panos_security_policy_rules`, `panos_nat_policy_rules`, `panos_decryption_policy_rules` and `panos_pbf_policy_rules` all declare `location.device_group.rulebase` and `location.shared.rulebase` (v2.0.14 schema). F3.5 decision (2026-10-08): do not emit it. The parser does not record the rulebase, and the accepted value string is unverified — the provider binary carries the literal `pre-rulebase` and no `post-rulebase` literal, so the omitted-attribute default is the only safe output. Verify the value against a live target, then record the rulebase per rule, chain within one rulebase, and emit `rulebase` for the four rule types. Note that `location.vsys` declares no `rulebase` field, so a vsys-scoped rule cannot carry it at all and must be reported instead.
- Security profile bodies are not parsed (antivirus, anti-spyware, vulnerability, URL filtering, file blocking, WildFire, zone protection). The v2 provider has resources for them, but emitting empty profile objects would silently create misconfigured resources. F2.9 decision (2026-10-04): the names and descriptions go to `MANUAL_SETUP_REPORT.txt` with the reason; real emission waits for the Epic 3 profile parsing.
- Schedules: `panos_schedule` exists in v2, but only entry names are parsed (day/time ranges not captured) and v2.0.14 has no monthly schedule support. F2.9 decision (2026-10-04): report entry; revisit when schedule parsing lands.
- IPsec tunnel monitor profiles have no v2 resource: `panos_monitor_profile` is the PBF path monitoring profile (`network/profiles/monitor-profile`), a different PAN-OS object — verified in the provider/pango source. F2.9 decision (2026-10-04): report entry.
- F3.1 legacy context conventions (kept so the pre-F3.1 name digests stay stable): the six security profile categories are declared with an empty context (their objects carry `device_group` + `vsys` identity, but the digest context is '' until F3.6), and template-scoped objects (zones, interfaces, VRs, LR, VPN) use `template` (absent until F3.6) as context. F3.2 put `vsys` in the digest for every type, so these categories now hash (scope, '', vsys, name); F3.6 (template-aware parsing) should unify these to the true defining DG/template and regenerate the affected goldens with a reviewed diff.
- Reference resolution order (F3.2, acceptance-recorded): the keyed chain is (referrer context, referrer vsys), then (Shared, referrer vsys), then (contextless, referrer vsys), then the flat first-declaration index. The flat index is not vsys-aware, so a name that exists only in another vsys still resolves through it. This keeps the F2.6 behavior for call sites that pass no vsys (template-scoped types). A strict per-vsys rule would break those sites; it stays as recorded until F3.6 gives them a real context.
- Device-aware resolution (F3.5) is limited to names a device declared. Only the interface generators pass `device` at declaration, so only interface references are device-restricted; a zone, address or profile name that repeats on two firewalls still resolves first-wins through the context chain. Extend the rule when a generator declares per-device objects other than interfaces.
- An entry under `devices/entry/<device>` (not inside a device group) records `device_group = 'Shared'`, because `device_group_of` has no other fallback. It is honest for the location choice (such an object is in no device group, and the emitted location is `vsys` or the template placeholder), but the naming digest then uses `'Shared'` for a device-level object and for a true shared object alike. F3.6 owns the device/template association; give device-level entries their own context there and regenerate the affected digests.

## Out of Scope

- Live Panorama API integration.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.
- Deeper post-run checks (beyond F4.1): parse the generated HCL and cross-check object counts against the input (round-trip; needs the F4.3/F4.4 coverage data); `tflint` integration.

## Notes on Already-Completed Work

- F3.5 (multi-vsys) corrected a wrong assumption held since F2.3: v2
  `location` **does** have a `vsys { name, ngfw_device }` sub-block for the
  object types and the four policy-rule types. `panos_security_profile_group`
  is the emitted type that lacks it. `localhost.localdomain` is the PAN-OS
  placeholder for "this device", so it is never emitted as `ngfw_device`;
  the resource is reported instead. Shared entries emit `shared = {}`, not
  `device_group = { name = "Shared" }`.
- F3.4 (full object types) closed two F1.2 extraction gaps: service object
  tags are extracted and emitted, and dual-protocol services keep both legs
  in the parse model (the emit limit is a provider constraint, recorded
  above). Address `ip-wildcard`, `disable-override`, EDL `exception_list`,
  `expand_domain`, `certificate_profile` and the recurring schedules are
  parsed and emitted; address types with no v2 attribute (location, external)
  are report-only.
- F3.8 (safe XML input) is implemented: both scripts reject DTDs before parsing (F1.7). If F3.8 is promoted, only `defusedxml` or the size limit remains.
- F2.4 (emitter rewrite) also fixed two F1.6 extraction gaps: dynamic address group filters are serialized from the structured `<filter>` XML, and IPv6 address objects (`<ipv6>`, `<ipv6-range>`) are parsed and emitted.

## Design Decisions (Epic 3 planning)

- Policy chains key on (device group, vsys) since F3.2. Each chain anchors
  at `where = "last"`, so a vsys boundary restarts the chain; a rule never
  pivots on, or depends on, a rule in another vsys.
- `location` carries the source scope since F3.5: `vsys { name, ngfw_device }`
  for a declared vsys on a type that accepts it, `template { name }` (plus
  `vsys` where the schema declares the field) for a declared template,
  otherwise the device group, `shared = {}`, or the `Shared` template
  placeholder. A declared scope the type cannot carry is reported, never
  dropped silently.

## Design Decisions (Epic 4 planning)

- The conversion report (F4.3) keys on logical entries — an `<entry name>` plus its properties — not physical lines; one entry spans many lines in the XML. The reported line number is the entry's opening tag.
- The coverage matrix (F4.4, former F2.8) is a permanent maintenance duty: every emitter change must keep the property matrix honest, or `CONVERSION_REPORT.txt` silently lies. F4.3/F4.4 include a test that an unmarked element read fails CI for this reason.
- The parser extraction gaps listed above will surface in the F4.2/F4.3 reports; fix each gap when the report confirms it in a fixture, rather than fixing them speculatively now.
