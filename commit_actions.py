"""F6.7 the action block per unit, as `actions.tf`: the commit action, and the push action F6.10.4 adds.

The provider declares two actions (2.0.14, `docs/CODEBASE_ASSEMBLY.md` §12), and both name one device group,
one template, or one template stack, so an action stays inside one unit. `panos_commit` is the commit path,
because the Terraform language has no native commit support; `panos_push_to_devices` is the push path. Six rules, stated
once here.

1. **One block per unit, one file per unit.** One block per manifest row and per action the pinned schema
   declares, in the identity order the manifest rows already print. `actions.tf` is a `.tf` file, so the gate
   rule (`sanity_checks.check_actions`) reads it, and it is written only when it has content, following the
   rule for the report files and the four data files. Emission is default, not a flag: the committed goldens
   pin what a default run emits, so a shape written only when a flag is on cannot be pinned
   (the F6.5 rule 1 argument). The file is the last `.tf` file of its unit, so the reader reads the action
   against the completed unit.
2. **The action names the fact its own unit declares, and no fact another unit owns.** The fact is the
   one `unit_manifest.named_fact` selects for the row, and the block states it only when the provider
   can name it for that fact: the device group, the template, the template stack, which are the facts
   `SCOPE_ANSWER` answers. A `vsys` or a `vsys_device` fact names no filter and no push type, so a unit whose
   selected fact is one of those writes no action, and the platform commits and pushes it through the parent
   unit. The shared unit names no fact, so it writes no action: a commit that names no filter commits the
   whole config, not a unit. A fact the row declares but an ancestor unit owns is not the unit's own fact, so
   the action states one fact: the one its row selects.
3. **The address names the identity the block states.** The local name is the §5 rule in `naming.py`
   (taken as an argument, so no second naming rule exists) applied to the fact the block states, plus
   the identity digest of the identity as the block states it: the fact in its `FACT_KEYS` position and
   every other fact empty. So the block is data the gate can read back on its own, the join to the
   manifest is the fact the block states, and a block that states two facts cannot agree with its own
   address. `tests/test_commit_actions.py` pins that no module defines a second naming rule.
4. **The field mapping and the answer are one table each.** `resource_mapping.ACTION_FILTERS` maps the
   `action` field to the scope fact it names, and `resource_mapping.SCOPE_ANSWER` answers the name
   inside; the `name` field of a push shape names the fact its `type` states. The emitter reads the
   tables through `filter_field` and `block_fields`, and the gate reads them through `field_fact`, so no
   branch names a field again. `PLACEHOLDER_DEVICE` names no firewall (F3.5), so it never enters a filter and
   never selects a fact.
5. **Shape, order, and bytes.** One name per block, so one block names one unit. Fields print inside
   `config`, the level the Terraform action grammar needs for 1.14 (measured: `terraform validate`
   refuses a field at the action's own level), in the declared order, and rows print in the identity
   order the manifest rows print; within one unit the blocks print in the `ACTION_SCHEMA` order, which is the
   order a push follows a commit. A quoted value prints with the same escape set
   `import_blocks.unescape` reads back, and no field states a timestamp or a path. `read_block` reads a
   written block back as a row through the one block reader, the way `import_blocks.read_block` does.
6. **The push block names no serial.** `devices` is an optional list of NGFW serials, and the tool names no
   serial (`resource_mapping.VALUE_VARIABLES`, F6.10.4), so the block prints no `devices` and the provider
   pushes to all devices in the target, which is the documented default. So the push half no longer needs the
   serial fact F6.7 held it for. The commit block and the push block for one unit name the same fact, so
   rule 3 gives them the same address, and the action type is the only difference: the action address is
   `action.<type>.<label>`, so the language reads them as two blocks.

Usage:
    from commit_actions import ACTIONS_FILE, ROW_FIELDS, build_rows, render, read_block
    from write_path import root_path, unit_path, write_file
    rows = build_rows(manifest_rows, naming.sanitize)
    write_file(unit_path(output_dir, directory, ACTIONS_FILE), render(rows))
    for shape in [read_block(block) for block in sanity_checks.blocks(files, ('action',))]:
        print(shape['fact'], shape['entry_name'])
"""

