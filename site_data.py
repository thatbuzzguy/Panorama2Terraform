"""F6.6 the site data layer: one row per site as `SITE_DATA.json`, and the `.tfvars` written from it.

A codebase separates the standard from the site (`docs/CODEBASE_ASSEMBLY.md` §9). Six rules, stated once
here.

1. **One file per codebase run, one row per site.** F6.1 rule 4 still refuses a per-unit file, because this
   feature writes no directory: a per-site file would sit outside the shape it names. A site is a unit (the
   device group and the template the export joins through one device), so the row joins to
   `CODEBASE_MANIFEST.json` on `directory` — the same join `OWNERSHIP.json` (F6.2) and `REFERENCE_EDGES.json`
   (F6.3) use. No second unit rule appears here: the identity and the directory name are read through
   `unit_manifest.facts_of` and `unit_manifest.directory_name`.
2. **A row is written for a site that names a value**, following the rule that a file is written only when it
   has content. A unit that names no value writes no row, and a run that names no value writes no file.
   `localhost.localdomain` names no device (F3.5), so it names no value and no variable.
3. **The row shape.** `directory` is the join; `variables` is `{the variable name: the value}`, sorted by
   name. For a string value the name is the value read through the §5 rule (`naming.py`), so the row states no
   value twice: the value is the fact and the name is the mapping result. `parse_rows` reads a written file
   back and refuses a row that is not the declared shape, the way `unit_manifest.parse_rows` does, including a
   variable name that is not the §5 shape of its string value.
4. **The `.tfvars` is written from the data**, not from the generator's state: the data is the fact and the
   `.tfvars` is its printed form. The file is `site.auto.tfvars`, because Terraform loads
   `*.auto.tfvars` automatically and keeps `terraform.tfvars` as the operator's own file for the credentials,
   which the tool never writes (§11). One line per variable, in name order across the whole file,
   and one line for a name two rows state, because one value cannot produce two names. A name two
   rows state with two different values is a refusal, because the file cannot print one line for it
   twice.
5. **How a value prints.** A string prints as `json.dumps(value)`, the same escape set `import_blocks.unescape`
   reads back, so no second escape rule appears. A list prints inline as `[ "a", "b" ]`, with each item through
   the same rule. A value that is neither a string nor a list of strings is a refusal, because the row shape
   declares no other kind. No table row maps a field to a list today, so a corpus run writes only strings; the
   writer prints a list because the row shape declares one.
6. **No timestamp and no path**, so two runs on the same bytes write the same bytes. The file is a data file,
   so the gate reads no data file (`ARCHITECTURE.md` §4.5) and no report names a field this module states.

Usage:
    from site_data import ROW_FIELDS, SITE_DATA_FILE, TFVARS_FILE, build_rows, parse_rows, render, render_tfvars
    rows = build_rows(ledger, generator.value_variables(), generator.sanitize_name)
    (output_dir / SITE_DATA_FILE).write_text(render(rows), encoding='utf-8')
    (output_dir / TFVARS_FILE).write_text(render_tfvars(rows), encoding='utf-8')
    for row in parse_rows((output_dir / SITE_DATA_FILE).read_text(encoding='utf-8')):
        print(row['directory'], row['variables'])
"""

import json

import naming
import unit_manifest

SITE_DATA_FILE = 'SITE_DATA.json'

# Terraform loads a `*.auto.tfvars` file automatically, so the generated values do not sit in the
# file the operator owns.
TFVARS_FILE = 'site.auto.tfvars'

# The row shape. Fixed, so two runs write the same bytes and a reader does not guess.
# `directory` is the join to the manifest row; `variables` is the mapping result.
ROW_FIELDS = ('directory', 'variables')

TFVARS_HEADER = ('# Site values (F6.6), written from ' + SITE_DATA_FILE + '. Terraform loads a\n'
                 '# *.auto.tfvars file automatically, so this file holds the site values and\n'
                 '# terraform.tfvars stays the operator\'s file for the credentials. Set the values\n'
                 '# here, or with TF_VAR_<name>.\n\n')


