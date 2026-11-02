# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_71ddcf75" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "default"
  protocol = {
    bgp = {
      enable = true
      local_as = "65001"
      router_id = "10.0.0.1"
      peer_group = [
        {
          name = "PG-Branch"
          type = {
            ebgp = {
              export_nexthop = "self"
              import_nexthop = "self"
            }
          }
          peer = [
            {
              name = "10.55.0.2"
              enable = true
              peer_as = "65002"
              local_address = {
                ip = "10.55.0.1"
              }
              peer_address = {
                ip = "10.55.0.2"
              }
            }
          ]
        }
      ]
      redist_rules = [
        {
          name = "redist-static"
          enable = true
          address_family_identifier = "ipv4-unicast"
        }
      ]
    }
    ospf = {
      enable = true
      router_id = "10.0.0.1"
      area = [
        {
          name = "0.0.0.0"
          type = {
            stub = {}
          }
          range = [
            {
              name = "10.0.0.0/8"
              advertise = {}
            }
          ]
        }
      ]
    }
  }
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_nobgp_45339c20" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "vr-nobgp"
  protocol = {
    bgp = {
      enable = false
    }
  }
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_dmz_abd4195a" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "vr-dmz"
  interfaces = ["ethernet1/3"]
}