import json

import container_coverage
import import_blocks
import resource_mapping
import unit_manifest

ACTIONS_FILE = 'actions.tf'

# The block level an action's fields live at. Terraform 1.14 requires it: `terraform validate` refuses
# a field at the action's own level, so the shape is a grammar fact and not a style choice.
CONFIG_BLOCK = 'config'

# The row shape. Fixed, so two runs write the same bytes and a reader does not guess.
# `action` is the `ACTION_SCHEMA` row the block is, `fact` is the scope fact the block names, `field` is the
# field that states it (`ACTION_FILTERS`), `entry_name` is the fact name, `local_name` is the §5 name plus the
# digest (rule 3), and `directory` is the manifest join, not a block field.
ROW_FIELDS = ('directory', 'action', 'fact', 'field', 'entry_name', 'local_name')

# The field a push shape uses for the fact key. `ACTION_FILTERS` states the relation (`name` names the fact its
# `type` states), so this names the field that carries the key, and `block_fields` and `field_fact` are the two
# readers of that one relation.
FACT_KEY_FIELD = 'type'


def filter_field(fact: str, action: str = '') -> str:
    """The `action` field that names `fact`, read through `ACTION_FILTERS`, the one mapping.

    With no action the caller means the commit shape, which states the fact through its filter field. For an
    action row the field must be one that row declares, and the push shape is the row whose mapping names the
    fact key instead of a fact, so `name` is the field that states the fact. A fact `SCOPE_ANSWER` does not
    answer names no field, the same rule the gate reads.
    """
    declared = resource_mapping.ACTION_SCHEMA.get(action, ((), {}))[1]
    for field, mapped in resource_mapping.ACTION_FILTERS.items():
        if action and field not in declared:
            continue
        if mapped == fact or (mapped == FACT_KEY_FIELD and resource_mapping.SCOPE_ANSWER.get(fact)):
            return field
    return ''


def block_fields(action: str, fact: str, entry_name: str) -> dict:
    """The fields one `ACTION_SCHEMA` row prints for one fact, in the order the row declares them.

    The field `filter_field` gives prints the fact name. The push shape also prints the field the mapping
    names for the fact key, which carries the fact key itself. So the emitter prints the same two tables the
    gate reads, and a fact the answer does not answer prints no field.
    """
    name_field = filter_field(fact, action)
    if not name_field:
        return {}
    required, declared = resource_mapping.ACTION_SCHEMA[action]
    fields = {name_field: entry_name}
    if FACT_KEY_FIELD in declared:
        fields[FACT_KEY_FIELD] = fact
    order = [field for field in required if field in fields] or sorted(fields)
    return {field: fields[field] for field in order}


def field_text(action: str, field: str, value: str) -> str:
    """One field value as the row declares it, with the escape set `import_blocks.unescape` reads back."""
    shape = resource_mapping.ACTION_SCHEMA[action][1][field]
    return f'[{json.dumps(value)}]' if shape == 'string_list' else json.dumps(value)


def field_fact(block, field: str) -> str:
    """The fact an `action` field names, read through `ACTION_FILTERS`, the one mapping.

    A filter field names its fact. The `name` field names the fact its `type` value states, which is a
    fact key (the push shape), and the value is read through the one field reader so a quoted value is
    read as the string it states. A field outside the mapping names no fact, so `check_actions` reports
    it as a field the row does not declare, or the block states no fact.
    """
    mapped = resource_mapping.ACTION_FILTERS.get(field, '')
    if mapped in unit_manifest.FACT_KEYS:
        return mapped
    value = import_blocks.block_value(block, mapped, CONFIG_BLOCK)
    return value if value in unit_manifest.FACT_KEYS else ''


def placed_identity(fact: str, entry_name: str) -> tuple:
    """The identity as the block states it: one fact in its `FACT_KEYS` position, the rest empty."""
    return tuple(entry_name if key == fact else '' for key in unit_manifest.FACT_KEYS)


