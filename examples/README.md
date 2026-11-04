# Examples Index

The layout rule is in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §1.1: `examples/` holds the
sample input and the two example text files, and this file is the index that names every document under it.

| Document | What it is for |
|---|---|
| [sample_panorama_config.xml](sample_panorama_config.xml) | The committed sample input. The quick start script runs it, and `../tests/test_golden_files.py` runs it for the `sample` golden case |
| [example_terraform_output.txt](example_terraform_output.txt) | Where the sample output lives: it points at the golden set, which is the canonical sample output |
| [example_interface_report.txt](example_interface_report.txt) | A real `INTERFACE_MIGRATION_REPORT.txt` from the kitchen-sink fixture run |

The canonical sample output is the golden set `../tests/golden/`, because it pins the bytes of a real run. A
sample run writes no committed output here: `../terraform_output/` is only the default value of
`--output-dir`, and the quick start writes `terraform_example/`, which is not committed.

Run the sample input:

```bash
python3 src/panorama_to_terraform.py examples/sample_panorama_config.xml --output-dir terraform_example
```

The developer scripts live in [`../tools/`](../tools/): `tools/quick_start.sh` runs this sample, and
`tools/build_kitchen_sink.py` prints the tree it assembles from the committed fixtures (the rule is in
[`../tools/README.md`](../tools/README.md)). Neither is part of the converter.
