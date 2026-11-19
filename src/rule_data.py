"""Epic 9 the rule as data: the declared row shape `RULE_ROW_FIELDS` and the two forms of the same rows.

A codebase separates the standard from the site (`docs/CODEBASE_ASSEMBLY.md` §9), and the tool's part is the data
a module consumes. For the four `*_policy_rules` types the single object iterates the rows, so the rule set is data
and the block is one `for_each` block per rule type per unit. The emitter change is Piece 19 and the write path is
Piece 18; this module owns the row shape, the chain grouping the single object reads, and the two forms.

Seven rules, stated once here. Every other rule is read through its owner, so no second rule appears.

1. **The row shape.** `RULE_ROW_FIELDS = ("directory", "resource", "entry", "key", "pivot", "properties")`.
   `directory` is the join to the manifest, the same join `OWNERSHIP.json` (F6.2), `REFERENCE_EDGES.json` (F6.3)
   and `SITE_DATA.json` (F6.6) use, read through `unit_manifest.directory_name`. `resource` names the coverage
   matrix row that covers the rule. `entry` is the entry name. `key` is the `for_each` key: the chain ordinal,
   zero-padded to four digits, joined by `_` to the identity digest. `pivot` is the entry name the rule is placed
   directly after, the empty string for the first rule of a chain. `properties` is the field set the matrix row
   names, sorted, read through the recorded object. `rulebase` is not declared: the parse records no rulebase fact,
   so no column can name a field the parse cannot capture (F3.5), and `docs/COVERAGE_MATRIX.md` §1 holds the honesty
   rule for every properties column. The column enters the shape when the live fact lands, not before.
2. **The key is the identity, not the name.** The key is `state_coverage.ownership_key` read with the facts as
   `unit_manifest.facts_of` reads them, so no second key rule exists, and the digest is `unit_manifest.identity_digest`
   on the facts part of that key, so no second digest rule exists. A name that repeats in two device groups, or in two
   virtual systems, is two entries, so `build_rows` states two rows with two digests. Because the digest is the unit
   identity digest, the key's digest half is the same digest `directory` names, and `parse_rows` refuses a row whose
   two halves disagree.
3. **The chain grouping is the F2.5 and F3.2 rule, stated once here.** Chains per (rule type, device group, vsys),
   `Shared` read through `unit_manifest.SHARED_UNIT` for the device group the parse cannot place, and `vsys1` for the
   virtual system the export declares none for. Document order within a chain, first-seen order across chains. The
   ordinal is the position in the chain, so the sorted key order is the XML order inside the chain, which is the apply
   order the single object needs. `TerraformGenerator._policy_rule_chains` reads the grouping here, so the group is
   stated once.
4. **Every properties column reads the field it names through the recorded object**, so the data file is an output and
   the honesty rule in `docs/COVERAGE_MATRIX.md` §1 holds for every column. `build_rows` reads every declared field
   through the recorded object, which records the read. A field the recorded object holds with no value prints no
   column, the way the per-entry report reads `entry_coverage.EMPTY_FIELD_VALUES`, and a field the parse never stored
   is a field held with no value.
5. **Two forms, one row set.** `render` prints the rows as JSON, which is the form a reader reads and the form the
   Terraform object reads. `render_csv` is the printed form of the same rows: the header in field order, one line per
   row in row order, every value as its JSON text, the same escape set `import_blocks.unescape` reads back. A printed
   form is not a reader input, so `parse_rows` reads the data and refuses the printed form. `data_file` names the file
   through the matrix row's `output_file`, as the `.json` form of it.
6. **No second rule and no writer.** The module states no naming rule (the §5 rule is taken as the `sanitize`
   argument for the rows, the way `unit_manifest.py` and `site_data.py` take it, and read through `naming.py` when a
   written name is read back), no unit rule, no identity key, no digest rule, no path, no console line, no
   environment name, and holds no writer of its own: `write_path.py` writes the file.
7. **No timestamp and no path**, so two runs on the same bytes write the same bytes, the byte rule the other data
   files share. `parse_rows` reads a written file back and refuses a row that is not the declared shape, the way
   `site_data.parse_rows` and `unit_manifest.parse_rows` do, including a `key` that is not the declared
   `ordinal_digest` shape and a `resource` that is not a matrix row.

Usage:
    from rule_data import RULE_ROW_FIELDS, build_rows, parse_rows, render, render_csv, data_file
    from write_path import unit_path, write_file
    import naming, rule_data

    rules = parser.parse_security_rules()
    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    name = rule_data.data_file("panos_security_policy_rules")
    directory = rows[0]["directory"]
    write_file(unit_path(output_dir, directory, name), rule_data.render(rows))
    write_file(unit_path(output_dir, directory, name.replace(".json", ".csv")), rule_data.render_csv(rows))
    for row in rule_data.parse_rows((output_dir / directory / name).read_text(encoding="utf-8")):
        print(row["entry"], row["key"])
"""

