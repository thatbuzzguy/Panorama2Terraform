# Backlog

Tech debt, out-of-scope items, and nice-to-haves. Promote items to `PLAN.md` when they become in-scope.

## Tech Debt

- `.gitignore` consistency: `*.xml` is ignored, yet `sample_panorama_config.xml` is committed (audit §4.9).
- Escape handling does not cover `\r` and control characters (audit §4.6). Fix lands with F1.7.
- Parser extraction gaps found by F1.2 unit tests (each silently drops data; fix lands with the Epic 2/3 rewrites):
  - Application filter `description` is not extracted.
  - Service object tags are not extracted.
  - Schedule `description` is not extracted.
  - Security rule profile group references are not extracted.
  - NAT rule `service` in member-list form is captured as whitespace text; only text form works.
  - Dynamic address group filter extraction captures leading whitespace instead of the filter content.
  - Ethernet subinterfaces (`ethernet.1.10`) are not parsed as individual interfaces; only vlan and aggregate subunits are.
  - IPv6 address objects (`<ipv6>` elements) are not extracted; the entry degrades to an empty value (pinned by F1.6 edge fixture).
  - Dual-protocol (tcp+udp) service objects keep tcp only; the udp definition is dropped (pinned by F1.6 edge fixture).

## Out of Scope

- Live Panorama API integration.
- PAN-OS version matrix testing.
- Dual-license legal review (audit §6.8).

## Nice-to-Haves

- Adopt `ruff format` as a gate. A one-time format pass of both legacy scripts is required first (about 1500 changed lines in `panorama_to_terraform.py`). Do it as its own task so the diff stays reviewable.
