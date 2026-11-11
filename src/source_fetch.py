#!/usr/bin/env python3
"""
F5.2: the cached API export. A byte producer for the input door. F5.4 adds the per-scope
request (`type=config&action=get&path=...`) and the wrapper rule for its response shape.
F8.1 adds the third accepted request shape, the device fact shape (`type=op&cmd=<command>`),
and the wrapper rule for its response shape.

Copyright (c) 2025 GSW Systems

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
Commercial terms are in LICENSE-COMMERCIAL.

The fetch layer reads the whole-config API export (`type=export`,
`category=configuration`) and hands the response bytes to
``xml_input.parse_bytes``. It is a producer only: it keeps no second copy
of the two checks, and it builds no device-object model, because the
container table, the entry ledger, the parent walk and the line map are
keyed on the ElementTree tree.

Five rules, stated once here:

1. The wrapper decision (F5.2 AC-2, F5.4 AC-1, F8.1). A fetched response is a `response` /
   `result` wrapper, not a config root. The fetch parses the whole response
   bytes, then moves the tree root to the element the request shape names.
   No reparse, so the line map survives. The three accepted request shapes each have one accepted
   response element, and a response is read against the shape its own request states:
   `type=export&category=configuration` takes the `config` element under `result`;
   `type=config&action=get&path=<scope path>` takes the element the path names, and `result`
   becomes the root, read as the place the path names; `type=op&cmd=<command>` takes exactly one
   element under `result`, the fact element the command names, and `result` becomes the root, read
   as the place the command names. The fetch layer states no command-to-element table, and the join states none
    either, so which
   element a command names is a fact the tool cannot read offline, so it stays in `backlog.md`.
   A response shape that does not match its request is refused, not guessed. An op
   response is a device fact, not a config: it names no scope, so the source states no scope and the
   container table needs no wrapper row and no row for the fact element.
   `response` and `result` are never read as containers.
2. The cache entry is what gets parsed (F5.2 AC-3). The entry name is the
   SHA-256 hex of the request identity (host and sorted params), so the same
   request finds the same entry, and the credential is not part of the
   identity. The params are the words the request's shape states plus the part it declares (the
   path, or the command), so each scope and each command finds its own entry. Both checks run
   before any file is written, and the entry holds
   exactly the bytes the door parsed, so a report line names bytes a reader
   can reopen. A cache hit calls no producer. `--offline` reads the cache
   only and refuses when the entry does not exist.
3. The three https rules (F5.2 AC-5). The producer accepts https only,
   refuses a redirect that changes the scheme, and verification is on by
   default; `--insecure` is an explicit flag. The standard-library producer
   can enforce all three, which is why it replaces the planned SDK producer.
4. The key rule (F5.2 AC-5). The API key comes from the environment
   (`PANOS_API_KEY`), never from argv, and is needed only when the producer
   is called. It reaches the request URL and nothing else: never the cache
   name, the cache bytes, a report line, or a generated file.

The producer is a callable that takes an `ApiRequest` and hands bytes, so
every test injects a producer and no test calls the network.

Usage:
    from source_fetch import ApiRequest, fetch
    request = ApiRequest(host='panorama.example.com')
    source = fetch(request, 'panorama_cache')   # reads the API once, then the cache
    scope_request = ApiRequest(host='panorama.example.com', path='device-group/entry/Edge')
    source = fetch(scope_request, 'panorama_cache', offline=True)
    fact_request = ApiRequest(host='panorama.example.com', command='show system info')
    source = fetch(fact_request, 'panorama_cache')      # `result` holds the one fact element
    line = source.line_of(source.root.find('.//entry'))
"""

import hashlib
import os
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

import write_path
from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    ENTRY_SEGMENT,
    ParsedSource,
    SourceOrigin,
    UnsafeInputError,
    add_max_input_argument,  # noqa: F401 -- re-exported: the entry points read the input limit through
                              # this module, the owner of the limit, so no entry point states its own.
    parse_bytes,
    read_input,
)

# The source kind the report names for a fetched input. F5.6 adds 'state'.
SOURCE_KIND = 'api'

