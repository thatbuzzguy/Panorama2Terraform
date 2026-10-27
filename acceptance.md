# Acceptance Criteria — F5.2 Cached API Export (current task)

Scope: the converter reads a Panorama whole-config export from a declared source
through `xml_input.parse_bytes`. The fetch layer is a byte producer only: it hands
bytes to the input door and never builds a device-object model, because the container
table, the entry ledger, the parent walk and the line map are keyed on the ElementTree
tree. What it fetches is cached, and the cache entry is what gets parsed.

Two decisions taken before the code (the to-do pieces that opened this feature):

1. **Normalise the wrapper.** A fetched response parses as a `response`/`result`
   wrapper, not a config root. The fetch layer parses the whole response bytes, then
   moves the tree root to the `config` element under `result`. No reparse, so the line
   map survives. `response` and `result` sit above the config root, so the container
   table never scans them and needs no row. A per-scope fetch (`type=config&action=get`)
   holds no `config` element and is refused by this rule; it belongs to F5.4.
2. **Standard-library producer.** `source_fetch.py` uses `urllib.request` over https,
   like `xml_input.py` stays standard library. This supersedes the `pan-os-python`
   piece: the SDK does not expose the redirect rule, and a standard-library producer
   can enforce all three https rules and needs no test skip. No test calls the network;
   each test injects a fixture-backed producer. The superseded decision is recorded in
   `backlog.md`.

Out of scope for this task:

- The provenance record (`SOURCE.txt`) and the report label change to `Source:` (F5.3).
  This feature keeps the label as it is, so a file run writes the same report bytes as
  before.
- Cache pruning. A cache entry is not pruned while a report references it; that rule
  waits for the provenance record (F5.3).
- Per-scope fetch for the cross-source shadow report (F5.4).
- `split_device_groups.py`. The splitter reads a file; its input path is unchanged.

## AC-1 — The fetch layer is a byte producer only

1. `source_fetch.py` hands the bytes it reads to `xml_input.parse_bytes` with a
   `SourceOrigin` of kind `api`. It keeps no second copy of the two checks: the size
   refusal and the DTD refusal run on the bytes as they arrived, through the door.
2. `fetch` returns a `ParsedSource` — origin, tree, line map — never a device-object
   model. The root is the config root after the wrapper decision (AC-2).
3. `source_fetch.py` imports the standard library only, and no third-party module
   anywhere in the project. `xml_input.py` is unchanged. Pinned by an import scan of
   the module source.
4. No test calls the network. Every test injects a producer callable that hands bytes.

## AC-2 — The response wrapper decision

1. After the parse, the tree root becomes the `config` element under `result`. The
   origin and the line map are the same object: a report line names the same line number
   the response bytes carry.
2. A response that is not `type="success"` with `code="0"` is refused before the cache
   entry is written, and the refusal names the type and the code.
3. The three accepted shapes are `response`/`result`/`config`, `result`/`config`, and a
   plain `config` root. A `result` that holds no `config` element is refused, because it
   is the per-scope shape F5.4 will handle with its own rule.
4. The container table is unchanged. No row names `response` or `result`.

## AC-3 — The cache entry is what gets parsed

1. The cache entry name is the SHA-256 hex of the request identity: the host and the
   sorted request params. The API key is not part of the identity, so no cache name,
   report line, or generated file can carry the credential.
2. The two checks run before any file is written. The cache entry holds exactly the
   bytes the door parsed, and the origin names that file, so a report line can reopen
   the bytes it describes.
3. On a cache hit, no producer is called. On a miss, the producer is called once, the
   checked bytes are cached, and the same bytes are parsed.
4. Two runs on the same cache bytes produce identical output bytes.
5. A cache hit that is over the input limit is refused through the door, naming the
   cache entry.

## AC-4 — `--offline` reads the cache only

1. `--offline` never calls a producer. With no cache entry it refuses, naming the entry
   name it looked for.
2. `--offline` on an existing entry runs with no API key: no credential is needed to
   reopen cached bytes.
3. A run with no network passes CI: every F5.2 test is offline, by injected producer or
   by cache hit.

## AC-5 — The three https rules and the key rule

1. The producer accepts https only. A bare host is treated as https; a URL with another
   scheme is refused.
2. A redirect that changes the scheme is refused.
3. Verification is on by default. `--insecure` is an explicit flag and is refused with
   `--offline`, which never reaches the network.
4. The API key comes from the environment (`PANOS_API_KEY`), never from argv. It is
   needed only when the producer is called. It never reaches the cache name, the cache
   bytes, a report line, or a generated file.

## AC-6 — CLI and call sites

1. `input_file` becomes optional. `--source file` (default) needs the file and behaves
   exactly as before. `--source api` needs `--host`, and takes `--cache-dir` (default
   `panorama_cache`), `--offline`, and `--insecure`. `--offline` and `--insecure` apply
   only to `--source api`, so a file source refuses them; `--insecure` is refused with
   `--offline`, which never reaches the network.
2. `PanoramaParser` takes a `ParsedSource`, not a path: the parse boundary returns the
   same contract for every source. Every call site is migrated; no backward path is
   kept.
3. A fetch refusal prints `Error:` and exits 1, like every other input refusal. It
   writes no output.

## AC-7 — Gate

1. `ruff check .` clean, `pytest` green.
2. Both golden sets byte-identical (file runs write the same bytes as before).
3. Report determinism: the same input produces the same bytes, pinned by the existing
   tests; an api run on the same cache bytes repeats byte for byte.
4. Exit codes unchanged: a fetch refusal is an input refusal (1), the F4.1 gate still
   decides the conversion exit code, and a WARN still does not fail the run.
5. An api run of the same config content writes the same `.tf` bytes as a file run of
   that content; the report header names the cache entry as the source name.

## Documents to update

`docs/ARCHITECTURE.md` §1 and §3, `README.md`, `docs/USAGE_GUIDE.md` (the CLI),
`backlog.md` (the superseded producer decision, the closed wrapper decision),
`PLAN.md` (F5.2 complete), `to-do.md`, `agent-status.md`.
