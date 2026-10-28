"""F6.1 the unit as data: one manifest row per declared scope, as `CODEBASE_MANIFEST.json`.

A unit is one declared scope (`docs/CODEBASE_ASSEMBLY.md` §1). The manifest is the shape a
codebase needs before a directory, an owner, or a reference edge can be named. Five rules,
stated once here.

1. The unit. One unit is one combination of the four scope facts (`ARCHITECTURE.md` §2.2), and
   a unit exists when the ledger has a report row in it. The rows come from
   `entry_coverage.EntryLedger`, so the manifest adds no parse data. An entry inside a
   config-object entry is a property level (§3.1), so the parent row's count covers it.
2. The directory name. `sanitize(unit name) + '_' + 8-hex digest of the unit identity`, in the
   `ARCHITECTURE.md` §5 shape. The digest is always present, not only on a collision: a
   collision-only rule makes one unit's name depend on the other units in the run, so adding an
   unrelated scope would move an existing directory. The name depends on the unit alone, which is
   the same reason §5 puts the digest in a local name. The unit name is the deepest scope the
   export declares, in the level order the F3.9 rule states; `Shared` names the shared section,
   and `localhost.localdomain` names no device (F3.5), so the placeholder never names a unit.
3. The row shape. The row is data, so a document describes its fields and never restates a row
   (`docs/README.md` rule). The fields print in the declared order, the rows are in identity
   order, the reference names are sorted, and no field states a timestamp or a path, so two runs
   on the same bytes write the same bytes. `parse_rows` reads a written file back, and a row that
   is not the declared shape is a refusal, the way `provenance.parse_record` refuses a line that
   is not a field.
4. One file per codebase. A reader cannot find a per-unit file before it knows the directory
   name, and the directory name is the fact this module decides. F6.1 writes no directory, so a
   per-unit file would sit outside the shape it names. The set of units is a run fact, and the
   edge list (F6.3) needs the whole set, so one file holds one row per unit. The file is written
   only when it has content, following the existing rule for the report files.
5. The unit order lives on this row, as `rank` and `after`, because this file is the place that
   names each unit; a fourth data file that listed directories would be a second place that states
   the unit set. This module states the row shape only. `reference_edges.order` fills the two
   fields, because the order comes from the three rules `reference_edges.py` states.

The reference names are recorded by the reference rule (`TerraformGenerator.name_ref`) at the site
that applies it and arrive here as `references`; this module resolves no name. The sanitizing rule
is `TerraformGenerator.sanitize_name` (`ARCHITECTURE.md` §5), so this module takes it as an
argument and defines no second rule.

Usage:
    from unit_manifest import MANIFEST_FILE, build_rows, render, parse_rows
    rows = build_rows(ledger, generator.unit_references(), generator.sanitize_name)
    rows = reference_edges.order(rows, ownership_rows, edge_rows)    # rule 5: fills rank and after
    (output_dir / MANIFEST_FILE).write_text(render(rows), encoding='utf-8')
    for row in parse_rows((output_dir / MANIFEST_FILE).read_text(encoding='utf-8')):
        print(row['directory'], row['rank'], row['after'])
"""

import hashlib
import json
from typing import Callable

import container_coverage

MANIFEST_FILE = 'CODEBASE_MANIFEST.json'

# Field order. Fixed, so two runs write the same bytes and a reader does not guess.
# The field names are the printed keys, so `parse_rows` reads a row back as itself.
# `rank` and `after` are the unit order (rule 5), so they print after the F6.1 fields.
FIELD_ORDER = ('unit', 'device_group', 'vsys', 'template', 'vsys_device',
               'directory', 'entry_count', 'references', 'rank', 'after')

# The four scope facts (F3.1, F3.2), read through `container_coverage`, so the identity order is
# the order the state scan keys on (`state_coverage.ownership_key`).
FACT_KEYS = container_coverage.SCOPE_FACT_KEYS

# The level order the F3.9 rule states (device group, then template, then device), read from the
# deepest level inward, so the deepest declared scope names the unit. The virtual system is the
# innermost scope the export declares, so it is first here.
NAME_LEVELS = ('vsys', 'vsys_device', 'template', 'device_group')

DIGEST_HEX = 8

# The shared section, as the F3.9 rule names it. `Shared` in `device_group` is the parse fallback
# for an entry the parse cannot place (§2.2), so it is the name of the shared unit and never a
# fact value: the shared unit is the unit whose four facts are empty.
SHARED_UNIT = 'Shared'

# A name that sanitizes to nothing, as §5 states it.
UNNAMED = 'unnamed'


