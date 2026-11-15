# Acceptance — Piece 5, naming and printing state one rule

Criteria set 2026-11-14 for `to-do.md` Piece 5, the eight naming and printing findings `backlog.md`
recorded on 2026-11-12. Each item states the rule, the module that owns it, the decision, and the test
that pins it. A pin measures content: it reads the parse object, the report, or the `.tf` bytes a run
wrote, and no pin reads the tracking markdown. A pin that fails on content is a finding recorded in
`backlog.md`, not a pin to relax.

Gate before commit: `ruff check .` clean, and the full `python3 -m pytest` with every pin passing and no
skips. Baseline before this piece: 1,659 pins in 50 test modules, all pass, no skips, exit 0
(`/tmp/opencode/baseline_pytest.txt`), measured 2026-11-14. Counts by module are in
`/tmp/opencode/collect_before_final.txt`. No pin may be weakened; a pin may change what it asserts when the rule
changes, and each such change is recorded in the next section.

Source-scan pins: four items keep one (item 4 keeps two), and each states why content cannot show its rule.
Item 2's rule is
"the word is stated once", which no run can show, because two definitions print the same string. Item 4's
rule is "no print site states a second order", which content cannot show for the certificate rows, because
every certificate row prints the same order under the row order and under the name-first sort. Item 5's rule
is "the read layer owns the rule", which no run can show, because a state value never reaches a `.tf` file.
Item 8's rule is "the marker is stated once", for the same reason as item 2. Each of those four items keeps a
content pin as well, and each item has at least one pin that fails on the code before the change.

## Pins that changed

A pin changes when the rule it measures changes. Each change is recorded here, with what the pin asserted
before. A pin that cannot fail before the change says so.

- `tests/test_filter_containers.py::test_the_parse_method_states_no_path_of_its_own` (was
  `test_the_parse_method_states_the_six_paths_and_no_field_name`): now asserts the method states no path
  string constant and reads the six paths through `FILTER_PATHS`. Before: the method stated the six paths as
  its own string constants. Fails before the change.
- `tests/test_filter_containers.py::test_the_emitter_prints_the_fields_the_entry_row_declares`: the field
  order is now the row order. The report's `captured` order stays sorted, because `entry_coverage` states that
  as its own rule for the report, not as a print order. Fails before the change.
- `tests/test_robustness.py::test_escape_string_prints_the_shapes_it_escapes` (was
  `test_escape_string_strips_illegal_control_chars`): the escape prints a control character it is handed,
  because the rule is no longer the escape's. Fails before the change.
- `tests/test_sanity_gate.py::test_placeholder_check_warns_and_does_not_fail`: reads the marker through
  `resource_mapping.PLACEHOLDER_TEXT` instead of spelling it. Fails before the change.
- `tests/test_reports.py::test_per_gateway_placeholder_line_survives`: reads the marker through the same
  constant instead of spelling `***CHANGE_ME***`. Fails before the change.
- `tests/test_real_or_report.py`: the module-level copy
  `PLACEHOLDER_TEXT = 'Manual Terraform configuration is required'` is gone, and the five pins read the
  constant through the table. Fails before the change, at the read of the constant.
Two scan helpers change, and each is read by one pin:

- `tests/test_container_coverage.py::_segments_of_method`, read by
  `tests/test_container_coverage.py::test_every_row_path_is_read_by_its_method`: reads the paths a method names
  through a table constant (`resource_mapping.FILTER_PATHS`) through the module that states them, so a method
  that states no path literal still matches its row. It cannot fail before the change, because the pre-change
  method stated the paths as literals and the scan matched them; the pins that fail before the change for item
  4 are the ones named there.
- `tests/test_entry_coverage.py::_name_guards`, read by
  `tests/test_entry_coverage.py::test_every_name_guard_records_the_entry_it_reads`: counts an entry name read
  through the text rule (`xml_input.read_text`) as the same guard. It cannot fail before the change, for the
  same reason: the pre-change methods read the name by the same spelling the scan already matched. The asserted
  guard count (69) and the one exception (`('_list_names', 'positive')`) are unchanged.

