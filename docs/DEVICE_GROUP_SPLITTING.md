# Automatic Device Group Splitting - Complete Guide

## Quick Answer

**Q: Does the script automatically split Panorama configs by HA pair/device group?**

**A: YES - with the included `split_device_groups.py` utility!**

## The Problem

When you export from Panorama, you get ONE big XML file containing:
- All device groups (typically one per HA pair)
- All templates
- All shared objects

Example Panorama structure:
```
Panorama Export (panorama_config.xml)
├── Device Group: DG-Internet (HA Pair 1)
├── Device Group: DG-DMZ (HA Pair 2)
├── Device Group: DG-Guest (HA Pair 3)
├── Templates: Internet-Template, DMZ-Template, Guest-Template
└── Shared: Common objects
```

## The Solution

Use the **two-step process**:

### Step 1: Split by Device Group
```bash
python3 split_device_groups.py panorama_export.xml
```

This automatically creates:
```
split_configs/
├── DG-Internet.xml  (HA Pair 1 only)
├── DG-DMZ.xml       (HA Pair 2 only)
└── DG-Guest.xml     (HA Pair 3 only)
```

### Step 2: Convert Each Device Group
```bash
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-vr-tf
python3 panorama_to_terraform.py split_configs/DG-DMZ.xml --output-dir dmz-vr-tf
python3 panorama_to_terraform.py split_configs/DG-Guest.xml --output-dir guest-vr-tf
```

Result: Three separate Terraform configurations, one per HA pair!

## Complete Workflow

### Scenario: 3 HA Pairs → Single PA-5450 with 3 VRs

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Export from Panorama                            │
└─────────────────────────────────────────────────────────┘

ssh admin@panorama
> set cli config-output-format xml
> show
# Save entire configuration to file
> scp export /tmp/panorama_export.xml

Download: scp admin@panorama:/tmp/panorama_export.xml ./

┌─────────────────────────────────────────────────────────┐
│ Step 2: Split by Device Group                           │
└─────────────────────────────────────────────────────────┘

python3 split_device_groups.py panorama_export.xml

Output:
  Found 3 device groups:
    - DG-Internet
    - DG-DMZ  
    - DG-Guest
  
  Splitting configurations into: split_configs
  
  Processing device group: DG-Internet
    ✓ Saved to: split_configs/DG-Internet.xml
  
  Processing device group: DG-DMZ
    ✓ Saved to: split_configs/DG-DMZ.xml
  
  Processing device group: DG-Guest
    ✓ Saved to: split_configs/DG-Guest.xml

┌─────────────────────────────────────────────────────────┐
│ Step 3: Convert Each Device Group to Terraform          │
└─────────────────────────────────────────────────────────┘

# Internet Edge (HA Pair 1 → Internet-VR)
python3 panorama_to_terraform.py \
  split_configs/DG-Internet.xml \
  --output-dir internet-vr-tf

# DMZ (HA Pair 2 → DMZ-VR)
python3 panorama_to_terraform.py \
  split_configs/DG-DMZ.xml \
  --output-dir dmz-vr-tf

# Guest (HA Pair 3 → Guest-VR)
python3 panorama_to_terraform.py \
  split_configs/DG-Guest.xml \
  --output-dir guest-vr-tf

┌─────────────────────────────────────────────────────────┐
│ Step 4: Customize Each Configuration                    │
└─────────────────────────────────────────────────────────┘

# Update virtual router names
sed -i 's/"default"/"Internet-VR"/g' internet-vr-tf/virtual_routers.tf
sed -i 's/"default"/"DMZ-VR"/g' dmz-vr-tf/virtual_routers.tf
sed -i 's/"default"/"Guest-VR"/g' guest-vr-tf/virtual_routers.tf

# Update interface mappings
# Internet-VR: ethernet1/1-8
# DMZ-VR: ethernet1/9-16
# Guest-VR: ethernet1/17-24

┌─────────────────────────────────────────────────────────┐
│ Step 5: Deploy to PA-5450                               │
└─────────────────────────────────────────────────────────┘

