# Documentation Index

Each rule in this project lives in one document. The other documents link to
that document instead of restating the rule.

| Document | What it is for |
|---|---|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | Run each script, and read each output file |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Why the output looks the way it does. Each rule names the test that pins it |
| [RESOURCE_MAPPING.md](RESOURCE_MAPPING.md) | The provider v2 decision for each type, with the reason |
| [COVERAGE_MATRIX.md](COVERAGE_MATRIX.md) | Which XML element feeds which resource, and the test that proves it |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | Plan and run a migration, for one device or several virtual routers |
| [CODEBASE_ASSEMBLY.md](CODEBASE_ASSEMBLY.md) | What a full codebase needs and the rules behind the files the run writes. Design record for Epic 6; §3 to §11 and §14 landed |
| [API_CONVERSION_PATH.md](API_CONVERSION_PATH.md) | The second conversion path, which reads only API responses. Design record for Epic 8, closed |
| [API_DOCUMENTATION_AND_MOCKS.md](API_DOCUMENTATION_AND_MOCKS.md) | What the PAN-OS API documentation can give the committed response set, what it cannot, and the mocking options. Planning record, not a design decision |
| [TEMPLATE_STACK_DEPLOYMENT.md](TEMPLATE_STACK_DEPLOYMENT.md) | The template and stack unit: which membership name enters the edge set, the scope a template or a stack entry is declared inside, and what the tool can state for a template entry the export declares and no device names. Design record for Epic 10, landed |
| [MULTI_RUN_CODEBASE.md](MULTI_RUN_CODEBASE.md) | The codebase several runs write into: the run's read set and write set, the four records as codebase state, the cross-run ownership, edge and order facts, the gate for a partial run, and the write boundary. Design record for Epic 11, open |
| [DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md) | Split one export into one file per device group |
| [INPUT_SHAPES.md](INPUT_SHAPES.md) | What bytes an input can be, which entry point accepts each shape, and what the run states when a shape is refused or read. Design record for Epic 13, landed |
| [IMPORT_BINDING.md](IMPORT_BINDING.md) | Which block a run binds to the object the live config already has, how that decision is recorded as data, and which facts an id needs. Design record for Epic 14, planning |
| [ADVANCED-ROUTING-ENGINE-SUPPORT.md](ADVANCED-ROUTING-ENGINE-SUPPORT.md) | Logical routers, and the routing config the converter does not read |
| [VPN_ROUTING_CONFIG_EXAMPLES.md](VPN_ROUTING_CONFIG_EXAMPLES.md) | The XML shapes the parser reads for VPN and routing |
| [WRITING_RULES.md](WRITING_RULES.md) | The rules a document follows when it is written. Owner document for the writing rules |
| [LICENSING.md](LICENSING.md) | Who holds the copyright for each part, and what each grant covers |

## Who owns each rule

