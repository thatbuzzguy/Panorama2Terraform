# Documentation update pass acceptance criteria — documents current, planning files cleared

This pass updates the documentation set and the tracking markdown. It writes no tool code, so no test,
golden, fixture, response or tflint file moves. Two goals: every document states the features and options
that exist today, and no planning file keeps a feature that is finished.

Closed conditions:

1. The gate for this pass is `python3 tools/check_documents.py` reporting no finding, plus the full
   `python3 -m pytest`, `ruff check .` and `ruff format --check .`, read single-threaded. The pass adds no
   pin, so the pin count must not move.
2. The tracking markdown rule (`AGENTS.md`) is that completed epic, phase, feature and task information is
   removed after the epic or phase is complete, and that the git history is the record. So the pass removes
   finished work from `PLAN.md`, `to-do.md`, `backlog.md` and the completed-piece history in `agent-status.md`;
   what stays in each is the open work, the still-current rules, and the measurement.
3. `AGENTS.md` is aligned by the user's decision: the status file stays `agent-status.md`, so the
   `agent-status.html` line in the working-tree `AGENTS.md` is corrected to name the markdown status file.
   The rest of the working-tree `AGENTS.md` is the user's edit and is left as written.

Criteria for the documents:

1. `docs/USAGE_GUIDE.md` names every entry point that exists, so the scope line covers the path 2 entry
   point `src/api_to_terraform.py` beside the converter and the splitter, and the guide states how that entry
   point runs and which arguments it accepts (`shared_arguments`, so no input file and no source arguments).
   The rule itself stays owned by `docs/API_CONVERSION_PATH.md` §6; the guide links to it.
2. `docs/USAGE_GUIDE.md` §Post-run sanity gate names every check in `sanity_checks.CHECK_ORDER`. The eight
   checks the table currently omits — `import_blocks`, `scope_blocks`, `actions`, `protocol_object`,
   `filter_blocks`, `certificate_blocks`, `round_trip`, `request_set` — are added with the severities the
   module states, read through `README.md` §Post-run sanity gate, which is the full table.
3. `README.md` names the rule data pair in the data-file inventory and in the unit directory listing, so the
   file set matches what the run writes inside the unit directories (`rule_data.data_file` and
   `rule_data.printed_file`, the `.json` and `.csv` forms of the declared rows).
4. `README.md` names the path 2 entry point as a run choice beside `--source api`, one line, linking to
   `docs/API_CONVERSION_PATH.md`.
5. Every feature and option present in `src/` that a document should name is checked against the four
   indexes and the documents: the CLI flags, the two file sets, the gate rule set, and the entry points. The
   audit findings are applied or recorded as findings, not silently left.
6. `docs/README.md`, `examples/README.md`, `tools/README.md` and the `docs/` documents keep the one-owner rule:
   the pass adds no restatement of a rule whose owner is elsewhere; new sentences link to the owner.

Criteria for the planning files:

7. `PLAN.md`: Epic 8 is recorded as closed at `dc0c245` (F8.10, read through `agent-status.md`), and the
   completed epic sections (Epic 6, Epic 7, Epic 8, Epic 9) and the closed-item Sequencing section are
   removed; the git history holds them. What stays is the current state, the goals, and the open Epic 10
   with its open pieces.
8. `to-do.md`: the completed Piece 24 line is removed; the open pieces E10.2 and E10.3 stay, with the blocked
   items and the layout rules.
9. `backlog.md`: the closed audit sections (measured 2026-11-11 and 2026-11-12, all closed) are removed; the
   scan-scope entry keeps the rule, not the closure narrative of the gaps it closed; the open findings stay.
10. `agent-status.md`: the completed-piece history paragraphs (Pieces 3 to 15, the audit series, the Epic 6
    and Epic 9 piece detail) are removed; the file keeps the current position, the open items, the document
    rules, and the watch list.
