# Acceptance Criteria — F4.2 Entry Coverage (Parse Side)

Scope: F4.2 only. The parse side records each entry's source position and the
container table moves from `docs/ARCHITECTURE.md` §3.1 into code. A container
the parser does not read is reported instead of skipped.

Out of scope for this task (tracked in PLAN.md Epic 4 and backlog.md):
- F4.3 field coverage, `tests/COVERAGE.md`, per-object field reports.
- F4.4 property-level coverage, `EMITTED_TYPES` reconciliation.
- `MANUAL_SETUP_REPORT.txt` section redesign and report determinism beyond the
  new section (F4.3).
- `resource_name_map` and name dedup (F4.4).
- F4.1 gate severity: a coverage gap is an operator action, so this task adds
  no FAIL finding and changes no F4.1 exit code.

---

## AC-1 — The parse records the source line of every element

1. `xml_input.parse_xml(path, max_input_bytes)` returns a `ParsedSource` with:
   `name` (file name, no absolute path), `root`, and `line_of(element)`.
2. `line_of(element)` returns the 1-based line of that element's **opening
   tag** in the source text.
3. The read still happens once, under the F3.8 size cap and the parser-level
   DTD refusal. No bytes are read before both checks pass. The F3.8 tests in
   `tests/test_safe_input.py` stay green and unchanged.
4. A parse error is still raised as `xml.etree.ElementTree.ParseError`, so the
   F3.8 error contract (the shared catch in both entry points) is unchanged.
5. The tree is equivalent to `ET.fromstring` for the pinned shapes: tag,
   `name` attribute, child order, comments, and namespaced tags. Namespace
   prefixes map to the `{uri}tag` form ElementTree produces.
6. The line map covers the tree that was parsed. An element copied out of it
   (the device-group splitter builds new trees) is not in the map, and the
   module states that.
7. A line number is the line in the source file, so it matches the text the
   operator can open. A UTF-16 input is pinned: the BOM is not a line.

## AC-2 — The container table lives in code, one row per parse method

1. `container_coverage.CONTAINER_TABLE` is the single source of truth for the
   parse side. Each row holds: parse method, container path, destination kind,
   note.
2. Destination kinds are the five in the code: `emitted`, `report`,
   `inventory`, `count-only`, `bookkeeping`. `docs/ARCHITECTURE.md` §2.4 and
   §3.1 point at the code instead of restating the rows.
3. Every parse method (`PanoramaParser.parse_*`) has at least one row.
4. Every row names a parse method that exists in `PanoramaParser`.
5. Every row's path is a pattern that method actually reads, checked against
   the method's source AST (`find` / `findall` patterns). An orphan row fails.
6. The table is pinned by tests, so a new parse method without a row fails the
   gate.

## AC-3 — The entry-container rule is stated once and pinned

1. A container is a **section** when no config-object entry lies between it and
   the config root or a scope entry. The scope containers are `device-group`,
   `templates`, `template-stack`, `devices`, `vsys` — the same set the four
   scope facts walk (F3.5).
2. A container inside a config-object entry is a property level, not a section.
   It is not reported here; F4.4 covers it.
3. The rule is in `container_coverage.py`. The tests call the module functions
   instead of restating the rule.
4. Matching is by suffix on the tag chain from the config root, so a section
   found through the corpus layout (`pre-rulebase/security/rules`) matches the
   table row (`security/rules`).

## AC-4 — An unknown container is reported, not skipped

1. A section container with no table row produces one finding: tag chain from
   the config root, opening line, entry count.
2. A known container that is absent from the input is not a finding. An absent
   section is not a gap.
3. A known container present with no entries is not a finding, so the corpus
   stays quiet for empty sections.
4. Findings are sorted by tag chain, then line. Two runs on the same input
   write the same bytes. The report section names the input file name, never an
   absolute path.
5. The section is written in `MANUAL_SETUP_REPORT.txt` and printed on the
   console only when there is a finding. A run with no findings writes the same
   bytes as before this feature.
6. A finding does not change the conversion exit code (F4.1 sets it).

## AC-5 — Tests pin the rules

