"""F6.4 the import block: one block per entry, as `imports.tf`.

An import block binds a resource block to the object the provider already has. Six rules, stated once here.

1. **One block per entry, one file per codebase.** The gate reads `.tf` files only (`ARCHITECTURE.md` §4.5),
   so the agreement rule (`sanity_checks.check_import_blocks`) can only read a `.tf` file. F6.1 rule 4 still
   refuses a per-unit file, because this feature writes no directory.
2. **The id is base64 of a JSON object** (`docs/CODEBASE_ASSEMBLY.md` §12). For an ordinary object type the
   object is the location object plus the entry name: `{"location": ..., "name": ...}`. Keys sort at every
   level and the separators are compact, so the same entry encodes to the same bytes; `ensure_ascii` keeps the
   file ASCII, so two runs on the same bytes write the same bytes.
3. **One location rule.** The location object of the id is the same data `TerraformGenerator.location_data`
   builds for the resource block, so the block and the id cannot state two different locations.
4. **One naming rule.** The local name is the name `declare_block_name` recorded at the site that applied the
   rule, and the entry name is the name the block states through `entry_coverage.name_field`, the one rule for
   the field that carries it: `name` for a type that declares one, and the field that names the scope for a type
   that declares none (`device_group` for `panos_device_group_parent`, F6.5). The gate reads the block through
   the same rule. This module defines no sanitizing rule and resolves no name.
5. **The four `*_policy_rules` types write no block.** Their import object names the rulebase, the position in
   the live rulebase, and a list of names, so no per-entry object exists (the rule, and the reason, are stated
   in `acceptance.md` Decision 3 and pinned by `tests/test_import_blocks.py`). The type set is read from the
   `rulebase` field `LOCATION_SCHEMA` declares, so no second table names the four types.
6. **Shape, order, and bytes.** One block states two fields, `to` then `id`. Rows print sorted by unit
   directory, then by local name, which a reader can reproduce from the file. No row states a timestamp or a
   path. The file is written only when it has content, following the rule for the report files and the three
   data files.

Usage:
    from import_blocks import IMPORT_FILE, ROW_FIELDS, build_id, decode_id, read_block, render, row
    shape = row(directory, 'panos_address', 'addr_1a2b3c4d', 'Web', {'device_group': {'name': 'VG1'}})
    (output_dir / IMPORT_FILE).write_text(render([shape]), encoding='utf-8')
    print(decode_id(shape['import_id']))
"""

import base64
import json
import re

import resource_mapping

IMPORT_FILE = 'imports.tf'

# The row shape. Fixed, so two runs write the same bytes and a reader does not guess.
ROW_FIELDS = ('unit', 'resource_type', 'local_name', 'entry_name', 'import_id', 'rule')

# The rule decision for a type this module cannot write a block for, as the gate line states it.
RULE_DECISION = ('the import object names the rulebase, the position, and a list of names, '
                 'so no per-entry import object exists (F3.5)')


def rule_types() -> set[str]:
    """The types whose `LOCATION_SCHEMA` row declares `rulebase`: the four `*_policy_rules` types."""
    return {resource_type for resource_type, scopes in resource_mapping.LOCATION_SCHEMA.items()
            if any('rulebase' in fields for fields in scopes.values())}


def build_id(location: dict, entry_name: str) -> str:
    """base64 of the JSON object for one entry: the location object and the entry name (§12)."""
    document = json.dumps({'location': location, 'name': entry_name},
                          sort_keys=True, ensure_ascii=True, separators=(',', ':'))
    return base64.b64encode(document.encode('utf-8')).decode('ascii')


