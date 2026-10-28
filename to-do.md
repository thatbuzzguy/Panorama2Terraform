# To Do — F5.6 Terraform state as a source

F5.1 to F5.4 landed; their records are in the git history. F5.5 (read-through data blocks)
waits for `DATA_SOURCE_SCHEMA` verified against the provider. F5.6 is in progress, with the
acceptance criteria written in `acceptance.md`.

## Decisions taken

1. The state source is a **reference source**, in the same position the declared parent source
   holds (F5.4). `--state PATH` names it, and `--workspace NAME` names the workspace it belongs
   to. The run does not generate output from it, so no `.tf` byte changes.
2. The door keeps its two byte checks for every source kind; the parse step is chosen by the
   kind. A JSON document has no prolog, so the DTD check cannot refuse one. The tree rule does
   not apply, so the state source gives the scan one shape per entry: the entry name, the matrix
   row, the properties, and the position (the Terraform resource address, not a source line).
3. The ownership key is §2.1 identity as the F3.9 rule reads it: the matrix row, the entry name,
   and the four declared scope facts, read from the `location` block the state holds.
4. The drift fact compares only a property the matrix row declares that both sides hold by the
   same name. No name mapping rule exists, so `tags` (parse) and `tag` (provider) are not
   compared. Recorded as a limitation below.
5. Both facts print in `CONVERSION_REPORT.txt`, in their own sections after the shadow section.
   No console line. Neither changes the exit code.
6. The record shape does not change: `kind` is `state`, `scope` names the workspace, `request`
   and `cache_entry` are `-`.

## Pieces

- [ ] `state_input.py`: the state producer — the byte checks through the door, the JSON read,
      the entry shape, the refusals, the resource address.
- [ ] `state_coverage.py`: the state index (identity key), the ownership scan, the drift scan,
      the two line shapes, the two headings and rule paragraphs.
- [ ] `entry_coverage.py`: `value` read on the recorded object that does not count as an output
      read, so the state scan cannot move a property finding.
- [ ] `main()`: `--state` and `--workspace`, the state read, the scan, the two report sections,
      the state record in read order.
- [ ] Fixture: `tests/fixtures/state_workspace.json` — one owned entry with a differing property,
      one owned entry with no difference, and entries the scan must not read.
- [ ] Tests: `tests/test_state_input.py` (the shape, the checks, the refusals, the record) and
      `tests/test_state_coverage.py` (the two facts, the sections, the console, the exit code,
      the CLI rules, determinism).
- [ ] Docs: `docs/ARCHITECTURE.md` §1 module table, §3 the state producer, §3.2 the two facts;
      `docs/USAGE_GUIDE.md` CLI table and report list; `README.md` report list.

## Open items for this feature

- The ownership key does not name a scope level the state cannot state. A state `location` block
  names one level, so a run entry the export places at a different level is a different key. The
  backlog carries this.
- A property the two sides name differently is not compared. A mapping rule needs the provider
  attribute names as data (`lib_docs/` reference, recorded in the backlog).

## After F5.6

F5.5 (read-through data blocks) is the next feature, with its pieces recorded above in the
`backlog.md` provider facts.
