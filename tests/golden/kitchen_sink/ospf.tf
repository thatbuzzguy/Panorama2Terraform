# OSPF Configuration
# Note: OSPF configuration requires careful validation.
# Verify all area configurations and interface assignments.

resource "panos_ospf" "default" {
  location {
    template {
      name = "Shared"
    }
  }
  virtual_router = panos_virtual_router.default.name
  enable = true
  router_id = "10.0.0.1"
}

resource "panos_ospf_area" "area_0_0_0_0" {
  location {
    template {
      name = "Shared"
    }
  }
  virtual_router = panos_virtual_router.default.name
  name = "0.0.0.0"
  type = "stub"
  depends_on = [panos_ospf.default]
}

resource "panos_ospf_area_interface" "ospf_ethernet1_1" {
  location {
    template {
      name = "Shared"
    }
  }
  virtual_router = panos_virtual_router.default.name
  ospf_area = "0.0.0.0"  # Adjust to correct area
  name = "ethernet1/1"
  enable = true
  passive = true
  metric = 10
  depends_on = [panos_ospf.default]
}