def decode_id(value: str) -> dict:
    """Read a written id back as data. The inverse of `build_id`.

    A value that is not the declared shape is a refusal, the way `unit_manifest.parse_rows` refuses a row that
    is not the declared shape: an id is data, so a reader cannot fall back to reading prose.
    """
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(f'the id is not base64: {value!r}') from exc
    try:
        document = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'the decoded id is not JSON: {value!r}') from exc
    if not isinstance(document, dict):
        raise ValueError(f'the id is not an object: {value!r}')
    extra = [key for key in document if key not in ('location', 'name')]
    if extra:
        raise ValueError(f'the id states a field it does not declare: {extra}')
    if not isinstance(document.get('location'), dict):
        raise ValueError(f'the id location is not a sub-block object: {document}')
    if not isinstance(document.get('name'), str) or not document['name']:
        raise ValueError(f'the id name is not a name: {document}')
    for sub_block, fields in document['location'].items():
        if not isinstance(fields, dict):
            raise ValueError(f'location.{sub_block} is not an object of fields: {document}')
        if any(not isinstance(value, str) for value in fields.values()):
            raise ValueError(f'location.{sub_block} states a field that is not a name: {document}')
    return {'location': {sub_block: dict(sorted(fields.items()))
                         for sub_block, fields in sorted(document['location'].items())},
            'name': document['name']}


def row(unit: str, resource_type: str, local_name: str, entry_name: str, location: dict) -> dict:
    """One import row from the same data the resource block uses: the type, the names, the location."""
    shape = dict.fromkeys(ROW_FIELDS, '')
    shape['unit'] = unit
    shape['resource_type'] = resource_type
    shape['local_name'] = local_name
    shape['entry_name'] = entry_name
    if resource_type in rule_types():
        # No id: the import object for this type names a rulebase, a position, and a list (rule 5).
        shape['rule'] = RULE_DECISION
    else:
        shape['import_id'] = build_id(location, entry_name)
    return shape


def render(rows: list) -> str:
    """The import file as text: one block per row, in the order a reader can reproduce."""
    lines = ['# Import blocks (F6.4): one block per entry, built from the same identity data the '
            'resource block uses.\n'
            '# The id is base64 of the location object and the entry name, the provider shape (§12).\n\n']
    for shape in sorted(rows, key=lambda row: (row['unit'], row['local_name'])):
        if not shape['import_id']:
            # A row that states a rule instead of an id names no block.
            continue
        lines.append(f'import {{\n  to = {shape["resource_type"]}.{shape["local_name"]}\n'
                     f'  id = "{shape["import_id"]}"\n}}\n\n')
    return ''.join(lines)


def read_block(block) -> dict:
    """One written `import` block, read back as a row through the gate's one block reader.

    The block is data, so a shape it does not declare is a refusal (`decode_id`), the way
    `unit_manifest.parse_rows` refuses a row that is not the declared shape. `unit` is empty here: the unit
    is the manifest fact, not a block field.
    """
    shape = dict.fromkeys(ROW_FIELDS, '')
    shape['resource_type'] = block.rtype
    shape['local_name'] = block.local
    decoded = decode_id(block_value(block, 'id'))
    shape['entry_name'] = decoded['name']
    shape['import_id'] = build_id(decoded['location'], decoded['name'])
    shape['rule'] = RULE_DECISION if block.rtype in rule_types() else ''
    return shape


def block_value(block, key: str) -> str:
    """One quoted field of a block at the block's own level, as the gate reads it.

    A field inside a sub-block is not the block's field: `location = { name = "DG-A" }` states the location's
    name, not the block's. The block's own level is the smallest indent in the body, so the reader reads the
    block's `name` and not the sub-block's.
    """
    indents = [len(line) - len(line.lstrip()) for line in block.body.split('\n') if line.strip()]
    indent = min(indents) if indents else 0
    # A quoted value may carry an escaped quote, so the reader stops only at the closing quote.
    match = re.search(rf'^ {{{indent}}}{re.escape(key)}\s*=\s*"((?:[^"\\]|\\.)*)"', block.body, re.M)
    return unescape(match.group(1)) if match else ''


def unescape(value: str) -> str:
    """A quoted HCL string value, read back as the string it states.

    The generator writes the escape sequences HCL supports (`\\`, `\"`, `\\t`, `\\r`, `\\n`), and `json.dumps`
    writes the same ones, so the value in the block and the value in the id are the same string only after both
    are read back.
    """
    for escape, char in (('\\\\', '\\'), ('\\"', '"'), ('\\t', '\t'), ('\\r', '\r'), ('\\n', '\n')):
        value = value.replace(escape, char)
    return value
