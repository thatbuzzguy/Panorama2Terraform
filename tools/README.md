# Tools Index

The layout rule is in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §1.1: `tools/` holds the developer
scripts, and this file is the index that names every document under it. Neither script is part of the
converter, so neither uses the `src/` import rule: `build_kitchen_sink.py` imports no tool module.

| File | What it is for |
|---|---|
| [quick_start.sh](quick_start.sh) | Runs the committed sample input from `../examples/` and prints the reports. It resolves `src/` and `examples/` from the repository root, so it runs from any directory |
| [build_kitchen_sink.py](build_kitchen_sink.py) | Assembles the fixture corpus in `../tests/fixtures/` from the committed files. It writes fixtures, which a golden set reads, so its output is checked in and deterministic |

Run the quick start from the repository root:

```bash
bash tools/quick_start.sh
```
