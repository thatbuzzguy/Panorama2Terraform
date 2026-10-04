# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# Source: FW-Template
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default"
  interfaces = [panos_ethernet_interface.ethernet1_1.name, panos_ethernet_interface.ethernet1_2.name]
}

resource "panos_virtual_router_static_route_ipv4" "default_default_gw" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "default-gw"
  virtual_router = panos_virtual_router.default.name
  destination = "0.0.0.0/0"
  nexthop = {
    ip_address = "192.168.1.254"
  }
  metric = 10
}

resource "panos_virtual_router_static_route_ipv4" "default_dmz_route" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "dmz-route"
  virtual_router = panos_virtual_router.default.name
  destination = "172.16.0.0/16"
  nexthop = {
    ip_address = "192.168.1.5"
  }
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_2" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "default"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_nobgp" {
  location = {
    template = {
      name = "device-specific"
    }
  }
  name = "vr-nobgp"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_dmz" {
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
resource "panos_virtual_router" "lr_main" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-main"
  interfaces = [panos_ethernet_interface.ethernet1_1.name]
}

resource "panos_virtual_router_static_route_ipv4" "lr_main_lr_default" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main.name
  destination = "0.0.0.0/0"
  interface = "lr-peer"
}

