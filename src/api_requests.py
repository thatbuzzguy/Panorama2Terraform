"""F8.2 the scope index, and F8.3 the response-to-request join: the set of scopes path 2 reads, as one
entry per scope, and each response read against the request that made it.

Five rules, stated once here (`docs/API_CONVERSION_PATH.md` §2.2, §2.3, §2.4 and §3):

1. The scope set is read, not guessed. It comes from the membership responses the run read, through
   the four membership lists `parse_associations` reads (`docs/ARCHITECTURE.md` §3, rule 3). Two
   levels, no more: one entry per scope container the run read, then one entry per scope entry those
   containers name. A name a membership list read joins to the container that defines it, and the
   entry counts only when the run read the response for that container. So no scope is guessed, and
   no request is made for a scope the run did not read.

2. The set is read in sorted order, one entry per scope: the containers first, then the entries in
   path order. A name two lists read gives one entry, so the set does not depend on document order.

3. The join (`docs/API_CONVERSION_PATH.md` §2.3) reads one response against the index entry whose request
   made it, so it is checked and not assumed: the element the response holds is the element its own
   request names, read through `source_fetch.py`, and the entry name inside the response agrees with the
   index, which is what the join owns.

4. The join (`docs/API_CONVERSION_PATH.md` §2.4) reads one section against the response that holds its
   container, so the run's unit of parse stays one response: the line map, the parent walk, and the entry
   ledger are keyed on the source that was parsed, and a report position can only name a line inside the
   response that holds the entry. The join answers one response per section, so no section needs a tree
   built from many responses. The run order calls the parse method, which is the entry point's work, so
   this module keeps no parser and states no merge rule.

5. The unit join (`docs/API_CONVERSION_PATH.md` §3) reads the run's unit set through `unit_manifest.units`, so
   path 2 states no second unit rule. The fact path 2 adds is the scope the run read for a unit: each row names
   the response its entry came from, and the join matches that name to the index entry through the name rule in
   `source_fetch.py`. A unit the join answers no entry for, and an index entry the run read no rows for, are
   findings the join reports as data rows: no console line, no writer, no report section, and no exit code,
   which the gate decides.

The module reads no source and no membership of its own: `source_fetch.py` reads the bytes through
the input door, and `PanoramaParser.parse_associations` reads the four lists. What this module owns is the
join between a name a list read and the request that reads the scope it names, the join between a response
and the entry that asked for it, the join between a section and the response that holds its container, and the
join between a unit and the request that read the response for it. So it states no membership reader, no
request shape, no wrapper rule, no cache rule, no request identity rule, no path rule, no naming rule, no
writer, no console line, no environment name, and no merge rule, and it names no field of its own: the fact
order comes from `unit_manifest` and the field name for the row's source comes from `ownership`. The pins that
scan the `src/` set read it with the other modules. The four lists name three of the five
scope facts, so the index reaches those three containers: no membership row reads `vsys` or `devices`, so
the index makes no request for them, and the run reads such a scope as its declared scope. The module takes
the four tables as data, so a run that read one response holds one table set, and the join of the four
tables across responses is the run order's work (`docs/API_CONVERSION_PATH.md` §2.4). A device fact request
names no index entry, so the join has no fact to read its element name against, and `backlog.md` records that.

Usage:
    from api_requests import scope_index
    # One response per membership container, read through the door with the injected producer.
    membership = {}
    for parser in parsers_for_the_responses_the_run_read:
        for table, names in parser.parse_associations().items():
            for owner, value in names.items():
                membership.setdefault(table, {}).setdefault(owner, []).extend(value)
    index = scope_index('panorama.example.com', membership, api_requests.membership_lists())
    for entry in index:
        source = fetch(entry.request, 'panorama_cache')   # one response per entry
        # F8.5: the run parses each response on its own, so the join names the response for a section.
        # `name` is the entry the run read for the row's scope, which the run order states.
        response = response_for_section(section, index, name=entry.name)
    # F8.7: the unit join reads the unit set through `unit_manifest`, and reports the two directions as data.
    pairs = join_units(index, ledger)
    findings = unit_findings(index, ledger)
"""

from dataclasses import dataclass

import container_coverage
import ownership
import source_fetch
import unit_manifest
from xml_input import ENTRY_SEGMENT

# The parse method that owns the four membership lists. The lists are its rows in the container
# table, so this module states no second list (`tests/test_api_requests.py`).
MEMBERSHIP_METHOD = 'parse_associations'

