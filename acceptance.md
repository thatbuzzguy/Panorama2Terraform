# Decision — the `disable-override` extraction for the seven rows — acceptance criteria

This slice closes the parser extraction gap `backlog.md` names for the property scan (F4.4): seven matrix
rows name no property for `disable-override`, so `OWNERSHIP.json` states `unknown` for an entry of those
types even when the export carries the flag. The seven are `panos_address_group`, `panos_administrative_tag`,
`panos_application_group`, `panos_custom_url_category`, `panos_external_dynamic_list`,
`panos_security_profile_group`, `panos_service_group`.

## Facts measured before the change

- Measured 2026-11-04 against the pinned provider (`PaloAltoNetworks/panos ~> 2.0.14`, terraform v1.16.2,
  `terraform providers schema -json`): 128 resources, and 25 of them declare `disable_override` as an
  optional string. All seven types above are among the 25, so the provider can hold the flag for each of
  them and the emitter can print it as an argument.
- `panos_ike_gateway`, which `tests/test_ownership.py` pins as `unknown`, is not among the 25: the rule
  that states `unknown` for a row that does not name the property is unchanged.
- Two rows name the property today: `panos_address` (F3.4) and `panos_service` (F6.2). Both read the flag
  through the parse, and both emitters print it as the string after `description`, only when the value is
  `yes` or `no`. That shape is the shape the seven follow.
- The entry-mark rule (F4.3) and the read record (F4.4) are unchanged: a key the parse method read off the
  XML element is not a property an output used, so a row that names the property needs the emitter to read
  the key, and the property scan measures the read through a fixture entry.

## Decision

1. Extraction rule: the seven parse methods read the flag through `_get_text(entry, 'disable-override')`,
   the same helper every other field in those methods reads through. The captured key is the parsed-object
   key `disable_override`, the name the matrix row and `OWNERSHIP.json` use. `parse_address_objects` keeps
   its child-element branch, because that method walks the entry's children for its value type, and no
   second rule is added.
2. Print rule: one generator helper states the shape once — `disable_override = "yes"`, printed after the
   entry's descriptive field, or after `name` when the block prints no descriptive field, and only when the
   value is `yes` or `no`. The nine sites (the two that print today plus the seven) call that helper, so no
   second shape rule appears. An entry with no value prints nothing.
3. The seven matrix rows name `disable_override` in `properties` in the same change.

## Acceptance criteria

1. Each of the seven parse methods keeps the flag in the object it marks, read through `_get_text`: the
   entry that carries `yes` in the fixture reads `yes`, and an entry that carries nothing reads `''`.
2. Each of the seven emitters reads the key and prints the string in the shape the helper states, after its
   descriptive field, so `test_declared_property_is_a_key_the_emitter_reads` grounds the row.
3. A fixture entry carries `disable-override` for each of the seven rows, so the property scan measures the
   read through a corpus entry and `test_measured_reads_equal_the_declared_properties` holds for the seven
   rows. The corpus findings do not move: a captured field an output reads is not a finding.
4. `OWNERSHIP.json` states the flag as the parse read it: `yes` for an entry the fixture carries, and `no`
   for a row that declares the property with no value. `panos_ike_gateway` still states `unknown`, because
   its row does not name the property.
5. The provider fact is pinned against the live schema: the set of matrix rows that name the property is
   the set of emitted types the provider declares it for, and the pin names the seven.
6. Goldens: the committed golden that holds a fixture entry carrying the flag moves, and it moves from a
   real run. `test_golden_files.py` and `test_terraform_validate.py` pass for the bytes that run wrote.
7. The entry-mark rule stays green, and the sanity gate reports `PASS (0 FAIL, 0 WARN)` for the fixture the
   run reports on.
8. `ruff check .` is clean and `python3 -m pytest` passes.
9. `docs/COVERAGE_MATRIX.md` states the property-level change and names the pin; `docs/CODEBASE_ASSEMBLY.md`
   §4 rule 6 states which rows name the property; `src/ownership.py` names them in the `FLAG_KEY` comment;
   `backlog.md` loses the closed item, and `to-do.md` and `agent-status.md` carry the decision.
