"""F5.3 provenance record: what one run read, written as `SOURCE.txt`. F5.4 makes the
file one record per source the run read, so a two-source run writes the main record and
the parent record.

Six rules, stated once here.

1. What the record states, in this field order: the source kind, the source name, the
   path, the scope the source holds, the request identity, the cache entry, the size of
   the bytes, and the SHA-256 hex of those bytes. A field that does not apply to the
   source kind is `-`, so one shape reads.
2. The record is data: one `field: value` line per field, in the fixed order, with no
   prose and no timestamp. A timestamp would make two runs on the same bytes differ,
   which the determinism rule does not allow. `parse_record` reads one record and
   `parse_records` reads a record file, so a tool can act on a record instead of reading
   it. Records are separated by one blank line; a one-record file writes the same bytes as
   the F5.3 rule.
3. The byte facts come from the door. `xml_input.ParsedSource` records the size and the
   hash of the bytes it parsed, and `state_input.StateSource` records the same two facts for
   the bytes its door checked, so the record names the bytes the door checked, not a file that
   may have changed since the run.
4. The pruning rule: a cache entry is not pruned while a written record references it, so
   the reference is the `cache_entry` field of a parsed record, never a printed line.
   `prunable_entries` is the decision, and `prune` is the action that runs it: it reads the record
   file back through `parse_records`, so the reference stays data, and removes what the decision names.
   `--prune-cache` gates the action, and a run that does not declare it keeps its cache.
5. The record directory is the output directory, so `SOURCE.txt` is a codebase root-set file named through
   `write_path.root_path` (`docs/CODEBASE_ASSEMBLY.md` §14). One record file per run: the prune action reads
   the record file the same run wrote, and this module states no path rule of its own.
6. Records are in read order: the order the run read them. For a path 1 run that is the main source,
   then the declared parent, then the state source (F5.6). For a path 2 run it is one record per request the
   run read (`docs/API_CONVERSION_PATH.md` §2.5), because one response is one source. Which order a path 2 run
   reads is the run order's decision, so this module states no read rule for it. `scope` is the fact the door
   records, so the record does not state a naming rule of its own; the one definition is
   `xml_input.DEFAULT_SCOPE`, a per-scope request states the path it declared, and a state source states the
   workspace the run declared. A state source has no request, so its two request fields are `-` and its record
   references nothing: it prunes nothing.

The record is a run output, not a report body. The report bodies name the source name and
never the path (F4.2 rule 6), so the path field here does not touch the report byte rule.

The record never names the API key. It names the request identity, which is the key-free
shape the cache entry is hashed from (F5.2 AC-5.4).

Usage:
    from provenance import record_for, render, render_records, parse_record, parse_records, prune
    from write_path import root_path, write_file
    record = record_for(source, request=request)
    write_file(root_path(output_dir, PROVENANCE_FILE), render_records([record, parent_record, state_record]))
    reference = parse_records((output_dir / PROVENANCE_FILE).read_text())[0].cache_entry
    pruned = prune(root_path(output_dir, PROVENANCE_FILE), cache_dir)
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import source_fetch
import state_input
from xml_input import ParsedSource

PROVENANCE_FILE = 'SOURCE.txt'

# Field order. Fixed, so two runs write the same bytes and a reader does not guess.
# The field names are the printed keys, so `parse_record` reads the record back as itself.
FIELD_ORDER = ('kind', 'name', 'path', 'scope', 'request', 'cache_entry', 'size', 'sha256')

# The value for a field that does not apply to the source kind, so one shape reads.
ABSENT = '-'


@dataclass(frozen=True)
class ProvenanceRecord:
    """One run's record of what it read, as data."""

    kind: str
    name: str
    path: str
    scope: str
    request: str
    cache_entry: str
    size: int
    sha256: str


