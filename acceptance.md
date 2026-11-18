# Acceptance — the open 2026-11-11 audit findings (Piece 10)

Criteria set 2026-11-18 for the six findings `backlog.md` recorded from the audit measured 2026-11-11. One
section per finding, each with the decision and the pin or measurement that holds it. The six are worked one at
a time, and each is measured before the next is started.

Owners: `docs/ARCHITECTURE.md` §1.1 for the layout rule and the response set; `tests/test_api_requests.py` for
the response-set pins; `.github/workflows/python-tests.yml` for the CI gate; `tests/conftest.py` for the skip
rule; the test modules named in item 5 for the pins that restate a table as a measured count; `docs/ARCHITECTURE.md`
§1.1 and `tests/test_layout.py` for the index rule.

Rules this piece works under, from `agent-status.md` §Rules to keep when writing documents:

- One owner document per rule; every other document links to it.
- No test counts in a document. A document names the test that pins a rule.
- A pin measures content or a name, never the wording of a document.
- A historical record is not kept in the markdown; the git history is the record.
- No pin is weakened. When a pin changes what it asserts, the reason is recorded here.

## Item 1 — the committed response inside the corpus

**Decision.** `tests/fixtures/` is the corpus: the files the pins read through the file producer. `tests/responses/`
is the response set: the bytes the pins read through the injected producer for the request that produced them.
`tests/fixtures/api_response.xml` has a `response` root, so it is a response, not a Panorama export, and it is not
corpus material. Its key-free identity for host `panorama.test` is
`panorama.test?category=configuration&type=export` =
`241cbc8980537850768efb4f106eaf6665bbc113a5ecd7c9fbd42449f200d34f.xml`, which the committed whole-config export
response already holds, and the response set holds one file per accepted shape, so the fixture cannot be added as a
fourth file. Its entries cannot be merged into that file either: the committed response already holds an address
entry named `web-server` under `shared/address`, so merging would give the address set two entries with the same
name in two containers, which breaks the pin that reads the address set as the one entry named `web-server`.

So the content stays in the corpus in the form the corpus pins read it: the file is renamed
`tests/fixtures/export_config.xml` and holds the same entries as a Panorama export, root `config`, no wrapper. The
response set's export response is written to hold the same config content, so the pins that compare the two
producers read the same content, one through each. The names the pins measure are unchanged
(`Edge`, `web-server`); the physical lines are re-measured on each file.

- AC-1.1: a pin that reads the corpus reads only files the read rule accepts. Held by
  `tests/test_build_kitchen_sink.py::test_the_read_set_is_the_set_the_corpus_pins_read_less_the_record`, read as
  the derivation from the rule (item 5). Measured 2026-11-18: 66 accepted, 65 read, 3 skipped, held in the pin's
  docstring as the measurement. Before the piece the corpus measured 68 accepted and 67 read; the three files with
  a `response` root left it (item 1 and item 2), so the count moved with the set the rule answers, which is what
  the derivation reading means.
- AC-1.2: no file in the corpus has a `response` root. Held as the content property in item 2, so the block that
  keeps `api_response.xml` in the corpus is removed.
- AC-1.3: a committed response is read through the injected producer for the request that produced it. Held by
  `tests/test_source_fetch.py::test_a_committed_response_is_read_through_the_injected_producer`, and the module's
  `_bytes()` reads `RESPONSES_DIR`, not `FIXTURES_DIR`.
- AC-1.4: a file-source pin reads a Panorama export. The pins change what they measure: they run the tool on
  `export_config.xml`, which is the corpus form of the same content, instead of on a response. Held by the pins in
  `tests/test_provenance.py` and `tests/test_source_fetch.py` that read `FETCH_FIXTURE`, including
  `test_api_run_writes_the_same_tf_bytes_as_the_file_run`, which keeps its strength because the response and its
  corpus twin hold the same config content.
- AC-1.5: the same content reaches both producers. Held by
  `tests/test_source_fetch.py::test_api_run_writes_the_same_tf_bytes_as_the_file_run` (same `.tf` bytes from either
  source), so the twin relation cannot drift.
- AC-1.6: the root index names every file in the response set. Held by `tests/test_layout.py`; `README.md` names
  each file it holds.

Re-measured lines, recorded in the pins as measurements: the export response carries the `config` element at line
10, the `device-group` entry `Edge` at line 12, and the address entry `web-server` at line 18; the corpus export
carries `config` at line 2 and `web-server` at line 8.

## Item 2 — the response-set rule as a property of each file

**Decision.** The rule is stated as a content property of each file, so the pin measures content and not a name
comparison between the two sets: a file in the response set has a `response` root; a file in the corpus is a
Panorama export, so its root is not `response`. Three corpus files have a `response root`, so all three are
responses: one is already the file that holds its shape (item 1), and the other two move, each named by the
key-free identity of the request the pins name for it.