## 1. One digest per name, the static-route block

Rule: `docs/ARCHITECTURE.md` §5 — a block's local name is the sanitized name plus the digest of the object's
source identity, and the identity holds the raw name, so one name is digested once.

Decision: `generate_virtual_routers` passes the route's own name to `declare_block_name`, not the name it
built by prefixing the router's block name (`f"{resource_name}_{route['name']}"`), so the digest is taken once
and `_declaration_index` holds the key a reference by the route's name reads. The router is not part of the
route's identity; two routes with the same name in one scope take the taken-name counter, which is the rule
`declare_block_name` already states.

Measured: the kitchen-sink golden `virtual_routers.tf` names move, because the digest input changes from
`vr1_3f0e80e0_r1` to `r1`. The pin computes the name through `naming.sanitize` and `hashlib` from the route
name, so it does not restate the golden.

Owner: `src/panorama_to_terraform.py::generate_virtual_routers`, `declare_block_name`.

Pins:

- `tests/test_robustness.py::test_a_static_route_block_digests_the_route_name_once` — content with one router
  and two static routes: the block names the run wrote are the §5 shape of each route's own name, and
  `name_ref` for a route name resolves to the block the run declared for it. Fails before the change: the
  printed name is the double digest and the reference answers the plain name.
- `tests/test_golden_files.py::test_golden_bytes_match` for
  `kitchen_sink/fw_template_00a08cdc/virtual_routers.tf`, and the pins that read the whole golden set through
  `tf_bytes`: `tests/test_ownership.py::test_the_goldens_are_byte_identical`,
  `tests/test_reference_edges.py::test_the_golden_tf_bytes_are_unchanged`,
  `tests/test_unit_manifest.py::test_the_generated_tf_bytes_are_unchanged`. Fails before the change, because
  the names the run wrote differ from the goldens the change recorded.
- `tests/test_robustness.py::test_declare_resource_name_avoids_collisions` — unchanged pin that keeps the
  taken-name counter half. It cannot fail before the change, because the counter rule is the same on both
  sides of the change.

## 2. The fallback word is stated once

Rule: `src/naming.py` §5 — a name that sanitizes to nothing is `UNNAMED`, and no module defines the word a
second time.

Decision: `declare_block_name` reads `naming.UNNAMED`. `src/unit_manifest.py` defined a second `UNNAMED` for
the directory fallback, so it migrates: `unit_manifest` reads `naming.UNNAMED` and states no definition. Two
modules held the word before the change, and a third stated it as a literal (`declare_block_name`).

Owner: `src/naming.py` (the definition), `src/unit_manifest.py`, `declare_block_name`.

Pins:

- `tests/test_unit_manifest.py::test_the_fallback_word_is_stated_once_in_src` — source scan, for the reason
  stated above: the word appears as a definition in `naming.py` only, and the two readers call `naming.UNNAMED`
  rather than spelling it. Fails before the change: three places state it. This is the pin that fails before
  the change for item 2.
- `tests/test_unit_manifest.py::test_the_word_prints_the_same_string_at_both_print_sites` — content pin, added:
  a run on content whose name sanitizes to nothing prints the same word at both print sites, the unit directory
  name through `unit_manifest` and the block name through `declare_block_name`. It measures the rule as content
  and cannot fail before the change, for the same reason the scan pin exists.
- `tests/test_robustness.py::test_declare_empty_name_gets_a_stable_name` — content pin, unchanged: an empty
  name still prints `unnamed_<8 hex>`. It cannot fail before the change, because the word prints the same shape
  from either definition.

## 3. One name names one value, at the record site

Rule: `src/site_data.py` §9 rule 4 — one name names one value, and a second value for a name is a refusal the
writer cannot print. `site_data` is the owner of the pair, so the rule is stated once as one function,
`site_data.record_pair(store, name, source)`, and both sites read it: `printed_value` when it records the pair,
and `render_tfvars` when it merges rows.

