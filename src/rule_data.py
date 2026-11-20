"""Epic 9 the rule as data: the declared row shape `RULE_ROW_FIELDS` and the two forms of the same rows.

A codebase separates the standard from the site (`docs/CODEBASE_ASSEMBLY.md` §9), and the tool's part is the data
a module consumes. For the four `*_policy_rules` types the single object iterates the rows, so the rule set is data
and the block is one `for_each` block per rule type per unit. The write path landed in Piece 18 and the emitter change
is Piece 19; this module owns the row shape, the two file names, the chain grouping the single object reads, and the
two forms, and the run writes the pair through `write_path.py`.

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
5. **Three forms, one row set.** `render` prints the rows as JSON, which is the form a reader reads and the form the
   Terraform object reads. `render_csv` is the printed form of the same rows: the header in field order, one line per
   row in row order, every value as its JSON text, the same escape set `import_blocks.unescape` reads back. A printed
   form is not a reader input, so `parse_rows` reads the data and refuses the printed form. `data_file` names the file
   through the matrix row's `output_file`, as the `.json` form of it, and `printed_file` names the printed form
   through the same row, as the same stem with the `.csv` suffix, and `locals_name` names the third form of the same
   rows through the same row: the map the `.tf` file prints, as the same stem with no suffix, which is also the name
   of the block that reads it. Both files are unit-set files
   (`docs/CODEBASE_ASSEMBLY.md` §14), so the run writes one pair per rule type inside the unit directory the
   `directory` column names, and writes it only when that unit has rows: the rows of one rule type are the rows of
   one unit, because the chain grouping keys on the device group and the virtual system, which are two of the five
   unit facts, so the file holds that unit's rows and names its unit only by its directory.
    `printed_entries` reads the entries the `.tf` file prints for one rule type: the key, and the text the file
    prints for its values. It is the part of the printed map this module owns, so the gate reads the printed map
    through here and states no reader of its own, and reads no value from the text it is handed, because reading a
    value is the gate's one field reader's job and a shape rule stays in `parse_rows`. The three tables the printed
    form reads are stated here, so the emitter, the gate's block rule and the matrix test read one table.
6. **No second rule and no writer.** The module states no naming rule (the §5 rule is taken as the `sanitize`
   argument for the rows, the way `unit_manifest.py` and `site_data.py` take it, and read through `naming.py` when a
   written name is read back), no unit rule, no identity key, no digest rule, no path, no console line, no
   environment name, and holds no writer of its own: `write_path.py` is the writer, one pair per rule type per
   unit, and the run writes a pair only when that unit has rows.
7. **No timestamp and no path**, so two runs on the same bytes write the same bytes, the byte rule the other data
   files share. `parse_rows` reads a written file back and refuses a row that is not the declared shape, the way
   `site_data.parse_rows` and `unit_manifest.parse_rows` do, including a `key` that is not the declared
   `ordinal_digest` shape and a `resource` that is not a matrix row.

Usage:
    from rule_data import (
        RULE_ROW_FIELDS, build_rows, parse_rows, render, render_csv, data_file, printed_file, locals_name,
        printed_entries,
    )
    from write_path import unit_path, write_file
    import naming, rule_data

    rules = parser.parse_security_rules()
    rows = rule_data.build_rows("panos_security_policy_rules", rules, naming.sanitize)
    for directory in sorted({row["directory"] for row in rows}):
        unit_rows = [row for row in rows if row["directory"] == directory]
        data_name = rule_data.data_file("panos_security_policy_rules")
        printed_name = rule_data.printed_file("panos_security_policy_rules")
        map_name = rule_data.locals_name("panos_security_policy_rules")
        write_file(unit_path(output_dir, directory, data_name), rule_data.render(unit_rows))
        write_file(unit_path(output_dir, directory, printed_name), rule_data.render_csv(unit_rows))
        for row in rule_data.parse_rows((output_dir / directory / data_name).read_text(encoding="utf-8")):
            print(row["key"], map_name)
"""

import csv
import io
import json
import re

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

# The two file names are the two forms of the stem the matrix row's `output_file` names, which `resource_mapping`
# owns. This module states no second file-name rule: one stem, the two suffixes.
_JSON_SUFFIX = ".json"
_CSV_SUFFIX = ".csv"

