# Acceptance — criteria for the pin update (2026-11-22)

The task is the version pins: the provider constraint, the Terraform minimum, and the tool pins CI runs the
gate with. Two decisions were taken on these criteria, 2026-11-22: the floor is `>= 1.16` with CI at 1.16.7, and the
Terraform minimum gets one owner. A pin move is a golden change, so the template, the goldens, the probe, CI and the
documents that state the version move in one commit with the measurements that cover the new pin.

The work is in the `pin-update` worktree, because another agent holds main. The files there are the plan; the
measurement record for main is not changed by it.

## Criteria

1. **One place states each pin.** The provider version already has one owner: `tests/conftest.py::declared_provider`
   reads it from a golden `provider.tf`, and the schema fixture reads it from there, so a provider move is a byte
   change and no rule change. The Terraform minimum is written by three places — the `terraform` block in
   `src/panorama_to_terraform.py`, the generated `README.md`, and the generated `actions.tf` header in
   `src/commit_actions.py` — and read by `tests/test_commit_actions.py::test_the_generated_terraform_block_declares_the_minimum`
   and `::test_the_generated_readme_names_the_file_and_the_minimum`. The decision is that the minimum gets the same
   shape: one constant read by the three places, and one helper in `tests/conftest.py` read by the pins, so a move
   changes one place and not five.
2. **A pin move moves the goldens with it.** 17 `provider.tf` files and 6 `actions.tf` files carry the version
   strings byte for byte. The template and the goldens are one commit, and the no-change tests read the same bytes.
3. **Provider facts stay measurements.** The documents that state provider facts name the pinned provider, so the
   pin statement changes; a dated measurement is not restated. The fact that lets the 2.0.14 measurements stand for
   2.0.15 is the schema identity measured below, and it is stated once, in `docs/CODEBASE_ASSEMBLY.md` §12.
4. **A fact that needs a live target stays blocked regardless of the pin.** F3.5 rulebase value, the device serial,
   and the per-device template variable override are unaffected by the pin move and stay in `backlog.md`.
5. **The gate answers the same before and after the pin moves**, or the difference is measured before the pin moves.
6. **The tool pins move only with their own measurement.** A lint pin move is a gate change: the new version can
   report a finding the pinned version does not, so the finding is fixed in the same commit or the pin stays.

## Measurements taken for the criteria (2026-11-22)

1. **The provider schema is identical between 2.0.14 and 2.0.15.** `terraform providers schema -json` answers
   byte for byte the same for both: 2,146,209 bytes, md5 `dfab791bae568bdd5ccdc69ca066a5b4`, on Terraform 1.16.2.
   So no resource, data source, action schema or value-list fact in the documents changes. Provider 2.0.15 was
   published 2026-11-06, and its two changes are Go dependencies (pan-os-codegen #746) and the device-group
   membership marshal (#745). The tool emits no `devices` for `panos_device_group`, so #745 is inside the provider's
   own API call and reaches no committed output.
2. **The committed goldens validate on provider 2.0.15.** 17 unit directories, 17 validate, with Terraform 1.16.2,
   and 17 validate with Terraform 1.17.2. The copies were read from the worktree and only the version string was
   changed, so this is the same content the pins run.
3. **The tflint answer reproduces on the pinned binary.** tflint v0.66.0 with the bundled Terraform ruleset v0.17.0,
   run with `--format=json --no-color` and one `--only` flag per rule in sorted order, answers byte for byte the
   same as the committed `tests/tflint/probe.json`, for the probe at 2.0.14 and at 2.0.15. So the rule-set pins are
   unchanged by the provider move, and the committed answer is still a reproducible measurement.
4. **The Terraform lines upstream.** Latest stable 1.17.2 (2026-11-11), newest 1.16 patch 1.16.7. Security support
   for 1.14 ended 2026-08-26 and for 1.15 ended 2026-10-21, so `>= 1.14` states a floor upstream no longer
   supports. CI pins 1.16.1; the recorded measurements name 1.16.2, the version on this machine.
5. **The tool pins.** pytest 9.2.0 against the pinned 9.1.1: the same run shape, the same four tflint skips at the
   same positions, nothing else different. ruff 0.17.6 against the pinned 0.16.10: the pinned version reports
   nothing, the newer version reports one SIM102 finding at `tests/test_state_coverage.py:653`, so a ruff move needs
   that change in the same commit. tflint v0.66.0 is still the latest release, so the rule-set pin does not move.
