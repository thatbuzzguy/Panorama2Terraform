# Palo Alto Panorama to Terraform Converter

A comprehensive Python utility to convert Palo Alto Panorama XML configuration exports into Terraform configuration files, **specifically designed to facilitate firewall migrations between different Palo Alto platforms**.

## 🎯 Purpose

This tool is purpose-built for **migrating Palo Alto firewalls to different platforms** (e.g., PA-3000 → PA-5000, physical → VM-Series). It extracts your complete configuration and generates both:
1. **Terraform files** for automated deployment
2. **Interface migration report** for planning interface mapping

## 📦 What's Included

- `panorama_to_terraform.py` - Main conversion script (comprehensive parser and generator)
- `split_device_groups.py` - Device group splitting utility
- `sample_panorama_config.xml` - Example configuration with all features
- `README.md` - This file
- `quick_start.sh` - Quick start demonstration script
- `docs/` - Documentation (**MIGRATION_GUIDE.md** step-by-step migration workflow, **USAGE_GUIDE.md** technical documentation, coverage and feature guides)
- `examples/` - Sample reports (**example_interface_report.txt**, **example_terraform_output.txt**)

## 🚀 Quick Start

```bash
# 1. Make scripts executable
chmod +x panorama_to_terraform.py quick_start.sh

# 2. Run the quick start demo
./quick_start.sh

# 3. Or convert your own Panorama config
python3 panorama_to_terraform.py your_config.xml --output-dir terraform_output
```

## 📋 Requirements

- Python 3.6+
- Terraform 1.0+
- Access to Palo Alto Panorama or Firewall

## 🎯 Supported Features (Enhanced for Migration)

### Configuration Objects
- ✅ **Zones** - Security zones with interface assignments
- ✅ **Interfaces** - Ethernet, VLAN, Loopback with IP addresses
- ✅ **Virtual Routers** - Routing configuration and static routes
- ✅ **BGP** - ⭐ NEW - BGP configuration with peers and peer groups
- ✅ **OSPF** - ⭐ NEW - OSPF configuration with areas and interfaces
- ✅ **IPsec VPN** - ⭐ NEW - IKE gateways, IPsec tunnels, crypto profiles
- ✅ **Security Profiles** - Antivirus, Anti-Spyware, Vulnerability, URL Filtering, File Blocking, WildFire
- ✅ **Security Profile Groups** - Profile group assignments
- ✅ Address Objects (IP, FQDN, Range)
- ✅ Address Groups (Static & Dynamic)
- ✅ Service Objects (TCP/UDP)
- ✅ Service Groups
- ✅ Security Policy Rules
- ✅ NAT Policy Rules
- ✅ Device Groups

### Migration-Specific Features
- ✅ **Interface Migration Report** - Complete interface and IP inventory
- ✅ **VPN Migration Report** - ⭐ NEW - VPN configuration with key management instructions
- ✅ **Platform Guidance** - PA-200/500, PA-800, PA-3000, PA-5000, PA-7000, VM-Series
- ✅ **Migration Checklist** - Step-by-step migration workflow
- ✅ **Interface Mapping Planning** - Tools to plan interface changes

### Generated Terraform Resources
- `panos_bgp` - ⭐ NEW
- `panos_bgp_peer_group` - ⭐ NEW
- `panos_bgp_peer` - ⭐ NEW
- `panos_ospf` - ⭐ NEW
- `panos_ospf_area` - ⭐ NEW
- `panos_ospf_area_interface` - ⭐ NEW
- `panos_ike_crypto_profile` - ⭐ NEW
- `panos_ipsec_crypto_profile` - ⭐ NEW
- `panos_ike_gateway` - ⭐ NEW
- `panos_ipsec_tunnel` - ⭐ NEW
- `panos_ipsec_tunnel_proxy_id_ipv4` - ⭐ NEW
- `panos_zone`
- `panos_ethernet_interface`
- `panos_virtual_router`
- `panos_static_route_ipv4`
- `panos_security_profile_group`
- `panos_address_object`
- `panos_address_group`
- `panos_service_object`
- `panos_service_group`
- `panos_security_rule_group`
- `panos_nat_rule_group`

## 📖 Migration Workflow

```
Export Config → Run Converter → Review Interface Report
                                        ↓
                                Plan Interface Mapping
                                        ↓
                                Adjust Terraform Configs
                                        ↓
                                Test in Lab → Deploy to Production
```