# The printed map, as rule 5 states the third form: the map name on the `locals` line, then one entry per row
# keyed by the declared `ordinal_digest` shape, in the order the file prints the entries. The indent of the map and
# of its entries is read from the file, so a hand-written map reads as the same map the emitter printed. The gate
# reads the printed form through `printed_entries`, so no second reader for the map appears.
_PRINTED_MAP_RE = re.compile(r"(?m)^(\s*)locals \{\n(\s+)([a-z0-9_]+) = \{\n(.*?)\n\2\}", re.S)
# One entry of the printed map, from its key line to the line that closes it, at whatever indent the file states.
# The reader names the entry and hands the text over, so the gate's one field reader reads the values inside it and
# this module reads no value of its own. The indent is captured and back-referenced so a hand-written entry with a
# different indent reads as the same entry the emitter printed.
_PRINTED_ENTRY_RE = re.compile(r'(?m)^(\s+)"([^"]+)" = \{\n(.*?)\n\1\}', re.S)

# A property value is what the recorded object can hold: a string, a boolean, a list, or a mapping. A PBF rule's
# `action` is a mapping, so the shape cannot declare only strings. A number is not a value the rule parse stores,
# so a file that states one is refused, and so is no value, because a field with no value prints no column.
_CAPTURED_SCALARS = (str, bool)


# The three tables the printed form reads, stated once here so the emitter, the gate, and the matrix test read one
# table. `RULE_ENTRY_FIELDS` is the mapping from a row field to the pair the printed entry states for it: the name
# the provider declares, and the shape word the value prints as (`SHAPE_WORDS`, read through `SHAPE_TO_SCHEMA`). The
# entry is the only place the provider's declared shape can be honoured, because the block body prints a reference
# and `terraform validate` cannot type-check `each.value.<field>`: the shape word is the provider's declared type,
# measured from the pinned provider schema on 2026-11-19. `RULE_ENTRY_READERS` names the reader for a field whose
# provider object key is the value the row records, because a block body prints a reference and cannot name an object
# key from a value, so the gate compares such a field by the shape word the table states and not by content.
# `RULE_BODY_DEFAULTS` states the one provider field the parse records no value for, so the block body prints a value
# for it and not a reference. Every field order these tables read is the matrix row's `properties` order, so this
# module states no field list of its own.
RULE_ENTRY_FIELDS = {
    "panos_security_policy_rules": {
        "name": ("name", "string"),
        "action": ("action", "string"),
        "applications": ("applications", "string_list"),
        "description": ("description", "string"),
        "destination_addresses": ("destination_addresses", "string_list"),
        "destination_zones": ("destination_zones", "string_list"),
        "disabled": ("disabled", "bool"),
        "log_end": ("log_end", "bool"),
        "log_start": ("log_start", "bool"),
        # F4.4: the parsed-object key the emitter reads for the profile group reference, printed as the object
        # `profile_setting.group`.
        "profile_group": ("profile_setting", "object"),
        "services": ("services", "string_list"),
        "source_addresses": ("source_addresses", "string_list"),
        "source_zones": ("source_zones", "string_list"),
    },
    "panos_nat_policy_rules": {
        "name": ("name", "string"),
        "description": ("description", "string"),
        "destination_addresses": ("destination_addresses", "string_list"),
        # The two columns that build one provider object state one entry field: the address column names the object
        # and the port column names the field inside it.
        "destination_translation_address": ("destination_translation", "object"),
        "destination_translation_port": ("destination_translation", "number"),
        # The one row field the parse records as one value and the provider takes as a list, through `_get_text`.
        "destination_zone": ("destination_zone", "string_list"),
        "disabled": ("disabled", "bool"),
        # F4.4: the provider takes one name here, so a member list cannot print as the field.
        "service": ("service", "string"),
        "source_addresses": ("source_addresses", "string_list"),
        "source_translation_address": ("source_translation", "object"),
        "source_translation_type": ("source_translation", "one_of"),
        "source_zones": ("source_zones", "string_list"),
    },
    "panos_decryption_policy_rules": {
        "name": ("name", "string"),
        "action": ("action", "string"),
        "categories": ("category", "string_list"),
        "description": ("description", "string"),
        "destination_addresses": ("destination_addresses", "string_list"),
        "destination_zones": ("destination_zones", "string_list"),
        "disabled": ("disabled", "bool"),
        "log_end": ("log_fail", "bool"),
        "log_setting": ("log_setting", "string"),
        "log_start": ("log_success", "bool"),
        "profile": ("profile", "string"),
        "services": ("services", "string_list"),
        "source_addresses": ("source_addresses", "string_list"),
        "source_users": ("source_user", "string_list"),
        "source_zones": ("source_zones", "string_list"),
        "type": ("type", "one_of"),
    },
    "panos_pbf_policy_rules": {
        "name": ("name", "string"),
        "action": ("action", "one_of"),
        "applications": ("applications", "string_list"),
        "description": ("description", "string"),
        "destination_addresses": ("destination_addresses", "string_list"),
        "disabled": ("disabled", "bool"),
        # The provider declares the fact as an object with one `enabled` field (F2.9).
        "enforce_symmetric_return": ("enforce_symmetric_return", "object"),
        "schedule": ("schedule", "string"),
        "services": ("services", "string_list"),
        "source_addresses": ("source_addresses", "string_list"),
        "source_users": ("source_users", "string_list"),
        # v2 models the PBF source as `from { zone = [...] }` (F2.9).
        "source_zones": ("from", "object"),
    },
}

