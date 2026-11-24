# Device Group Splitting

**Question:** does the tool split a Panorama export by device group?

**Answer:** yes, with `split_device_groups.py`. It is optional pre-processing.
The converter handles a full export on its own, so split only when you want one
Terraform directory per device group.

The document index is in [README.md](README.md). The migration workflow,
including the multi-virtual-router case, is in
[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).

## Two-step process

```bash
# 1. One XML file per device group
python3 src/split_device_groups.py panorama_export.xml

# 2. Convert each file
python3 src/panorama_to_terraform.py split_configs/dg_internet.xml --output-dir internet-tf
python3 src/panorama_to_terraform.py split_configs/dg_dmz.xml --output-dir dmz-tf
```

The default output directory is `split_configs` inside the input file's
directory. `--output-dir` (or `-o`) sets another one. Both scripts take the same
`--max-input-bytes` input check, and a refusal writes nothing, including the file-name
collision the splitter refuses.

## What each split file holds

Each output file is a `config` root with:

- the device group entry, copied as it appears in the source
- the shared section, so a device group can still reference a shared object.
  When the export has several `shared` sections, the splitter merges them: the first
  occurrence of a path is the container, an entry from a later section is written at
  the path the entry sits at, and the dedupe reads the pair (path, name) at the level the
  path names, so one name at two depths is two entries. This is the same level rule the
  parse set states for a `member` list ([ARCHITECTURE.md](ARCHITECTURE.md) §2.3). A section
  that states no entry writes no container, so a split file carries content only.
- the templates and template stacks that target one of the device group's own
  devices

The splitter names the output file through the §5 shape of the device group name, the
rule stated once in [`naming.py`](../src/naming.py) and read there rather than copied:
`DG/Internet` and `DG Internet` both read to `dg_internet.xml`, and a name that
sanitizes to nothing reads to `unnamed.xml`.

Two names that read the same shape name one file, so the run refuses the pair before it
writes and names both source names and the file name they read to. The run does not
number them, because the number a run would pick depends on the order the entries appear
in, which [ARCHITECTURE.md](ARCHITECTURE.md) §6 says is not a rule a run may depend on.

The bytes are the single writer's (`write_path.py`), so a split file is `LF` and ends with
the final line. The split files are not the unit set or the codebase root set
([CODEBASE_ASSEMBLY.md](CODEBASE_ASSEMBLY.md) §14), so the splitter keeps its own output
directory and states no writer of its own. Pinned by `tests/test_write_path.py`
`test_the_splitter_writes_through_the_single_writer` and `tests/test_split_device_groups.py`
`test_a_split_file_is_the_text_the_single_writer_writes`.

## The join rule

A device group, a template, and a template stack belong together when the export
lists the same device under each:

```
device-group/entry/DG-Internet/devices/entry/fw-1.example.com
templates/entry/HQ-Networks/devices/entry/fw-1.example.com
```

`HQ-Networks` is copied into the file for `DG-Internet`, even though the two names do not
resemble each other. A device group that lists no device, or whose devices no
template or template stack targets, gets no template, and the splitter prints
that fact. The old code matched a `DG-` prefix and a name substring; both matched
names instead of facts, and both are gone.

The tables the join reads are keyed by the source line the read layer records (F4.2), as
§2.3 states, so one entry is one row and a repeated name is not answered by one entry. A
row answers only the devices of the entry it names, and the join answers its rows in source
line order, because §6 preserves the order the input states. Two entries that state one name
read one file name, so the run refuses them before it writes.
Pinned by `tests/test_split_device_groups.py` `test_the_splitter_tables_are_keyed_by_the_source_line`,
`test_two_entries_with_one_name_are_two_rows_that_answer_their_own_devices`, and
`test_the_join_answers_the_rows_in_source_line_order`.

The run writes one container per path, and a `shared` section that states no entry writes no container, so a split
file carries content only. Pinned by `tests/test_split_device_groups.py`
`test_the_run_writes_one_container_per_path` and `test_an_empty_shared_section_writes_no_container`.

The splitter copies every element with `copy.deepcopy`. `ElementTree.append` does
not reparent: it keeps no parent bookkeeping, so appending an element that already
has a parent makes one element a child of two trees, and a later change to either
tree shows in both.

## Reading the split file back

The converter reads a split file as a normal export. The device group sits under
`devices/entry/localhost.localdomain`, which is the PAN-OS placeholder for "this
device", so no `ngfw_device` is written for those entries. The `location` block
names the device group, or the template the splitter copied.

Run the gate on the converted output. The splitter writes XML, so it has no `.tf`
to check and no gate run.

## Output example

```
$ python3 src/split_device_groups.py panorama_export.xml

Found 3 device groups:
  - DG-Internet
  - DG-DMZ
  - DG-Guest

Splitting configurations into: split_configs

Processing device group: DG-Internet
  - copied template: HQ-Networks
  ✓ Saved to: split_configs/dg_internet.xml

Processing device group: DG-DMZ
  - no template or template-stack targets this device group's devices: none copied
  ✓ Saved to: split_configs/dg_dmz.xml

Processing device group: DG-Guest
  ✓ Saved to: split_configs/dg_guest.xml

✓ Successfully split 3 device groups
```

The names the run prints for a group are the source names, because the run prints what the
row holds; the file name is the §5 shape of that name.

A single-firewall export has no device groups, so the splitter reports that and
exits non-zero. Convert such an export directly.

## Batch conversion

```bash
python3 src/split_device_groups.py panorama_export.xml

for xml in split_configs/*.xml; do
    base=$(basename "$xml" .xml)
    python3 src/panorama_to_terraform.py "$xml" --output-dir "${base}-tf"
done
```

## Troubleshooting

| Symptom | Cause and action |
|---|---|
| "No device groups found" | The export came from a firewall, not Panorama, which is the firewall export row of [`../src/input_shapes.py`](../src/input_shapes.py). Run the converter on it directly. |
| "two device group names read one file name" | Two source names read the same §5 shape, so they name one file. Rename one of them in the export. The run writes nothing, because the number it would have to pick depends on the entry order. |
| No template copied | No device appears in both the device group and the template. Check both device lists. If Panorama really does not link them, add the device to the template, or copy the template section by hand. |
| Shared objects missing from a split file | The source had no `shared` section. A split file copies the shared section only when the export has one. |

The shape the splitter read is a row of [`../src/input_shapes.py`](../src/input_shapes.py), and the table states no
line for the splitter today: the line that names the row set the splitter read is pending Piece 13A.2
([INPUT_SHAPES.md](INPUT_SHAPES.md) §3 and §4).
