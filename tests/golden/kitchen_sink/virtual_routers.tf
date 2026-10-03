# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# NOTE: Your config uses Advanced Routing Engine (PAN-OS 10.2+)
# - 4 Virtual Routers (legacy)
# - 1 Logical Routers (advanced)
#
# Terraform provider panos supports both types.
# Virtual routers use: panos_virtual_router
# Logical routers use: panos_logical_router (if supported by provider version)
# Check: https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs

# Source: FW-Template
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "default"
  interfaces = ["ethernet1/1", "ethernet1/2"]
}

resource "panos_static_route_ipv4" "default_default_gw" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "default-gw"
  virtual_router = panos_virtual_router.default.name
  destination = "default"
  next_hop = "192.168.1.254"
  metric = 10
}

resource "panos_static_route_ipv4" "default_dmz_route" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "dmz-route"
  virtual_router = panos_virtual_router.default.name
  destination = "172.16.0.0/16"
  next_hop = "192.168.1.5"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "default_2" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "default"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_nobgp" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "vr-nobgp"
}

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_dmz" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "vr-dmz"
  interfaces = ["ethernet1/3"]
}

# Source: FW-Template
# Type: Logical Router (Advanced Routing Engine)
# NOTE: Terraform provider may use panos_virtual_router for logical routers
# Check provider documentation for logical router support
resource "panos_virtual_router" "lr_main" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "lr-main"
  interfaces = ["ethernet1/1"]
}

resource "panos_static_route_ipv4" "lr_main_lr_default" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main.name
  destination = "default"
  interface = "lr-peer"
}