| File | Request the pins name | Identity the file is moved under |
|---|---|---|
| `api_response.xml` → `export_config.xml` | the whole-config export | already held, so the corpus keeps the export form (item 1) |
| `scope_child.xml` | `panorama.test?action=get&path=device-group/entry/Production-DG&type=config` | `4d5f78d78ee8898b238ff3b4b6b2bda6658590c49a27d7173372bfa429f4904e.xml` |
| `scope_parent.xml` | `panorama.test?action=get&path=shared&type=config` | `18caa0bbc1b94e0377e658b82f67e90fe8a9a82658ee70e7646f3098ff72a074.xml` |

- AC-2.1: for every file in the response set, the root element is `response`. Held by
  `tests/test_api_requests.py::test_the_committed_responses_are_not_corpus_material`.
- AC-2.2: for every file in the corpus, the root element is not `response`, so a response that lives inside the
  corpus is a finding. Held by the same pin, read as a property of each file rather than as a comparison of the
  two name sets.
- AC-2.3: the response set is the files the pins read for the requests the pins name, each named by that request's
  key-free identity, and every accepted shape is represented by at least one file. Held by
  `tests/test_api_requests.py::test_one_committed_response_per_request_shape_names_the_request_identity_that_produced_it`,
  restated so the harness names the requests the pins read (five, measured 2026-11-18) and the shape set is read
  through `source_fetch.SHAPE_PARAMS`. The pins change what they assert: the old form held one file per shape,
  which cannot hold once the pins name two more requests; the strength is the same because each file is still named
  by the identity that produced it and each shape is still represented. The moved files state their request
  identity in the file, which is what the pin reads.
- AC-2.4: a committed response is read through the injected producer, so the pins that run the tool on the moved
  pair hand their bytes through an injected producer for the request that produced them. Held by the pins in
  `tests/test_source_fetch.py`, `tests/test_provenance.py`, `tests/test_shadow_coverage.py`,
  `tests/test_ownership.py`, and `tests/test_state_input.py` that read them.
- AC-2.5: a pin that measures the file-source rule reads a Panorama export, so the pins that read the pair through
  the file producer change what they measure. `tests/test_container_coverage.py::test_the_scan_reads_a_per_scope_root_as_the_place_the_path_names`
  hands the response bytes with the origin kind it measures (the pin measures the door's behaviour for one kind, not
  a corpus run); `tests/test_shadow_coverage.py::test_path_and_parent_apply_to_the_api_source_only` runs the tool on
  a corpus export. The reason is the rule: the corpus holds exports, and the pair are responses.
- AC-2.6: the corpus tables keyed by fixture name read the corpus, so the pair leave the round-trip table and the
  measurement is re-measured. Held by `tests/test_round_trip.py`, read as a derivation (item 5): the table is the
  facts the corpus produces, so a file that leaves the corpus leaves the table. Measured 2026-11-18: 19 facts,
  3 + 15 + 1 by category. The pair's facts are still measured through the response reads in
  `tests/test_shadow_coverage.py` and `tests/test_ownership.py`.
- AC-2.7: `docs/ARCHITECTURE.md` §1.1 states the property, and `README.md` names the files the response set holds.

## Item 3 — the provider-schema pins that never run in CI

**Decision.** The pins that read the provider schema run in the `terraform-gate` CI job, so the gate runs the whole
test set with the terraform binary present. The matrix job keeps running the whole suite on runners with no
terraform, where those pins skip for the missing binary. The gate job runs the whole suite rather than a list of
modules, because a list can drift: a module that starts reading the schema would not be in CI.

- AC-3.1: the `terraform-gate` job runs `pytest` with the terraform binary available, so the pins that read the
  schema fixture run there. Held by `.github/workflows/python-tests.yml`, which is the owner of the CI gate. No pin
  reads the workflow file, so this is recorded as the CI measurement, not as a pin.
- AC-3.2: the modules that read the schema through `tests/conftest.py` are named in `README.md` §Testing by the
  rule they read, and `docs/ARCHITECTURE.md` §1.1 names `tests/conftest.py` as the harness. Measured 2026-11-18:
  10 modules read the schema fixture; the document names the rule, not the count.
- AC-3.3: the skip rule says the pins skip only when the terraform binary is absent, so the matrix job is the job
  that skips and the gate job is the job that runs them. Held by item 4.

## Item 4 — the skip that hides a failure

**Decision.** The skip is only for a missing terraform binary. A `terraform init` failure, which is what a missing
provider cache or an unreachable registry answers, is a failure, not a skip. `tests/conftest.py` is the owner of the
skip rule for the schema fixture; `tests/test_terraform_validate.py` keeps the skip for a missing binary and reports
a failed init or validate as a failure.

- AC-4.1: `provider_schemas` skips when `shutil.which("terraform")` answers nothing, and asserts when `terraform
  init` returns non-zero. Held by `tests/conftest.py::provider_schemas`.