**Key Output: INTERFACE_MIGRATION_REPORT.txt**
- Lists all interfaces with IP addresses
- Shows interface types and modes
- Displays management profiles
- Includes VLAN tags
- Provides platform migration guidance

**Key Output: VPN_MIGRATION_REPORT.txt** ⭐ NEW (if VPNs detected)
- Lists all IKE gateways and IPsec tunnels
- **Highlights placeholder pre-shared keys**
- Provides key management best practices
- Includes security warnings and checklist
- **Critical: Keys must be updated before deployment**

## 💡 Example Usage

### Basic Conversion
```bash
python3 panorama_to_terraform.py panorama_export.xml
```

### Custom Output Directory
```bash
python3 panorama_to_terraform.py panorama_export.xml --output-dir /path/to/terraform
```

### Review Generated Configuration
```bash
cd terraform_output
ls -la

# You'll see:
# - provider.tf
# - variables.tf
# - zones.tf ⭐ NEW
# - interfaces.tf ⭐ NEW
# - virtual_routers.tf ⭐ NEW
# - security_profiles.tf ⭐ NEW
# - security_profile_groups.tf ⭐ NEW
# - address_objects.tf
# - address_groups.tf
# - service_objects.tf
# - service_groups.tf
# - security_rules.tf
# - nat_rules.tf
# - INTERFACE_MIGRATION_REPORT.txt ⭐ NEW - Critical for migration planning
# - README.md
```

## 🔧 Exporting from Panorama

### Via Web UI
1. Device → Setup → Operations
2. Save named Panorama configuration snapshot
3. Download and extract XML

### Via CLI
```bash
ssh admin@panorama
> set cli config-output-format xml
> configure
# show
> save config to export.xml
```

### Via API
```bash
curl -k -X GET 'https://panorama/api/?type=export&category=configuration&key=KEY' -o config.xml
```

## 🎨 Example Output - Interface Report

```
INTERFACE AND IP ADDRESS MIGRATION REPORT
Generated for Firewall Migration Planning

ETHERNET INTERFACES (4)
--------------------------------------------------------------------------------

Interface: ethernet1/1
  Type: ethernet
  Mode: layer3
  Comment: Trust Interface - Internal Network
  IPv4 Addresses:
    - 10.1.1.1/24
  IPv6 Addresses:
    - 2001:db8::1/64
  Management Profile: Ping-Only

Interface: ethernet1/2
  Type: ethernet
  Mode: layer3
  Comment: Untrust Interface - Internet Connection
  IPv4 Addresses:
    - 203.0.113.1/30
  Management Profile: Allow-All

MIGRATION CHECKLIST
1. Review interface naming differences between platforms
2. Map source interfaces to target platform interfaces
3. Verify IP addressing scheme is compatible
...
```

## 🔐 Deploying with Terraform

1. **Create credentials file** (`terraform.tfvars`):
```hcl
panos_hostname = "panorama.example.com"
panos_username = "admin"
panos_password = "your-password"
device_group   = "Production-DG"
```

2. **Initialize Terraform**:
```bash
cd terraform_output
terraform init
```

3. **Review changes**:
```bash
terraform plan
```

4. **Apply configuration**:
```bash
terraform apply
```

## ⚠️ Important Migration Notes

### What's Included
- Complete zone configurations
- Interface definitions with IP addresses
- Virtual router and static routes
- Security profile references
- All policy rules
- Address and service objects

### Manual Configuration Required
- **Interface adjustments** - Adapt to target platform hardware
- **Security profile details** - Full rule definitions
- VPN configurations
- GlobalProtect settings
- HA configurations
- Management interface specifics

### Migration Best Practices
1. ✅ **Always test in lab first** - Critical for successful migration
2. ✅ Review `INTERFACE_MIGRATION_REPORT.txt` before starting
3. ✅ Create interface mapping table for source → target
4. ✅ Backup existing configuration
5. ✅ Verify interface naming for target platform
6. ✅ Use version control (Git)
7. ✅ Apply changes incrementally
8. ✅ See `docs/MIGRATION_GUIDE.md` for detailed procedures

## 🐛 Troubleshooting

### XML Parse Errors
- Ensure XML is valid and complete
- Re-export from Panorama if corrupted

