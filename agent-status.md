# Agent Status

## Current position

F5.5 (read-through data blocks) is still the open feature, and its pieces are in `to-do.md`. On
2026-10-27 the Epic 6 planning pass ran: what a full codebase needs, and what the converter does not
do yet. The design record is `docs/CODEBASE_ASSEMBLY.md` (design only, no rule implemented), the
feature list is `PLAN.md` Epic 6, and the open decisions are in `backlog.md`. No code changed, so the
gate is unchanged from F5.6: `ruff check .` clean, `pytest` 758 passed, both golden sets
byte-identical, report and record determinism pinned, exit codes unchanged, every test offline.

The next code feature is still F5.5. It is the first half of the codebase reference mechanism, so the
Epic 6 reference decision (`docs/CODEBASE_ASSEMBLY.md` §5) waits for it. Write `acceptance.md` before
the F5.5 code.

## What F5.6 changed

- `state_input.py` (new, the producer and its door): `check_bytes` runs the two byte checks, then the
  kind chooses the parse step. `parse_state(data, origin, workspace=...)` reads the document;
  `read_state(path, workspace=...)` is the file producer. `StateEntry` (resource type, resource name,
  entry name, attributes, address) and `StateSource` (origin, name, size, sha256, scope, entries). The
  document-shape refusals use the door's refusal class, so an input refusal exits 1 and writes no
  record.
- `state_coverage.py` (new, the rule owner): the two headings, the two rule paragraphs, `nested_block`,
  `state_facts`, `state_properties`, `STATE_SCOPE_KEYS`, `STATE_IDENTITY_KEYS`, `state_index`,
  `state_findings`, `drift_properties`, `value_text`, `ownership_line`, `drift_line`. It owns no
  console wording, so a state fact prints only in the report.
- `xml_input.py`: `check_bytes` is the two byte checks for every source kind, and `origin_phrase` is
  the phrase a refusal uses to name a source. Only the parse step is chosen by the kind.
- `entry_coverage.py`: `RecordingDict.value(key)` reads a captured value without recording it, so the
  state scan is not an output read. `EMPTY_FIELD_VALUES` is the one definition of an empty value, read
  by the property rule and by the state scan.
- `container_coverage.py`: `PLACEHOLDER_DEVICE` is the one definition of the "this device" name, read
  by the generator (`_LOCAL_DEVICE_PLACEHOLDER`) and by the state scan.
- `provenance.py`: `record_for` reads the record facts from a `ParsedSource` or a `StateSource`; rule 5
  states the read order (main, parent, state) and that a state record references nothing, so it prunes
  nothing.
- `main()`: `--state` and `--workspace` (`--workspace` needs `--state`, exit 2; `--state` applies to
  both source kinds), the state read after the main and parent reads, the scan,
  `generate_conversion_report(ledger, shadows, state_findings)`, and the state record appended in read
  order.
- Fixture: `tests/fixtures/state_workspace.json`, 14 resources, one rule each, so every entry the scan
  must not key is in the file.
- Tests: `tests/test_state_input.py` (21 tests, six groups) and `tests/test_state_coverage.py`
  (23 tests, six groups). `conftest.run_pipeline` returns the parser, so a coverage test reads the
  facts from the run.

## Facts measured during F5.6

- A JSON document has no prolog, so the DTD check reaches no DOCTYPE and a `<!DOCTYPE` inside a JSON
  value is legal input. The size check still refuses a state document over the limit.
- The corpus pins iterate `tests/fixtures/*.xml` only, so a JSON fixture cannot move
  `test_committed_corpus_has_no_findings` or `CORPUS_FINDINGS`. A new XML fixture would.
- `EntryLedger.scope(entry)` returns only the declared facts, so a shared run entry keys with four
  empty facts, never the `Shared` fallback. This is why the ownership key reads declared facts.
- `LOCATION_SCHEMA` declares no `template_stack` sub-block for the address row, so a state entry placed
  in a template stack returns None from `state_facts` and is not keyed.
- A nested `location` block reads as an object or as a one-element list of an object; both shapes are
  in the fixture and both key the same entry.
- Values compare as the two sides hold them, so `["a", "b"]` and `["b", "a"]` are two values. That is
  the service group member-order finding in the fixture.