import csv
import io
import json

import entry_coverage
import naming
import state_coverage
import unit_manifest

# The row shape for the rule record. Fixed, so two runs write the same bytes and a reader does not
# guess. The name states the record it belongs to, because `src/` is one flat namespace (§1). `directory`
# is the manifest join; `resource`, `entry` and `key` are the identity; `key` and `pivot` are the chain facts.
RULE_ROW_FIELDS = ("directory", "resource", "entry", "key", "pivot", "properties")

# The `for_each` key shape, as rule 1 states it: the chain ordinal, zero-padded to four digits, joined by `_`
# to the digest `unit_manifest.DIGEST_HEX` states. A chain longer than 9,999 rules prints a longer ordinal, so
# the reader accepts at least this many digits, and `parse_rows` refuses a key that is not the declared shape.
ORDINAL_WIDTH = 4

# The data file is the `.json` form of the matrix row's `output_file`, which `resource_mapping` owns. This module
# states no second file-name rule: the name comes from the row, and the printed form is the same name with the
# `.csv` suffix, which `data_file`'s reader names.
_JSON_SUFFIX = ".json"

# A property value is what the recorded object can hold: a string, a boolean, a list, or a mapping. A PBF rule's
# `action` is a mapping, so the shape cannot declare only strings. A number is not a value the rule parse stores,
# so a file that states one is refused, and so is no value, because a field with no value prints no column.
_CAPTURED_SCALARS = (str, bool)


def data_file(resource_type: str) -> str:
    """The data file name for one rule type: the `.json` form of the matrix row's `output_file` (rule 5)."""
    output_file = entry_coverage.MATRIX_BY_RESOURCE[resource_type]["output_file"]
    return output_file[: -len(".tf")] + _JSON_SUFFIX


def chains(rules: list) -> list:
    """The chain grouping the single object reads (F2.5, F3.2), stated once here.

    One pass over the rules in document order, so the group is the order the export lists them. A rule is placed
    directly after the rule before it, and the first rule of a chain anchors at the end of the rulebase, so the pivot
    is the entry before it, or the empty string for the first rule of a chain. The `Shared` name is read through its
    owner; the `vsys1` name is the default this rule needs for a rule the export does not place in a virtual system,
    which is the fact the chain groups by and not the parse's honest scope (F3.5).
    """
    grouped: dict[tuple[str, str], list] = {}
    for rule in rules:
        key = (rule.get("device_group") or unit_manifest.SHARED_UNIT, rule.get("vsys") or "vsys1")
        grouped.setdefault(key, []).append(rule)
    return list(grouped.values())


def identity_key(resource_type: str, entry: str, facts: tuple) -> str:
    """The key's identity part, read through the one key rule and the one digest rule (rule 2).

    `state_coverage.ownership_key` is the one place that answers an identity key, and `unit_manifest.identity_digest`
    is the one place that answers a digest, so this function states neither. The facts are `unit_manifest.facts_of`'s
    tuple, which already holds the parse-fallback rule, so the `Shared` value cannot enter a digest here. The part of
    the key the digest rule hashes is its facts tail, so the digest is the same digest the manifest join names.
    """
    key = state_coverage.ownership_key(resource_type, entry, dict(zip(unit_manifest.FACT_KEYS, facts, strict=True)))
    return unit_manifest.identity_digest(key[len((resource_type, entry)) :])


def build_rows(resource_type: str, rules: list, sanitize) -> list:
    """One row per rule, in chain order, reading every field through its owner (rules 1 to 4).

    `rules` is the list the parse method returned, so each is the recorded object that records the fields this output
    reads (rule 4). `sanitize` is the §5 rule read through `naming.py`, taken as an argument so this module states no
    naming rule. The properties are the matrix row's fields, in sorted order, read through the recorded object, minus
    the fields it holds with no value, so `parse_rows` cannot be handed a property the row did not name: a field the
    parse did not store is a field held with no value, and prints no column.

    The row order is the chain order (rule 3), so the key's ordinal is the position in the chain and the sorted key
    order is the XML order inside the chain. `pivot` names the entry the rule is placed after, the empty string for
    the first rule of a chain.
    """
    matrix_row = entry_coverage.MATRIX_BY_RESOURCE[resource_type]
    rows = []
    for chain in chains(rules):
        previous_entry = ""
        for position, rule in enumerate(chain, 1):
            facts = unit_manifest.facts_of(rule)
            entry = rule.get("name") or ""
            properties = {}
            for field in sorted(matrix_row["properties"]):
                value = rule.get(field)
                if value not in entry_coverage.EMPTY_FIELD_VALUES:
                    properties[field] = value
            row = dict.fromkeys(RULE_ROW_FIELDS, "")
            row["directory"] = unit_manifest.directory_name(facts, sanitize)
            row["resource"] = resource_type
            row["entry"] = entry
            row["key"] = f"{position:0{ORDINAL_WIDTH}d}_{identity_key(resource_type, entry, facts)}"
            row["pivot"] = previous_entry
            row["properties"] = properties
            previous_entry = entry
            rows.append(row)
    return rows


