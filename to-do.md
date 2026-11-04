# To Do

The current feature is the `tools/build_kitchen_sink.py` rebuild finding, which `backlog.md` names and this
feature promotes. The tool assembles `tests/fixtures/kitchen_sink.xml` from the files in the corpus, so the
corpus set and the tool's set must be the same set, and the committed fixture must be what the tool writes.

Pieces:

- [ ] Decide the file set the tool reads. The corpus pins read the fixtures that are not hostile
      (`tests/test_data_file_gate.py`, `tests/test_data_blocks.py`), so the tool must skip the two files it
      cannot parse, and that skip must be a rule the tool states, not a list of names.
- [ ] Decide whether the committed `tests/fixtures/kitchen_sink.xml` is the tool's output. Measured
      2026-11-04: it holds no `ip-with-expand` entry, so a rebuild from the current fixture set answers a
      different file.
- [ ] If the tool owns the fixture, regenerate the fixture and the golden set for the case in the same
      commit, because the goldens are the bytes of a run on the fixture. If it does not, state what the tool
      is for, and keep the committed file as the input.

The rule this feature rests on is `docs/ARCHITECTURE.md` §1.1 for the layout and the F3.8 read order in
§3. `tools/README.md` names the tool and its files.

## Rules the layout keeps

- `docs/ARCHITECTURE.md` §1.1 is the owner document for the layout. `AGENTS.md` names the tracking markdown
  set, and each index names every document under it, so a file outside an index is a finding.
- Import rule: `src/` is one flat namespace, so a module may import any `src/` module without a cycle. The
  one test that checks the rule reads only `src/`. A test may import `src` modules and `tests/conftest.py`
  through `importlib`; nothing under `tests/` may import another test module. `src/` may not import from
  `tests/`.
- The corpus is the directory the scan runs over. A hostile fixture in it changes the set the tool prints for
  other fixtures, so pins that state the printed set name the fixture count.