# The three accepted request shapes (F8.1, `docs/API_CONVERSION_PATH.md` §2.1), one response
# element each. The wrapper decision reads a response against the shape its own request states, so
# a shape is never guessed from what the response looks like.
EXPORT_TYPE = 'export'
EXPORT_CATEGORY = 'configuration'
CONFIG_TYPE = 'config'
CONFIG_ACTION = 'get'
OP_TYPE = 'op'

# The params each shape states. `path` names the scope for the per-scope shape and `cmd` names the
# command for the device fact shape, so the part a request declares is part of its identity and
# each scope and each command gets its own cache entry. `ENTRY_SEGMENT` comes from the shared scope
# vocabulary in `xml_input.py`, the only module the fetch layer may import.
SHAPE_PARAMS = {
    EXPORT_TYPE: (('type', EXPORT_TYPE), ('category', EXPORT_CATEGORY)),
    CONFIG_TYPE: (('type', CONFIG_TYPE), ('action', CONFIG_ACTION)),
    OP_TYPE: (('type', OP_TYPE),),
}
PATH_PARAM = 'path'
CMD_PARAM = 'cmd'

DEFAULT_CACHE_DIR = 'panorama_cache'
API_KEY_ENV = 'PANOS_API_KEY'
CACHE_SUFFIX = '.xml'


class SourceFetchError(UnsafeInputError):
    """A fetch refusal with the same shape as every other input refusal.

    An UnsafeInputError subclass, so `main()` prints it unchanged and exits 1
    through the same path as a size or DTD refusal.
    """


@dataclass(frozen=True)
class ApiRequest:
    """What the producer asks for. The API key is not a field, so the cache
    identity can never carry the credential.

    A `path` (F5.4) makes the request a per-scope request. It is stored without a
    leading slash, so the path is the same shape the record states, and it is part of
    the request identity: one cache entry per request identity.

    A `command` (F8.1) makes the request a device fact request, and the command is part of the
    identity for the same reason. A request that states no params takes the words its own shape
    states; `params` is the override for a request that states them itself.
    """

    host: str
    path: str = ''
    command: str = ''
    params: tuple = ()

    def request_shape(self) -> str:
        """The shape the request declares: the device fact shape for a command, the per-scope
        shape for a path, the whole-config export for nothing else (F8.1). The wrapper decision
        reads the response against this shape, and never against what the response looks like."""
        if self.command:
            return OP_TYPE
        if self.path:
            return CONFIG_TYPE
        return EXPORT_TYPE

    def is_per_scope(self) -> bool:
        """True when the request declares a scope path, not the whole-config export."""
        return bool(self.path)

    def is_device_fact(self) -> bool:
        """True when the request declares a command (F8.1)."""
        return bool(self.command)

    def segments(self) -> tuple:
        """The declared path as segments: ('device-group', 'entry', 'Edge')."""
        return tuple(self.path.split('/')) if self.path else ()

    def request_params(self) -> tuple:
        """The params the identity hashes: the words its shape states, or the params the request
        states for itself, plus the part it declares (the path, or the command)."""
        params = dict(self.params or SHAPE_PARAMS[self.request_shape()])
        if self.path:
            params[PATH_PARAM] = self.path
        if self.command:
            params[CMD_PARAM] = self.command
        return tuple(sorted(params.items()))

    def https_host(self) -> str:
        """The host as the producer accepts it: https only.

        A bare host is treated as https. A URL with any other scheme is
        refused before the fetch starts, so the rule holds for a cache hit
        too: a declared source that breaks the rule is not a source this tool
        reads, even when its bytes are already cached.
        """
        if '://' in self.host:
            scheme, rest = self.host.split('://', 1)
            if scheme.lower() != 'https':
                raise SourceFetchError(
                    f"refusing the source host '{self.host}': the producer accepts https "
                    f"only, and this request names the scheme '{scheme}'."
                )
            return rest.split('/')[0]
        return self.host

    def canonical(self) -> str:
        """The request identity the cache key hashes: host and sorted params, no key."""
        query = '&'.join(f'{key}={value}' for key, value in self.request_params())
        return f'{self.https_host()}?{query}'

    def cache_name(self) -> str:
        """The cache entry file name: the hex of the request identity."""
        return hashlib.sha256(self.canonical().encode('utf-8')).hexdigest() + CACHE_SUFFIX

    def url(self, api_key: str) -> str:
        """The request URL. The key reaches this URL and nothing else.

        The query is encoded, because a command is words with spaces and an unencoded query is not
        a request. `canonical()` keeps the plain sorted shape, because the record reads the identity
        as data.
        """
        query = urllib.parse.urlencode(self.request_params())
        return f'https://{self.https_host()}/api/?{query}&key={api_key}'


