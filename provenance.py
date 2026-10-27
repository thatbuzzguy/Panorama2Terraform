"""F5.3 provenance record: what one run read, written as `SOURCE.txt`.

Four rules, stated once here.

1. What the record states, in this field order: the source kind, the source name, the
   path, the scope the source holds, the request identity, the cache entry, the size of
   the bytes, and the SHA-256 hex of those bytes. A field that does not apply to the
   source kind is `-`, so one shape reads.
2. The record is data: one `field: value` line per field, in the fixed order, with no
   prose and no timestamp. A timestamp would make two runs on the same bytes differ,
   which the determinism rule does not allow. `parse_record` reads the written text back,
   so a tool can act on a record instead of reading it.
3. The byte facts come from the door. `xml_input.ParsedSource` records the size and the
   hash of the bytes it parsed, so the record names the bytes the door checked, not a file
   that may have changed since the run.
4. The pruning rule: a cache entry is not pruned while a written record references it, so
   the reference is the `cache_entry` field of a parsed record, never a printed line.
   `prunable_entries` is the rule; no command runs the prune yet (see `backlog.md`).

The record is a run output, not a report body. The report bodies name the source name and
never the path (F4.2 rule 6), so the path field here does not touch the report byte rule.

The record never names the API key. It names the request identity, which is the key-free
shape the cache entry is hashed from (F5.2 AC-5.4).

Usage:
    from provenance import record_for, render, parse_record
    record = record_for(source, request=request)
    (output_dir / PROVENANCE_FILE).write_text(render(record), encoding='utf-8')
    reference = parse_record((output_dir / PROVENANCE_FILE).read_text()).cache_entry
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import source_fetch
from xml_input import ParsedSource

PROVENANCE_FILE = 'SOURCE.txt'

# Field order. Fixed, so two runs write the same bytes and a reader does not guess.
# The field names are the printed keys, so `parse_record` reads the record back as itself.
FIELD_ORDER = ('kind', 'name', 'path', 'scope', 'request', 'cache_entry', 'size', 'sha256')

# The value for a field that does not apply to the source kind, so one shape reads.
ABSENT = '-'

# The scope a source holds today: the whole config. A per-scope source names its own
# scope, which is the field F5.4 and F5.6 read.
DEFAULT_SCOPE = 'whole-config'


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


def record_for(source: ParsedSource, request: Optional[source_fetch.ApiRequest] = None,
               scope: str = DEFAULT_SCOPE) -> ProvenanceRecord:
    """Build the record for one run, from the source the door returned and the request it read.

    The origin already carries the kind, the report name and the path, so the record does
    not restate a naming rule. The request carries the identity and the entry name; a file
    source has no request, so those two fields are `-`.
    """
    path = source.origin.path
    return ProvenanceRecord(
        kind=source.origin.kind,
        name=source.origin.name,
        path=str(path) if path is not None else ABSENT,
        scope=scope,
        request=request.canonical() if request is not None else ABSENT,
        cache_entry=request.cache_name() if request is not None else ABSENT,
        size=source.size,
        sha256=source.sha256,
    )


def render(record: ProvenanceRecord) -> str:
    """The record as text: one `field: value` line per field, in the fixed order."""
    return ''.join(f'{key}: {getattr(record, key)}\n' for key in FIELD_ORDER)


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
