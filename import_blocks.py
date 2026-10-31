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
   the same rule. This module defines no sanitizing rule and resolves no name. The field readers here also serve
   the action rule (F6.7): `sub_block_body` is the one reader for the level a field is read at
   (`location` for a resource, `config` for an action), `block_list` reads a list field element by
   element with the same stop-at-the-quote rule, `fields` reads every field at a level, and
   `unescape` is the one escape set.
5. **The four `*_policy_rules` types write no block.** Their import object names the rulebase, the position in
   the live rulebase, and a list of names, so no per-entry object exists (the rule, and the reason, are stated
   in `docs/CODEBASE_ASSEMBLY.md` §7 rule 6 and pinned by `tests/test_import_blocks.py`). The type set is read from the
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


def sub_block_body(block, name: str) -> str:
    """The text inside one named sub-block of a block, as the one block reader reads it (F6.7).

    A sub-block is `name = { ... }` (the `location` shape) or `name { ... }`, which is the shape the
    Terraform 1.14 grammar uses for an action's `config`. One reader serves both, so a rule that reads
    a field inside a sub-block reads the same text the block states. A block with no such sub-block is
    read as `''`, because a reader cannot guess a level that is not there.
    """
    match = re.search(rf'\b{re.escape(name)}\s*(?:=\s*)?\{{', block.body)
    if match is None:
        return ''
    start = match.end() - 1
    depth = 0
    for index in range(start, len(block.body)):
        char = block.body[index]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return block.body[start + 1:index]
    return block.body[start + 1:]


def block_value(block, key: str, sub_block: str = '') -> str:
    """One quoted field of a block, as the gate reads it (the one field reader).

    A field inside a sub-block is not the block's field: `location = { name = "DG-A" }` states the
    location's name, not the block's, so `sub_block` names the level the field is read at. Without it
    the reader reads the block's own level, which is the smallest indent in the body. A quoted value
    may carry an escaped quote, so the reader stops only at the closing quote.
    """
    value = field_value(block, key, sub_block)
    return unescape(value[1:-1]) if value.startswith('"') else ''


def block_list(block, key: str, sub_block: str = '') -> tuple:
    """One list field of a block, element by element, through the same field reader (F6.7).

    The reader keeps the rule: read at the level `sub_block` names, stop at the closing quote. An
    element that is not a quoted string is not a name, so it is not read, and the shape check in
    `sanity_checks.check_actions` reports it.
    """
    value = field_value(block, key, sub_block)
    if not value.startswith('['):
        return ()
    return tuple(unescape(element)
                 for element in re.findall(r'"((?:[^"\\]|\\.)*)"', value))


def fields(block, sub_block: str = '') -> dict:
    """Every field of a block, as the raw value text, in the block's order (F6.7).

    `sub_block` names the level the fields are read at: the action rule reads the fields inside
    `config`, which is the grammar Terraform 1.14 requires for an action block (measured with
    `terraform validate`: a field at the block's own level is refused). Without it the reader reads the
    block's own level, so the value shapes the row declares can be checked against the value the block
    states: quoted string, `true` or `false`, `[ ... ]`, or `{ ... }`.
    """
    body = sub_block_body(block, sub_block) if sub_block else block.body
    found = {}
    for match in re.finditer(rf'(?m)^ {{{level_of(body)}}}([A-Za-z0-9_]+)\s*=\s*', body):
        found[match.group(1)] = read_value(body, match.end())
    return found


def field_value(block, key: str, sub_block: str = '') -> str:
    """The one match the field readers share: the value of `key` at the level `sub_block` names."""
    body = sub_block_body(block, sub_block) if sub_block else block.body
    match = re.search(rf'(?m)^ {{{level_of(body)}}}{re.escape(key)}\s*=\s*', body)
    return read_value(body, match.end()) if match else ''


def read_value(text: str, start: int) -> str:
    """One value read to its own close: the closing quote, the closing bracket, or the line end.

    A quote inside a container is skipped, and an escaped quote stops only at the closing quote, so
    a sub-block field or an escaped quote never answers for the block's field.
    """
    if start >= len(text):
        return ''
    open_char = text[start]
    if open_char not in '[{':
        end = text.find('\n', start)
        return text[start:end if end != -1 else len(text)].strip()
    close_char = ']' if open_char == '[' else '}'
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == '"':
            index += 1
            while index < len(text) and text[index] != '"':
                index += 2 if text[index] == '\\' else 1
            index += 1
            continue
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
        index += 1
    return text[start:]


def level_of(body: str) -> int:
    """The level the field readers read at: the smallest indent in the body (the one rule)."""
    indents = [len(line) - len(line.lstrip()) for line in body.split('\n') if line.strip()]
    return min(indents) if indents else 0


def unescape(value: str) -> str:
    """A quoted HCL string value, read back as the string it states.

    The generator writes the escape sequences HCL supports (`\\`, `\"`, `\\t`, `\\r`, `\\n`), and `json.dumps`
    writes the same ones, so the value in the block and the value in the id are the same string only after both
    are read back.
    """
    for escape, char in (('\\\\', '\\'), ('\\"', '"'), ('\\t', '\t'), ('\\r', '\r'), ('\\n', '\n')):
        value = value.replace(escape, char)
    return value
