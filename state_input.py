"""F5.6 state producer: the Terraform state document, read as a reference source.

Six rules, stated once here.

1. The door keeps its two byte checks for every source kind, through
   `xml_input.check_bytes`. The size check is kind-independent. The DTD check asks the parser,
   and only XML has a prolog, so a JSON document reaches no DOCTYPE: a `<!DOCTYPE` inside a JSON
   value is not a refusal. Only the parse step is chosen by the kind.
2. The tree rule does not apply to a JSON document. The container table, the parent walk, and the
   expat line map are keyed on the ElementTree tree, so a state document gives the scan one shape
   per entry instead of a tree: the entry name, the resource type, the attribute values, and the
   position. `state_coverage.py` reads that shape.
3. One entry is one instance object. The attributes of a resource are each instance's `attributes`
   object (the shape state format version 4 writes) or its `values` object (the shape an older
   document holds). A resource that states no `type` or no `name` is refused, because the identity
   key cannot read it.
4. A state entry has no source line, because only the expat handler path records one. Its position
   is its Terraform resource address: `type.name`, or `module.path:type.name` inside a module
   instance. The root module names no path, so an entry in it is addressed as `type.name`.
5. Refusals are input refusals (`UnsafeInputError`), so the CLI exits 1 and writes no record:
   the bytes are not JSON, the document is not an object, the document holds no `resources`
   array, or a resource item is not an object that names its type and name.
6. The state source is a reference source, so the run writes no output from it and no name comes
   from it. Its origin kind is `state`, and its `scope` names the workspace the run declared, or
   the default (`xml_input.DEFAULT_SCOPE`), so the provenance record needs no new field.

Usage:
    from state_input import read_state
    source = read_state('production.tfstate', workspace='production')
    for entry in source.entries:
        print(entry.address, entry.entry_name)

    # A producer that hands bytes uses the same door:
    from state_input import parse_state
    source = parse_state(data, SourceOrigin(kind='state', name='workspace.tfstate'))
"""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_SCOPE,
    SourceOrigin,
    UnsafeInputError,
    check_bytes,
    origin_phrase,
    read_input,
)

STATE_KIND = 'state'

# The fields a state document states, in the shape format version 4 writes.
RESOURCES_FIELD = 'resources'
INSTANCE_FIELD = 'instances'
ATTRIBUTE_FIELD = 'attributes'
VALUE_FIELD = 'values'

# The root module names no path, so a resource in it is addressed as `type.name`.
ROOT_MODULE = 'root'


@dataclass(frozen=True)
class StateEntry:
    """One instance object in the state document, read as an entry."""

    module: str
    resource_type: str
    resource_name: str
    attributes: dict

    @property
    def address(self) -> str:
        """The position a state entry has: the resource address Terraform uses."""
        base = f'{self.resource_type}.{self.resource_name}'
        return base if self.module in ('', ROOT_MODULE) else f'{self.module}:{base}'

    @property
    def entry_name(self) -> str:
        """The entry name the identity key reads: the name the provider stored in the values."""
        return self.attributes.get('name') or ''


@dataclass(frozen=True)
class StateSource:
    """A parsed state document: the source it came from, the entries it holds, and the record
    facts. The four facts a record states (`origin`, `size`, `sha256`, `scope`) are the same
    names `xml_input.ParsedSource` records, so `provenance.py` reads a state source with no new
    field."""

    origin: SourceOrigin
    entries: tuple[StateEntry, ...] = ()
    size: int = 0
    sha256: str = ''
    scope: str = DEFAULT_SCOPE

    @property
    def name(self) -> str:
        """Source name, no directory. A report line must not depend on the path (F4.2 rule 6)."""
        return self.origin.name


def _refusal(origin: SourceOrigin, problem: str) -> UnsafeInputError:
    """An input refusal with the same shape as every other door refusal."""
    return UnsafeInputError(f"refusing to read {origin_phrase(origin)}: {problem}")


def _attributes(resource: dict) -> Iterator[dict]:
    """The attribute objects a resource states, in document order.

    Format version 4 writes each instance as `instances[n].attributes`. An older document holds
    the same values in `values`. One entry is one instance, so a resource with two instances
    gives two entries.
    """
    instances = resource.get(INSTANCE_FIELD)
    if isinstance(instances, list):
        for instance in instances:
            if isinstance(instance, dict) and isinstance(instance.get(ATTRIBUTE_FIELD), dict):
                yield instance[ATTRIBUTE_FIELD]
    values = resource.get(VALUE_FIELD)
    if isinstance(values, dict):
        yield values


def parse_state(data: bytes, origin: SourceOrigin, workspace: str = '',
                max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> StateSource:
    """The state door (F5.6): check the bytes, then read them as one JSON document.

    The two door checks run through `xml_input.check_bytes`, so the size check applies to a JSON
    source exactly as it applies to a file or an api response. The size and the SHA-256 hex are
    measured on these bytes, so the F5.3 record names the bytes the door checked.

    Raises UnsafeInputError for a size, DTD, or document-shape refusal.
    """
    check_bytes(data, origin, max_input_bytes)
    try:
        document = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        message = getattr(exc, 'msg', str(exc))
        raise _refusal(origin, f'the state document is not JSON ({message})') from None
    if not isinstance(document, dict):
        raise _refusal(origin, f'a state document is one object, not {type(document).__name__}')
    resources = document.get(RESOURCES_FIELD)
    if not isinstance(resources, list):
        raise _refusal(origin, 'the state document holds no `resources` array')

    entries = []
    for resource in resources:
        if not isinstance(resource, dict):
            raise _refusal(origin, 'a `resources` item is not an object, so the scan cannot read it')
        resource_type = resource.get('type') or ''
        resource_name = resource.get('name') or ''
        if not resource_type or not resource_name:
            raise _refusal(origin, 'a resource names no type or no name, so the identity key cannot read it')
        module = resource.get('module') or ROOT_MODULE
        if not isinstance(module, str):
            raise _refusal(origin, f'the resource {resource_type}.{resource_name} names a module that is not a path')
        for attributes in _attributes(resource):
            entries.append(StateEntry(module=module, resource_type=resource_type,
                                      resource_name=resource_name, attributes=attributes))

    return StateSource(
        origin=origin,
        entries=tuple(entries),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        scope=workspace or DEFAULT_SCOPE,
    )


def read_state(path, workspace: str = '',
               max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES) -> StateSource:
    """The state producer (F5.6): read the file, then check and read the bytes.

    The size is checked before the read, so an over-limit file is never allocated, exactly as
    the file producer does. A state read is a file read, so `--offline` needs no rule here: the
    state source is never fetched.
    """
    origin = SourceOrigin(kind=STATE_KIND, name=Path(path).name, path=Path(path))
    data = read_input(origin.path, max_input_bytes)
    return parse_state(data, origin, workspace=workspace, max_input_bytes=max_input_bytes)
