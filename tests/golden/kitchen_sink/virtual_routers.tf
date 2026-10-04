# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# Source: FW-Template
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_d1a0562b" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default"
  interfaces = [panos_ethernet_interface.ethernet1_1_6ba52c24.name, panos_ethernet_interface.ethernet1_2_7a4a904a.name]
}

resource "panos_virtual_router_static_route_ipv4" "default_d1a0562b_default_gw_3c88b68c" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default-gw"
  virtual_router = panos_virtual_router.default_d1a0562b.name
  destination = "0.0.0.0/0"
  nexthop = {
    ip_address = "192.168.1.254"
  }
  metric = 10
}

resource "panos_virtual_router_static_route_ipv4" "default_d1a0562b_dmz_route_4759429f" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "dmz-route"
  virtual_router = panos_virtual_router.default_d1a0562b.name
  destination = "172.16.0.0/16"
  nexthop = {
    ip_address = "192.168.1.5"
  }
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_c9b8f3e2" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "default"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_nobgp_e8e053ce" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "vr-nobgp"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_dmz_bc9b8855" {
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

