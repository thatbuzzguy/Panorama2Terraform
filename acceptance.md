# Decision — the `lib_docs/` reference — acceptance criteria

This slice decides one open backlog item: `AGENTS.md` points to `lib_docs/` for API cheat sheets, and the
directory is not in the repo. Add the cheat sheets, or remove the reference.

## Facts

- The tool is standard library only. `requirements.txt` holds no runtime package, and every import in `src/`
  is the standard library or a sibling in the flat `src/` namespace. There is no pinned third-party library
  whose API a cheat sheet could record.
- The input boundary reads through `xml.etree` and the expat handler (`xml_input.py`) and the api producer
  reads through `urllib.request` (`source_fetch.py`). These are standard-library facts the code and its tests
  already rely on.
- `docs/ARCHITECTURE.md` §1.1 is the layout owner: the root holds `AGENTS.md`, the tracking markdown, the
  readme indexes, the license files and the tool-config files, and every other document lives in `docs/`.
  Each index names every document under it, so a `lib_docs/` directory at the root would be a finding
  against the rule, and a cheat sheet outside an index would be a second finding.
- The provider facts the cheat sheets would restate already live in the pins and the documents:
  `backlog.md` "Design Decisions (provider facts, re-measured 2026-10-31)", `docs/RESOURCE_MAPPING.md`, and
  the machine-readable tables in `src/`. The project rule is that a document describes a table and never
  restates it, so a cheat sheet would be a second copy of facts the pins already hold.

## Decision

Remove the reference. There is no library set the reference names, and the cheat sheets it promised are
either standard-library facts the code already relies on or provider facts the pins already hold. No
cheat sheet is added, and no new document is placed in `docs/`. `AGENTS.md` keeps one short direction that
states the standard-library rule, so the reference is not re-added by habit.

## Criteria

1. `AGENTS.md` names no `lib_docs/` directory and no location that breaks the layout rule.
2. `backlog.md` no longer carries the closed item, and the tracking markdown records the decision:
   `to-do.md` ticks the piece, `agent-status.md` states the position, and `PLAN.md` names the next feature.
3. No test reads `AGENTS.md` or scans the root markdown or an index, so no pin changes. The checked facts
   stay true after the change.
4. `ruff check .` is clean and `python3 -m pytest` passes 1443 tests.
5. The commit message starts with `Housekeeping:` (the style `git log` shows for this work) and states the
   decision and the reason.

## Result

Met. `AGENTS.md` names `lib_docs/` nowhere; the direction is replaced with the standard-library rule. The
closed item is removed from `backlog.md`, and the tracking markdown names the console line shape as the
next open piece. No test changed, because no test reads `AGENTS.md` or scans the root markdown. `ruff check .`
is clean and `python3 -m pytest` passes 1443 tests.