1. Line tracking: pinned line numbers on a fixture, a multi-line entry, a UTF-16
   input, and the copied-element case.
2. Table ↔ code parity in both directions (AC-2.3–AC-2.5).
3. The section rule: a section and a property level on the same fixture.
4. Unknown container: a fixture with unread sections, the finding fields, the
   report bytes, and the console line.
5. Corpus: every committed fixture and `sample_panorama_config.xml` produces no
   finding, so the parse side is fully covered before F4.3 starts.
6. The report is byte-identical between two runs of the same input.

## AC-6 — Gate stays green

- `ruff check .` clean.
- `pytest` passes (F3.6, F3.7, F3.8, F4.1 tests unchanged where possible).
- Golden `.tf` output unchanged for every fixture.
- `terraform validate` passes.
- Exit codes unchanged: 0 for a clean run, 1 for a broken output or a refused
  input.

---

## Audit Against The Current Code (2026-10-20)

| Criterion | Current state | Action |
|---|---|---|
| AC-1 | `parse_xml` returns `ET.fromstring(read_input(path))`. No element has a line number; `ElementTree` does not record one. | Build the tree through expat handlers so the opening line is recorded while the same bytes are parsed once. |
| AC-2 | The container table is prose in `docs/ARCHITECTURE.md` §3.1 (~40 rows). Nothing in code lists it, so no test can check it. | New `container_coverage.py` with `CONTAINER_TABLE` and the destination kinds. |
| AC-3 | `findall('.//address/entry')` is the rule, stated in docs §3.1 only, with one exception (`parse_interfaces` virtual-wire). | State the rule in code; tests pin both halves. |
| AC-4 | An unread container is skipped silently. The existing reports have no entry-container coverage. | Scan returns findings; the report gains a section; the console prints one line. |
| AC-5 | No test covers entry-container coverage. `tests/test_coverage_matrix.py` covers `EMITTED_TYPES` only (F4.4 scope). | New `tests/test_container_coverage.py` and line-tracking tests in `tests/test_safe_input.py`. |
| AC-6 | 170 tests pass, ruff clean, goldens and `terraform validate` green. | Must stay green. |

Corpus state measured before the change: every entry-container section in every
committed fixture and `sample_panorama_config.xml` is read by a parse method, so
the scan finds nothing on the existing corpus. The gaps recorded in
`docs/ARCHITECTURE.md` §3.1 are property-level shapes inside a known container
(schedule `time` ranges, EDL `recurring` values, QoS `class`, OSPF `area`
fields), which AC-3.2 assigns to F4.4. A new fixture is needed to demonstrate a
section the parser does not read.

---

## Result (2026-10-20) — F4.2 complete

Two criteria changed during implementation, and the code states them:

- AC-2.2 has **six** destination kinds. `nested-block` was added because a
  virtual-wire, TAP, `ip` and `ipv6/address` shape writes lines inside a parent
  resource block and has no resource type of its own. `docs/ARCHITECTURE.md` §2.4
  lists both kinds.
- AC-4 adds one rule the plan did not have: an entry container under `predefined`
  is not a finding, because those entries are PAN-OS built-in definitions, not
  operator objects. `container_coverage.is_predefined` states it.

One F3.8 test changed, as AC-1.1 required: `test_parse_reads_the_file_once` now
reads `parse_xml(...).root`. Every other F3.8 test is unchanged.

Gate:

- `ruff check .` clean.
- `pytest` 539 passed (509 before, 24 in `tests/test_container_coverage.py`,
  30 in `tests/test_safe_input.py`).
- Golden `.tf` output unchanged; `terraform validate` green on all four outputs.
- Exit codes unchanged. A run on a fixture with findings exits 0.
- A run with no findings writes the same bytes as the committed code before this
  feature (verified against commit 131bc69 for `sample_panorama_config.xml` and
  `kitchen_sink.xml`: same file set, byte-identical reports).

The corpus scan still finds nothing, as the audit predicted. The new fixture
`tests/fixtures/unknown_containers.xml` is the demonstration input: four sections
(`document`, `data-entry`, `device-group/entry/certificate`,
`devices/entry/vsys/entry/import`).