def build_rows(ledger, recorded: dict, sanitize) -> list:
    """One row per site the ledger shows and the mapping recorded a value for, in identity order.

    `recorded` is the pairs the emitter recorded at the site that applied the value-to-variable table,
    keyed by the unit's four scope facts. This module resolves no name and names no value the run did
    not print, so the `.tfvars` cannot state a value no `.tf` file consumes.
    """
    units = {unit_manifest.facts_of(entry) for entry in ledger.rows()}
    rows = []
    for facts in sorted(units):
        variables = recorded.get(facts) or {}
        if not variables:
            # A site that names no value writes no row.
            continue
        row = dict.fromkeys(ROW_FIELDS, '')
        row['directory'] = unit_manifest.directory_name(facts, sanitize)
        row['variables'] = {name: variables[name] for name in sorted(variables)}
        rows.append(row)
    return rows


def render(rows: list) -> str:
    """The site data as text: the rows in field order, with one trailing newline."""
    return json.dumps([{key: row[key] for key in ROW_FIELDS} for row in rows], indent=2) + '\n'


def parse_rows(text: str) -> list:
    """Read a written site data file back as data, in the order the file states the rows.

    A row that is not the declared shape is a refusal: the record is data, so a reader cannot fall back
    to reading prose. A variable name that is not the §5 shape of its value is refused too, because the
    name is the mapping result and not a free choice.
    """
    document = json.loads(text)
    if not isinstance(document, list):
        raise ValueError('the site data is not a list of rows')
    rows = []
    for row in document:
        if not isinstance(row, dict):
            raise ValueError(f'not a site row: {row!r}')
        extra = [key for key in row if key not in ROW_FIELDS]
        if extra:
            raise ValueError(f'not a declared site field: {extra}')
        missing = [key for key in ROW_FIELDS if key not in row]
        if missing:
            raise ValueError(f'the row does not state its fields: {missing}')
        if not isinstance(row['directory'], str) or not row['directory']:
            raise ValueError(f'directory is not a unit name: {row}')
        if not isinstance(row['variables'], dict):
            raise ValueError(f'variables is not a mapping of names to values: {row}')
        for name, value in row['variables'].items():
            if not isinstance(name, str) or not name:
                raise ValueError(f'a variable name is not a name: {row}')
            if not isinstance(value, (str, list)):
                raise ValueError(f'a site value is not a string or a list: {row}')
            if isinstance(value, list) and not all(isinstance(item, str) for item in value):
                raise ValueError(f'a site list holds a value that is not a string: {row}')
            if isinstance(value, str) and name != naming.variable_name(value):
                raise ValueError(f'the variable name is not the §5 shape of its value: {row}')
        rows.append({key: row[key] for key in ROW_FIELDS})
    return rows


def value_text(value) -> str:
    """One `.tfvars` value, printed as the row declares it (rule 5)."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f'a site list holds a value that is not a string: {value!r}')
        if not value:
            return '[]'
        return '[ ' + ', '.join(json.dumps(item, ensure_ascii=True) for item in value) + ' ]'
    raise ValueError(f'not a declared site value kind: {value!r}')


def render_tfvars(rows: list) -> str:
    """The `.tfvars` the tool writes from the data: one line per variable, in name order.

    A name two rows state prints one line, because the name is the §5 shape of the value, so one value
    cannot produce two names. If two rows state one name with two different values the file cannot
    print one line for it, so the writer refuses. No line states a timestamp or a path.
    """
    values: dict[str, object] = {}
    for row in rows:
        for name, value in row['variables'].items():
            if name in values and values[name] != value:
                raise ValueError(f'name {name} states two values: {values[name]!r} and {value!r}')
            values[name] = value
    lines = [TFVARS_HEADER]
    for name in sorted(values):
        lines.append(f'{name} = {value_text(values[name])}\n')
    return ''.join(lines)
