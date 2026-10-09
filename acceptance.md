# Acceptance criteria — F3.8 Safe XML input (Epic 3)

F3.8 makes both entry points refuse input they cannot parse safely,
before they spend memory on it and before they write any file.

## Audit of what both entry points accept today (2026-10-08)

- `panorama_to_terraform.py` (`PanoramaParser.__init__`) and
  `split_device_groups.py` (`split_panorama_config`) each do the same
  three things: read the whole file into memory as UTF-8 text
  (`errors='replace'`), search that text for `<!DOCTYPE`, then hand the
  **path** to `ET.parse` — a second read of a file already in memory.
- Nothing bounds the size. A multi-gigabyte file is allocated in full
  before the parse starts, and `xml.etree` then builds a tree several
  times the file size.
- The two copies of the DTD check are duplicated code, and one of them is
  bypassable.

## Facts verified for this task

- `xml.etree` parses with `xml.parsers.expat` (expat 2.6.1 here). expat
  expands an entity only when a DTD declares it: `&a;` with no DTD is a
  hard `ParseError` ("undefined entity"), and expat never fetches an
  external entity because ElementTree installs no
  `ExternalEntityRefHandler`. **A DTD is the only door**, so rejecting it
  closes the whole entity-expansion and XXE class — if the rejection
  actually sees the DTD.
- The F1.7 text search does not see every DTD. It reads the file as
  UTF-8, so a UTF-16 export hides the `<!DOCTYPE` bytes from the search
  while expat still parses and expands the DTD. Reproduced 2026-10-08: a
  UTF-16 file with `<!ENTITY a "&a2;&a2;">` parsed cleanly and expanded to
  `xx`, and the check reported no DTD.
- The same search also rejects a `<!DOCTYPE` that only appears in a prolog
  comment, which is legal input that Panorama exports may contain.
- A parser-level scan is cheap: a DTD can only appear in the prolog, so
  the scan stops at the root element start tag. Verified against UTF-8,
  UTF-16 with a BOM, UTF-16 with an encoding declaration and
  ISO-8859-1 with an encoding declaration; a malformed prolog reports
  nothing, which leaves the parse error message (with line and column) to
  the real parse.
- `defusedxml` would close the DTD class but not the size class, and it is
  a new runtime dependency for two scripts that need none today
  (requirements.txt holds dev tools only). **Decision: stay on the
  standard library** — a parser-level DTD scan plus a size limit.

## Criteria

1. **One implementation.** A new root module `xml_input.py` holds the size
   limit, the DTD rejection, the shared `--max-input-bytes` flag and the
   refusal exception. Both scripts call it; neither keeps its own copy.
2. **Size limit paid before the read.** Read at most `max_input_bytes + 1`
   bytes and refuse an input larger than the limit. Default 64 MiB
   (67 108 864 bytes), larger than any Panorama export this project has
   seen. `--max-input-bytes N` on both CLIs; a non-integer or non-positive
   value is an argparse error (exit 2), not a traceback.
3. **DTD rejection at parser level.** Scan the prolog with
   `xml.parsers.expat`; stop at the root element start tag; refuse when
   the parser reports a DOCTYPE declaration. It must hold for every
   encoding the parser accepts (so the UTF-16 bypass is closed) and must
   not refuse a `<!DOCTYPE` that appears only in a prolog comment.
4. **Nothing else expands.** Keep the verified facts above in the module
   docstring, and pin with a test that an entity reference without a DTD
   is a parse error and not an expansion.
5. **Refusal is reported.** The message names the file, the limit and the
   measured value, and says how to raise the limit. Exit non-zero. No
   traceback.
6. **No output on refusal.** A refused input writes no output file, and an
   existing output directory keeps its contents.
7. **Parse the bytes that were checked.** The tree comes from the bytes
   that passed both checks — one read, no second read of a path, so
   nothing can change between the check and the parse.
8. **Both scripts behave the same.** Same message text, same non-zero
   exit, same "no output" behaviour, same flag name and default.
9. **Existing hostile input still refused.** The F1.7 billion-laughs and
   XXE fixtures still fail cleanly with "DTD" in the message, and a
   malformed file still reports "not well-formed".
10. **Tests.** Over-limit refused, at-limit accepted (exact boundary),
    message content, no partial output, both scripts, the UTF-16 DTD
    bypass closed, a comment `<!DOCTYPE` accepted, the default limit
    documented and shared, and the F1.7 hostile fixtures still refused.
11. **Gates:** ruff clean, pytest green, terraform validate green (no
    generated-output change is expected from F3.8).

## Result (2026-10-08)

All eleven criteria hold. `ruff check .` clean, 419 tests pass (24 of them
new in `tests/test_safe_input.py`), `terraform validate` still green, and
both golden sets are byte-identical.

Evidence per criterion:

- 1: `xml_input.py` is imported by both scripts; the duplicated text read,
  the `re` import in the splitter and `ET.parse(path)` are gone.
  `test_parser_and_splitter_use_the_shared_default` pins the shared
  function object, the shared default and the shared refusal.
- 2: `test_over_limit_input_is_refused`, `test_at_limit_input_is_accepted`,
  `test_one_byte_over_the_limit_is_refused`,
  `test_nonpositive_limit_is_an_argparse_error`.
- 3: `test_utf16_dtd_is_refused`, `test_clean_utf16_input_is_accepted`,
  `test_dtd_in_a_prolog_comment_is_not_a_refusal`,
  `test_external_id_dtd_is_refused`.
- 4: `test_entity_reference_without_a_dtd_is_a_parse_error`.
- 5: `test_refusal_names_the_file_the_limit_and_the_measured_size`,
  `_assert_clean_failure` in every refusal test.
- 6: `test_refusal_writes_no_output_files`,
  `test_refusal_leaves_an_existing_output_directory_untouched`.
- 7: `test_parse_reads_the_file_once`, `test_read_input_returns_the_whole_file_at_the_limit`.
- 8: `test_both_scripts_print_the_same_refusal`,
  `test_splitter_applies_the_same_size_limit`,
  `test_both_scripts_document_the_shared_default`.
- 9: `test_hostile_fixtures_are_still_refused`, and the F1.7 suite
  (`tests/test_robustness.py`) passes unchanged.

Two decisions came out of the work:

- **No new dependency.** `defusedxml` was rejected: it does not cover the
  size risk, the standard library covers the DTD risk at parser level, and
  both scripts stay standard-library only.
- **The refusal never labels the DTD ids.** pyexpat calls
  `StartDoctypeDeclHandler` with `(name, systemId, publicId, standalone)`,
  which is not the order the Python documentation states, so the message
  says only "with an external id" rather than naming a value that could be
  the wrong one.
