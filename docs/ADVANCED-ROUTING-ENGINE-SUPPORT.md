# Advanced Routing Engine (logical routers)

PAN-OS 10.2+ Advanced Routing Engine (ARE) replaces legacy virtual
routers with logical routers. The converter handles both.

## What the converter does

- Parses virtual routers from `<virtual-router>` entries and logical
  routers from `<logical-router>` entries (template scope and
  per-vsys device scope).
- Emits both as `panos_virtual_router` resources, each with a
  `# Type: Virtual Router (Legacy)` or
  `# Type: Logical Router (Advanced Routing Engine)` comment, and
  static routes as `panos_virtual_router_static_route_ipv4` resources
  that reference the owning router.
- BGP and OSPF protocol configuration has no v2 provider resource; it
  goes to `MANUAL_SETUP_REPORT.txt` with the captured data
  (router ID, AS, peer groups, peers, areas).

## Example (logical router)

The kitchen-sink fixture (`tests/fixtures/kitchen_sink.xml`) contains a
logical router, `lr-main`. Its real generated output, pinned
byte-for-byte in `tests/golden/kitchen_sink/virtual_routers.tf`:

```hcl
# Source: FW-Template
# Type: Logical Router (Advanced Routing Engine)
resource "panos_virtual_router" "lr_main_c0d74e3d" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-main"
  interfaces = [panos_ethernet_interface.ethernet1_1_6ba52c24.name]
}

resource "panos_virtual_router_static_route_ipv4" "lr_main_c0d74e3d_lr_default_664e95ca" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main_c0d74e3d.name
  destination = "0.0.0.0/0"
  interface = "lr-peer"
}
```

(Local resource names are the sanitized PAN-OS name plus an 8-hex
digest of the object's source identity.)

## Not parsed

ARE routing profiles (BGP/OSPF authentication, timers,
redistribution), access lists, prefix lists, AS path lists,
community lists, route maps, MP-BGP address families, BFD, and
multicast are not parsed. Configure them on the target after
migration.

## References

- Advanced routing:
  <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-networking-admin/advanced-routing>
- `panos_virtual_router` (v2):
  <https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs/resources/virtual_router>
- `panos_logical_router` (v2, available but the converter emits
  `panos_virtual_router` for both router types):
  <https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs/resources/logical_router>