# The join between a membership list and the table `parse_associations` returns for it, and the scope
# container that defines the entries its names belong to. The four lists are the `MEMBERSHIP_METHOD`
# rows in `container_coverage.CONTAINER_TABLE`, so this is a join and not a second list. The fourth
# list names the templates a stack applies, and a template is defined inside the `templates`
# container, so its names join to that container and not to the stack.
LIST_JOIN = {
    'device-group/entry/devices': ('device_groups', 'device-group'),
    'templates/entry/devices': ('templates', 'templates'),
    'template-stack/entry/devices': ('template_stacks', 'template-stack'),
    'template-stack/entry/templates': ('stack_templates', 'templates'),
}

# The two levels the index has. A third level would be an entry inside a membership entry, and the
# entry inside a membership list carries no value for the relation the row records
# (`docs/ARCHITECTURE.md` §2.4), so no request can be built from it.
CONTAINER_LEVEL = 1
ENTRY_LEVEL = 2


@dataclass(frozen=True)
class ScopeIndexEntry:
    """One scope the run read, and the request that reads the response for it.

    `name` is the entry name the response-to-request join (F8.3) compares with the response, and
    `request` is the request that made it. `path` is the scope path as the record states it, with no
    leading slash, so the index, the request identity, and `SOURCE.txt` name the same string.
    """

    level: int            # CONTAINER_LEVEL or ENTRY_LEVEL
    container: str        # the scope container that defines the entry
    name: str             # the entry name; '' for a container entry
    path: str             # the scope path, in the shape the record states it
    request: source_fetch.ApiRequest   # the per-scope request the fetch layer reads


def membership_lists() -> tuple:
    """The four membership lists, read through the container table rows `parse_associations` owns."""
    return tuple(sorted(row.path for row in container_coverage.CONTAINER_TABLE
                        if row.method == MEMBERSHIP_METHOD))


def list_container(list_path: str) -> str:
    """The scope container the response holds for a membership list: the segment the row names first."""
    return list_path.split('/')[0]


def names_read(membership: dict, list_path: str) -> tuple:
    """The names one membership list read, through the table `parse_associations` returned.

    Only the names are read. A table keys on the entry that owns the list, which is a device for three
    tables and the stack for the fourth, so a key is never an index entry. A container that lists no
    name reads no name, so it gains no entry: no association is better than a guessed one.
    """
    table, _ = LIST_JOIN[list_path]
    return tuple(sorted({name for names in membership.get(table, {}).values() for name in names}))


def scope_path(container: str, name: str = '') -> str:
    """The scope path an entry names, in the shape the record states it.

    Built from the definitions the owners state: `ENTRY_SEGMENT` from `xml_input.py`, and the shape
    `container_coverage.is_scope_path` validates, so the module states no second path rule. A name
    that builds a path the one definition does not validate is refused.
    """
    path = container if not name else f'{container}/{ENTRY_SEGMENT}/{name}'
    if not container_coverage.is_scope_path(path):
        raise ValueError(
            f"refusing the scope index entry '{path}': the name '{name}' builds a shape the one scope "
            "path definition does not validate, so the index cannot read it as a scope."
        )
    return path


def scope_index(host, membership: dict, read) -> tuple[ScopeIndexEntry, ...]:
    """The scope index, in sorted order, one entry per scope.

    `membership` is the four tables `parse_associations` returned for the responses the run read, and
    `read` is the membership lists the run read. A list the container table does not name is refused,
    because the module states no list of its own. A name is in the set only when the run read the
    response that read the list it came from, and an entry counts only when the run read the response
    for the container that defines it, so the index guesses no scope.
    """
    lists = membership_lists()
    read = sorted(set(read))
    outside = [path for path in read if path not in lists]
    if outside:
        raise ValueError(
            f"refusing the read set {outside}: these are not membership lists, because no "
            f"`{MEMBERSHIP_METHOD}` row in the container table names them."
        )

    # Level 1: one entry per scope container the run read, in sorted order.
    containers = sorted({list_container(path) for path in read})
    entries = []
    for container in containers:
        path = scope_path(container)
        entries.append(ScopeIndexEntry(CONTAINER_LEVEL, container, '', path,
                                       source_fetch.ApiRequest(host=host, path=path)))

    # Level 2: one entry per scope entry those containers name. A name whose entries belong to a
    # container the run did not read enters no entry, so no scope is guessed.
    seen = set()
    for list_path in read:
        defines = LIST_JOIN[list_path][1]
        if defines not in containers:
            continue
        for name in names_read(membership, list_path):
            key = (defines, name)
            if key in seen:
                continue    # one entry per scope, so a name two lists read gives one entry
            seen.add(key)
            path = scope_path(defines, name)
            entries.append(ScopeIndexEntry(ENTRY_LEVEL, defines, name, path,
                                           source_fetch.ApiRequest(host=host, path=path)))

    return tuple(sorted(entries, key=lambda entry: (entry.level, entry.path)))