def local_name(fact: str, entry_name: str, sanitize) -> str:
    """The block address for one name, through the §5 rule and the manifest digest (rule 3)."""
    return f'{sanitize(entry_name)}_{unit_manifest.identity_digest(placed_identity(fact, entry_name))}'


def build_rows(manifest_rows: list, sanitize) -> list:
    """One row per unit the manifest names and per action the pinned schema declares, in the identity order
    the rows already print.

    A unit whose selected fact `SCOPE_ANSWER` does not answer (a vsys unit, a device unit, or the shared unit)
    writes no row, so the run writes no block for a unit an action cannot name, and an action never states a
    fact an ancestor unit owns.
    """
    rows = []
    for manifest_row in manifest_rows:
        facts = tuple(manifest_row[key] for key in unit_manifest.FACT_KEYS)
        key, name = unit_manifest.named_fact(facts)
        if key == '' or name == container_coverage.PLACEHOLDER_DEVICE:
            continue
        for action in resource_mapping.ACTION_SCHEMA:
            if not block_fields(action, key, name):
                continue
            shape = dict.fromkeys(ROW_FIELDS, '')
            shape['directory'] = manifest_row['directory']
            shape['action'] = action
            shape['fact'] = key
            shape['field'] = filter_field(key, action)
            shape['entry_name'] = name
            shape['local_name'] = local_name(key, name, sanitize)
            rows.append(shape)
    return rows


def render(rows: list) -> str:
    """The action file as text: one block per row, in the order a reader can reproduce.

    The order is the identity order the manifest rows print: the identity as the block states it, sorted in the
    `FACT_KEYS` order, then the `ACTION_SCHEMA` order inside one unit, so a reader reproduces it from the block
    text alone.
    """
    lines = ['# Commit and push actions (F6.7, F6.10.4): one block per action the pinned schema declares, for\n'
            '# each unit the manifest names. The block names the fact its own unit declares, and no fact\n'
            '# another unit owns. The push block states no `devices`, because the tool names no serial, so\n'
            '# the provider pushes to all devices in the target.\n'
            '# Actions need Terraform 1.14 or later, which the `terraform` block declares (§12).\n\n']
    order = list(resource_mapping.ACTION_SCHEMA)
    for shape in sorted(rows, key=lambda row: (placed_identity(row['fact'], row['entry_name']),
                                               order.index(row['action']), row['local_name'])):
        fields = block_fields(shape['action'], shape['fact'], shape['entry_name'])
        body = ''.join(f'    {field} = {field_text(shape["action"], field, fields[field])}\n'
                       for field in fields)
        lines.append(f'action "{shape["action"]}" "{shape["local_name"]}" {{\n'
                     f'  {CONFIG_BLOCK} {{\n{body}  }}\n}}\n\n')
    return ''.join(lines)


def read_block(block) -> dict:
    """One written `action` block, read back as a row through the gate's one block reader.

    `unit` is not a block field, so `directory` is empty here the way it is in `import_blocks`; the
    reader resolves nothing, it states what the block states. A block that states more than one name is
    not the declared shape (rule 5), so it is a refusal, the way `decode_id` refuses a value that is not
    base64 JSON.
    """
    shape = dict.fromkeys(ROW_FIELDS, '')
    fields = import_blocks.fields(block, CONFIG_BLOCK)
    names = {}
    stated = ''
    for field in sorted(fields):
        fact = field_fact(block, field)
        if not fact:
            continue
        values = (import_blocks.block_list(block, field, CONFIG_BLOCK) if fields[field].startswith('[')
                  else (import_blocks.block_value(block, field, CONFIG_BLOCK),))
        if len(values) > 1:
            raise ValueError(f'the block states more than one name in {field}: {block}')
        if values and values[0]:
            names[fact] = values[0]
            stated = field
    if len(names) != 1:
        raise ValueError(f'the block does not state one fact: {names or "no field names a fact"}')
    fact, entry_name = next(iter(names.items()))
    shape['action'] = block.rtype
    shape['fact'] = fact
    # The reader states the field the block used, which is the field the fact key names for a push block
    # and the filter field names for a commit block.
    shape['field'] = stated
    shape['entry_name'] = entry_name
    shape['local_name'] = block.local
    return shape