### Interface Naming Issues
- Review target platform interface naming conventions
- Update `interfaces.tf` accordingly
- See platform-specific notes in interface report

### Missing Resources
- Check device group permissions
- Verify shared resource access

### Zone Assignment Failures
- Ensure interfaces exist before zones
- Use Terraform `depends_on` if needed

## 📚 Documentation

- **docs/MIGRATION_GUIDE.md** - Complete migration workflow and procedures
- **docs/USAGE_GUIDE.md** - Technical documentation and API details
- **docs/VERSION_4.0_COMPLETE_COVERAGE.md** - Full object coverage details
- **examples/example_interface_report.txt** - Sample interface inventory
- **examples/example_terraform_output.txt** - Sample generated output
- **README.md** - This overview

## 🤝 Use Cases

### Ideal For:
- ✅ Migrating between Palo Alto hardware platforms
- ✅ Physical to VM-Series migrations
- ✅ VM-Series to physical migrations
- ✅ Platform upgrades (e.g., PA-3000 → PA-5000)
- ✅ Configuration standardization across devices
- ✅ Disaster recovery planning
- ✅ Configuration version control

### Not Suitable For:
- ❌ Multi-vendor migrations (Palo Alto only)
- ❌ Complex VPN configurations (manual setup needed)
- ❌ GlobalProtect (not in export)

## 🎯 Version

Current Version: **4.0.0** - **Production-Ready Edition**

### What's New in v4.0
- ✨ **Production-tested** on 133,000-line config with 10,000+ objects
- ✨ **16 new object types**: Tags, Custom URLs, App Groups/Filters, PBF, Decryption, etc.
- ✨ **Terraform Provider 2.0.7** support
- ✨ **36 total object types** (was 20 in v3.0)
- ✨ **Enhanced interfaces**: Tunnel, Aggregate, Subinterfaces
- ✨ **Complete coverage**: 95%+ of common Palo Alto objects
- ✨ **31 Terraform files** generated (was ~15)
- ✨ See `docs/VERSION_4.0_COMPLETE_COVERAGE.md` for full details

### Features in v3.0
- BGP and OSPF routing protocol support
- IPsec VPN with IKE gateway/tunnel configuration
- VPN key management reporting
- Multi-virtual-router migrations
- Automatic device group splitting

### Features in v2.0
- Zone configuration parsing and generation
- Interface configuration with IP addresses
- Virtual router and static route support
- Security profile and profile group support
- **INTERFACE_MIGRATION_REPORT.txt** generation
- Platform-specific migration guidance

### Features in v1.0
- Core configuration parsing
- Address/service object support
- Security/NAT rule conversion
- Basic Terraform generation

## 📄 License

This project is **dual-licensed**:

### Option 1: AGPL v3 (Free & Open Source)
**GNU Affero General Public License v3** - Free for open source use
- ✅ Free to use, modify, and distribute
- ⚠️ Must release source code if distributed or deployed as service
- ⚠️ Modifications must be AGPL v3
- See [LICENSE-AGPL](LICENSE-AGPL) for full terms

### Option 2: Commercial License (Proprietary)
**Proprietary License** - For commercial/proprietary use
- ✅ Use in closed-source products
- ✅ No source code release required
- ✅ Deploy as SaaS without sharing code
- ✅ Commercial support included
- See [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL) for details

### Which License Do I Need?

**Use AGPL v3 (Free) if:**
- Building open source projects
- Willing to share your source code
- Using internally and can share modifications
- Learning or experimenting

**Buy Commercial License if:**
- Building commercial/proprietary products
- Running as SaaS for clients
- Cannot release your source code
- Need commercial support and warranty
- Embedding in proprietary software

**📖 Detailed comparison:** See [DUAL-LICENSING-EXPLAINED.md](docs/DUAL-LICENSING-EXPLAINED.md)

**💼 Purchase commercial license:** Contact [Your Email]

### Quick Summary

| Feature | AGPL v3 | Commercial |
|---------|---------|------------|
| Cost | FREE | Paid |
| Proprietary use | ❌ | ✅ |
| SaaS deployment | ⚠️ Must share code | ✅ |
| Support | Community | ✅ Professional |
| Must release code | ✅ | ❌ |

## 🆘 Support