def entry_name(element) -> str:
    """The name an `entry` element carries, or a refusal when it carries none.

    An entry with no name gives the join nothing to compare with the index, so it is refused rather than
    guessed. An entry inside a membership entry names no scope (`docs/ARCHITECTURE.md` §2.4), so the join
    reads only the entries at the level its own request names.
    """
    name = element.get('name')
    if not name:
        raise ValueError(
            "refusing the entry inside the response: it carries no name, so the join has nothing to "
            "compare with the scope index."
        )
    return name


def entry_names_inside(element) -> tuple:
    """The entry names the response holds inside the element its own request names, in sorted order.

    A request that names an entry makes that entry the element the response holds, so the name the element
    carries is the one name the join compares. A request that names a place holds the entries inside it.
    """
    if element.tag == ENTRY_SEGMENT:
        return (entry_name(element),)
    return tuple(sorted(entry_name(child) for child in element if child.tag == ENTRY_SEGMENT))


def names_in_index(index, container: str) -> tuple:
    """The names the index has for one scope container, in sorted order."""
    return tuple(sorted(entry.name for entry in index
                        if entry.level == ENTRY_LEVEL and entry.name and entry.container == container))


def join_response(source, entry, index) -> tuple:
    """The response-to-request join (`docs/API_CONVERSION_PATH.md` §2.3): read one response against the
    index entry whose request made it, and return the entry names inside it in sorted order.

    Two checks, in this order:

    1. The element the response holds is the element its own request names. The join reads this through its
       owner, so it states no shape rule and no wrapper rule: it runs the one wrapper decision
       (`source_fetch.unwrap_config_root`) on the response, and that decision names the element through the
       one rule in that module (`source_fetch.names_element`). The door's origin and line map are the ones
       the join reports, so no second tree is built and no producer is called.
    2. The entry name inside the response agrees with the scope index, which is what the join owns, so the
       join is checked rather than assumed. For a request that names an entry, the name inside it is the
       name the index names for that entry. For a request that names a place, the names inside it are the
       names the index read for that container, so a name the index read must appear inside. A name inside
       that the index did not read gains no entry (`names_read`), so the join reads no membership here
       and states no membership rule of its own.

    The join reads only a response the index made a request for, because the index makes only per-scope
    requests: a whole-config response holds no scope entry, and a device fact names no scope, so a
    command's element name is not a fact the join can read offline (`backlog.md`).
    """
    request = entry.request
    if not request.is_per_scope():
        raise ValueError(
            f"refusing the response for '{entry.path}': the join reads a response against the index entry "
            "that made its request, and this request names no scope path, so no index entry names it."
        )

    # The response is read against the request the index entry states, so bytes that came from another
    # request are refused here rather than assumed to belong to this entry.
    accepted = source_fetch.unwrap_config_root(source, request)
    held = list(accepted.root)
    inside = entry_names_inside(held[0])

    if entry.level == ENTRY_LEVEL:
        if inside != (entry.name,):
            raise ValueError(
                f"refusing the response for '{entry.path}': the entry name inside it is {list(inside)}, "
                f"which does not agree with the index, where that entry is '{entry.name}'."
            )
        return inside

    agreed = names_in_index(index, entry.container)
    missing = [name for name in agreed if name not in inside]
    if missing:
        raise ValueError(
            f"refusing the response for '{entry.path}': the entry names inside it are {list(inside)}, "
            f"which do not agree with the index for '{entry.container}', because the index read "
            f"{list(missing)} and the response holds no entry for them."
        )
    return inside


def entry_for_path(index, path: str):
    """The index entry for one scope path, or None when the index has no entry for it.

    The join below answers which response holds a container, so it needs the entry for the shape the run
    read, and the index is the set of shapes the run read. A path the index has no entry for is a scope the
    run read no response for.
    """
    for entry in index:
        if entry.path == path:
            return entry
    return None