- The drift line is the ownership line with the values added, so the drift section is a subset of the
  ownership section.
- Pinned entries: `Web-Server-1` at line 5 of `address_objects.xml` (drift), `Web-Range` at line 13
  (ownership only), `Web-Services` at line 5 of `service_groups.xml` (member order), and
  `North-America` in `regions.xml` as a count-only row, which the scan cannot read.

## Facts measured during the Epic 6 planning pass (2026-10-27)

Provider 2.0.14, through `terraform providers schema -json` and the provider docs:

- The schema holds 128 resources, 128 data sources, and 2 actions: `panos_commit` and
  `panos_push_to_devices`. Actions need Terraform 1.14 or later; the provider needs 1.8 or later.
  `panos_commit` can commit one device group, one template, or one template stack, so a commit can stay
  inside one unit.
- No resource registers a device, defines an HA pair, sets a management interface, or holds an auth key.
  So the Day 1 bootstrap cannot be expressed in Terraform with this provider. The provider names a
  device (`location.ngfw_device`, `panos_device_group.devices`, the `target` argument) and nothing else.
- A resource exists for each scope: `panos_device_group` (`parent`, `devices`, `templates`),
  `panos_device_group_parent`, `panos_template` (`default_vsys`), `panos_template_stack`,
  `panos_template_variable`, `panos_vsys`. The container table marks the two parse methods that read the
  scopes as `bookkeeping`, so no scope is emitted today.
- No resource schema declares an `id` attribute, so the import id is the base64 JSON of the location plus
  the name. For the four `*_policy_rules` types the import object also names the rulebase, the position,
  and a list of names. The generator writes the same location block, so an import block can come from the
  same data as the resource block.
- The provider supports a local inspection mode (`config_file`, `panos_version`), which reads a config
  file with no server. No rule in this project uses it, and a plan in that mode cannot show drift.
- The gate reads `resource` blocks only, so a `data` block, an `import` block, and an `action` block are
  not checked. F5.5 writes the first rule that reads a block that is not a resource block.
- `panorama_to_terraform.py` `generate_variables` declares `panos_hostname`, `panos_username` and
  `panos_password`, and `generate_provider_config` uses them, while the fetch rule keeps the key in the
  environment only. One rule must cover both.
- `tests/golden/kitchen_sink/zones.tf` writes `ngfw_device` as a literal, so a serial change changes
  every resource in that template. A codebase needs the device name as a variable.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record (the audit report) keeps its findings and states the current
  state separately, so a reader does not take an old finding as a fact.
- A record is data, so a document describes its fields and never restates a record. The
  example in `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, not a pin.

## Watch for F5.5

- `DATA_SOURCE_SCHEMA` must be written from the provider `data_source_schemas`, not from memory. The
  check ran on 2026-10-27 through the `provider_schema` fixture: 128 data sources mirror the 128
  resources, the 126 shared types have the identical attribute set and the identical `location`
  sub-blocks, and the two name-level mismatches are `panos_certificate_import` and
  `panos_virtual_router_interface` (a resource with no data source) and `panos_certificate` and
  `panos_predefined_dlp_file_type` (a data source with no resource).
- Corrected during that check: a data source schema does declare required attributes. `location` is
  required for all 128, and `name` is required for every data source that has a `name` attribute (106
  types). 22 data sources have no `name` attribute, the settings, policy and collection shapes, so the
  gate rule must be stated without `name` for them. The gate reads only `resource` blocks today, so the
  F5.5 rule is the one that reads a `data` block at all: without `--validate` nothing checks a `data`
  block, and validate accepts a `location` sub-block the type does not declare by dropping it silently.
- The provider check needs the terraform binary and the provider cache. It skips without them, so the
  table test needs a committed schema snapshot or a skip marker, decided before the test is written.
- The prune action still needs the record directory decided. A state record references nothing, so it
  prunes nothing, and the prune rule reads a record file, not one record.
- A coverage fact that comes from a run must be read from the run's ledger, so the scan tests run the
  pipeline in process.
- F5.5 is the first half of the codebase reference rule (`docs/CODEBASE_ASSEMBLY.md` §5). Write the gate
  block reader so a later kind can use it: `import` blocks (Epic 6 F6.4) and `action` blocks (F6.7) need
  the same reader, so a second block reader should not appear.