# Deploy all three VRs
terraform init
terraform apply
```

## What Gets Split

### Each Device Group XML Contains:

✅ **Device Group Configuration**
- Address objects specific to that DG
- Service objects specific to that DG
- Security policies for that DG
- NAT policies for that DG
- Security profiles for that DG

✅ **Template Configuration** (when the export associates one)
- Zones for that HA pair
- Interfaces for that HA pair
- Virtual routers for that HA pair
- BGP/OSPF config for that HA pair
- VPN tunnels for that HA pair
- Static routes for that HA pair

The splitter takes the association from the export, not from a name. A
template belongs to a device group when both list the same device:

```
device-group/entry/DG-Internet/devices/entry/fw-1.example.com
templates/entry/HQ-Networks/devices/entry/fw-1.example.com
```

`HQ-Networks` is copied into `DG-Internet.xml` even though the two names do
not resemble each other. A device group that lists no device, or whose
devices no template targets, gets no template, and the splitter prints
that fact.

✅ **Shared Objects** (included in all)
- Shared address objects
- Shared service objects
- Shared security profiles

### What Doesn't Get Split

The splitter includes shared objects in each split config because device groups reference them. This is intentional and correct.

## Splitter Script Features

### Automatic Detection
```python
# Finds all device groups automatically
Found 3 device groups:
  - DG-Internet
  - DG-DMZ
  - DG-Guest
```

### Template And Template Stack Matching
The splitter joins a device group, a template, and a template stack on the
devices each one lists in the export:

- A template is copied when it targets one of the device group's devices.
- A template stack is copied when it targets one of the device group's
  devices.
- A device group that lists no device copies neither, and the splitter
  prints `device group lists no devices: no template or template-stack
  copied`.
- A device group whose devices no template and no template stack targets
  prints `no template or template-stack targets this device group's
  devices: none copied`.

The device group name never finds a template. The old code stripped a `DG-`
prefix and then tested whether the device group name appeared inside a
template name; both matched names instead of facts, and both are gone.

### Safe File Naming
Device group names are sanitized for filenames:
- `DG/Internet` → `DG_Internet.xml`
- `DG Internet` → `DG_Internet.xml`

### Preserves References
- Shared objects included in each split
- Template stack references maintained
- Device references preserved

## Example Output

### Running the Splitter

```bash
$ python3 split_device_groups.py panorama_export.xml

Found 3 device groups:
  - DG-Internet
  - DG-DMZ
  - DG-Guest

Splitting configurations into: split_configs

Processing device group: DG-Internet
  - copied template: Internet
  ✓ Saved to: split_configs/DG-Internet.xml

Processing device group: DG-DMZ
  - no template or template-stack targets this device group's devices: none copied
  ✓ Saved to: split_configs/DG-DMZ.xml

Processing device group: DG-Guest
  ✓ Saved to: split_configs/DG-Guest.xml

✓ Successfully split 3 device groups

Next steps:
  1. cd split_configs
  2. Run panorama_to_terraform.py on each XML file:
     python3 panorama_to_terraform.py <device-group>.xml --output-dir <device-group>-tf
```

### Converting Split Configs

```bash
$ python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-tf

Parsing Panorama configuration from split_configs/DG-Internet.xml...
Extracting configuration elements...

Found:
  - 1 device groups
  - 15 address objects
  - 5 address groups
  - 8 service objects
  - 2 service groups
  - 12 security rules
  - 3 NAT rules
  - 4 zones
  - 8 interfaces
  - 1 virtual routers
  - BGP enabled with 2 peers
  - 3 IKE gateways
  - 3 IPsec tunnels

Generating Terraform configuration in internet-tf...

✓ Successfully generated Terraform configuration!

📄 Generated Migration Reports:
  - INTERFACE_MIGRATION_REPORT.txt (Interface and IP inventory)
  - VPN_MIGRATION_REPORT.txt ⚠️  (VPN config with key management instructions)
