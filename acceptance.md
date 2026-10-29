# Acceptance criteria — F6.6 The site data layer

F6.6 (Epic 6, Goal 6) separates the standard from the site: the device name a resource block
prints becomes a variable, the site values become a data file, and the `.tfvars` the platform
reads is written from that data. The design record is `docs/CODEBASE_ASSEMBLY.md` §9.

F6.6 writes no directory, so the write path (§14) stays open, and no feature after F6.6 is
started here.

## Decisions

### 1. The mapping is default output, not a flag

The value-to-variable mapping applies to every run. It is not an opt-in shape.

1. A table that only applies when a flag is on is not a rule: the same input fact would print two
   ways from one table, so the tool would have two rules for one value.
2. The gate rule `variables` (F2.10) already refuses a declaration with no consumer, so the only
   way to keep a run clean is to declare exactly what the run prints. A flag would create a
   declaration set that depends on the flag, and the report and the gate could not agree with the
   bytes.
3. `docs/CODEBASE_ASSEMBLY.md` §9 rule 1 states the problem as a codebase rule, not as a style: a
   literal device name makes a site change a code change, because it appears in every resource in
   the template.

Consequence for the goldens: the golden files that carry a device location change. For the
kitchen-sink case, `address_objects.tf`, `service_objects.tf`, `zones.tf` and
`virtual_routers.tf` print `ngfw_device = var.<name>` instead of the literal, and `variables.tf`
gains the device variable. The sample set is byte-identical, because the sample names no device:
its only device entry is the "this device" placeholder, which names no device (F3.5). That is the
proof that the change is the mapping and not a style: the rule prints a reference only for a value
the table maps, and a run that reads no mapped value writes the same bytes as before.

No other golden byte changes, because no other emitter changes.

### 2. The site data file, and how a site row joins to a unit

`SITE_DATA.json`, one file per codebase run, one row per site. F6.1 rule 4 still refuses a
per-unit file, because F6.6 writes no directory: a per-site file would sit outside the shape it
names, and a reader cannot find it before it knows the directory name. The row is written for a
unit that names at least one site value, following the rule that a file is written only when it has
content, so a run that names no value writes no file.

A site is a unit (the device group and the template the export joins through one device, §1), so
the row joins to `CODEBASE_MANIFEST.json` on `directory`, the same join `OWNERSHIP.json` (F6.2) and
`REFERENCE_EDGES.json` (F6.3) use. No second unit rule and no second place that states the unit set
appears here: the identity and the directory name are read through `unit_manifest.facts_of` and
`unit_manifest.directory_name`.

| Field | Value |
|---|---|
| `directory` | the unit this row joins to, the `CODEBASE_MANIFEST.json` `directory` |
| `variables` | `{the variable name: the value}`, sorted by name. Empty for a site that names no value |

The name is the value read through the §5 naming rule, so `variables` is the mapping result and the
row states no value twice. `parse_rows` reads a written file back as data and refuses a row that is
not the declared shape, the way `unit_manifest.parse_rows` does. Rows print in identity order.

The reports do not name a site field, and the gate reads no data file, so this file is not a gate
input (`ARCHITECTURE.md` §4.5).

### 3. The value-to-variable mapping is a pinned table

`resource_mapping.VALUE_VARIABLES` is the table. One row per location field the emitter prints — the
five fields `LOCATION_SCHEMA` declares — and each row states what the block prints for it:

| Field | Prints as | Reason |
|---|---|---|
| `ngfw_device` | variable | the device the site names. Hardware replacement changes the serial, so this is the value a codebase changes per site (§9 rule 1) |
| `name` | literal | the entry name is the row identity, not a site value (§8 rule 3) |
| `vsys` | literal | a virtual system is a scope name, not a site value |
| `panorama_device` | literal | the Panorama host is the credential gap (§11), and the codebase states no device fact in a location (§8 rule 6) |
| `rulebase` | literal | the parse records no rulebase (F3.5) |

