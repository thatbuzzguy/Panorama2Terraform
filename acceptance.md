# Piece 11B.1 acceptance record — the merge rule in `codebase_state.py`

Criteria, written before the code, and the record of the piece as it landed. The piece is offline work on the
committed fixtures; no pin calls a network. Piece 11A.3 is reviewed at `7bfb55b` and is not reopened; Phase 11A is
complete. The tree was clean at `0250f04` when this piece began, and no committed golden changed.

## Criteria

1. **One join key per record, stated as data in `codebase_state.py`**, and the fact each key joins on is named.
   The key for the ownership record is read through `state_coverage.ownership_key` (`docs/ARCHITECTURE.md` §3.2),
   the one identity key rule; the keys for the other three records are the field the record states. No module
   states a second key.
2. **The merge is read through each record module's `parse_rows`.** The module defines no row shape, no reader, no
   second shape rule, and it takes rows that came from `parse_rows`, so the gate's data rule
   (`sanity_checks.DATA_FILES`, `docs/ARCHITECTURE.md` §3.2) stays the only data rule over the four records.
3. **The merge rule, stated once**: the run's rows replace the codebase's rows for the rows the run built, and the
   rows for the units the run did not build stay as the record states them. The merged set is keyed by row
   identity, not by run.
4. **The merge holds no run field, no timestamp and no order-of-writes fact**: it adds no field to a row, so a
   merged row is the record's own shape, and the order of the merged set is read through each record module's own
   order rule, not through which side a row came from.
5. **A record that has no existing file writes today's bytes**, so no committed golden changes. The order the
   merged set is written in is the order the record module's own rule states for its rows; where a record module
   states no order rule for a row it reads back, the condition is recorded in `backlog.md` and no rule is invented.
6. **`codebase_state.py` is a data module**: it writes no file, states no record-directory path rule, names no
   console line, states no environment name, defines no second naming rule and no writer, and imports only the
   standard library and the house modules, so the `src/` scans (the writer scan, the environment-name scan, the
   console-line scan and the second-naming-rule scan) read it clean. It is named in the `docs/ARCHITECTURE.md` §1
   module table in the same commit as the module.
7. **One pin per stated fact**, in the module that owns the fact, with a new test module only where the fact spans
   the four records (`tests/test_codebase_state.py`, named in `docs/MULTI_RUN_CODEBASE.md` §8 and in the root
   `README.md` index in the same commit). Pins are grounded on a committed fixture or a committed response set,
   never on a hand-built row, and no test module imports another test module.
8. **Out of scope**: the unit-set comparison (11B.2), ownership, edges and the plan order over the merged set
   (11B.3), and the gate for a partial run (11B.4). If a record's rows cannot be merged by one join key read
   through its own `parse_rows`, the condition goes in `backlog.md` and no rule is invented for it.
9. **The gate**, single-threaded: `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py` and
   `python3 -m pytest`, with the new counts measured.
10. **The documents**: `docs/MULTI_RUN_CODEBASE.md` §3 names the pins that hold, `docs/ARCHITECTURE.md` §1 names the
    module, `README.md` names the new test module, and `to-do.md`, `agent-status.md` and `acceptance.md` state the
    current state. Plain literal wording, no metaphor, no emoji, no test count in a document, and every test a
    document names exists.

## The measurement, before the code

Row identity, read through each record module's `parse_rows` on a run of the committed corpus. The run measured is
the kitchen-sink fixture (11 units), and the order check and the key-uniqueness check are read over every fixture
the read rule accepts.

- `CODEBASE_MANIFEST.json`: 11 rows. Identity is the five scope facts (`unit_manifest.FACT_KEYS`), and `directory`
  is the §5 shape of them (`naming.sanitize` plus the 8-hex `identity_digest`), so the join key is unique per row
  for every accepted fixture. `parse_rows` states the rows in the fact order, which is not the join-key order on
  26 of the accepted fixtures, so the merge reads the order through `unit_manifest.FACT_KEYS` and not through the
  key.
- `OWNERSHIP.json`: 61 rows. `parse_rows` states the rows in `ownership.row_key` order, which is
  `state_coverage.ownership_key` plus `source`. The join key the design names, (`type`, `entry`) with the facts, is
  unique for every row of every accepted fixture, so `source` is not needed to keep two rows apart on the committed
  material, and the key order is the order the file states. Two sources that state one entry are two rows today, so
  a merged set can hold only one row per key: the condition is recorded in `backlog.md`.
- `REFERENCE_EDGES.json`: 9 rows. Identity is the four fields in field order — the referrer's directory, the
  target's directory, the matrix row and the entry name — which is the pair of entry identities the join states. The
  key is unique per row for every accepted fixture and the file order is the key order.
