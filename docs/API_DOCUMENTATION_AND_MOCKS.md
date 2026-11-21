# API documentation and the offline response set

Planning record for using the PAN-OS API documentation as a source for the committed response set
(`tests/responses/`), which `API_CONVERSION_PATH.md` §5 and `ARCHITECTURE.md` §1.1 own. This document
adds no rule; it states what the documentation can give the test set, what it cannot, and the pieces
that follow. It changes no owner document: the response-set rule stays in `API_CONVERSION_PATH.md` §5,
and this document links to it.

## 1. The current state of the API-related work

The fetch layer (F5.1 to F5.4, F8.1) and path 2 (F8.1 to F8.9) are landed. What exists today:

- The producer boundary: `source_fetch.py` reads bytes through `xml_input.parse_bytes`, keeps the F3.8
  checks inside the door, and caches the bytes the door parsed. Every test injects a producer, so no test
  calls a network and Goal 1 holds for the api path.
- The three accepted request shapes and one response shape each: the whole-config export, the per-scope
  read, the device fact (`SHAPE_PARAMS`). The response is checked against the request that made it, and the
  wrapper decision is the one place that names the element a shape reads.
- The committed response set (`tests/responses/`, F8.4): five files, one file per committed request,
  each named by its key-free identity hash and stating that identity in its prolog. One response is the
  per-scope membership read the scope index is built from; the device fact response shows the shape and
  names no live fact.
- Path 2 reads those bytes offline, and the gate's request-set rule reads the join against the index.

What is not built, and what the documentation question reaches:

- The response set is thin. It holds one response per accepted shape, not the shapes the error paths and
  the read paths can produce, so pins that state a shape can only show one instance of it.
- The facts `API_CONVERSION_PATH.md` §4 names stay blocked, each on the condition its table row states:
  the rulebase value string and the rule position (F3.5), the device serial and which element a command
  names, the per-device template variable override, and the built-in name table. The project's rule is
  that a piece cannot be written from a response the project does not hold, which is why these facts are
  in `backlog.md` and not in `to-do.md`.

## 2. What the documentation can state, and what it cannot

The official documentation (the PAN-OS and Panorama API Usage Guide, and the on-device documentation at
`https://HOSTNAME/restapi`) is a source for three kinds of fact, and only those three:

1. The request shapes. The XML API request types are documented per action, and the three shapes
   `source_fetch.SHAPE_PARAMS` states match the documented request types (`type=export`,
   `type=config&action=get&path=`, `type=op&cmd=`). Documentation confirms a shape the code already
   states; it cannot confirm a value the code reads from a live target, such as the accepted rulebase
   value string.
2. The envelope shape. The documented success response and the documented error response give the shape
   the wrapper decision reads: the status and code fields, the `result` element, the error fields, and the
   rule that the detail values can change between releases and should not be parsed. This is the shape side
   of the response check, and it is the half the committed set can show.
3. The resource and path vocabulary. The REST API resource URIs, the documented locations (shared,
   device-group, vsys, predefined), and the documented XPath syntax name the containers the container table
   already lists, so the documentation can verify that the scope-path set and the membership lists are the
   documented shape, not an assumed one.

A documented fact is not a live fact. The project's rule separates them: a pin may read a shape from a
committed response, but a value a live target states (the rulebase string, a device serial, the element a
command names for a specific command, how a device states a per-device variable override) needs a live
target. Documentation can state the shape a response for such a fact would have, so the mock work can close
the shape half of a §4 row and leave the value half gated on the live condition. The rule that a documented
response is an illustration, not a measurement, is already the pattern the committed op response follows
(`tests/test_api_requests.py::test_the_committed_op_response_shows_one_shape_and_names_no_live_fact`).

## 3. Mocking options

