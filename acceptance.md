# Acceptance Criteria — F5.6 Terraform state as a source

The feature reads a Terraform state document as a declared reference source, in the same
position the declared parent source holds (F5.4), and reports two facts:

- the ownership fact: which entries another workspace already owns;
- the drift fact: which owned entry holds a value this run does not match.

Both are property-level facts, so the F4.4 property scan reads them: the entry must be covered
by a matrix row, on both sides.

The state source is a reference source. The run does not generate output from it, so no `.tf`
byte changes, and the golden sets are unchanged.

## AC-1 The state shape a scan can read

1. The door keeps its two byte checks for every source kind. The size check runs on the state
   bytes, and the DTD check runs on the state bytes too. A JSON document has no prolog, so the
   DTD check refuses nothing for it: `<!DOCTYPE` inside a JSON value is not a refusal.
2. The tree rule does not apply to a JSON document. The container table, the parent walk, and
   the expat line map are keyed on the ElementTree tree, so a state document gives the scan one
   shape per entry: the entry name, the matrix row, the properties, and the position.
3. A state entry is one instance object in the state document. Its matrix row is the row keyed
   by its resource type, through `entry_coverage.MATRIX_BY_RESOURCE`: the same table, the same
   key, no second naming rule. Its properties are the attribute keys it holds, read with the
   F4.3 rule (the entry name and the scope facts are identity, not content; an empty value is
   not a property).
4. A state entry has no source line, because only the expat handler path records one. Its
   position is its Terraform resource address: `type.name`, or `module.path:type.name` inside a
   module instance.
5. A state document is refused when its bytes are not JSON, when the document is not an object
   with a `resources` array, or when a resource object names no `type` or no `name`, because the
   scan cannot key it. A refusal is an input refusal (exit 1) and writes no record.
6. A nested block is read as an object, or as a one-element list of an object, because the
   provider writes a nested block either way.

## AC-2 The ownership fact

1. The key is §2.1 identity as the F3.9 rule reads it: the matrix row, the entry name, and the
   four declared scope facts (§2.2). `Shared` is the parse fallback, so the key uses the facts
   the source declares, never the fallback.
2. The state document gives its scope facts from the `location` block it holds, through the
   block names `LOCATION_SCHEMA` declares. The `shared` block names the shared section, which
   declares no name, so it fills no fact. `localhost.localdomain` is the PAN-OS "this device"
   placeholder, so it names no device (F3.5).
3. The first state entry that carries a key wins, in document order, because one run entry is
   one finding (the F5.4 rule).
4. The scan scope is the F4.4 rule on both sides: an entry no matrix row covers is not a
   finding, and a state resource whose type has no matrix row is not in the index.
5. A run with no declared state source has no state to read, so it reports no ownership fact.

## AC-3 The drift fact

1. A drift fact is a property the matrix row declares, that both sides hold, with values that
   are not equal. A property one side does not hold is not compared.
2. A property the two sides name differently is not compared. The matrix row names the key the
   emitter reads; the state names the attribute the provider stored. No mapping rule exists, so
   no comparison is made. The parse key `tags` and the provider attribute `tag` are this case.
3. A value is compared as the two sides hold it. Member order is part of the value, so a member
   list in a different order is a drift finding.
4. A drift fact needs an ownership fact: an entry the state does not own cannot drift, so the
   drift section is a subset of the ownership section.
5. The state scan is not an output, so its read does not count as a property an output used
   (F4.4). It reads captured values through the non-recording read, so the property section is
   unchanged by the state scan.

## AC-4 Where the facts print, and the exit code

1. Two sections in `CONVERSION_REPORT.txt`, after the shadow section, in this order: ownership,
   then drift. Each section prints only when it has a finding.
2. Fixed line shapes:
   - ownership: `line <n>  <object type>/<entry name>  <matrix row>  state source: <name> (<address>)`
   - drift: `line <n>  <object type>/<entry name>  <matrix row>  state source: <name> (<address>)  value differs: <property> (<run value> vs <state value>)`
   The line names the run entry's source line, the same line the entry rows print. Values are
   printed as their JSON text, so a line stays on one line. Properties are in sorted order.
3. The lines are grouped by the F3.9 scope rule, the same rule the other report sections use.
4. The console prints no state line (the console prints the gap lines only). Both facts are
   operator actions, so neither changes the exit code, which the F4.1 gate still decides.

## AC-5 The read stays offline

1. A state read is a file read: no network rule changes, and `--offline` still means the api
   producer reads the cache only.
2. Every test uses a committed fixture. No test opens a connection.

## AC-6 The record

1. `kind` names the source kind, `state`. `scope` names the workspace the run declared, or the
   default (`xml_input.DEFAULT_SCOPE`). The record shape does not change, so `parse_records`
   reads a state record with no new field.
2. A state source has no request and no cache entry, so those two fields are `-`, and the record
   references nothing: it prunes nothing.
3. The record file holds one record per source read, in read order: the main source, then the
   declared parent, then the state source.
4. The byte facts are the bytes the door checked, so the state record names a file a reader can
   reopen.

## AC-7 CLI argument rules

1. `--state PATH` names the state document. It applies to any source kind, because the state
   source is a reference source. A missing state file is an input refusal (exit 1).
2. `--workspace NAME` names the workspace the state document belongs to. It applies to the state
   source only, so it is an argument error (exit 2) without `--state`.
3. The gates that do not change: `ruff check .` clean, `pytest` green, both golden sets
   byte-identical, report and record determinism, exit codes unchanged (input refusal 1, argument
   error 2), every test offline.

## AC-8 Determinism

Two runs with the same arguments on the same bytes write the same bytes. The state index keeps
the first entry for a key in document order, and the findings are sorted by line, then object
type, then name.