# The reader a field is built by, when the provider's object key is the value the row records. `RULE_ENTRY_FIELDS`
# names the shape word, so the reader names the field that cannot be read as one row value, and the gate compares
# such a field by its shape word. The names are the emitter's methods, read at the print site.
RULE_ENTRY_READERS = {
    "panos_security_policy_rules": {"profile_group": "_profile_setting"},
    "panos_nat_policy_rules": {
        "source_translation_address": "_nat_translation",
        "destination_translation_address": "_destination_translation",
    },
    "panos_decryption_policy_rules": {"action": "_decryption_action", "type": "_decryption_type"},
    "panos_pbf_policy_rules": {
        "source_zones": "_pbf_from",
        "action": "_pbf_action",
        "enforce_symmetric_return": "_pbf_enforce_symmetric_return",
    },
}

# The NAT family is the one provider field the parse records no value for (F3.5), so no row column names it and the
# block states the default word the export implies. IPv4 is the Panorama default family.
RULE_BODY_DEFAULTS = {"panos_nat_policy_rules": ("nat_type", "ipv4")}


def _file_stem(resource_type: str) -> str:
    """The stem the matrix row names for one rule type (rule 5): `output_file` without its `.tf` suffix.

    Both file names are this stem with one of the two suffixes, so the module states one file-name rule and not two.
    """
    return entry_coverage.MATRIX_BY_RESOURCE[resource_type]["output_file"][: -len(".tf")]


def data_file(resource_type: str) -> str:
    """The data file name for one rule type: the `.json` form of the matrix row's `output_file` (rule 5)."""
    return _file_stem(resource_type) + _JSON_SUFFIX


def printed_file(resource_type: str) -> str:
    """The printed form's name for one rule type: the same stem with the `.csv` suffix (rule 5)."""
    return _file_stem(resource_type) + _CSV_SUFFIX


def locals_name(resource_type: str) -> str:
    """The `locals` map name for one rule type, and the name of the block that reads it: the same stem (rule 5).

    The map is the third form of the row set, the form the `.tf` file prints, so the block, the map, the `.json`
    form and the `.csv` form read one name and no second naming rule appears.
    """
    return _file_stem(resource_type)


def printed_entries(text: str, resource_type: str) -> list:
    """One row as the `.tf` file prints it: the key, and the text the file prints for its values (rule 5).

    One answer per entry, in the order the file prints the entries, which is the sorted key order. A key that is not
    the declared `ordinal_digest` shape is no answer, the way `parse_rows` refuses it. The module names the entry and
    hands over its text without reading a value from it: reading a value is the gate's one field reader's job, so a
    shape rule stays in `parse_rows` and no second reader for the map appears. The map name is read through
    `locals_name`, so the block name, the map name and the two file names are one name.
    """
    map_name = locals_name(resource_type)
    answer = []
    for match in _PRINTED_MAP_RE.finditer(text):
        if match.group(3) != map_name:
            continue
        for _indent, key, entry in _PRINTED_ENTRY_RE.findall(match.group(4)):
            ordinal, _, digest = key.partition("_")
            if len(ordinal) >= ORDINAL_WIDTH and ordinal.isdigit() and len(digest) == unit_manifest.DIGEST_HEX:
                answer.append({"key": key, "entry": entry})
    return answer


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
