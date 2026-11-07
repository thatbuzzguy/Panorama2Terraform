# Acceptance criteria — F8.1, the accepted request shapes (Epic 8, Phase 8A)

Scope: `src/source_fetch.py` (the device fact shape and its wrapper rule), the one scope path
definition in `src/container_coverage.py`, and the pins that hold both. No module is added, no
fixture is committed, and no parse method runs over an op response: the committed response harness
is F8.4, and the device facts in `docs/API_CONVERSION_PATH.md` §4 stay blocked. Path 1 is unchanged
except the one wording the CLI prints from the scope path set.

## 1. The three accepted request shapes

1.1 `source_fetch.py` states the three shapes as data: the whole-config export
(`type=export&category=configuration`), the per-scope read (`type=config&action=get&path=<scope
path>`), and the device fact shape (`type=op&cmd=<command>`). One shape per `type` value, so the
wrapper decision reads a response against the shape its own request states.

1.2 The request states its shape through what it declares: a command is the device fact shape, a
path is the per-scope shape, and nothing else is the whole-config export. The params the request
identity hashes are the words its shape states, plus the part it declares, so the identity names
the shape and no shape is guessed from what a response looks like.

1.3 The identity rule is unchanged: host and sorted params, never the key. Each op request gets its
own cache entry, the same rule the declared path already has.

1.4 A command value reaches the request URL encoded, because a command is words with spaces and an
unencoded query is not a request. The identity string is the plain sorted shape, because the record
reads it as data.

## 2. The op wrapper rule

2.1 One accepted response shape for an op request, stated in `source_fetch.py`: `result` holds
exactly one element, and that element is the element the command names — its first word. `result`
becomes the root, read as the place the command names, the same way the per-scope rule reads the
place the path names.

2.2 A response that does not match its own command is refused, not guessed: a root that is not
`result`, a `result` that holds nothing or more than one element, and the `config` element, which the
whole-config shape names. An element the command does not name is not refused here, because the fetch
layer states no command-to-element table (see 2.6). No cache entry is written for a refused response.

2.3 The response success check (type `success`, code `0`) runs for the third shape as well, before
the cache entry is written.

2.4 The origin and the line map are the same objects after the unwrap, so a report line still names
the line the response bytes carry.

2.5 An op response is not a config source: no scope path comes from it, the source states no scope,
and the container table names no row for the command element, so the envelope rule (the envelope is
never a scanned container) is unchanged.

2.6 The op shape rule checks the shape, not the element name: `result` holding any single element
passes the shape rule, because `source_fetch.py` states no command-to-element table and guesses
none. Which element a command names is checked by the response-to-request join (F8.3), which this
piece does not build. A response read by an op request is refused when it is not the op shape: a
root that is not `result`, a `result` that holds nothing or more than one element, and the `config`
element the whole-config shape names.

## 3. The pins for the op shape (`tests/test_source_fetch.py`)

3.1 `test_the_request_states_which_of_the_three_shapes_it_is` — the three shapes, and the params
each one states in the request identity.

3.2 `test_an_op_response_holds_the_one_element_the_command_names` — the accepted shape, `result` as
the root, the same origin and line map, no scope stated, and the cache entry holds the bytes as
they arrived.

3.3 `test_an_op_response_that_breaks_the_op_shape_is_refused` — no element, more than one element,
the `config` element, and a root that is not `result`; no cache entry for a refused response.

3.4 `test_the_op_shape_checks_the_shape_and_the_join_checks_the_element_name` — the boundary between
this piece and F8.3.

3.5 `test_the_response_check_runs_for_the_op_shape` — the success check before the cache write.

3.6 `test_the_command_is_part_of_the_request_identity` — key-free, one entry per command, and the
command reaches the URL encoded.

3.7 `test_an_op_response_is_not_a_config_source` — the scan reads no container from it, and the
container table states no row for a fact element.

## 4. The scope path definition and the `predefined` path

4.1 `container_coverage.SCOPE_PATH_ROOTS` is the one definition that validates a scope path, so the
decision is stated inside that set and nowhere else. The set gains `predefined`, so a path that names
the built-in section is a scope path and the run can read it. Pinned by
`tests/test_container_coverage.py::test_a_predefined_path_is_read_by_the_one_scope_path_definition`.

4.2 `predefined` is read as a place, not as a scope: `SCOPE_CONTAINERS` keeps the five scope facts,
so an entry whose container is `predefined` answers no scope fact and `is_scope_entry` answers False
for it. The path shape is unchanged: `/<place>` or `/<place>/entry/<name>`, so a path that names a
container inside `predefined` stays outside the shape rule and is recorded as a finding.

4.3 The scan rule for a built-in container is unchanged: an entry container under `predefined` is not
a finding, and the pin that holds it
(`tests/test_container_coverage.py::test_predefined_entries_are_not_findings`) passes unchanged.

4.4 The CLI prints the set through the one definition, so the argument error names `predefined`. Its
wording says a place the scope path definition validates, because the set already holds `shared`,
which is a place and not a scope container.

## 5. The pins that read the `src/` set

5.1 The writer scan, the environment-name scan, the console-line scan and the second-naming-rule scan
pass unchanged. `source_fetch.py` writes only through `write_path.py`, states no console line, defines
no naming rule, and stays the only module that states the environment name.

5.2 No test calls the network. The producer stays injectable, as `tests/test_source_fetch.py` does
today, and the fetch layer imports the standard library only.

5.3 Two existing assertions move to the new spec, both because the identity now carries the words
the shape states, so the declared path is no longer the last part of the sorted identity:
`tests/test_source_fetch.py::test_the_declared_path_is_part_of_the_request_identity` and
`tests/test_provenance.py::test_the_record_file_holds_one_record_per_source_read`. One existing
docstring says the wrapper has one branch per shape rather than two. No other existing pin changes.

## 6. The checks

6.1 `ruff check .` is clean.

6.2 `python3 -m pytest` passes with no skip: the baseline 1567 pins, plus the op-shape pins in
`tests/test_source_fetch.py` and the one pin for the `predefined` decision in
`tests/test_container_coverage.py`.

6.3 The commit is one ASD-STE100 message. When a rule lands, `docs/API_CONVERSION_PATH.md` §2.1 states
it in the present tense and names the pin, and the completed piece leaves `to-do.md`.
