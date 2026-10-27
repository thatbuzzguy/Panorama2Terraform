#!/usr/bin/env python3
"""
F5.2: the cached API export. A byte producer for the input door.

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

Four rules, stated once here:

1. The wrapper decision (F5.2 AC-2). A fetched response is a `response` /
   `result` wrapper, not a config root. The fetch parses the whole response
   bytes, then moves the tree root to the `config` element under `result`.
   No reparse, so the line map survives. `response` and `result` sit above
   the config root, so the container table never scans them and needs no
   row. A `result` that holds no `config` element is the per-scope shape;
   it is refused here and belongs to F5.4.
2. The cache entry is what gets parsed (F5.2 AC-3). The entry name is the
   SHA-256 hex of the request identity (host and sorted params), so the same
   request finds the same entry, and the credential is not part of the
   identity. Both checks run before any file is written, and the entry holds
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
    source = fetch(request, 'panorama_cache', offline=True)
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

from xml_input import (
    DEFAULT_MAX_INPUT_BYTES,
    ParsedSource,
    SourceOrigin,
    UnsafeInputError,
    parse_bytes,
    read_input,
)

# The source kind the report names for a fetched input. F5.6 adds 'state'.
SOURCE_KIND = 'api'

# Request shape the container table knows: the whole-config export.
EXPORT_TYPE = 'export'
EXPORT_CATEGORY = 'configuration'

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
    identity can never carry the credential."""

    host: str
    params: tuple = ((EXPORT_CATEGORY, 'configuration'), (EXPORT_TYPE, 'export'))

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
        query = '&'.join(f'{key}={value}' for key, value in sorted(self.params))
        return f'{self.https_host()}?{query}'

    def cache_name(self) -> str:
        """The cache entry file name: the hex of the request identity."""
        return hashlib.sha256(self.canonical().encode('utf-8')).hexdigest() + CACHE_SUFFIX

    def url(self, api_key: str) -> str:
        """The request URL. The key reaches this URL and nothing else."""
        query = '&'.join(f'{key}={value}' for key, value in sorted(self.params))
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


def unwrap_config_root(source: ParsedSource) -> ParsedSource:
    """The wrapper decision: move the tree root to the config element (F5.2 AC-2).

    The origin and the line map are the same object, so a report line still names
    the line the response bytes carry. Three shapes are accepted:
    `response`/`result`/`config`, `result`/`config`, and a plain `config` root.
    The response success check runs here, before the cache entry is written.
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
    if root.tag == 'result':
        config = root.find('config')
        if config is None:
            raise SourceFetchError(
                f"refusing the API response from '{source.name}': the result holds no config "
                "element. A per-scope fetch is the shape F5.4 reads with its own rule."
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
          api_key: Optional[str] = None) -> ParsedSource:
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
        return unwrap_config_root(parse_bytes(data, origin, max_input_bytes))

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
    source = parse_bytes(data, origin, max_input_bytes)
    source = unwrap_config_root(source)
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_bytes(data)
    return source
