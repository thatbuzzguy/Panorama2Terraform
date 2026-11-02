# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

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