The table covers the location fields only, because `location` is the part of a block that names the
scope a site is in. A property at the block's own level is the entry's content, not a site value, so
it is not in the table (decision 4).

`ngfw_device` is the only row that maps to a variable. The test pins that the table covers every
field `LOCATION_SCHEMA` declares, so the rule is complete and cannot gain a field without a row.

The variable name is the §5 naming rule applied to the value. The rule moves to `naming.py`,
because the gate must read it without the generator (decision 7) and no module may define a second
one. `TerraformGenerator.sanitize_name` calls `naming.sanitize`; the modules that take the rule as an
argument keep taking it, so no second naming rule exists. A device name that names no device names
no variable: `localhost.localdomain` (`container_coverage.PLACEHOLDER_DEVICE`) never enters a
location (F3.5), so it never enters the table's mapping, and no site row states it.

The provider fact for `target` (§12) is not implemented here: the tool writes no provider `target`
argument today, and the per-unit `.tfvars` that names one belongs to the write path (§14), which is
still open. Recorded in `backlog.md`.

### 4. `panos_template_variable` stays a literal

`panos_template_variable` prints the value the export states, as F6.5 chose. It does not become a
`var.` reference, for two reasons:

1. In PAN-OS the block *is* the variable. A `var.` reference for its own value would make the
   resource a pass-through that prints a value the `.tfvars` supplies, which states the fact twice.
2. The tool cannot know which values a module takes as parameters: §9 says a module is a standard a
   person writes, so a value the tool turns into a variable is a choice the tool cannot make for the
   entry content.

The decision is recorded in `backlog.md` as the follow-up for the write path. No variable is
declared for a template variable value, so the gate rule `variables` cannot be tripped by it, and
the emitter prints what it reads.

### 5. The `.tfvars` writer

The tool writes `site.auto.tfvars` from the site data rows, not from the generator's state: the data
is the fact, and the `.tfvars` is its printed form.

1. The file name is `site.auto.tfvars`, not `terraform.tfvars`. Terraform loads
   `terraform.tfvars` as the operator's own file, which holds the credentials, and the tool never
   writes a credential (§11). Terraform loads a `*.auto.tfvars` file automatically, so the
   generated values sit in a file the operator does not own and the run cannot overwrite their
   credentials.
2. One line per variable, sorted by name: `<name> = <value>`. A name that two site rows state
   prints one line, because the name is the §5 shape of the value, so one value cannot produce two
   names.
3. A string prints as `json.dumps(value)`, which is the same escape set `import_blocks.unescape`
   reads back, so no second escape rule appears.
4. A list prints inline as `[ "a", "b" ]`, with each item through the same rule. An empty list
   prints `[]`.
5. A value that is neither a string nor a list of strings is a refusal, because the row shape
   declares no other kind.
6. The file is written only when it has content, following the rule for the report files and the
   three existing data files.

### 6. Which emitter prints the reference, and what it records

`TerraformGenerator.location_field`, called by `location_block`, prints one location field as the table
says: `var.<name>` through `naming.variable_text` for a field the table maps to a variable, and the escaped
value through the existing escape rule for every other field. The printed text is the mapping result, not a
block reference, so no `HclRef` and no change to the dependency wiring rule (§4.3): a location field is a
value, and a reference is a name that resolves to a block.

`location_data` keeps the value, because the value is the fact the import id encodes (decision 7).
The mapping is applied at the print site, and the print site records the pair — the unit facts, the
variable name, and the value — the way `name_ref` records a reference name for the manifest
(F6.1). `site_data.build_rows` resolves nothing and names no value the run did not print, so the
declaration set is the set the run consumed, and the gate rule `variables` cannot be tripped.

`generate_variables()` therefore runs after the emitters: the file cannot state a variable the run
has not consumed. The order rule for `scope.tf` (before the object files) is unchanged; only the
position of `variables.tf` moves. `tests/test_scope_objects.py` is updated to pin the new position,
and `docs/CODEBASE_ASSEMBLY.md` §6 and `docs/ARCHITECTURE.md` §4.1 name it.