The harness already has one mock point: the injected producer, a callable that takes an `ApiRequest` and
hands bytes. The options below work through it and through the committed response set; none of them adds a
network call to CI, and none adds a third-party package (`source_fetch.py` stays standard-library only, so
an HTTP mocking library is not an option under the project's rule).

**Option A — a documentation-derived response builder (recommended).** A tool script under `tools/`,
the way `build_kitchen_sink.py` works: a generator, not a pin, that assembles response bytes from the
documented envelope shape plus content read from the corpus fixtures, and prints them without writing a
file. The committed response set then grows: one file per request the run needs, named by the identity
hash the record reads, and each prolog names the request and the fixture the content came from. This gives:

- error and edge responses as committed fixtures: the failed response, the response with no result
  element, the result that holds more than one element, a per-scope response whose element does not match
  its path — the shapes the refusal pins describe today through a bytes string built inside the test. A
  committed fixture makes the same bytes readable from both sides: the pin reads them through the injected
  producer, and a person can reopen them.
- the `predefined` read as a committed response, so the built-in name table has a home and the read that
  needs it has input, which `backlog.md` records as the condition for that row of §4.
- a rulebase read as a committed response: the shape side closes, and the value half stays gated on the
  live condition, stated as `<!-- doc-derived, pending live verification -->` in the prolog.

**Option B — a canned server behind the same seam.** A dict from request identity to response bytes, read
through the injected producer, that answers every request the scope index can make for one fixture. This is
the shape a fixture-driven mock server takes, but stated as data the door already accepts, so it keeps the
identity rule: the same request finds the same entry. It is the same as Option A with the bytes held in the
test set rather than committed as records; it does not give the readable-file property, so Option A is the
preferred shape.

**Option C — a real HTTP mock server.** Rejected for CI, for three reasons: it adds a network, which Goal 1
refuses for the test set; it needs a third-party package, which the standard-library rule refuses; and the
producer seam already answers the same fact without either. A real server is only worth reaching for when a
live target is in scope, and a live target is where the §4 facts already are.

The one documented thing that can enter the fetch layer as data is the error-code set: the documented XML
API error codes and REST API error codes are a stable set, so the response check could read a data table
for the codes the tool reports, rather than accepting only code 0. That is a small scope decision, so it
goes in `backlog.md` rather than a piece here.

## 4. What is required to finish the planned API features

Path 2's landed rules need no new work from this area. The open path-2 work is the piece order
`API_CONVERSION_PATH.md` §9 step 8 — the §4 facts — plus the findings `backlog.md` records for path 2. The
mock work changes the condition for two of them, and leaves the rest on the live target:

| §4 fact | What the mock work can close | What stays on the live target |
|---|---|---|
| rulebase per rule | the request shape and the response shape for a rulebase path, as a committed response | the accepted value string (F3.5) |
| rule position | the response shape that holds entries in document order | the rulebase value, so the position fact stays gated |
| device serial | — the command-to-element table is a live fact, so the mock can only show the shape | the element a command names, and the serial |
| per-device template variable override | — | how a device states it |
| built-in name table | the `predefined` response shape, so the read and its pin can be written from a committed response | the names themselves |

Three further requirements follow from the mock decision itself:

1. A committed response set that grows needs the identity rule to hold for every new file: the file name
   is the key-free identity hash the record reads as `cache_entry`, so the builder must compute the name
   through `source_fetch.py` rather than assemble a path. The harness pins in `tests/test_api_requests.py`
   already read this rule, so a grown set is read by the same pins.
2. A documented response must stay labelled as doc-derived, not as a measurement. The rule that the op
   response is an illustration is the pattern: the prolog names the request identity and the source of the
   content, and a pin that reads such a file may read the shape only, never a value a live target states.
3. The corpus boundary is unchanged: a committed response is not corpus material, so the scan and the
   fixture assembler never read it (`ARCHITECTURE.md` §1.1). A builder that takes fixture content into a
   response reads the fixture through the same rule the assembler keeps, and the response set stays its own
   set.

## 5. Piece shape, if this is taken into scope

Promoted to `PLAN.md` as Epic 12 only on decision. The pieces, in order:

- **12A, the builder**: the tool script, the documented envelope shape as data, and the rule that the
  builder writes no file and names each response by the request identity the record reads.
- **12B, the edge responses**: the refusal shapes as committed files, the pins moved from test-side bytes
  strings to the committed set, and the pins that read the same bytes through the injected producer.
- **12C, the doc-derived reads**: the `predefined` response, the rulebase-path response, and the pins that
  read them through the harness, each pin reading only the shape and naming the live condition.

Each piece needs the acceptance criteria written in `acceptance.md` before code, following the project rule.

## 6. Source list

- pan.dev XML API and REST API pages: pointers to the official guide, the version pages, and the on-device
  documentation at `https://HOSTNAME/restapi`.
- PAN-OS and Panorama API Usage Guide, 11.1: request structure, REST request and response structure
  (the success and error shapes this document §2 names), resource methods and query parameters (the
  documented location set), the XML API error codes, the REST API error codes, and the rule that the
  REST API covers a subset and needs the XML API or another interface to commit.
- The project's own owner documents, unchanged by this record: `API_CONVERSION_PATH.md` §2, §4, §5, §9,
  and `ARCHITECTURE.md` §1.1 and §3.
