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
python3 split_device_groups.py panorama_export.xml

# 2. Convert each file
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-tf
python3 panorama_to_terraform.py split_configs/DG-DMZ.xml --output-dir dmz-tf
```

The default output directory is `split_configs` inside the input file's
directory. `--output-dir` (or `-o`) sets another one. Both scripts take the same
`--max-input-bytes` input check, and a refusal writes nothing.

## What each split file holds

Each output file is a `config` root with:

- the device group entry, copied as it appears in the source
- the shared section, so a device group can still reference a shared object.
  When the export has several `shared` sections, the splitter merges them and
  keeps one entry per name inside a container.
- the templates and template stacks that target one of the device group's own
  devices

The splitter names the output file from the device group name, with `/` and a
space replaced by `_`: `DG/Internet` and `DG Internet` both write
`DG_Internet.xml`.

## The join rule

A device group, a template, and a template stack belong together when the export
lists the same device under each:

```
device-group/entry/DG-Internet/devices/entry/fw-1.example.com
templates/entry/HQ-Networks/devices/entry/fw-1.example.com
```

`HQ-Networks` is copied into `DG-Internet.xml`, even though the two names do not
resemble each other. A device group that lists no device, or whose devices no
template or template stack targets, gets no template, and the splitter prints
that fact. The old code matched a `DG-` prefix and a name substring; both matched
names instead of facts, and both are gone.

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
$ python3 split_device_groups.py panorama_export.xml

Found 3 device groups:
  - DG-Internet
  - DG-DMZ
  - DG-Guest

Splitting configurations into: split_configs

Processing device group: DG-Internet
  - copied template: HQ-Networks
  ✓ Saved to: split_configs/DG-Internet.xml

Processing device group: DG-DMZ
  - no template or template-stack targets this device group's devices: none copied
  ✓ Saved to: split_configs/DG-DMZ.xml

Processing device group: DG-Guest
  ✓ Saved to: split_configs/DG-Guest.xml

✓ Successfully split 3 device groups
```

A single-firewall export has no device groups, so the splitter reports that and
exits non-zero. Convert such an export directly.

## Batch conversion

```bash
python3 split_device_groups.py panorama_export.xml

for xml in split_configs/*.xml; do
    base=$(basename "$xml" .xml)
    python3 panorama_to_terraform.py "$xml" --output-dir "${base}-tf"
done
```

## Troubleshooting

| Symptom | Cause and action |
|---|---|
| "No device groups found" | The export came from a firewall, not Panorama. Run the converter on it directly. |
| "Could not extract config for {name}" | The named entry is not in the file. Check the name, including any quote character. |
| No template copied | No device appears in both the device group and the template. Check both device lists. If Panorama really does not link them, add the device to the template, or copy the template section by hand. |
| Shared objects missing from a split file | The source had no `shared` section. A split file copies the shared section only when the export has one. |