### 7. The gate rules

No new check, so `CHECK_ORDER` is unchanged. Two rules change, and each violation type is pinned.

1. **`import_blocks`** (F6.4). The agreement rule reads the block's location through the one block
   reader, which now reads a field as the block states it: the unescaped value for a quoted field,
   and the reference text `var.<name>` for a field the table maps. For a field the table maps, the
   rule compares the printed name against the §5 name of the value the id states; for every other
   field it compares the value. The id keeps the value, because the provider parses the id and a
   variable name is not a device name. The rule reads the table and the one naming rule, so no second
   location rule and no second naming rule appear.
   The rule compares names, so it cannot detect an id that states the mapping result instead of the
   value: `naming.variable_name` is idempotent, so the §5 name of `fw_2_example_com` is
   `fw_2_example_com`. The writer always states the value in the id, so an id built by the tool cannot
   carry the name. What the rule can detect is pinned: a block that prints a literal for a mapped
   field, and a value for an unmapped field that does not agree with the id. This is a limit of
   comparing a mapping result, not a gap in the test.
2. **`variables`** (F2.10). The rule now reads both directions: every declared variable has a
   `var.` consumer, and every `var.` consumer names a variable this run declares. The second
   direction is what makes a generated declaration set checkable when the declaration set comes
   from the mapping.

The corpus produces no finding for either rule.

### 8. Quality gates

- `ruff check .` is clean, and `pytest` is green. Every test runs offline.
- The goldens change only as decision 1 states: the four kitchen-sink files that carry a device
  location, and `variables.tf` for that case. The sample set is byte-identical.
- Exit codes are unchanged: 0 for a run, 1 for an input refusal, 2 for an argument error. No new
  flag, so no new argument error path.
- Two runs on the same bytes write the same bytes for `SITE_DATA.json` and `site.auto.tfvars`, and
  neither file names a path or a timestamp.
- No report names a field the site data states, and the gate reads no data file.
- No second naming rule, no second location rule, no second block reader, and no second unit rule
  appears in any module.

## Acceptance criteria

1. **The table.** `VALUE_VARIABLES` covers every field `LOCATION_SCHEMA` declares, states what the
   emitter prints for each, and maps only `ngfw_device` to a variable. Pinned by
   `tests/test_site_data.py`.
2. **The site row.** One row per site that names a value, the declared fields in the declared
   order, rows in identity order, the join to the manifest on `directory`, read back as data, and a
   row that is not the declared shape is refused.
3. **The `.tfvars` bytes.** The writer rule is pinned for a string and for a list, the lines are
   sorted and deduped, and a run that names no value writes no file.
4. **The device name as a variable.** The emitter prints `var.<name>` for a mapped field, and the
   golden bytes pin it for the kitchen-sink case. A field the table does not map still prints as a
   literal. The placeholder device names no device and no variable.
5. **The declaration set.** `variables.tf` declares the credentials plus the values the run
   consumed, and the test reads the site set through `site_data.parse_rows`, so the file and the
   data cannot disagree.
6. **Gate.** `check_import_blocks` detects a variable field that does not agree with the id, and
   `check_variables` detects a consumer that names no declaration. No fixture trips a false
   positive.
7. **Determinism.** Two runs on the same bytes write the same bytes for both new files.
8. **No change elsewhere.** Reports, the manifest, the ownership record, the edge record, the
   provenance record, `scope.tf`, `imports.tf`, and `read_through.tf` are unchanged for the corpus,
   except the goldens decision 1 pins.
9. **Docs.** `docs/CODEBASE_ASSEMBLY.md` §9 names the module and the test for each rule, §14 moves
   the step, `docs/ARCHITECTURE.md` §1, §3.7, §4.1, §4.2, §4.5, §4.6 and §5 state the changed rules,
   and `README.md` and `docs/USAGE_GUIDE.md` name `SITE_DATA.json` and `site.auto.tfvars`.