class _SameSchemeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only when it keeps the scheme (F5.2 AC-5.2).

    The signature is the parent's, including `msg`. A guard with fewer arguments
    is not the handler urllib calls.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old_scheme = urllib.parse.urlsplit(req.full_url).scheme
        new_scheme = urllib.parse.urlsplit(newurl).scheme
        if old_scheme != new_scheme:
            raise SourceFetchError(
                f"refusing the redirect from '{req.full_url}' to '{newurl}': "
                f"the redirect changes the scheme from '{old_scheme}' to '{new_scheme}'. "
                "A downgrade can send the credential to a plain connection."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _ssl_context(insecure: bool) -> ssl.SSLContext:
    """Verification is on by default; `--insecure` is the only way off (F5.2 AC-5.3)."""
    if insecure:
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def network_producer(request: ApiRequest, api_key: str, insecure: bool = False) -> bytes:
    """The default producer: one https GET, and the response bytes as they arrive.

    The size cap applies to the bytes as they arrive, inside the door, after
    any decompression. The producer returns bytes only; it never parses them.
    """
    opener = urllib.request.build_opener(
        _SameSchemeRedirectHandler(),
        urllib.request.HTTPSHandler(context=_ssl_context(insecure)),
    )
    with opener.open(request.url(api_key)) as response:
        return response.read()


def names_element(element, request: ApiRequest) -> bool:
    """True when `element` is the element the request path names (F5.4 AC-1.2).

    The one definition of which element a per-scope request names, so the wrapper decision and the
    response-to-request join (F8.3) read one rule and no module states a second.

    A path that names an entry (`container/entry/name`) names that entry by name; a path
    that names a container names the element with that tag. The wrapper decision checks
    the response against the request; it does not guess a shape the path does not state. A
    device fact request declares a command and no path, so this rule names no element for it:
    the tool states no command-to-element table, so the join has no fact to read a command's
    element name against (`backlog.md`).
    """
    segments = request.segments()
    if not segments:
        # The device fact shape declares no path, so no element name follows from it.
        return False
    if len(segments) == 3 and segments[1] == ENTRY_SEGMENT:
        return element.tag == 'entry' and element.get('name') == segments[2]
    return element.tag == segments[0]


def unwrap_config_root(source: ParsedSource, request: Optional[ApiRequest] = None) -> ParsedSource:
    """The wrapper decision: move the tree root to the element the request shape names
    (F5.2 AC-2, F5.4 AC-1, F8.1).

    The origin and the line map are the same object, so a report line still names
    the line the response bytes carry. A whole-config request accepts
    `response`/`result`/`config`, `result`/`config`, and a plain `config` root. A
    per-scope request accepts `response`/`result` and `result`, and `result` must hold
    exactly one element, the element the path names; `result` then becomes the root,
    read as the place the path names. A device fact request accepts `response`/`result` and
    `result`, and `result` must hold exactly one element, the fact element the command names;
    `result` then becomes the root, read as the place the command names, and the source states no
    scope, because a command names no scope. A shape that does not match its request is
    refused. The response success check runs here, before the cache entry is written.
    """
    root = source.root
    if root.tag == 'response':
        response_type = root.get('type') or ''
        code = root.get('code') or ''
        if response_type != 'success' or code != '0':
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': "
                f"type '{response_type}' code '{code}', which is not 'success' code '0'. "
                "The cache entry is not written for a refused response."
            )
        result = root.find('result')
        if result is None:
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': "
                "the response has no result element."
            )
        root = result
    if request is not None and request.request_shape() == OP_TYPE:
        # The device fact shape (F8.1): `result` holds the one fact element the command names, and
        # `result` itself becomes the root, read as the place the command names. The response is a
        # device fact, not a config, so no scope comes from it and no container name comes from it:
        # the envelope rule keeps `result` out of the scan, and the container table states no row
        # for a fact element. The join (F8.3) reads a response against the index entry its request names, and it
        # states no command-to-element table either, so a command's element name stays a fact the join cannot read
        # offline, and `backlog.md` records it.
        if root.tag != 'result':
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the device fact request for "
                f"'{request.command}' needs the result element, and the root element "
                f"'{root.tag}' is the whole-config shape."
            )
        held = list(root)
        if len(held) != 1:
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the result holds no element, "
                f"or {len(held)} elements, not the one fact element the command "
                f"'{request.command}' names."
            )
        if held[0].tag == 'config':
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the result holds the config "
                f"element, which the whole-config shape names, not the fact element the command "
                f"'{request.command}' names."
            )
        return replace(source, root=root)
    if request is not None and request.is_per_scope():
        # The per-scope shape (F5.4): `result` holds the element the path names, and
        # `result` itself becomes the root, read as the place the path names.
        if root.tag != 'result':
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the per-scope request for "
                f"'{request.path}' needs the result element, and the root element "
                f"'{root.tag}' is the whole-config shape."
            )
        held = list(root)
        if len(held) != 1:
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the result holds no element, "
                f"or {len(held)} elements, not the one element the path '{request.path}' names."
            )
        if not names_element(held[0], request):
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the element under the result "
                f"does not match the path '{request.path}'. The wrapper decision reads the "
                "shape the request states, not a shape that looks similar."
            )
        return replace(source, root=root, scope=request.path)
    if root.tag == 'result':
        config = root.find('config')
        if config is None:
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the result holds no config "
                "element. The whole-config request needs the config element; a per-scope "
                "response is read only by the request that declares its path (F5.4)."
            )
        return replace(source, root=config)
    if root.tag == 'config':
        return source
    raise SourceFetchError(
        f"refusing the API response from '{source.name}': the root element '{root.tag}' is "
        "not the whole-config export shape the container table knows."
    )


