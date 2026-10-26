# Acceptance Criteria — Documentation Refresh (current task)

Scope: bring every document in this repository in step with the code. A
document may state only what the code does today, and each rule it states names
the test or the module that holds it.

Out of scope for this task:
- Any change to parser, generator, gate or test behaviour. The gate must stay
  green without a behaviour change.
- Fixing the report gaps the documents describe (the ones recorded in
  `backlog.md`). The documents report them; they do not fix them.
- Feature work on F4.4 (the property-level matrix).

---

## AC-1 — Every claim is verified against the code

1. Each document was checked against the code it describes. A claim is kept
   only when the code holds it.
2. No document states a capability the code does not have. The retired claims
   are listed in the drift table below.
3. Where a limit exists, the document states the limit and points at
   `backlog.md`, instead of presenting the output as complete.

## AC-2 — One document per topic, no overlap

1. The two multi-VR documents merge into the migration guide, and the quick
   answer merges into the device-group splitting guide.
2. `docs/` has one index (`docs/README.md`) that names each document and the
   reader task it serves. Every document is reachable from it.
3. No document restates a rule that another document owns. It links instead.
   The rule owner is: data model and pipeline → `ARCHITECTURE.md`; per-type
   mapping → `RESOURCE_MAPPING.md`; coverage → `COVERAGE_MATRIX.md`; CLI use →
   `USAGE_GUIDE.md`; operator workflow → `MIGRATION_GUIDE.md`; splitting →
   `DEVICE_GROUP_SPLITTING.md`.

## AC-3 — Style

1. ASD-STE100 Simplified Technical English: short sentences, present tense,
   one idea per sentence, active voice, the same word for the same thing.
2. Programming vocabulary is allowed where it is the precise term.
3. No marketing voice, no emoji, no unverifiable claim, no pricing or support
   promises.
4. No test counts in documents. A document names the test that pins a rule; the
   count lives in `agent-status.md` and the git history.
5. No epic, phase or task numbering in documents, except where a feature id is
   the name a module or test uses (for example `F4.4`).

## AC-4 — In-code documentation

1. The generated output `README.md` text lists the files the generator writes
   and the steps an operator takes before apply.
2. The CI workflow comment states what the terraform job runs today.
3. Module and test docstrings state current behaviour, not a plan.
4. `quick_start.sh` prints the current steps, including the post-run gate.

## AC-5 — Records

1. `PLAN.md` keeps the goals and the open epic, without restating completed
   epic detail.
2. `to-do.md` tracks the pieces of this task.
3. `backlog.md` gains each gap a document confirmed, and loses nothing that is
   still open.
4. `agent-status.md` records where this task ended.

## AC-6 — Gate stays green

- `ruff check .` clean.
- `pytest` passes with no test expectation changed, because no behaviour
  changes.
- Golden `.tf` output unchanged.
- `terraform validate` passes.
- Exit codes unchanged.

---

## Drift table (claims found while reading)

