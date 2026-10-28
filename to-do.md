# To Do

F6.2 (ownership as data) is complete. Acceptance criteria are in `acceptance.md`; the rules landed in
`ownership.py`, `main()`, the service parse and emit legs, `resource_mapping.py`, and
`tests/test_ownership.py`.

Pieces, all done:

1. [x] Measure the corpus for the repeated-name groups and the flag, so the decisions rest on a
   measurement (acceptance.md Decision 2 rule 8, AC-3.7).
2. [x] Write the acceptance criteria for F6.2 (`acceptance.md`).
3. [x] `ownership.py`: the row shape, the scan scope, the owner rule, `render`, `parse_rows`, and the
   report line shape.
4. [x] Close the service extraction gap: capture `disable_override` in `parse_service_objects`, emit it
   in `generate_service_objects`, and add the property to the `panos_service` matrix row.
5. [x] New fixture `tests/fixtures/ownership_override.xml`: the shared entry plus the device-group entry,
   with and without the flag, and a service entry that carries the flag.
6. [x] `main()`: write `OWNERSHIP.json` when the rows have content, and pass the findings to the
   conversion report section.
7. [x] `tests/test_ownership.py`: the row scope, the declaring unit and the join, the owner rule, the
   service leg, the report finding, determinism, and the corpus no-false-positive set.
8. [x] Gates: `ruff check .`, `pytest`, both golden sets byte-identical, exit codes unchanged.
9. [x] Docs: `docs/CODEBASE_ASSEMBLY.md` §2, §4, §5 and §14, `docs/ARCHITECTURE.md` (§1 module table,
   §3.5, §4.5 section order), `docs/USAGE_GUIDE.md` (the output file table and the record section),
   `README.md` (the file list), `PLAN.md`, `backlog.md`, `agent-status.md`.
10. [ ] Commit: "F6.2: ownership as data, the override rule".

Still open for Epic 6, out of scope for F6.2: the directory write path, the edge list (F6.3), the
import blocks (F6.4), and the gate rule that reads a data file.