def render(rows: list) -> str:
    """The rule data as text: the rows in field order, with one trailing newline."""
    return json.dumps([{key: row[key] for key in RULE_ROW_FIELDS} for row in rows], indent=2) + "\n"


def render_csv(rows: list) -> str:
    """The printed form of the same rows (rule 5): the header, then one line per row, every value as JSON text.

    Every value prints as `json.dumps(value, ensure_ascii=True)`, the same escape set `import_blocks.unescape` reads
    back, so no second escape rule appears. `csv` quotes a field that holds the delimiter, so a description with a
    comma stays one field. This is the printed form, not the reader input: `parse_rows` reads the data and refuses
    this form.
    """
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(RULE_ROW_FIELDS)
    for row in rows:
        writer.writerow([json.dumps(row[key], ensure_ascii=True) for key in RULE_ROW_FIELDS])
    return stream.getvalue()


def parse_rows(text: str) -> list:
    """Read a written rule data file back as data, in the order the file states the rows.

    A row that is not the declared shape is a refusal: the record is data, so a reader cannot fall back to reading
    prose. The printed form is refused as well, because a printed form is not a reader input (rule 5). A `key` that
    is not the declared `ordinal_digest` shape, a `resource` that is not a matrix row, a `properties` field the row
    does not name, a value that is not something the recorded object can hold, and a key half that disagrees with the
    row's own directory half are all refusals.
    """
    if text.split("\n", 1)[0] == ",".join(RULE_ROW_FIELDS):
        raise ValueError("the printed CSV is not the reader input, which is the data form")
    document = json.loads(text)
    if not isinstance(document, list):
        raise ValueError("the rule data is not a list of rows")
    rows = []
    for row in document:
        if not isinstance(row, dict):
            raise ValueError(f"not a rule row: {row!r}")
        extra = [key for key in row if key not in RULE_ROW_FIELDS]
        if extra:
            raise ValueError(f"not a declared rule field: {extra}")
        missing = [key for key in RULE_ROW_FIELDS if key not in row]
        if missing:
            raise ValueError(f"the row does not state its fields: {missing}")
        if not isinstance(row["entry"], str) or not row["entry"]:
            raise ValueError(f"entry is not a name: {row}")
        if row["resource"] not in entry_coverage.MATRIX_BY_RESOURCE:
            raise ValueError(f"resource is not a matrix row: {row}")
        if not isinstance(row["pivot"], str):
            raise ValueError(f"pivot is not a name: {row}")
        # The digest is the last segment, because a sanitized unit name holds underscores of its own.
        if not isinstance(row["directory"], str) or not row["directory"]:
            raise ValueError(f"directory is not a unit name: {row}")
        halves = row["directory"].rsplit("_", 1)
        if len(halves) != 2:
            raise ValueError(f"directory is not the §5 shape of a unit with its digest: {row}")
        name, digest = halves
        if not name or name != naming.sanitize(name) or len(digest) != unit_manifest.DIGEST_HEX:
            raise ValueError(f"directory is not the §5 shape of a unit with its digest: {row}")
        ordinal, _, key_digest = row["key"].partition("_")
        if len(ordinal) < ORDINAL_WIDTH or not ordinal.isdigit():
            raise ValueError(f"key is not the declared ordinal_digest shape: {row}")
        if len(key_digest) != unit_manifest.DIGEST_HEX:
            raise ValueError(f"key is not the declared ordinal_digest shape: {row}")
        if key_digest != digest:
            raise ValueError(f"the key half is not the row's own unit digest: {row}")
        if not isinstance(row["properties"], dict):
            raise ValueError(f"properties is not a mapping of fields to values: {row}")
        named = entry_coverage.MATRIX_BY_RESOURCE[row["resource"]]["properties"]
        for field, value in row["properties"].items():
            if field not in named:
                raise ValueError(f"properties names a field the row does not: {field}")
            if not _json_value(value):
                raise ValueError(f"a rule property is not something the recorded object can hold: {row}")
        rows.append({key: row[key] for key in RULE_ROW_FIELDS})
    return rows


def _json_value(value) -> bool:
    """A property value as the recorded object holds it, and as JSON reads it back (rule 4)."""
    if isinstance(value, _CAPTURED_SCALARS):
        return True
    if isinstance(value, list):
        return all(_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(field, str) and _json_value(item) for field, item in value.items())
    return False
