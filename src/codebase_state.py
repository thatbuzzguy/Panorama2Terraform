"""Epic 11 the codebase as state: the merge between the rows a codebase already holds and the rows a run read.

Seven rules, stated once here. The four records are the codebase root set (`docs/CODEBASE_ASSEMBLY.md` §14), and
the rule that reads them is `sanity_checks.DATA_FILES` (`docs/ARCHITECTURE.md` §3.2), so this module adds the join
key and the merge and names no file, no path, no directory and no row shape. It writes no file and reads no file:
the rows arrive through each record module's `parse_rows`, and the writer is `write_path.py`.

1. **One join key per record, as data** (`JOIN_KEYS`), and the fact each key joins on: the manifest record on
   `directory`, which is the §5 shape of the unit identity; the ownership record on (`type`, `entry`) with the
   facts, read through `state_coverage.ownership_key`, the one identity key rule; the edge record on the pair of
   entry identities with the matrix row and the entry name; the site record on `directory`. No module states a
   second key, and no record gains a second join.
2. **The merge rule.** The run's rows replace the codebase's rows for the rows the run built, and the rows for the
   units the run did not build stay as the record states them. The merged set is keyed by row identity, not by run,
   so no record can state which run wrote a row.
3. **A record with no existing rows is the run's own set**, in the order the record's own rule built it. That is
   what keeps the bytes a single run writes today, so no committed golden changes.
4. **The order of a merged set is read through each record's own order rule**: `unit_manifest.FACT_KEYS` for the
   manifest, `ownership.row_key` for the ownership record, `reference_edges.FIELD_ORDER` for the edge record. The
   order is not read through which side a row came from, so no order-of-writes fact appears. `site_data.py` states
   no order rule for a row it reads back, so a merged site file is read in the order the join key states it; the
   condition that a site row names no facts and cannot state the identity order on its own is recorded in
   `backlog.md`, and on the accepted corpus the site file already shows that order, so today's bytes are unchanged.
5. **No run field and no timestamp.** The merge adds no field to a row, so a merged row is the record's own shape
   and reads back through `parse_rows` as itself.
6. **The reader is each record module's `parse_rows`.** This module defines no shape and no reader, so a record it
   cannot read is a refusal the record module already states, and the gate's data rule stays the only data rule.
   The entry point's reference read of the records a codebase already holds is that data read, so the run gains only
   the fields `parse_rows` reads back. Pinned by
   `tests/test_codebase_state.py::test_the_run_reads_the_existing_records_through_the_readers_the_shapes_owners_state`.
7. **A data module.** It writes no file, states no record-directory path rule, names no console line, states no
   environment name, defines no naming rule and holds no writer of its own, and imports only the standard library
   and the house modules.

Usage:
    from codebase_state import JOIN_KEYS, join_key, merge_rows
    from write_path import root_path, write_file
    for name, module in sanity_checks.DATA_FILES:  # the data rule, read through its owner
        record = [entry for entry in JOIN_KEYS if entry[0] is module][0]
        path = root_path(output_dir, name)
        merged = merge_rows(record, module.parse_rows(path.read_text(encoding="utf-8")), run_rows[module])
        write_file(path, module.render(merged))
    for record in JOIN_KEYS:
        for row in merged[record[0]]:
            print(join_key(record, row), row)
"""

import ownership
import reference_edges
import site_data
import state_coverage
import unit_manifest

# One row per record: the module that owns the row shape, the fields the join key is built from, the fact the key
# joins on, the order rule the record module states for its rows, and the key rule the record reads through its
# owner. A record whose key is the one identity key rule names that rule here, so no key rule is built in this
# module; a record whose order rule it does not state names nothing, and rule 4 says what that means. The four
# records are the set `sanity_checks.DATA_FILES` states, so this table adds the join key only and names no file.
JOIN_KEYS = (
    (unit_manifest, ("directory",), "the unit identity", unit_manifest.FACT_KEYS, None),
    (ownership, ("type", "entry"), "the entry identity", ownership.row_key, state_coverage.ownership_key),
    (reference_edges, reference_edges.FIELD_ORDER, "the pair of entry identities", reference_edges.FIELD_ORDER, None),
    (site_data, ("directory",), "the unit identity", None, None),
)


def join_key(record: tuple, row: dict) -> tuple:
    """The identity one row is merged by, read through the record's own join key.

    For the ownership record the key is the entry identity read through `state_coverage`, so this function builds
    no key of its own. For the other three the key is the field the record states, which `parse_rows` reads back as
    itself.
    """
    _module, fields, _fact, _order, key_rule = record
    if key_rule is None:
        return tuple(row[field] for field in fields)
    # `key_rule` takes the facts as a mapping of the fact keys, and a row read through `parse_rows` states them, so
    # the row is the facts.
    return key_rule(row[fields[0]], row[fields[1]], row)


def merge_rows(record: tuple, codebase_rows: list, run_rows: list) -> list:
    """The merge rule, stated once: the run's rows replace the codebase's rows for the rows the run built, and the
    rows for the units the run did not build stay as the record states them.

    `codebase_rows` and `run_rows` are rows read through the record module's `parse_rows`, the one reader of its
    shape. A record with no existing rows is the run's own set, in the order the record's own rule built it, which
    is the bytes a single run writes today (rule 3).
    """
    if not codebase_rows:
        return list(run_rows)

    # Keyed by the join key, so one key holds one row and no row states which run wrote it.
    rows = {join_key(record, row): row for row in codebase_rows}
    for row in run_rows:
        rows[join_key(record, row)] = row

    order = record[3]
    if order is None:
        # Rule 4: the record states no order rule for a row it reads back, so the merged set is read in the order
        # the join key states it.
        return [rows[key] for key in sorted(rows)]
    if callable(order):
        # `ownership.row_key` is read through its owner, so the order is the record's own rule, not a copy of it.
        return sorted(rows.values(), key=order)
    return sorted(rows.values(), key=lambda row: tuple(row[field] for field in order))
