# Tools Index

The layout rule is in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §1.1: `tools/` holds the developer
scripts, and this file is the index that names every document under it. Neither script is part of the
converter, so neither uses the `src/` import rule: `build_kitchen_sink.py` imports no tool module.

| File | What it is for |
|---|---|
| [quick_start.sh](quick_start.sh) | Runs the committed sample input from `../examples/` and prints the reports. It resolves `src/` and `examples/` from the repository root, so it runs from any directory |
| [build_kitchen_sink.py](build_kitchen_sink.py) | Assembles the fixture corpus into one merged tree and prints it. It writes no file, so `../tests/fixtures/kitchen_sink.xml` stays the record the golden set reads |

## The rule the fixture assembler keeps

- The tool is a generator, not a pin. `../tests/fixtures/kitchen_sink.xml` is the record that the golden set
  and the corpus pins read, and the record is curated by hand, so the tool prints the tree it assembles and
  writes no file.
- The tool reads a fixture when the F3.8 input rule accepts it. A fixture that declares a DTD, or that the
  parse cannot read, is hostile input: it exists to trip the refusal, so it is not material for a merged
  corpus, and the tool skips it by rule, not by name. The tool states the DTD check itself, because `tools/`
  imports no tool module, and `tests/test_build_kitchen_sink.py` pins that the tool's decision agrees with
  `xml_input` for every committed fixture.
- The record is the result, so the tool never reads it as an input.
- The merge rule: an entry merges with the entry of the same name; a leaf with text always appends; another
  element merges with the element of the same tag, or appends. `tests/test_build_kitchen_sink.py` pins the
  rule, the read set, and that two runs answer the same bytes.
- The tool takes no command-line path, so it reads only the committed files, and its direct `ET.parse` call
  stays accepted (the F3.8 decision).

Run the quick start from the repository root:

```bash
bash tools/quick_start.sh
```

Assemble the corpus into a temporary file, so the record stays as the committed fixture:

```bash
python3 tools/build_kitchen_sink.py > /tmp/merged.xml
```