- `SITE_DATA.json`: 3 rows. Identity is `directory`, the join to the manifest row, and it is unique per row for
  every accepted fixture. `parse_rows` states no order rule: it reads the rows in the order the file states them,
  which is the identity order the writer built through `unit_manifest.units`. A site row names no facts, so the
  identity order cannot be read from the row alone, and the order of a merged site file needs a rule the record
  module does not state; the condition is recorded in `backlog.md`. On every accepted fixture the file order is
  already the join-key order, so reading a merged site file in the key order writes today's bytes.
- What a second run into the same codebase directory does today: it writes each record from its own rows, so the
  file is replaced. Kitchen-sink run, then a run of `address_objects.xml` into the same directory: the manifest
  goes from 11 rows to 1, `OWNERSHIP.json` from 61 to 5, and the two records the second run names no rows for keep
  the file the first run wrote, because a file is written only when it has content. The 10 manifest rows and the
  56 ownership rows for units the second run did not build are gone.
- The committed response set (5 files) holds one shadow pair, `device-group/entry/Production-DG` and `shared`, that
  states the same entry name `Web-Server-1` in two scopes. The two rows have two different keys, so the join key
  separates them; the set holds no pair of responses that states one key twice, so the collapse condition cannot be
  pinned on it. A full offline response-set run is not possible (`api_producer` answers None for requests with no
  committed response, and `--offline` refuses a missing cache entry), so pins read the response set through the
  injected producer.

## The pins, as landed

Ten pins, one per stated fact, all grounded on committed material: the codebase's rows are the rows a run wrote for
`tests/fixtures/kitchen_sink.xml` and the run's rows are the rows a run wrote for
`tests/fixtures/address_objects.xml`, each read back through its own module's `parse_rows`. No pin builds a row by
hand, and no test module imports another test module. The measurement the pins read is the measurement above, so the
merge counts in the pins are the measured ones: the manifest 11 against 1 gives 11, `OWNERSHIP.json` 61 against 5
gives 62, and the two records the second run names no rows for are the codebase's own rows.

`tests/test_codebase_state.py`:

- `test_the_join_key_for_the_manifest_record_is_the_unit_identity_read_as_directory` — criterion 1, the manifest key.
- `test_the_join_key_for_the_ownership_record_is_the_entry_identity_read_through_state_coverage` — criterion 1, the
  key read through its owner, and the fact that `source` separates no two rows on the committed material.
- `test_the_join_key_for_the_edge_record_is_the_pair_of_entry_identities` — criterion 1, the edge key, with each half
  of the pair naming a unit the manifest row names.
- `test_the_join_key_for_the_site_record_is_the_unit_identity_read_as_directory` — criterion 1, the site key, read
  against the manifest row.
- `test_the_run_rows_replace_the_codebase_rows_for_the_rows_the_run_built` — criterion 3, the merge rule.
- `test_a_record_with_no_existing_file_writes_the_bytes_a_single_run_writes_today` — criterion 5, the byte rule
  between two runs, read on the four cases the golden set names.
- `test_the_merge_adds_no_field_so_a_merged_row_reads_back_as_itself` — criterion 4, no run field, and the data rule's
  reader reading the merged rows back as itself.
- `test_the_order_of_a_merged_set_is_the_order_each_record_states_not_the_order_of_writes` — criterion 4, the order
  read through each record module's own order rule, and criterion 5's determinism half: reading the two sets in the
  other order answers the same rows in the same order.
- `test_the_module_states_no_rule_an_owner_states_and_writes_no_file` — criterion 6, the module shape.

`tests/test_data_file_gate.py`:

- `test_the_data_rule_reads_a_merged_record_through_the_same_reader` — criterion 2, the table stays the only data rule
  and its reader reads a record that holds rows from two runs the same way; the merged codebase reports no finding.

## Gate, as measured

Read single-threaded, at the commit that holds the piece:

- `ruff check .`: clean, `py310`.
- `ruff format --check .`: clean on the 108 files it reads.
- `python3 tools/check_documents.py`: no finding, every document agrees with measurement.
- `python3 -m pytest`: 1,767 passed and the same 4 `tflint` skips — 1,771 pins in 54 test modules, in 246.53 s. The
  new module holds 9 pins and `tests/test_data_file_gate.py` holds 28. The tree holds 81 Python files and `src/` holds
  24 modules.

No committed golden changed: the golden set pins the `.tf` bytes of a single run, and the byte rule pin reads the
record bytes of the same four runs through each module's `render`.

## The documents, as landed

`docs/ARCHITECTURE.md` §1 names `codebase_state.py`, `docs/MULTI_RUN_CODEBASE.md` §3 names the pins that hold for
rules 1, 2, 3, 4 and 5, `docs/MULTI_RUN_CODEBASE.md` §8 names the test module that holds them, `README.md` §Testing
names `tests/test_codebase_state.py` and the data rule's new pin, and `docs/LICENSING.md` states the module count the
live tree reads. The two conditions the piece cannot state as rules — the site record's order for a row it reads
back, and the ownership key holding one row for an entry two sources state — are in `backlog.md`. `to-do.md` holds
11B.2, 11B.3 and 11B.4; the run integration into `generate_run` is Phase 11C.