| Document | Claim | Code says | Action |
|---|---|---|---|
| `docs/USAGE_GUIDE.md` | "Automatic deduplication of resources" | no name-keyed dedup since F3.1 | remove |
| `docs/USAGE_GUIDE.md` | supported address types are netmask/range/FQDN | every type with a v2 attribute emits; location and external types are report-only | restate |
| `docs/USAGE_GUIDE.md` | supported list omits zones, interfaces, VPN, decryption, PBF, monitor profiles | all emit | restate |
| `docs/USAGE_GUIDE.md` | output list omits `CONVERSION_REPORT.txt` | written when a run has report rows | add |
| `docs/USAGE_GUIDE.md` | "Debug Mode" adds `logging` | no logging in either script; the reports and the gate are the read-out | remove |
| `docs/USAGE_GUIDE.md` | "Version History v1.0" | history lives in git | remove |
| `docs/USAGE_GUIDE.md` | "Large configurations: modify the script" | the splitter and the input size cap are the supported route | restate |
| `docs/MIGRATION_GUIDE.md` | interfaces "generated as reference", VPN "not supported", profiles "listed only" | interfaces, zones, routers, VPN and profile groups emit real resources | restate |
| `docs/MIGRATION_GUIDE.md` | "Check for deprecated features" | unverified | remove |
| `docs/VPN_ROUTING_CONFIG_EXAMPLES.md` | BGP and OSPF generate `bgp.tf` and `ospf.tf` | report-only, no such file | restate |
| `docs/COVERAGE_MATRIX.md` | "20 rows" | `COVERAGE_MATRIX` holds 28 rows | regenerate the table |
| `docs/COVERAGE_MATRIX.md` | table missing decryption, PBF and monitor-profile rows | three rows exist in code | add |
| `docs/RESOURCE_MAPPING.md` | 23 emitted / 10 report-only / 2 not emitted | 28 / 10 / 3 | correct |
| `docs/RESOURCE_MAPPING.md` | Network table lists 6 types | 11 emitted network types | add the five interface kinds |
| `docs/DEVICE_GROUP_SPLITTING.md` | split output contains `bgp.tf`, `ospf.tf` | no such file | correct the tree |
| `docs/DEVICE_GROUP_SPLITTING.md` | "Bug in splitter" for missing shared objects | shared objects are copied by design | restate |
| `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md` | ARE redistribution is not parsed | `parse_bgp` captures `redist-rules`, the report does not print them | restate, record in backlog |
| `docs/DUAL-LICENSING-EXPLAINED.md` | pricing, support tiers, warranty, contact addresses | unverified legal and commercial claims | trim |
| `docs/ARCHITECTURE.md` §7 | "F4.3 — no per-entry CONVERSION_REPORT.txt" | F4.3 landed 2026-10-20 | correct |
| `docs/ARCHITECTURE.md` §4.5 | "Three report files" | four reports plus the gate report | correct |
| `.github/workflows/python-tests.yml` | "validate check is xfail until Epic 2" | the gate runs green | correct |
| `tests/test_golden_files.py` | goldens are the "before/after reference" for the Epic 2 rewrite | the rewrite landed | correct |
| `AGENTS.md` | "API cheat sheets are in lib_docs/" | `lib_docs/` does not exist | record in backlog |
| generated output `README.md` | file list names 7 files; "Adjust rule ordering as needed" | the generator writes more files and preserves XML order | correct |

---

## Result

Met. Every document states what the code does today.

- Documents rewritten or corrected: `README.md`, `docs/README.md` (new index),
  `docs/USAGE_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/RESOURCE_MAPPING.md`,
  `docs/COVERAGE_MATRIX.md`, `docs/MIGRATION_GUIDE.md`,
  `docs/DEVICE_GROUP_SPLITTING.md`, `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md`,
  `docs/VPN_ROUTING_CONFIG_EXAMPLES.md`, `docs/DUAL-LICENSING-EXPLAINED.md`,
  `AGENTS.md`, `PLAN.md`, `backlog.md`, `ADVERSARIAL_AUDIT_REPORT.md` (status table
  added, findings kept as the audit record).
- The two multi-VR documents were removed; their content merged into
  `MIGRATION_GUIDE.md` and `DEVICE_GROUP_SPLITTING.md`. `docs/` now holds one index
  and one owner per rule.
- In-code documentation corrected: the generated `README.md` file list, the CI
  workflow comment, `tests/test_golden_files.py`, `quick_start.sh`, and the module
  docstrings in `panorama_to_terraform.py`, `split_device_groups.py`,
  `container_coverage.py`, `entry_coverage.py`, `resource_mapping.py`,
  `tests/test_container_coverage.py`.
- Two claims in the code were overstated and are now marked as not implemented: the
  property-level scan (F4.4), and the report lines that name it. The report text is
  output, so it changes with the feature, not with this task.
- New gaps recorded in `backlog.md`: the overlapping BGP and OSPF read paths, the
  manual report sections that do not name their scope, BGP redistribution captured
  but not printed, and `lib_docs/` missing.
- Gate: `ruff check .` clean, `pytest` 566 passed, both golden sets byte-identical,
  `terraform validate` green on all four outputs, exit codes unchanged. No test
  expectation changed.
- Output that changed is text a document owns: the generated `README.md` file list,
  and `quick_start.sh`, which is a demonstration script. No generated `.tf` file
  changed.

