# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# Source: FW-Template
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_9e05ceea" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default"
  interfaces = [panos_ethernet_interface.ethernet1_1_c0c4e030.name, panos_ethernet_interface.ethernet1_2_d9d5f535.name]
}

resource "panos_virtual_router_static_route_ipv4" "default_9e05ceea_default_gw_ba29e75f" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default-gw"
  virtual_router = panos_virtual_router.default_9e05ceea.name
  destination = "0.0.0.0/0"
  nexthop = {
    ip_address = "192.168.1.254"
  }
  metric = 10
}

resource "panos_virtual_router_static_route_ipv4" "default_9e05ceea_dmz_route_88b86d34" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "dmz-route"
  virtual_router = panos_virtual_router.default_9e05ceea.name
  destination = "172.16.0.0/16"
  nexthop = {
    ip_address = "192.168.1.5"
  }
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_4e0da682" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "default"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_nobgp_6974e750" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "vr-nobgp"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_dmz_d54df80a" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "vr-dmz"
  interfaces = ["ethernet1/3"]
}

# Source: FW-Template
# Type: Logical Router (Advanced Routing Engine)
resource "panos_virtual_router" "lr_main_cb9aa879" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-main"
  interfaces = [panos_ethernet_interface.ethernet1_1_c0c4e030.name]
}

resource "panos_virtual_router_static_route_ipv4" "lr_main_cb9aa879_lr_default_81cdac78" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main_cb9aa879.name
  destination = "0.0.0.0/0"
  interface = "lr-peer"
}

