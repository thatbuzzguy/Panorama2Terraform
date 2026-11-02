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

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_device_level_7cfc3546" {
  location = {
    ngfw = {
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "vr-device-level"
  interfaces = ["ethernet1/1"]
}

# Source: FW-Template
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_c03bed95" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default"
  interfaces = ["ethernet1/1", "ethernet1/2"]
}

resource "panos_virtual_router_static_route_ipv4" "default_c03bed95_default_gw_96fe6d2d" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default-gw"
  virtual_router = panos_virtual_router.default_c03bed95.name
  destination = "0.0.0.0/0"
  nexthop = {
    ip_address = "192.168.1.254"
  }
  metric = 10
}

resource "panos_virtual_router_static_route_ipv4" "default_c03bed95_dmz_route_9f887ae9" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "dmz-route"
  virtual_router = panos_virtual_router.default_c03bed95.name
  destination = "172.16.0.0/16"
  nexthop = {
    ip_address = "192.168.1.5"
  }
}

# Source: FW-Template
# Type: Logical Router (Advanced Routing Engine)
resource "panos_virtual_router" "lr_main_2258b30f" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-main"
  interfaces = ["ethernet1/1"]
}

resource "panos_virtual_router_static_route_ipv4" "lr_main_2258b30f_lr_default_2029ebbd" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main_2258b30f.name
  destination = "0.0.0.0/0"
  interface = "lr-peer"
}

