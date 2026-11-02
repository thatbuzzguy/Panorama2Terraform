# Acceptance criteria — F6.10.4: the site half

Feature record: `PLAN.md` Epic 6, `to-do.md` slice 1 of the F6.10 slices. The write path landed (F6.10.3), so
the facts the write path can now decide are the site half: the `target` fact, the `panos_push_to_devices`
shape, and the `README.md` label.

Scope: the shape table, the provider block, the action emitter, the generated `README.md`, and the tests that
pin them. No new gate rule, no new CLI argument, no new naming rule, no new reference rule, no new unit rule,
no new reader, no change to `CHECK_ORDER` and no change to the exit codes.

## 1. The `target` fact

What the corpus shows, stated as evidence for the rule:

1. `target` takes one NGFW serial (`docs/CODEBASE_ASSEMBLY.md` §12, verified against provider 2.0.14).
2. The parse records a device entry name as the fact `vsys_device`. Every device name the corpus states is a
   hostname: `fw-1.example.com` (`tests/fixtures/multi_device_templates.xml`), `fw-2.example.com`
   (`tests/fixtures/kitchen_sink.xml`), `device1`. No corpus entry states a serial.
3. The one device entry the sample states is `localhost.localdomain`, which names no device (F3.5,
   `container_coverage.PLACEHOLDER_DEVICE`), so it names no fact and no variable.
4. Therefore the tool cannot name a serial without guessing. It names no serial today, and it must not start
   guessing here.

The rule:

1. **`VALUE_VARIABLES` is still the single shape owner.** `target` is one row in that table, with the shape
   word `operator_supplied`: the run names the variable, holds no value for it, and the operator supplies the
   value in `terraform.tfvars` (§11). This is the F7.1 `reference_only` shape with one difference: a serial is
   not a secret, so the declaration is not `sensitive`. `sensitive = true` stays the `reference_only` row's
   rule alone, so the table is read in one place and no name list decides a marking.
2. **The name is the §5 rule applied to the field**, because there is no value to name it from. `target` is the
   only row in the table whose name does not come from a value, so `naming.py` is still the only naming rule.
3. **No site row and no `.tfvars` line is written for it**, because §9 rule 2 writes a row only for a site that
   names a value. The `.tfvars` is the printed form of a row, and there is no row.
4. **The provider block is the consumer.** The run prints `target = var.target` in the `provider` block of a
   unit whose manifest row names a device fact, and prints no `target` for a unit that names no device, because
   the `variables` gate rule refuses a declaration with no consumer, and a unit that names no device has no
   serial to target. `provider.tf` is a unit-set file, so the declaration and its consumer are in the same
   directory (§14).
5. `generate_provider_config()` records the pair at the print site, before `generate_variables()` runs, the way
   F6.6 orders them, so the declaration set is what the run consumed.

## 2. The `panos_push_to_devices` shape

The pinned schema declares two actions, and the push row is the one with required fields: `name` and `type`
(§12). Measured against the provider docs: `type` takes `device_group`, `template`, `template_stack`,
`log_collector_group`, `wildfire_appliance`, `wildfire_cluster`; `devices` is an optional list of serials, and
when the action states no `devices` the provider pushes to all devices in the target.

The rule: the emitter writes one push block per unit the manifest names, for the three fact keys
`SCOPE_ANSWER` answers, so F6.7's reason for holding the push half is closed: the shape no longer needs a
serial, because the tool names no serial and the provider's documented default covers it.

1. **Emission is default, not a flag** (the F6.5 rule 1 argument, unchanged): the committed goldens pin what a
   default run emits.
2. **`name` states the fact its own unit declares, and `type` states the fact key**, both read through
   `ACTION_FILTERS` and `SCOPE_ANSWER`: the `name` field names the fact its `type` states. No new mapping
   table, and no branch names the fields again. A fact the row declares but an ancestor owns is not the unit's
   own fact, so the block states one fact.
3. **A unit whose fact is not one `type` takes writes no push block**: the shared unit names no fact, and a
   `vsys` or `vsys_device` fact names no push type, so those units are pushed through the parent unit's block,
   the way F6.7 stated them for the commit. `PLACEHOLDER_DEVICE` names no firewall, so it names no fact.
4. **No `devices` field**, because the tool names no serial (rule 1 above), so the block keeps the provider's
   default and the gate reads no serial. `force_template_values`, `include_template` and `description` are not
   printed either: the parse records no push description, and the tool states no policy about forcing template
   values.
5. **Order and bytes are unchanged rules**: fields inside `config`, the required fields in the declared order,
   rows in the identity order the manifest rows print, and within one unit the `ACTION_SCHEMA` order, which is
   also the Panorama order (commit, then push). The address rule is the same rule for both block kinds, so the
   commit block and the push block for one unit share one address, and the action type is the only difference
   (the action address is `action.<type>.<label>`, so Terraform reads them as two blocks).
6. **No new gate finding.** `check_actions` already reads the push shape through the one block reader and the
   one field reader, and `read_block` now states the field that named the fact instead of the filter field the
   fact would answer for, so the reader reports what a push block states.

## 3. The `README.md` label

The F5.5 precedent: the generated `README.md` labels a shape a reader cannot see from a `.tf` file alone, and
states no field the data states. This slice applies it to the write path's own files:

1. The README names `imports.tf`, `SITE_DATA.json` and `site.auto.tfvars`, and names `target` as the fact the
   tool names as a variable and cannot name as a value.
2. It states no row, no value, and no mapping result, so §9 rule 6 still holds for it with the label as the one
   exception: no report names a field the site data states, and the README names the files, not a field.
3. The label is deterministic (no count, no path, no timestamp), so two runs on the same bytes write the same
   bytes.
4. No gate rule reads the README, so the file stays in the codebase root set (§14) and `CHECK_ORDER` is
   unchanged.
5. Goldens pin `.tf` files only, so the README is not a golden; the tests that read it read the run output.

## 4. Byte and pin consequences

- `provider.tf` changes for a unit that names a device, and `actions.tf` gains the push blocks, so both golden
  sets regenerate from a real run (`python3 panorama_to_terraform.py <source> --output-dir <dir>`), never by
  hand.
- `tests/test_site_data.py` changes for the table pins (§9 rule 2), the report pin (the README label), and the
  `target` print pins. `tests/test_variables.py` changes for the declaration set, which is now the credentials
  plus the site values plus the names the table records with no value. `tests/test_commit_actions.py` gains the
  push emission pins.
- The corpus produces no finding for the `variables` rule, the `actions` rule, or the `data_files` rule, and the
  exit codes are unchanged.