def response_for_section(section: str, index, name: str = ''):
    """The run-over-many-sources join (`docs/API_CONVERSION_PATH.md` §2.4): the index entry whose response
    holds the container a section names.

    One response is one source, so the run runs each parse method over the response that holds its container,
    and the report row for an entry names that response with the line inside it. The join answers the response
    in two parts, both read through their owners: the place the section names first, which is the segment
    `list_container` already states, and the entry inside that place that the run read, built through
    `scope_path` and validated through `container_coverage.is_scope_path`, so the join states no second path
    rule.

    `name` is data the run states, because a section names a container and never the entry it sits inside. For
    a place read the join answers the response for the place, and that response holds every entry inside it.
    For an entry read `name` is the entry the run read for the row's scope, and that response holds the entry.
    So the join answers one response per section, and no section needs a tree built across responses.

    Two refusals, in this order:

    1. A section whose first segment names no place the one definition validates names no scope, so the run
       reads its container inside the response for the scope that holds it, and the join has no scope to
       answer. A row that names only a container is the case this refusal states.
    2. A section inside a place the index has no entry for is refused, because the set is read from the
       membership responses and no membership row reads that scope, so the run read no response for it. A
       built-in place is that case: the run can read `predefined` as a declared scope, but the index makes no
       entry for it, and the fact the built-in name table needs is a live fact (`backlog.md`).
    """
    place = list_container(section)
    if not container_coverage.is_scope_path(place):
        raise ValueError(
            f"refusing the section '{section}': its first segment does not name a place the one scope path "
            "definition validates, so no response holds its container. The run reads a container inside a "
            "config entry inside the response for the scope that entry defines, and this section names no "
            "scope the run read."
        )
    shape = scope_path(place, name)
    entry = entry_for_path(index, shape)
    if entry is None:
        raise ValueError(
            f"refusing the section '{section}': the index has no entry for '{shape}', so the run read no "
            "response for the scope that holds its container. The set is read from the membership responses, "
            "and no membership row reads this scope."
        )
    return entry


def response_names(index) -> dict:
    """The response name each index entry's own request produces, read through the one name rule in
    `source_fetch.py` (`cache_name`), so the join states no cache rule and no request identity rule of its own.

    That name is also the value a report row carries for the source that holds the entry, so the join reads the
    row and the index against the same rule.
    """
    return {entry.request.cache_name(): entry for entry in index}


def join_units(index, ledger) -> list:
    """The unit join (`docs/API_CONVERSION_PATH.md` §3): the pair the join answers for each unit.

    Two parts, both read through their owners. The unit set is `unit_manifest.units`, so path 2 states no
    second unit rule and counts no unit a second way: a unit exists when the ledger has a row in it, and the
    facts are in the order the one rule states. The field a row carries the source on is the name `ownership`
    states, so the join holds no field name of its own and adds no field to the declared row shape.

    The fact path 2 adds is the scope the run read for a unit. A row names the response its entry came from, so
    the join answers the index entry whose request produced that name: the place response for a place read, and
    the entry response for an entry read (F8.5). The same content read two ways gives two answers, which is the
    fact path 1 cannot state.

    The join reads the row set through one ledger, because the join is per response (F8.5), so for a run that
    read one response the row set is that response's rows. Which row set a run that read more than one response
    joins is the run order's decision (`backlog.md`), so this module states no merge rule here.

    Returns the pairs as `(facts, entry)`, in the order `unit_manifest.units` states them, and inside a unit in
    the order the response names sort in. A unit the join answers no entry for is not a pair here, because
    `unit_findings` reports it.
    """
    names = response_names(index)
    rows = list(ledger.rows())
    pairs = []
    for facts in unit_manifest.units(ledger):
        answered = sorted({row[ownership.SOURCE_FIELD] for row in rows
                           if unit_manifest.facts_of(row) == facts and row[ownership.SOURCE_FIELD] in names})
        for name in answered:
            pairs.append((facts, names[name]))
    return pairs


def unit_findings(index, ledger) -> list:
    """The two directions the unit join reports as data (`docs/API_CONVERSION_PATH.md` §3).

    1. A unit the join answers no entry for, because the response its rows name is one the index made no
       request for. A whole-config response holds no scope entry, and a scope no membership row reads gains no
       entry, so a run that read the same content as a whole-config export, or as a predefined read, holds a
       unit with no request. The join reports the unit; it states no rule that such a source is definitions,
       and `backlog.md` keeps that decision.
    2. An index entry the run read no rows for, so no unit answers it. The set is read from the membership
       responses, so an entry the index names can exist while the run read no row for it.

    Each row is the pair the join answers, `(facts, entry)`, and the side the join has no fact for is None, so
    the data states the direction. The units are in the order the one unit rule states, and the entries are in
    the index order. The join reports these as rows only: no console line, no writer, no report section, no
    exit code, and no gate rule, because those shapes have owners.
    """
    names = response_names(index)
    rows = list(ledger.rows())
    read = {row[ownership.SOURCE_FIELD] for row in rows}
    findings = [(facts, None) for facts in unit_manifest.units(ledger)
                if not any(row[ownership.SOURCE_FIELD] in names
                           for row in rows if unit_manifest.facts_of(row) == facts)]
    findings += [(None, entry) for entry in index if entry.request.cache_name() not in read]
    return findings
