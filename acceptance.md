# Acceptance criteria — the stale certificate REFERENCE_ONLY claim (task for this commit)

Scope: markdown only. The fix writes no code and no test, so no golden moves. The finding is a stale claim:
`backlog.md` states that `resource_mapping.VALUE_VARIABLES` has no row for `private_key` or `passphrase`, and
`agent-status.md` names that claim as the Next item. The rule that makes it a finding is in `AGENTS.md`: a claim
about what the tool does must name the module or the test that holds it, and a stale claim is a finding.

## 1. The finding is measured before it is rewritten

1.1 The rows exist. `src/resource_mapping.py` `VALUE_VARIABLES` holds `'private_key': REFERENCE_ONLY` and
`'passphrase': REFERENCE_ONLY`, added with the certificate work (F7.14), which names them in the comment above
the rows.

1.2 The emitter reads them. `panorama_to_terraform.py` `_protocol_fields` reads the table at the print site
(line 3802), and `_generate_certificate_blocks` prints certificate blocks through that rule.

1.3 The golden proves the reference prints.
`tests/golden/kitchen_sink/vsys1_78d8e4bc/certificates.tf` states `passphrase = var.vsys_cert` and
`private_key = var.vsys_cert`, and `tests/golden/kitchen_sink/vsys1_78d8e4bc/variables.tf` declares `vsys_cert`
with `sensitive = true`.

1.4 The pins hold the rule. `tests/test_variables.py` pins the declaration set read through the table, and
`tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file` pins that no generated file
holds the parsed value. `python3 -m pytest tests/test_variables.py tests/test_robustness.py
tests/test_certificate_blocks.py` passes.

## 2. The documents

2.1 `backlog.md`: the sentence in `Design Decisions (the value the parse cannot carry)` states what the table
holds, not what it lacks, and names the module and the tests. The facts that stay genuinely open in the
certificate entries stay: the `panos_certificate` data-source-only asymmetry, no certificate type declares a
`device_group` sub-block, the `selects` choice for a `local` that states both alternatives, the `sensitive`
marks on the rows. The table is not restated row by row.

2.2 `backlog.md`: the open-fact list in the round-trip entry no longer names the closed fact, and keeps the two
`.github/` template files as the recorded finding.

2.3 `PLAN.md`: the Sequencing sentence that carries the same stale claim states that the rows are landed.

2.4 `agent-status.md`: the Current position Next paragraph names the next actionable item. The gated feature
items are blocked on facts the tool cannot read offline, so the actionable items are the Nice-to-Haves:
`ruff format` as a gate is the next actionable slice, its own task per `backlog.md`; `tflint` integration is the
following item.

2.5 `to-do.md`: no open implementation piece remains for a landed feature. It states the current position and
the next actionable slice, and records no work blocked offline as an open piece.

## 3. The checks

3.1 `ruff check .` is clean.

3.2 `python3 -m pytest` passes 1567 pins with no skip.

3.3 The commit is markdown only, with an ASD-STE100 message.

## Result

Measured before writing the fix. `src/resource_mapping.py` lines 1265–1266 hold `'private_key': REFERENCE_ONLY`
and `'passphrase': REFERENCE_ONLY`, and the F7.14 comment above them names the rows. `panorama_to_terraform.py`
line 3802 is the print site that reads the table, and `_generate_certificate_blocks` prints through it.
`tests/golden/kitchen_sink/vsys1_78d8e4bc/certificates.tf` lines 14–15 state `passphrase = var.vsys_cert` and
`private_key = var.vsys_cert`, and `variables.tf` line 24 declares `variable "vsys_cert"` with
`sensitive = true`. `python3 -m pytest tests/test_variables.py tests/test_robustness.py
tests/test_certificate_blocks.py` passes 53 pins.

After the fix: `ruff check .` is clean, `python3 -m pytest` passes 1567 pins with no skip (the provider-cache
pins ran, so none skipped), and `git status` names only the tracking markdown: `backlog.md`, `PLAN.md`,
`agent-status.md`, `to-do.md` and this file. No code and no test moved. `PLAN.md` carried the same stale claim
in its Sequencing section, so the fix states the same fact there; the same claim in `agent-status.md` and
`to-do.md` is closed, and the Next item now names `ruff format` as a gate.