def fetch(request: ApiRequest, cache_dir, producer: Optional[Callable[[ApiRequest], bytes]] = None,
          offline: bool = False, insecure: bool = False,
          max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
          api_key: Optional[str] = None) -> Optional[ParsedSource]:
    """Read the cached API export and return the parsed source (F5.2 AC-3).

    The origin names the cache entry as its name and its path, so a report line
    names bytes a reader can reopen. On a hit, no producer is called, and the
    cache file is read through the same capped read the file producer uses. On a
    miss, the producer is called once, the two checks run on the bytes as they
    arrived, the response check runs, and only bytes that passed all three reach
    the cache. The parsed bytes are the cache bytes.

    `--offline` reads the cache only and refuses when the entry does not exist.
    No credential is needed to reopen cached bytes.
    """
    entry = Path(cache_dir) / request.cache_name()
    origin = SourceOrigin(kind=SOURCE_KIND, name=entry.name, path=entry)

    if entry.exists():
        data = read_input(entry, max_input_bytes)
        return unwrap_config_root(parse_bytes(data, origin, max_input_bytes), request)

    if offline:
        raise SourceFetchError(
            f"refusing to read the cache entry '{entry.name}': --offline reads the cache "
            "only, and no entry for this request exists. Run once with the network to "
            "create it."
        )

    key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
    if producer is None and not key:
        raise SourceFetchError(
            f"cannot fetch '{request.canonical()}': the API key is not set. "
            f"Set {API_KEY_ENV} in the environment; the converter never takes a key "
            "as an argument."
        )

    # The checks run inside the door, so no file is written for bytes that fail
    # them. The cache entry then holds exactly the bytes the door parsed.
    data = producer(request) if producer is not None else network_producer(request, key, insecure)
    if data is None:
        # A producer that has no bytes for this request answers None, so the run reads no response for it and
        # writes no cache entry: an empty entry would be a response the record could not name. The run order
        # then holds no part for the request, and the join reports the index entry as a finding.
        return None
    source = parse_bytes(data, origin, max_input_bytes)
    source = unwrap_config_root(source, request)
    # The write path is the only writer (F6.10.3); bytes reach it untranslated, so the cache holds
    # the bytes the door parsed.
    write_path.write_file(entry, data)
    return source
