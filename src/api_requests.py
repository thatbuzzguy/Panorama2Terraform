"""F8.2 the scope index: the set of scopes path 2 reads, as one entry per scope.

Two rules, stated once here (`docs/API_CONVERSION_PATH.md` §2.2 and §7):

1. The scope set is read, not guessed. It comes from the membership responses the run read, through
   the four membership lists `parse_associations` reads (`docs/ARCHITECTURE.md` §3, rule 3). Two
   levels, no more: one entry per scope container the run read, then one entry per scope entry those
   containers name. A name a membership list read joins to the container that defines it, and the
   entry counts only when the run read the response for that container. So no scope is guessed, and
   no request is made for a scope the run did not read.

2. The set is read in sorted order, one entry per scope: the containers first, then the entries in
   path order. A name two lists read gives one entry, so the set does not depend on document order.

The module reads no source and no membership of its own: `source_fetch.py` reads the bytes through
the input door, and `PanoramaParser.parse_associations` reads the four lists. What this module owns
is the join between a name a list read and the request that reads the scope it names. So it states no
membership reader, no request shape, no cache rule, no request identity rule, no path rule, no naming
rule, no writer, no console line, no environment name, and no merge rule, and the pins that scan the
`src/` set read it with the other modules. The four lists name three of the five scope facts, so the
index reaches those three containers: no membership row reads `vsys` or `devices`, so the index makes
no request for them, and the run reads such a scope as its declared scope. The module takes the four
tables as data, so a run that read one response holds one table set, and the merge across responses is
the run order's work (`docs/API_CONVERSION_PATH.md` §2.4).

The response-to-request join (`docs/API_CONVERSION_PATH.md` §2.3) is the next piece. It reads the two
parts this rule already names: the entry name, and the request that made the response. So the join is
a new function in this module, not a change to the rules above.

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
"""

from dataclasses import dataclass

import container_coverage
from source_fetch import ApiRequest
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
    request: ApiRequest   # the per-scope request the fetch layer reads


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
                                       ApiRequest(host=host, path=path)))

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
                                          ApiRequest(host=host, path=path)))

    return tuple(sorted(entries, key=lambda entry: (entry.level, entry.path)))
