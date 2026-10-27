# Acceptance Criteria — F5.3 Provenance Record (current task)

Scope: one record per completed run, written to `SOURCE.txt` in the output directory.
The record names the bytes the run read, so a reader can reopen them. The record is a
run output, not a report body, so the report byte rule still holds. The record is data,
so the cache reference it carries can be read by a tool.

The feature also carries the report label change from `Input file:` to `Source:`, which
F5.1 left as it was. The report bodies keep the F4.2 rule 6: they name the source name,
never the path. The path is in the record, because a record is the file a reader reopens.

Out of scope for this task:

- The prune *action*. This feature states the pruning rule and the data the rule reads;
  no command runs it. Recorded in `backlog.md`.
- The cross-source shadow report (F5.4) and the state source (F5.6). Both need the scope
  field this feature adds.
- `split_device_groups.py`. It writes XML and has no run record.
- The gate checks. The gate reads `.tf` files; the record is not a `.tf` file, so the
  gate table is unchanged and the exit codes are unchanged.

Decisions taken before the code (the to-do pieces that opened this feature):

1. **What the record states.** Eight fields, in this order: the source kind, the source
   name, the path, the scope the source holds, the request identity, the cache entry, the
   byte count, and the SHA-256 hex of the bytes the door parsed. A field that does not
   apply to the source kind is written as `-`, so a tool reads one shape, not two.
2. **The record is data.** One `field: value` line per field, fixed order, no prose, no
   timestamp. A timestamp would make two runs on the same bytes differ, and the project
   rule is that two runs on the same input produce identical bytes.
3. **The byte facts come from the door.** The record names the bytes the door parsed, so
   the size and the hash are recorded by `xml_input.parse_bytes` on the bytes it checked,
   not read back from a file that may have changed since.
4. **The goldens cover `.tf` files only.** `tests/test_golden_files.py` says so, so the
   label change regenerates no golden. The tests that pin the label lines are migrated,
   and the goldens must still be byte-identical.
5. **The cache reference is data, not a printed line.** The `cache_entry` field is what
   the pruning rule reads, so the rule can be stated as a function over parsed records.

## AC-1 — The record states the facts a reader needs

1. One record per completed conversion run, in the output directory, as `SOURCE.txt`.
2. Fields: `kind` (`file`, or `api`; F5.6 adds `state`), `name` (the report value, no
   directory), `path` (the file a reader can reopen, as the run received it), `scope`
   (`whole-config` today, the declared scope for a per-scope source), `request` (the key-free
   request identity), `cache_entry`, `size`, `sha256`.
3. The field names are the printed keys, so `parse_record` reads a written record back as the
   same record. The byte count field is `size`, because `bytes` is a builtin.
4. A field that does not apply to the source kind is `-`. A file run writes `-` for the
   two api fields; an api run writes both.
5. `size` and `sha256` describe the bytes the door parsed. For an api run they equal the
   cache entry bytes; for a file run they equal the input file bytes.
5. The record names no credential. The key rule (F5.2 AC-5.4) holds for the record: the
   `request` field is the identity, and the identity has no `key=`.

## AC-2 — The record is data and is written outside the report bodies

1. `provenance.py` writes one `field: value` line per field, in the fixed order, and no
   other line. `parse_record` reads the written text back as the same fields.
2. The report bodies do not change their rule: `CONVERSION_REPORT.txt` and the container
   section name the source name only, never the path. A run on a fixture writes no path in
   a report body.
3. `render(record)` round-trips through `parse_record(render(record))`. The cache
   reference survives the round trip, which is what makes the pruning rule possible.

## AC-3 — The report label change

1. The two report writers print `Source:` instead of `Input file:`: the per-entry report
   header (`entry_coverage.py`) and the container coverage section
   (`container_coverage.py`). One label, not two.
2. Both sources print the same label, and both print the source name as the value, so a
   file run and an api run differ only in the value.
3. The golden sets are byte-identical after the change. No golden is regenerated, because
   the goldens cover `.tf` files only; the tests that pinned `Input file:` are migrated to
   `Source:`.

## AC-4 — The pruning rule reads the reference as data

1. A cache entry is not prunable while a written record references it. The reference is
   the `cache_entry` field of a parsed record.
2. An entry that no parsed record references is prunable. A record for a source with no
   cache entry references nothing, so it protects no entry: a report line that shows the
   entry name is not a reference.
3. The rule is a function over parsed records, so a prune action built later cannot read a
   printed line instead. No command runs the prune in this feature.

## AC-5 — Determinism and the gate

1. Two runs with the same arguments on the same bytes write the same `SOURCE.txt` bytes: no
   timestamp, no run count, and no path other than the path the run received. The
   cache-derived name in `cache_entry` repeats across cache directories, because it comes from
   the request identity, so a determinism test can compare the records and find the path as
   the only difference.
2. A run that refuses the input writes no record, like every other input refusal.
3. Exit codes are unchanged: an input refusal is 1, an argument error is 2, and the F4.1
   gate still decides the conversion exit code. A WARN still does not fail the run.
4. `ruff check .` clean, `pytest` green, both golden sets byte-identical.

## Documents to update

`docs/ARCHITECTURE.md` §3 (the provenance record as a new §3.3), §4.5 (the output file
set), §6 (determinism), `docs/USAGE_GUIDE.md` (the output file list, and the record),
`README.md` (the reports list), `docs/README.md` (the rule owner table), `backlog.md` (the
prune action, and the record field F5.4 needs), `PLAN.md` (F5.3 complete), `to-do.md`,
`agent-status.md`.
