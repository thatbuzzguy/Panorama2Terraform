# Acceptance criteria — F8.6, one record per request (Epic 8, Phase 8B)

Scope: the provenance record rule for a path 2 run — one record per request the run read — the pins in
`tests/test_provenance.py` and the pin `tests/test_write_path.py::test_the_record_directory_is_the_output_
directory_for_the_prune`, the rule statement in `src/provenance.py` (the module that owns the record), and the
design record `docs/API_CONVERSION_PATH.md` §2.5 with `docs/ARCHITECTURE.md` §3.3 as the owner document for the
record. No new module, no new record field, no change to the field order, no entry point (F8.9), no gate rule
(F8.8), no unit join (F8.7), no path rule for a record directory, and no membership rule. Path 1 is unchanged.

## 1. One record per request the path 2 run read

1.1 One response is one source (`docs/API_CONVERSION_PATH.md` §2.4), so the record file holds one record per
request the run read. A run that read N requests writes N records, in the order the run read them. For a path 2
run that order is the order the index names its entries, because the run reads the membership responses first
and then the entries in path order. `provenance.py` states the read order for the sources it owns (the main
source, then the declared parent, then the state source) and states no read rule of its own for a path 2 run,
because the run order is the entry point (F8.9).

1.2 The eight fields, the fixed order, the `-` value for a field that does not apply to the source kind, and the
one blank line between records are unchanged (`docs/ARCHITECTURE.md` §3.3). `parse_records` reads a path 2
record file back as itself, so the record stays data, and a second run that read the same requests writes the
same record bytes.

1.3 For each request the index names, `scope` names the path that request declared, which is the fact the door
records, and `request` names the key-free identity of that request, which is the shape the cache entry is hashed
from. `cache_entry` names the entry that identity names, `name` is the report value for the response, and the two
byte facts come from the door.

1.4 A device fact request declares no path, so its record states the door's default for `scope`, because a
command names no scope. The index makes no device fact request, so this case stays a finding in `backlog.md`.

1.5 The record names no credential: every request the run read is named by its key-free identity.

## 2. The prune action reads the record file the same run wrote

2.1 The record directory is the output directory: `SOURCE.txt` is a codebase root-set file, named through
`write_path.root_path`, so the action reads the record file at the codebase root. There is no record directory,
so `write_path.py` states no third builder and the module that owns the record states no path rule of its own.

2.2 The reference is the `cache_entry` field of a parsed record, so a run that read N requests protects the N
entries its own record names, and an entry no record references is pruned. The action reads the record file back
through `parse_records` and decides through `prunable_entries`; it builds no path.

## 3. No test calls a network

3.1 Every path 2 response in these pins is handed by an injected producer through `source_fetch.fetch`, as
`tests/test_source_fetch.py` and `tests/test_api_requests.py` do. The `device-group` read is the committed
response set (`tests/responses/`), read through the injected producer, so the record names the same bytes the
fixture holds.

3.2 The record the pins write goes through `write_path`, the single writer, and the path is named through the
builder for the set the record belongs to.

## 4. The pins

4.1 `tests/test_provenance.py` (the record group, plus the new path 2 group):

1. `test_the_record_file_holds_one_record_per_source_read` — grows to the path 2 case: the F5.4 pair, then a
   run that read N requests and wrote N records in the order it read them, one record per request.
2. `test_the_path_2_record_names_the_request_that_made_each_response` — AC-1.3, AC-1.5, AC-3.1.
3. `test_a_path_2_record_file_reads_back_with_no_new_field` — AC-1.2, and the byte rule between two runs.
4. `test_the_prune_protects_every_entry_a_path_2_run_read` — AC-2.2.

4.2 `tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune` grows to the
path 2 case: the record file the run wrote is the codebase root set, so the action reads it at the root and the N
records protect the N entries the run read, and the record module states no path rule (AC-2.1).

4.3 The existing pins that read the record unchanged: the field names, the round trip, the refusal of a line that
is not a field, the key rule, the report label, the reference rule, the gate counts, and the exit codes.

## 5. The checks

5.1 `ruff check .` is clean.

5.2 `python3 -m pytest` passes with no skip: the baseline 1620 pins, plus the pins above. No existing pin
regresses.

5.3 The commit is one ASD-STE100 message. When the rule lands, `docs/API_CONVERSION_PATH.md` §2.5 states it in
the present tense with the pins named, `docs/ARCHITECTURE.md` §3.3 states the path 2 case for the record,
`README.md` names the path 2 case in the testing list and in the record file description, `docs/README.md` names
the record module in the second-path owner row, the completed piece leaves `to-do.md`, the device fact case stays
a finding in `backlog.md`, and `agent-status.md` names the next piece (F8.7, the unit join).