def record_for(source: Union[ParsedSource, state_input.StateSource],
               request: Optional[source_fetch.ApiRequest] = None) -> ProvenanceRecord:
    """Build the record for one source the run read, from the source the door returned and
    the request it read.

    The origin already carries the kind, the report name and the path, so the record does
    not restate a naming rule. The request carries the identity and the entry name; a file
    source and a state source have no request, so those two fields are `-`. `scope` is the
    fact the door records: `whole-config`, the declared path of a per-scope source (F5.4), or
    the declared workspace of a state source (F5.6). Both door shapes state the same four
    record facts, so no new field is needed.
    """
    path = source.origin.path
    return ProvenanceRecord(
        kind=source.origin.kind,
        name=source.origin.name,
        path=str(path) if path is not None else ABSENT,
        scope=source.scope,
        request=request.canonical() if request is not None else ABSENT,
        cache_entry=request.cache_name() if request is not None else ABSENT,
        size=source.size,
        sha256=source.sha256,
    )


def render(record: ProvenanceRecord) -> str:
    """The record as text: one `field: value` line per field, in the fixed order."""
    return ''.join(f'{key}: {getattr(record, key)}\n' for key in FIELD_ORDER)


def render_records(records: Iterable[ProvenanceRecord]) -> str:
    """A record file: the records in read order, separated by one blank line.

    One record writes the same bytes as `render`, so a one-source run is unchanged.
    """
    return '\n'.join(render(record) for record in records)


def parse_records(text: str) -> list:
    """Read a record file back as data, in read order.

    A blank line separates records; a record that is not all declared fields is a refusal,
    through `parse_record`.
    """
    return [parse_record(chunk) for chunk in text.split('\n\n') if chunk.strip()]


def parse_record(text: str) -> ProvenanceRecord:
    """Read a written record back as data. A tool reads the cache reference from here.

    A line that is not a declared field, or a field the record must always state, is a
    refusal: the record is data, so a reader cannot fall back to reading prose.
    """
    values = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(': ')
        if key not in FIELD_ORDER or not value:
            raise ValueError(f'not a record field: {line!r}')
        values[key] = value
    missing = [key for key in FIELD_ORDER if key not in values]
    if missing:
        raise ValueError(f'the record does not state its fields: {missing}')
    values['size'] = int(values['size'])
    return ProvenanceRecord(**values)


def cache_reference(record: ProvenanceRecord) -> Optional[str]:
    """The cache entry a record references, or None when the source kind has no cache entry."""
    return None if record.cache_entry == ABSENT else record.cache_entry


def prunable_entries(cache_dir, records: Iterable[ProvenanceRecord]) -> list[Path]:
    """The cache entries no record references (F5.3 AC-4).

    A prune action decides through this function, so the reference stays data. An entry a
    record references is not prunable. A record for a source with no cache entry references
    nothing, so it prunes nothing.
    """
    referenced = {reference for reference in map(cache_reference, records) if reference is not None}
    cache = Path(cache_dir)
    return sorted(path for path in cache.iterdir() if path.is_file() and path.name not in referenced)


def prune(record_file, cache_dir) -> list[Path]:
    """The prune action for one run (rule 4): read the record file back as data, decide through
    `prunable_entries`, and remove the entries the decision names.

    The reference is the record file the run wrote, not the record objects the run built, so the action
    reads it through `parse_records` and decides through `prunable_entries`: it states no second decision
    and builds no path, so the caller names the record path through the builder for the set the record
    belongs to. A record file the action cannot read is a refusal, the way a record line that is not a
    field is a refusal, and the message names the record file. A cache directory that holds no entry has
    nothing to prune, so it is not a refusal. The action removes files and writes none, so the single
    writer is not involved.
    """
    record_path = Path(record_file)
    if not record_path.is_file():
        raise ValueError(f'cannot read the record: {record_path}')
    cache = Path(cache_dir)
    if not cache.is_dir():
        return []
    try:
        records = parse_records(record_path.read_text(encoding='utf-8'))
    except ValueError as e:
        # The refusal names the record file, because the action reads a file and not one record.
        raise ValueError(f'cannot read the record {record_path}: {e}') from e
    removed = []
    for entry in prunable_entries(cache, records):
        entry.unlink()
        removed.append(entry)
    return removed