def facts_of(obj: dict) -> tuple:
    """The unit identity a ledger row or a parsed object states, in `FACT_KEYS` order.

    The `Shared` value in `device_group` is the parse fallback, not a declared device group
    (§2.2), so it never enters the identity; the state scan holds the same rule. A ledger row
    never states the fallback and a parsed object can, so reading both through this one function
    keeps the row and the reference record on the same unit.
    """
    return tuple('' if key == 'device_group' and (obj.get(key) or '') == SHARED_UNIT
                 else (obj.get(key) or '') for key in FACT_KEYS)


def fact(facts: tuple, key: str) -> str:
    """One fact of an identity, read in `FACT_KEYS` order."""
    return facts[FACT_KEYS.index(key)]


def unit_name(facts: tuple) -> str:
    """The name a unit is called by: the deepest scope the export declares."""
    for key in NAME_LEVELS:
        value = fact(facts, key)
        if value and not (key == 'vsys_device' and value == container_coverage.PLACEHOLDER_DEVICE):
            return value
    return SHARED_UNIT


def identity_digest(facts: tuple) -> str:
    """The 8-hex digest of the unit identity: the four facts, in field order, joined by `|`."""
    return hashlib.sha256('|'.join(facts).encode()).hexdigest()[:DIGEST_HEX]


def directory_name(facts: tuple, sanitize: Callable[[str], str]) -> str:
    """The directory name for one unit: the §5 shape, always with the digest."""
    return f'{sanitize(unit_name(facts)) or UNNAMED}_{identity_digest(facts)}'


def build_rows(ledger, references: dict, sanitize: Callable[[str], str]) -> list:
    """One row per unit the ledger shows, in identity order.

    `references` is the reference names `name_ref` recorded, keyed by the referrer's facts. A unit
    exists only when the ledger has a report row in it, so a reference recorded for a unit with no
    row adds nothing here; `tests/test_unit_manifest.py` pins that every recorded name belongs to
    a unit the ledger shows across the fixture corpus.
    """
    units: dict = {}
    for row in ledger.rows():
        units[facts_of(row)] = units.get(facts_of(row), 0) + 1

    rows = []
    for facts in sorted(units):
        row = dict.fromkeys(FIELD_ORDER, '')
        row.update(zip(FACT_KEYS, facts))
        row['unit'] = unit_name(facts)
        row['directory'] = directory_name(facts, sanitize)
        row['entry_count'] = units[facts]
        row['references'] = sorted(references.get(facts, ()))
        # Rule 5: `reference_edges.order` fills these two fields. They start empty so a run that
        # applies no order rule still writes the declared shape.
        row['rank'] = 0
        row['after'] = []
        rows.append(row)
    return rows


def render(rows: list) -> str:
    """The manifest as text: the rows in field order, with one trailing newline.

    Fields print in the declared order, not alphabetically, and no field states a timestamp or a
    path, so two runs on the same bytes write the same bytes.
    """
    return json.dumps([{key: row[key] for key in FIELD_ORDER} for row in rows], indent=2) + '\n'


def parse_rows(text: str) -> list:
    """Read a written manifest back as data, in identity order.

    A row that is not the declared shape is a refusal: the manifest is data, so a reader cannot
    fall back to reading prose.
    """
    document = json.loads(text)
    if not isinstance(document, list):
        raise ValueError('the manifest is not a list of rows')
    rows = []
    for row in document:
        if not isinstance(row, dict):
            raise ValueError(f'not a manifest row: {row!r}')
        extra = [key for key in row if key not in FIELD_ORDER]
        if extra:
            raise ValueError(f'not a declared manifest field: {extra}')
        missing = [key for key in FIELD_ORDER if key not in row]
        if missing:
            raise ValueError(f'the row does not state its fields: {missing}')
        if any(not isinstance(row[key], str) for key in FIELD_ORDER
               if key not in ('entry_count', 'references', 'rank', 'after')):
            raise ValueError(f'the name fields of a row are not names: {row}')
        if not isinstance(row['entry_count'], int):
            raise ValueError(f'entry_count is not a count: {row}')
        if not isinstance(row['references'], list) \
                or not all(isinstance(name, str) for name in row['references']):
            raise ValueError(f'references is not a list of names: {row}')
        if not isinstance(row['rank'], int):
            raise ValueError(f'rank is not a position: {row}')
        if not isinstance(row['after'], list) \
                or not all(isinstance(unit, str) for unit in row['after']):
            raise ValueError(f'after is not a list of directories: {row}')
        rows.append({key: row[key] for key in FIELD_ORDER})
    return sorted(rows, key=lambda row: tuple(row[key] for key in FACT_KEYS))