| Rule | Owner |
|---|---|
| Identity, the five scope facts, parsed object shape | `ARCHITECTURE.md` §2 |
| Safe input read, container table, entry marks | `ARCHITECTURE.md` §3 |
| Per-scope source shape, the envelope rule, the scope path shape | `ARCHITECTURE.md` §3.1, and `container_coverage.py` |
| Cross-source shadow scan (the fact, the line shape, the heading) | `ARCHITECTURE.md` §3.2, and `shadow_coverage.py` |
| The destination one entry takes (the one place that answers it, and the order) | `ARCHITECTURE.md` §3.2, and `entry_coverage.py` (`EntryLedger.destination`) |
| The `number` reading rule (the three answers, and the fact it states for text it cannot read) | `ARCHITECTURE.md` §4.9 rule 11, and `PanoramaParser._protocol_field`; the entry line that prints the fact is `ARCHITECTURE.md` §3.2 rule 7, and `entry_coverage.py` |
| Emit order, location, reference resolution, policy chains, reports, gate | `ARCHITECTURE.md` §4 |
| The round-trip cross-check (the block set against the entry set, per unit and row) | `ARCHITECTURE.md` §4.6, and `sanity_checks.check_round_trip`, which reads the scan scope through `entry_coverage.matrix_row_for` |
| The request-set gate rule (the join's rows against the scope index, per unit and per entry) | `API_CONVERSION_PATH.md` §3, and `sanity_checks.check_request_set`, which reads the join through `api_requests.unit_findings` and the unit through `unit_manifest` |
| The protocol object shape, the one-of mapping, and what prints | `ARCHITECTURE.md` §4.9, and `resource_mapping.PROTOCOL_SHAPE` |
| The filter container shape, the row scope, and the path-keyed input spellings | `ARCHITECTURE.md` §4.10, and `resource_mapping.FILTER_SHAPE` |
| The certificate container shape, the choice by presence, and the `sensitive` print | `ARCHITECTURE.md` §4.11, and `resource_mapping.CERTIFICATE_SHAPE` |
| Local resource naming | `ARCHITECTURE.md` §5 |
| Determinism | `ARCHITECTURE.md` §6 |
| Provider type per object kind | `RESOURCE_MAPPING.md`, and `resource_mapping.py` |
| Provider element per emitted type | `COVERAGE_MATRIX.md`, and `resource_mapping.COVERAGE_MATRIX` |
| Migration workflow | `MIGRATION_GUIDE.md` |
| Device group to template join | `DEVICE_GROUP_SPLITTING.md` |
| Input shapes, the archive producer rule, the shape table, and the splitter diagnostic | `INPUT_SHAPES.md`; the shape table is code in `src/input_shapes.py`, which the `ARCHITECTURE.md` §1 table names, and §3 states the rules around it without restating a row |
| Which export a run needs, and how to get one | `USAGE_GUIDE.md` §Which export a run needs is the owner; `README.md`, `DEVICE_GROUP_SPLITTING.md` and the troubleshooting rows link to it and state no shape wording |
| Codebase unit, ownership, order between units, import blocks, scope objects, site data, commit action, the write path, the rule data pair | `CODEBASE_ASSEMBLY.md` §3 to §11 and §14, and the modules `unit_manifest.py`, `ownership.py`, `reference_edges.py`, `import_blocks.py`, `site_data.py`, `commit_actions.py`, `write_path.py`, `rule_data.py` |
| Which block a run binds to the live object, the mode as data, the whole-block fact, and the completeness half for a bound unit | `IMPORT_BINDING.md` §1 to §4; `import_blocks.py` for the block shape, the row shape, and the two mode values and the level as data (`MODE_VALUES`, `MODE_LEVEL`), `unit_manifest.py` for the unit row and the mode field decision 2 names, `entry_coverage.py` for the property scan and the report line, and `sanity_checks.check_import_blocks` for the agreement rule. Each pending owner is named by the decision that takes it, and the mode field has the owner decision 2 names |
| The run's read set and write set, the records as codebase state, the cross-run ownership, edge and order facts, the gate for a partial run, and the write boundary | `MULTI_RUN_CODEBASE.md` §1 to §7, and the modules `unit_manifest.py`, `ownership.py`, `reference_edges.py`, `sanity_checks.py`, `write_path.py`, and `codebase_state.py` for the merge rule |
| Which membership name enters the edge set, and the plan order that name produces | `TEMPLATE_STACK_DEPLOYMENT.md` §2, `api_requests.LIST_JOIN` for the join between a membership list and the table its owner returns, and `reference_edges.py` for the pair and the order |
| The scope a template entry or a stack entry is declared inside, and the manifest field that states it | `TEMPLATE_STACK_DEPLOYMENT.md` §3, `resource_mapping.SCOPE_PLACEMENT` for the placement key, `resource_mapping.LOCATION_SCHEMA` for the sub-block that key can name, and `unit_manifest.FACT_KEYS` for the facts the row reads |
| What the tool can state for a template entry the export declares and no device names, and which facts stay a live fact | `TEMPLATE_STACK_DEPLOYMENT.md` §4, `unit_manifest.facts_of` for the empty `vsys_device` fact, `site_data.py` for the site row and its printed form, `reference_edges.py` for the edge set and the order, `commit_actions.py` for the action blocks, and the scope block emitter |
| The credential rule, stated once | `CODEBASE_ASSEMBLY.md` §11 is the owner; `ARCHITECTURE.md` §3 links to it and keeps only what the fetch layer enforces, and `README.md`, `docs/USAGE_GUIDE.md` and `docs/MIGRATION_GUIDE.md` link to it |
| Provenance record, the cache reference, and the prune action it gates | `ARCHITECTURE.md` §3.3, and `provenance.py`; the two file sets the record belongs to are `CODEBASE_ASSEMBLY.md` §14; the path 2 case, one record per request the run read, is `API_CONVERSION_PATH.md` §2.5 and `tests/test_provenance.py` |
| Repository layout: the directories, the import rule, the flat test rule, and the four test sets | `ARCHITECTURE.md` §1.1, `AGENTS.md` (the tracking set), and the four readme indexes (`README.md`, this file, `../examples/README.md`, `../tools/README.md`) |
| The writing rules: what a document may state and what a pin can hold | `WRITING_RULES.md` is the owner; `agent-status.md` and the other documents link to it, and `AGENTS.md` owns the rule that completed detail is removed from the tracking markdown |
| The fixture assembler: its read rule, its merge rule, and the rule that the committed fixture is the record it does not write | `ARCHITECTURE.md` §1.1, `../tools/README.md`, and `tests/test_build_kitchen_sink.py` |
| The second path: the committed response set, where it lives, and the rule that no test calls a network | `API_CONVERSION_PATH.md` §5, `ARCHITECTURE.md` §1.1 for the set, and `tests/test_api_requests.py`, `tests/test_source_fetch.py`, `tests/test_build_kitchen_sink.py`; the byte agreement between the two paths for content that holds no fact §4 names is `API_CONVERSION_PATH.md` §5 and `tests/test_api_path.py` |
| The second path: the accepted request shapes, the scope index, and the response-to-request join | `API_CONVERSION_PATH.md` §2, `source_fetch.py` for the shapes, `container_coverage.SCOPE_PATH_ROOTS` for the one scope path definition, and `api_requests.py` for the index and the join |
| The second path: the run over many sources, the section-to-response join, the unit join, and the row source field | `API_CONVERSION_PATH.md` §2.4, §2.5 and §3, `api_requests.py` for the joins, `unit_manifest.units` for the unit set, `ownership.SOURCE_FIELD` for the field name the join reads, and `tests/test_api_path.py`, `tests/test_unit_manifest.py`, `tests/test_ownership.py` |
| The second path: what it shares with the first path, and what it does not close | `API_CONVERSION_PATH.md` §1 and §7 |
| The second path: the run order, the cross-response join, and the entry point that decides both | `API_CONVERSION_PATH.md` §6, `api_to_terraform.py` for the run order, `panorama_to_terraform.py` (`join_value`) for the join rule, and `tests/test_api_path.py` |
| The license rule: the fork source, the two holders, the measured split, the notice set, and the scope of each grant | `LICENSING.md`. The `git blame` author count is the authority for the split, and the notices in `src/` agree with it |

The machine-readable tables are code, not documents:
[`../src/resource_mapping.py`](../src/resource_mapping.py),
[`../src/container_coverage.py`](../src/container_coverage.py), the entry marks in
[`../src/entry_coverage.py`](../src/entry_coverage.py), and the input shape table in
[`../src/input_shapes.py`](../src/input_shapes.py). A document explains a table and
never restates it row by row.