```

## Directory Structure After Workflow

```
project/
├── panorama_export.xml                    # Original Panorama export
├── split_configs/                         # Step 2 output
│   ├── DG-Internet.xml                    # HA Pair 1 only
│   ├── DG-DMZ.xml                         # HA Pair 2 only
│   └── DG-Guest.xml                       # HA Pair 3 only
├── internet-vr-tf/                        # Step 3 output for Internet VR
│   ├── provider.tf
│   ├── variables.tf
│   ├── virtual_routers.tf                 # Customize: default → Internet-VR
│   ├── interfaces.tf                      # Customize: ethernet1/1-8
│   ├── zones.tf
│   ├── bgp.tf
│   ├── vpn.tf
│   ├── security_rules.tf
│   ├── nat_rules.tf
│   ├── INTERFACE_MIGRATION_REPORT.txt
│   └── VPN_MIGRATION_REPORT.txt
├── dmz-vr-tf/                             # Step 3 output for DMZ VR
│   ├── virtual_routers.tf                 # Customize: default → DMZ-VR
│   ├── interfaces.tf                      # Customize: ethernet1/9-16
│   ├── ospf.tf
│   └── ...
└── guest-vr-tf/                           # Step 3 output for Guest VR
    ├── virtual_routers.tf                 # Customize: default → Guest-VR
    ├── interfaces.tf                      # Customize: ethernet1/17-24
    └── ...
```

## Advanced Usage

### Custom Output Directory

```bash
python3 split_device_groups.py panorama_export.xml --output-dir /tmp/my-splits
```

### Input Limit

The splitter applies the same input checks as the converter: it refuses an
export larger than 64 MiB before reading it, and an export that declares a
DTD. A refusal writes nothing. Raise the size limit for a trusted file:

```bash
python3 split_device_groups.py big_export.xml --max-input-bytes 268435456
```

### Process Specific Device Group Only

If you only want one device group:
```bash
# Split all
python3 split_device_groups.py panorama_export.xml

# Then just convert the one you want
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-tf
```

### Scripted Batch Conversion

```bash
#!/bin/bash
# convert_all.sh - Convert all device groups automatically

# Split
python3 split_device_groups.py panorama_export.xml

# Convert each
for xml in split_configs/*.xml; do
    base=$(basename "$xml" .xml)
    echo "Converting $base..."
    python3 panorama_to_terraform.py "$xml" --output-dir "${base}-tf"
done

echo "All device groups converted!"
```

## Troubleshooting

### Issue: "No device groups found"

**Cause**: You exported from a firewall, not Panorama

**Solution**: This is expected. Use the regular converter directly:
```bash
python3 panorama_to_terraform.py firewall_export.xml --output-dir firewall-tf
```

### Issue: "Could not extract config for device group"

**Cause**: Device group structure is unusual or corrupted

**Solution**: Check the device group exists in the XML:
```bash
grep -o 'device-group/entry name="[^"]*"' panorama_export.xml
```

### Issue: Template not included in split

**Cause**: The template targets no device that the device group contains.
The splitter copies a template only when the export lists one device in
both.

**Solution**: Check the device lists of the device group and of the
template:
```bash
grep -A 6 'device-group' panorama_export.xml | grep -B 2 -A 4 'devices'
grep -A 6 '<templates>' panorama_export.xml
```
If Panorama really does not link them, add the device to the template in
Panorama, or copy the template section into the split file by hand.

### Issue: Missing shared objects

**Cause**: Bug in splitter

**Solution**: Shared objects should be included automatically. Check XML structure:
```bash
grep -A 5 "<shared>" split_configs/DG-Internet.xml
```

## Integration with Multi-VR Migration

This splitter is specifically designed for the multi-VR migration workflow documented in **MULTI_VR_MIGRATION_GUIDE.md**.

**Complete Process:**
1. Export from Panorama (one big file)
2. Split by device group (one file per HA pair)
3. Convert each to Terraform (one config per HA pair)
4. Customize VR names and interfaces
5. Deploy to single large firewall

## Summary

### Without Splitter (Manual Process)
```
❌ Export from Panorama → one big XML
❌ Manually edit XML to separate device groups (tedious!)
❌ Or convert all-in-one and manually split Terraform (error-prone!)
```

### With Splitter (Automated Process)
```
✅ Export from Panorama → one big XML
✅ Run splitter → automatic separation by device group
✅ Convert each → clean Terraform per HA pair
✅ Customize → ready for multi-VR deployment
```

**The splitter automates the tedious device group separation, making multi-VR migrations much easier!**

## Files Included

- `split_device_groups.py` - The device group splitter utility
- `panorama_to_terraform.py` - Main converter (works on split configs)
- `MULTI_VR_MIGRATION_GUIDE.md` - Complete multi-VR migration guide
- `DEVICE_GROUP_SPLITTING.md` - This document

**Everything you need for automated multi-HA-pair to multi-VR migrations!**