- AC-4.2: with the binary present, a network failure is a failure, so a network failure cannot read as a pass.
  Measured 2026-11-18 on this machine: `terraform init` against `PaloAltoNetworks/panos ~> 2.0.14` returns 0, so the
  full run passes with no skips.
- AC-4.3: the documents that state the skip say only the binary, so `README.md` §Testing, `docs/ARCHITECTURE.md`
  §4.6, and the module docstrings change to state that a provider-cache failure is a failure.

## Item 5 — pins that restate an owner table as a measured count

**Decision.** Each pin states the property: the tool's answer equals the value derived from the owner table's rows,
so a wrong table entry is a finding. The measured number stays in the pin's docstring as a dated measurement.

- AC-5.1 `tests/test_build_kitchen_sink.py`: the accepted set, the skipped set and the read set are derived from the
  read rule and the record, so the pin compares the tool's decision per file with the rule's decision per file in
  both directions. Measured 2026-11-18: 68 accepted, 67 read, 3 skipped. The comment count and the curated-name
  count become properties (the printed tree holds no comment; the record's curated names are the names no accepted
  fixture carries), and the numbers 17 and 13 stay as the measurement in the docstring.
- AC-5.2 `tests/test_filter_containers.py`: `CHOICE_ROWS` is derived from `resource_mapping.FILTER_SHAPE` (the rows
  that state `selects`), and the pin checks each choice against the provider schema. The route-map counts (73 levels,
  34 mirrored rows, 17 `string_list` rows, 14 choice rows) are counts of the table's own rows, so they have no
  derivation and stay as measurements in the docstring; the pin keeps the per-row properties.
- AC-5.3 `tests/test_resource_mapping.py`: the `disable_override` pin reads the matrix rows that name the
  property, and compares that set with the pinned provider schema in both directions, so the pin names no list of
  its own. The measurement (128 resources, 25 declaring the flag, 9 emitted among them) stays in the docstring.
- AC-5.4 `tests/test_property_coverage.py`: the unmeasured rows are derived from the container table — a matrix row
  is measured when a corpus entry reaches the container its row names — so `panos_device_group_parent` is the row the
  container table names no container for. The single-row fact stays as the measurement in the docstring.
- AC-5.5 `tests/test_data_file_gate.py`: the data-file count is derived from the `sanity_checks.DATA_FILES` rows
  present in the run's output, so the pin compares the gate's count with the derivation; the number 4 stays as the
  measurement in the docstring.

## Item 6 — the two `.github/` template files outside every index

**Decision.** The index rule is: every markdown document in the repository is named by the index for its directory,
and a directory that holds no index of its own is named by the root index. The two `.github/` template files stay in
the repository, because GitHub reads a contribution template from `.github/`, so `README.md` names them and
`tests/test_layout.py` reads the rule as a property of every markdown document in the tree. `tools/check_documents.py`
reads the two files with the rest of the markdown, and `backlog.md` closes the finding.

- AC-6.1: for every markdown document in the tree, its name is in the index for its directory, or in the root index
  when its directory holds no index of its own. Held by
  `tests/test_layout.py::test_the_indexes_name_every_document_under_them`, which reads names only.
- AC-6.2: the root index names the two template files. Held by the same pin, and by `README.md` stating them as the
  contribution forms.
- AC-6.3: the response-set half of the pin reads names only, so the count leaves `tests/test_layout.py` and the set
  is held by `tests/test_api_requests.py`, which states which files the pins read. Measured 2026-11-18: 5 files.

## Gate

Run in order, with no parallel runner: `ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`. Record the pin count before and after, the module count, and the time. The
baseline measured 2026-11-18 is 1,688 pins in 52 modules in 305.56 s, with no skips, `ruff check .` clean,
`ruff format --check .` clean, and `check_documents.py` reporting no finding. No pin is removed from the full run.

Measured after the piece, 2026-11-18, in one run in the order above: `ruff check .` clean (0.015 s),
`ruff format --check .` clean on the 100 Python files (0.011 s), 1,686 pins in 52 modules in 313.68 s with no
skips (305.56 s to 313.68 s across three runs of the same set), and `python3 tools/check_documents.py` reports no
finding (11.09 s). The count fell by 2 in `tests/test_sanity_gate.py` (101 to 99), and no pin was removed or
weakened: that pin is the corpus run, parametrized through `tests/conftest.py::corpus_fixtures`, so its case set is
the corpus the read rule answers. The three response-rooted files left the corpus (item 1 and item 2), so two cases
left the pin with them. Their facts are still read through the injected producer in `tests/test_shadow_coverage.py`
and `tests/test_ownership.py`.

Finished: mark Piece 10 complete in `to-do.md`, close or narrow the six findings in `backlog.md`, update
`agent-status.md` §Current position, and commit. Only the files this piece changed are committed; `AGENTS.md` is not
staged, committed, reverted or modified, because it holds an uncommitted user edit.