Decision: refuse. `printed_value` records the source fact that names the variable (the entry name for a
`reference_only` name, the value for a `variable` one, F7.7), so a second entry that reads to a name the record
already holds is a refusal, not a merge. The last value winning is not a rule the tool can print: two blocks
would reference one variable that names one of the two entries, and the operator cannot tell which. The record
keeps the source per name, and the shape decides whether the value prints in `.tfvars`, so
`value_variables()` now filters by shape (`== VARIABLE`) and `generate_variables` decides `held` through
`._value_shapes`.

Measured reachability: inside one unit a `VARIABLE` value cannot collide, because the only `VARIABLE` row is
`ngfw_device` and the unit key holds that device fact; the reachable case is two `reference_only` entries whose
names sanitize identically (`naming.variable_name` maps `-`, `.` and `_` to `_`), which is what the pin builds.

Owner: `src/site_data.py` (§9 rule 4, `record_pair`), read by `printed_value` and `render_tfvars`.

Pins:

- `tests/test_variables.py::test_the_record_refuses_two_entries_that_name_one_variable` — content with two
  certificate entries in one unit named `AP-1` and `AP_1`, each with a `private_key`: the run refuses and names
  both source names, no record row and no `.tfvars` line prints for the name, and the writer half answers the
  same message for the same pair through `record_pair`. Fails before the change: the function the pin reads did
  not exist, and the run took the last value.
- `tests/test_site_data.py::test_a_name_two_rows_state_prints_one_line` and
  `tests/test_site_data.py::test_only_the_device_field_maps_to_a_variable` — unchanged pins for the writer half
  and the shape filter. They cannot fail before the change, because the writer already refused one name with two
  values and the filter answered the same set; what the change moved is the statement, not the answer.

## 4. One order for a nested object: the row order

Rule: `docs/ARCHITECTURE.md` §4.9 — a shape table row states the fields in the order the print uses, at every
level. `hcl_value` prints dict keys in the order the table built them, so the order is stated once.

Decision: the row order is the print order, and the two emitters read it. The `sorted()` calls in
`generate_filter_containers` and `_generate_certificate_blocks` are removed, and the name-first sort is removed
with them, because the row already states `name` as a field. `parse_filter_containers` reads
`resource_mapping.FILTER_PATHS` instead of its own six string literals, so its docstring claim holds.

Measured: the `FILTER_SHAPE` table holds 121 rows, 32 of which state `name`, and all 32 state it off the first
position, so the print order differs from the old name-first sort for them; the six entry rows the emitter
prints are among them, so the filter goldens move. `FILTER_PATHS` and the hardcoded six differ at two paths
(`community-list` and `prefix-list`), so the parse's return order moves. The `CERTIFICATE_SHAPE` table holds 7
rows, 3 of which state `name`, and none state it off the first position, so no certificate block moves: the
certificate pin measures the rule and cannot fail before the change, which is why item 4 keeps one source scan.
`PROTOCOL_SHAPE` (194 rows, 42 stating `name`, 12 off first) already printed in row order, so no protocol
golden moves.

Owner: `hcl_value` (the statement), `generate_filter_containers`, `_generate_certificate_blocks`,
`parse_filter_containers`.

Pins:

- `tests/test_filter_containers.py::test_the_parse_reads_the_paths_the_table_states` — content: the container
  keys the parse returns are `FILTER_PATHS` in the table's order. Fails before the change: two paths sit in a
  different order.
- `tests/test_filter_containers.py::test_the_emitter_prints_the_fields_the_entry_row_declares` — content: the
  field lines the run wrote are in the row's order, read back from the bytes, on rows that state `name` off the
  first position. Fails before the change.
- `tests/test_golden_files.py::test_golden_bytes_match` for `filter_containers/fw_template_00a08cdc/filters.tf`
  and `kitchen_sink/fw_template_00a08cdc/filters.tf`. Fails before the change.
- `tests/test_filter_containers.py::test_the_parse_method_states_no_path_of_its_own` — source scan, for the
  reason stated above: the method states no path literal, reads them through `FILTER_PATHS`, and states no
  field name of its own. Fails before the change.
