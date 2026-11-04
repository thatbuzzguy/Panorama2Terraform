# Decision — the record directory, and the prune action — acceptance criteria

This slice closes the open backlog item: the pruning rule is stated in `provenance.py` but no action runs
it. The action needs the record directory decided first, because a record is written per output directory
and a run must know which record file the prune reads. This slice decides the directory, then builds the
action that reads that record file and removes the entries no written record references.

## Facts

- The record is `SOURCE.txt`, written on every completed run. `docs/CODEBASE_ASSEMBLY.md` §14 names it in
  the codebase root set, and `tests/test_write_path.py` pins that every file the run wrote names exactly
  one of the two sets, so a record directory of its own would be a third set and would need a third path
  builder. `write_path.py` states two builders, `unit_path` and `root_path`, and no module builds a path
  for a file it does not own.
- A record is data. `parse_records` reads a record file, so the reference a prune acts on is the
  `cache_entry` field of a parsed record, never a printed line. A record line that is not a declared
  field, or a field the record must state, is refused through `ValueError`.
- `provenance.prunable_entries(cache_dir, records)` is the decision: it names the entries no record
  references. A record for a source with no cache entry (a file source, a state source) references
  nothing, so it prunes nothing.
- The cache directory is `--cache-dir` (default `panorama_cache`), and a cache entry name is the request
  identity without the key. The cache holds bytes, so it is written by the fetch layer, not by the write
  path. The single-writer scan forbids a module writing a file; it does not forbid removing one.
- The exit codes are: an argument rule violation is 2; an input or record refusal is 1; the gate FAIL is
  1; a WARN does not change the code. An opt-in action that writes no output cannot change what the gate
  counts, so it cannot change the code it decides.
- The project's opt-in precedent is `--data-blocks` (F5.5) and `--import-blocks` (F6.4): a flag that
  gates a step, off by default, so a run that declares nothing writes the same bytes. No flag names the
  output layout (`tests/test_write_path.py`).

## Decision

**The record directory is the output directory itself.** `SOURCE.txt` stays the record file, and it stays
in the codebase root set, so `write_path.root_path` names it. The three candidates and why two are
rejected:

1. The output directory itself — chosen. The record describes the whole run, which is what §14 says a
   root-set file does, and the run already knows its own output directory. No new set, no new builder,
   no new file shape.
2. A dedicated record directory named for the output directory — rejected. It is a third file set, so the
   pin that every file names exactly one set fails, and `write_path.py` would need a third builder, which
   its rule 2 forbids.
3. A records directory beside the cache — rejected. The cache holds bytes the door parsed and is not a
   set the gate reads; a record set placed there would be read by no rule, and it would split one run's
   output across two roots. The record must be read by the run that wrote it, so it stays with the run's
   output.

Consequence for the prune: the run reads the record file it wrote in its own output directory, so there is
no guesswork about which records the action reads. One record file per run, and a two-source run holds two
records in it, so the action reads the file through `parse_records`, not one record.

**The prune is an opt-in CLI option that gates a run step**: `--prune-cache`, off by default. It is not a
separate command, because the reference it acts on is the record the same run wrote. Argument rule: it
applies to `--source api` only, because a file run reads no cache and its record references nothing; for
`--source file` it is an argument error (exit 2), following the `--offline` and `--insecure` rule. The
step runs after the record is written, because the written record is the reference, and after the gate, so
the exit code the gate decides does not move.

**Exit codes.** A prune that removes nothing changes nothing. A record file the action cannot read is a
refusal, so it exits 1, and the message names the record file, not the input file. A cache directory that
holds nothing is not a refusal: there is nothing to prune. A run that does not declare the action is
unchanged.

## Criteria

1. `provenance.py` states the record directory: `SOURCE.txt` is a codebase root-set file named through
   `write_path.root_path`, and the module owns no path rule of its own. `docs/CODEBASE_ASSEMBLY.md` §14
   stays the owner document for the two sets, and `docs/ARCHITECTURE.md` §3.3 states the record rule and
   links to it.
2. The prune action lives in `provenance.py`, with the rule it acts on. It reads the record file through
   `parse_records`, decides through `prunable_entries`, and removes what that function names. It builds no
   path and states no second decision.
3. `prunable_entries` is unchanged: a referenced entry is not prunable, an unreferenced entry is prunable,
   and a record with no cache entry prunes nothing.
4. `--prune-cache` is an opt-in flag that gates the step, off by default, and it names no part of the
   layout, so the no-flag scan still holds. It applies to `--source api` only (exit 2 for `--source file`).
5. `main()` order is unchanged except the new step: the record is written, the gate runs, the prune runs
   last. A run that does not declare the action writes the same bytes and keeps the cache.
6. Exit codes: the gate still decides the code; a prune that removes nothing does not change it; a record
   file that cannot be read is a refusal and exits 1 with a message that names the record file; the record
   is not a gate input, so `data_file_count` and `file_count` are unchanged.
7. The console prints the pruned entries only when the action ran and removed something. A run that
   declares nothing prints nothing new.
8. Tests are offline and deterministic, and drive the cache directory through fixtures the way
   `tests/test_source_fetch.py` and `tests/test_provenance.py` do: an injected producer, or a seeded cache
   read with `--offline`. No test calls the network.
9. Pins: the record directory (the root set, the one builder); a referenced entry not pruned; an
   unreferenced entry pruned; the two-record file case (two sources, one file); a record that cannot be
   read; a run that does not declare the action is unchanged; the argument rule (exit 2); the exit-code
   behaviour.
10. `ruff check .` is clean and `python3 -m pytest` passes (baseline 1450 tests). Goldens are unchanged,
    because a default run writes the same bytes.
11. The commit message follows the `git log` style, uses ASD-STE100, and states the decision, the action
    shape, and the pins. The tracking markdown is a second commit.

## Result

Met.

- The record directory is the output directory, and `SOURCE.txt` stays a codebase root-set file named
  through `write_path.root_path`. `provenance.py` states no path rule: the caller names the record path, and
  the action takes it as an argument. Pinned by
  `tests/test_write_path.py::test_the_record_directory_is_the_output_directory_for_the_prune`.
- The action is `provenance.prune(record_file, cache_dir)`: it reads the record file through
  `parse_records`, decides through `prunable_entries`, and removes what the decision names.
  `prunable_entries` is unchanged.
- `--prune-cache` is an opt-in flag that gates the step, off by default, and applies to `--source api` only
  (exit 2). `main()` runs it after the record is written and after the gate.
- Exit codes: the gate still decides; a prune that removes nothing changes nothing; a record the action
  cannot read is a refusal and exits 1, and the message names the record file. A cache directory that holds
  no entry is not a refusal.
- The console prints one line per pruned entry, and only when the action removed something.
- Tests added: group 6 of `tests/test_provenance.py` (ten pins) and one pin in `tests/test_write_path.py`.
  Each run drives the cache through a seeded cache read with `--offline`, or an injected producer, so no
  test calls the network.
- No golden changed: the action writes no output, so a default run writes the same bytes.