### For Migration Assistance
1. Review `docs/MIGRATION_GUIDE.md` for detailed procedures
2. Check `INTERFACE_MIGRATION_REPORT.txt` for interface planning
3. Test in lab environment first
4. Consult Palo Alto platform compatibility matrix

### For Script Issues
1. Review generated files
2. Check Terraform validation output
3. Consult provider documentation
4. Validate XML export

## 📖 Additional Resources

- [Palo Alto Terraform Provider](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [PAN-OS API Documentation](https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)

## 📊 Version History

### v4.0.3 (December 2025) - Advanced Routing Engine Support ⭐
**🎯 New Feature: Logical Routers (PAN-OS 10.2+)**
- Added support for **Advanced Routing Engine** logical routers
- Automatically detects and parses both virtual routers (legacy) and logical routers
- Generates Terraform for mixed VR/LR configurations
- Properly identifies router types in generated files
- **Impact:** Full support for PAN-OS 10.2+ Advanced Routing Engine migrations
- See [docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md](docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md) for details

### v4.0.2 (December 2025) - Multi-VR & Split Script Fixes ⭐
**🐛 Fixed: Multiple Critical Issues**

**1. Virtual Router Multi-VR Support:**
- **Critical Fix:** Virtual routers missing when names duplicated across templates
- Added template-aware parsing with interface signature deduplication
- Now captures ALL VRs including multi-VR templates and duplicate names
- **Impact:** Configs with multiple templates now get all VRs (e.g., found 7 instead of 6)
- See [docs/MULTI_VR_MIGRATION_GUIDE.md](docs/MULTI_VR_MIGRATION_GUIDE.md) for technical details

**2. Split Device Groups Script:**
- **Critical Fix:** split_device_groups.py missing 99% of objects in split files
- Fixed: Only copied first `<shared>` section (Panorama has 11+ sections)
- Fixed: Duplicate device group detection
- Now merges ALL shared sections into split files
- **Impact:** Split files now include all 3,699 addresses, 430 services, etc. (was 0)
- See [docs/DEVICE_GROUP_SPLITTING.md](docs/DEVICE_GROUP_SPLITTING.md) for technical details

**Action Required:**
- ⚠️ If you have multiple templates with VRs: Regenerate your files
- ⚠️ If you used split_device_groups.py: Re-split to get all objects

### v4.0.1 (December 2025) - CRITICAL FIX ⭐
**🐛 Fixed: Shared Object References**
- **Critical Fix:** Objects with empty values/members in Terraform output
- Added detection and filtering of reference-only entries (entries with only `<id>` tags)
- Changed parse order to prioritize device-group definitions over shared references  
- Fixed 4 parsing methods: address objects, address groups, service objects, service groups
- **Impact:** All objects now have correct values populated
- See [docs/VERSION_4.0_COMPLETE_COVERAGE.md](docs/VERSION_4.0_COMPLETE_COVERAGE.md) for technical details
- ⚠️ **If you used v4.0.0, regenerate your Terraform files**

### v4.0.0 (December 2025) - Production Enhancement
**🚀 Major Release**
- Added 16 new object types (tags, custom URLs, app groups/filters, external lists, decryption, PBF, etc.)
- Expanded from 20 to 36 object types (80% increase)
- Updated to Terraform Provider 2.0.7
- Tested on 133,411-line production config with 10,299 objects
- Achieved 95%+ coverage of Palo Alto objects
- 100% success rate on production data
- Applied AGPL v3 + Commercial dual licensing

### v3.0 (November 2025) - VPN & Routing
**🔐 Advanced Networking**
- Added BGP support with peer configuration
- Added OSPF support with area configuration  
- Added VPN support (IKE gateways, IPsec tunnels, crypto profiles)
- Added device group splitting utility
- Added multi-VR migration workflows

### v2.0 (October 2025) - Network Objects
**🌐 Network Infrastructure**
- Added zone support
- Added interface support (ethernet, VLAN, loopback, tunnel, aggregate)
- Added virtual router support
- Added static route support
- Comprehensive documentation

### v1.0 (September 2025) - Initial Release
**🎯 Foundation**
- Basic object support (addresses, services, rules)
- Security policy conversion
- NAT policy conversion  
- Address and service object/group support

---

**Made with ❤️ for Network Engineers migrating Palo Alto firewalls to different platforms**

**🔥 Perfect for platform upgrades, physical-to-VM migrations, and infrastructure modernization projects**