- `tests/test_filter_containers.py::test_the_print_sites_state_no_second_order_rule` — source scan, for the
  reason stated above: neither print site states a sort, and both build their fields through the one table walk.
  Fails before the change.
- `tests/test_certificate_blocks.py::test_the_block_prints_the_fields_in_the_order_the_row_states` — content:
  each certificate block prints its fields in its row's order. It measures the rule rather than a change, for
  the reason recorded above, and it is what holds the rule for a row a reorder would move.
- `tests/test_entry_coverage.py::test_captured_fields_skip_empty_values_and_sort` and
  `tests/test_container_coverage.py::test_every_row_path_is_read_by_its_method` read the report order and the
  table paths as their own rules, so the `captured` sort stays and the coverage scan reads the paths through
  `FILTER_PATHS`. Neither pin can fail before the change, for the reason recorded in the pin-change section.

## 5. The read layer owns the control-character rule

Rule: `src/xml_input.py` — the text the read layer reads is the text the source states, and it holds no control
character. The XML door refuses one in text and in a character reference (measured both ways: `&#7;` is
"reference to invalid character number", a raw `0x07` byte is "not well-formed"), and the JSON state door states
no such rule, so `state_input` applies the read layer's rule to the values it reads: `json.loads` accepts
`\u0007` inside a string, so the refusal must run on the decoded value, not on the bytes.

Decision: the read layer owns the rule. `escape_string` keeps only the escape shapes HCL needs (backslash,
quote, tab, CR, LF) and no longer strips, so a value the door refused cannot reach the printer changed by the
escape path. `sanity_checks.check_control_chars` stays the gate's check on the printed text and reads the same
definition, so it is no longer a second statement of the rule; it still decides a hand-written file, which the
gate can read and the door never saw.

Measured: no run pin can show the gate firing on tool output, because a state value never reaches a `.tf` file;
the pins measure the door's refusal and the escape's shapes.

Owner: `src/xml_input.py` (the statement, `CONTROL_CHARS` and `ESCAPE_SHAPES`), `src/state_input.py`,
`escape_string`, `src/sanity_checks.py::check_control_chars` (the reader).

Pins:

- `tests/test_state_input.py::test_the_state_door_refuses_a_control_character_in_a_value` — content: a state
  document whose value states `\u0007` is refused by the door with the origin named, the three escape shapes are
  accepted as content, and the CLI shape is exit 1 with no record written. Fails before the change: `json.loads`
  accepted it and the value reached the parse object.
- `tests/test_robustness.py::test_escape_string_prints_the_shapes_it_escapes` — content: the escape prints the
  tab, CR, LF, quote and backslash shapes, and prints a control character it was handed as the text, because the
  rule is no longer the escape's. Fails before the change (the escape stripped it).
- `tests/test_sanity_gate.py::test_the_control_character_rule_is_stated_once_in_src` — source scan, for the
  reason stated above: the rule's definition is `xml_input`, and no `src/` module holds a strip. Fails before
  the change.
- `tests/test_sanity_gate.py::test_control_char_check_detects_a_raw_control_character` — content, unchanged: the
  gate still reports a raw control character and DEL on a hand-written file, and an escaped tab stays clean. It
  cannot fail before the change, because the gate answered the same findings from its own copy of the rule.
- `tests/test_write_path.py::test_the_bytes_a_run_writes_hold_no_cr` — content, unchanged: a run writes no raw
  CR, which is the print side of the same rule. It cannot fail before the change, for the same reason.

## 6. One whitespace rule for the text a value has

Rule: `src/xml_input.py` — the text a value has is the text the source states, without the whitespace the export
puts around it, because that whitespace is the export's formatting. A name read from the `name` attribute is read
through §5, and `naming.sanitize` already strips the whitespace by the same effect, so the value rule and the
naming rule agree.

Decision: one rule, read by the six helpers the audit named: `_get_text`, `_get_members`, `_get_single_value`,
`_protocol_field`, `_list_names`, and `split_device_groups._device_names`. They call `xml_input.read_text`, so
no helper states a second rule. The four that did not strip migrate to the majority behaviour the two already
had. A missing element still answers `None`, so the rule does not turn an absent field into an empty one.

