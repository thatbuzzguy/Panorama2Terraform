# Interface Configurations
# Note: These are reference configurations. Adjust for your hardware platform.

resource "panos_ethernet_interface" "ethernet1_1_c0c4e030" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1"
  comment = "Trust uplink"
  layer3 = {
    interface_management_profile = "Management1"
  }
}

resource "panos_ethernet_layer3_subinterface" "ethernet1_1_0_18e97c24" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1.0"
  parent = panos_ethernet_interface.ethernet1_1_c0c4e030.name
  tag = 0
  ip = [
    {
      name = "192.168.1.1/24"
    }
  ]
}

resource "panos_ethernet_interface" "ethernet1_2_d9d5f535" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/2"
  layer2 = {}
}

resource "panos_vlan_interface" "vlan_10_c0a7bc93" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "vlan.10"
  ip = [
    {
      name = "10.10.10.1/24"
    }
  ]
}

resource "panos_loopback_interface" "loopback_1_410dbf16" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "loopback.1"
  ip = [
    {
      name = "169.254.0.1/32"
    }
  ]
}

resource "panos_tunnel_interface" "tunnel_1_efa265d0" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "tunnel.1"
  ip = [
    {
      name = "10.255.0.1/32"
    }
  ]
}

resource "panos_aggregate_interface" "ae1_dfd607ea" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1"
  layer2 = {}
}

resource "panos_aggregate_layer3_subinterface" "ae1_101_277c257e" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1.101"
  parent = panos_aggregate_interface.ae1_dfd607ea.name
  tag = 101
  ip = [
    {
      name = "172.16.1.1/24"
    }
  ]
}

resource "panos_aggregate_layer3_subinterface" "ae1_101_20_5fdf6533" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1.101.20"
  parent = panos_aggregate_layer3_subinterface.ae1_101_277c257e.name
  tag = 20
  ip = [
    {
      name = "172.16.20.1/24"
    }
  ]
}