Measured: the corpus holds no member text or field value with surrounding whitespace (2,869 element texts, of
which 1,761 are the export's formatting; 0 member values and 0 single-value fields change), so no golden
moves; the pin states the whitespace in the content.

Owner: `src/xml_input.py` (the statement), the value helpers, `src/split_device_groups.py`.

Scope note: a name read from the `name` attribute by a parse method is not read through a value helper, so the
block's local name is the §5 shape and the printed value keeps what the export states for it. The rule covers the
text a value helper reads: element text, member text, and the entry name a helper reads inside a level.

Pins:

- `tests/test_parse_helpers.py::test_the_value_helpers_read_the_text_the_read_layer_states` — content that states
  `  spaced  ` as element text and as a member: each of the six helpers answers `spaced`, an absent element
  answers `None`, and the shape words and element spellings are read through the table so the pin states no rule
  of its own. Fails before the change for the four helpers that did not strip.
- `tests/test_parse_helpers.py::test_a_value_with_surrounding_whitespace_prints_without_it` — content: a run on
  content with a device group entry whose `description` states `  spaced  ` prints `description = "spaced"` in the
  `.tf` bytes the run wrote, and the gate reads the same run clean. Fails before the change, which is the audit's
  probe. Item 6 needs no scan pin, because content shows the rule.

## 7. `UnitText.add_once` keeps its own once record

Rule: `docs/CODEBASE_ASSEMBLY.md` §14 — a file states a section header once per unit. "Once" is about the text
the file added, not about text that appears somewhere in what the file already holds.

Decision: `UnitText` keeps a once record per file and per unit (a set), separate from the accumulated text, so
header prose that contains the section text cannot stop the section. The order the text is added in is unchanged,
and `write` still writes one file per unit that has content.

Owner: `src/panorama_to_terraform.py::UnitText`.

Pin: `tests/test_write_path.py::test_add_once_keeps_its_own_once_record` — a `UnitText` whose header contains the
section text, with two units: the file the run writes holds the header and the section for each unit, and a
second call for the same text states nothing. Fails before the change: the section is missing, because the header
contained it.

## 8. The VPN key prints the reference the table states

Rule: `src/resource_mapping.py::VALUE_VARIABLES` is the only place that decides the shape of a field the provider
marks `sensitive`: `key` is `reference_only`, so no generated file states the value, the run records the name with
no value, and the operator supplies the value (`docs/CODEBASE_ASSEMBLY.md` §11, F7.1, F7.7). The name is the §5 name
of the entry that holds the field, because a field cannot name itself.

Decision, changed by measurement (was: print the reference and remove the placeholder rule): the block prints the
reference only when the run read a value for the field. The export carries no pre-shared key, so the parse stores
no value, the name rule has nothing to name, and a pair with no source is not a record `render_tfvars` can print.
The block therefore prints the marker, and the marker is stated once in the table as
`resource_mapping.PLACEHOLDER_TEXT`, read by the print site (`printed_value`, the empty-value branch), the gate
rule `check_placeholders` (`EXPECTED_PLACEHOLDERS`), the report, and the pins. The placeholder gate rule stays,
because the gate reads a hand-written file the operator must edit before apply: the marker is an expected output,
so it is a WARN, not a FAIL. The parse no longer fabricates the value, so `pre_shared_key` is dropped from the
`COVERAGE_MATRIX` row for `panos_ike_gateway`: the property scan measures what a run reads, and the row stated a
property the parse no longer holds.

Measured: the bytes `vpn.tf` writes do not move, because the marker prints the same way through the print site as
the parse wrote it before. No golden for `variables.tf` moves, because no pair is recorded. The property-coverage
pins re-measure clean after the matrix row change.

Owner: `generate_vpn_config`, `resource_mapping.VALUE_VARIABLES` and `PLACEHOLDER_TEXT` (the rule),
`src/sanity_checks.py::check_placeholders` (the reader), `generate_manual_setup_report` (the report).

Pins:

- `tests/test_sanity_gate.py::test_a_reference_only_field_with_no_value_prints_the_marker` — content: the parse
  stores no value for the field, `vpn.tf` prints the marker through the print site, the same call on the same
  field answers the marker, and the record holds no row for the entry, so the unit declares no variable for it
  and no printed form names it. Fails before the change: the parse stored a value, and `printed_value` answered a
  variable name built from an empty source.
- `tests/test_sanity_gate.py::test_placeholder_check_warns_and_does_not_fail` — content: the gate reads the
  marker through the table's one statement, and it is a WARN, not a FAIL, and a comment that names the marker is
  documentation, not an emitted value. Fails before the change, because the table stated no marker.
- `tests/test_reports.py::test_per_gateway_placeholder_line_survives` — content: one line per pre-shared-key
  gateway inside its own section, and the marker the line names is the same constant the print site wrote. Fails
  before the change.
- `tests/test_real_or_report.py` — content, five pins: `test_report_only_areas_go_to_manual_setup_report`,
  `test_no_report_when_no_report_only_items`, `test_decryption_rules_emit_real_v`,
  `test_pbf_rules_emit_chained_v`, `test_pbf_monitor_profiles_emit_real_v`. No `.tf` file the run wrote holds the
  marker, because the marker lives in the report. The module states no copy of the marker; it reads it through
  `resource_mapping.PLACEHOLDER_TEXT`. Fails before the change, at the read of the constant, which is why the
  before-change run stops at this module's collection.
- `tests/test_sanity_gate.py::test_the_placeholder_is_stated_once_in_src` — source scan, for the reason stated
  above: the marker appears as a definition in `resource_mapping.py` only, no other `src/` module spells it, and
  the print site, the gate rule, and the report read it through the owner. Fails before the change: the print
  sites and the gate spelled it.
- `tests/test_property_coverage.py::test_measured_reads_equal_the_declared_properties` — content: the matrix row
  for `panos_ike_gateway` now states no `pre_shared_key`, and the measured reads the run produces still equal the
  declared properties. `tests/test_data_file_gate.py::test_check_order_puts_the_data_rule_after_the_block_rules`
  keeps the `CHECK_ORDER` position of the placeholder rule. Neither pin can fail before the change, for the reason
  recorded in the table at the end of this file.

## Measurement

Measured 2026-11-15, after the gate run.

Baseline: 1,659 pins in 50 test modules, all pass, no skips, `ruff check .` clean.
After: 1,673 pins in 50 test modules (16 pins added, 2 removed by rename), all pass, no skips,
`ruff check .` clean, exit 0 (`/tmp/opencode/final_pytest4.txt`). Counts by module are in
`/tmp/opencode/collect_final.txt`.

Counts by module that changed:

| Module | Before | After |
| --- | --- | --- |
| `tests/test_certificate_blocks.py` | 15 | 16 |
| `tests/test_filter_containers.py` | 19 | 21 |
| `tests/test_parse_helpers.py` | 4 | 6 |
| `tests/test_robustness.py` | 20 | 21 |
| `tests/test_sanity_gate.py` | 98 | 101 |
| `tests/test_state_input.py` | 21 | 22 |
| `tests/test_unit_manifest.py` | 34 | 36 |
| `tests/test_variables.py` | 19 | 20 |
| `tests/test_write_path.py` | 18 | 19 |
| All modules | 1,659 | 1,673 |

Goldens that moved, one copy per unit directory:
`tests/golden/kitchen_sink/fw_template_00a08cdc/filters.tf`,
`tests/golden/kitchen_sink/fw_template_00a08cdc/virtual_routers.tf`, and
`tests/golden/filter_containers/fw_template_00a08cdc/filters.tf`. No certificate golden moved, and no
`variables.tf` golden moved.

Before the change: the pins as they now stand, run against the source before the change (`git checkout
HEAD^ -- src/`, the parent of `53c9d1c`), in a scratch tree at `/tmp/opencode/before` so the pins and the goldens
are the ones this piece wrote. 23 pins fail, 1,645 pass, no skips, exit 1
(`/tmp/opencode/before_final2.txt`). The five `tests/test_real_or_report.py` pins cannot run at all before the
change: they read the marker through `resource_mapping.PLACEHOLDER_TEXT`, which the table did not state, so the
run stops at their collection (`/tmp/opencode/before_final.txt`). 28 of the 1,673 pins fail before the change,
and each of the eight items has at least one.

Pins that fail before the change, by item:

| Item | Pins that fail before the change |
| --- | --- |
| 1 | `test_robustness.py::test_a_static_route_block_digests_the_route_name_once`; `test_golden_files.py::test_golden_bytes_match[kitchen_sink-fw_template_00a08cdc/virtual_routers.tf]` |
| 2 | `test_unit_manifest.py::test_the_fallback_word_is_stated_once_in_src` |
| 3 | `test_variables.py::test_the_record_refuses_two_entries_that_name_one_variable` |
| 4 | `test_filter_containers.py::test_the_parse_method_states_no_path_of_its_own`, `test_filter_containers.py::test_the_parse_reads_the_paths_the_table_states`, `test_filter_containers.py::test_the_emitter_prints_the_fields_the_entry_row_declares`, `test_filter_containers.py::test_the_print_sites_state_no_second_order_rule`; `test_golden_files.py::test_golden_bytes_match[filter_containers-fw_template_00a08cdc/filters.tf]` and `[kitchen_sink-fw_template_00a08cdc/filters.tf]` |
| 5 | `test_robustness.py::test_escape_string_prints_the_shapes_it_escapes`; `test_sanity_gate.py::test_the_control_character_rule_is_stated_once_in_src`; `test_state_input.py::test_the_state_door_refuses_a_control_character_in_a_value` |
| 6 | `test_parse_helpers.py::test_the_value_helpers_read_the_text_the_read_layer_states`; `test_parse_helpers.py::test_a_value_with_surrounding_whitespace_prints_without_it` |
| 7 | `test_write_path.py::test_add_once_keeps_its_own_once_record` |
| 8 | `test_sanity_gate.py::test_the_placeholder_is_stated_once_in_src`, `test_placeholder_check_warns_and_does_not_fail`, `test_a_reference_only_field_with_no_value_prints_the_marker`; `test_reports.py::test_per_gateway_placeholder_line_survives`; `test_real_or_report.py` (five pins, at the read of the constant) |
| 1 and 4, through the whole golden set | `test_ownership.py::test_the_goldens_are_byte_identical`, `test_reference_edges.py::test_the_golden_tf_bytes_are_unchanged`, `test_unit_manifest.py::test_the_generated_tf_bytes_are_unchanged` |

The pins that measure the rule and cannot fail before the change, with the reason:

| Pin | Item | Reason it cannot fail before the change |
| --- | --- | --- |
| `test_unit_manifest.py::test_the_word_prints_the_same_string_at_both_print_sites` | 2 | two definitions of one word print the same string |
| `test_certificate_blocks.py::test_the_block_prints_the_fields_in_the_order_the_row_states` | 4 | no certificate row states `name` off the first position, so the sort answered the row order |
| `test_site_data.py::test_a_name_two_rows_state_prints_one_line`, `test_only_the_device_field_maps_to_a_variable` | 3 | the writer already refused one name with two values, and the filter answered the same set |
| `test_sanity_gate.py::test_control_char_check_detects_a_raw_control_character`, `test_write_path.py::test_the_bytes_a_run_writes_hold_no_cr` | 5 | the gate answered the same findings from its own copy of the rule |
| `test_container_coverage.py::test_every_row_path_is_read_by_its_method`, `test_entry_coverage.py::test_every_name_guard_records_the_entry_it_reads` | 4, 6 | the pre-change methods stated the literals the scans already matched |
| `test_property_coverage.py::test_measured_reads_equal_the_declared_properties` | 8 | the matrix row and the parse changed together, so the agreement holds on both sides |
| `test_robustness.py::test_declare_resource_name_avoids_collisions`, `test_declare_empty_name_gets_a_stable_name` | 1, 2 | unchanged pins that measure a rule the change does not alter |
