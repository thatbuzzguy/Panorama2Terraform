# Interface Configurations
# Note: These are reference configurations. Adjust for your hardware platform.

resource "panos_ethernet_interface" "ethernet1_1_d74b05bd" {
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

resource "panos_ethernet_layer3_subinterface" "ethernet1_1_0_279a35e7" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1.0"
  parent = panos_ethernet_interface.ethernet1_1_d74b05bd.name
  tag = 0
  ip = [
    {
      name = "192.168.1.1/24"
    }
  ]
}

resource "panos_ethernet_interface" "ethernet1_2_ff1cc5a5" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/2"
  layer2 = {}
}

resource "panos_vlan_interface" "vlan_10_fe4bedf2" {
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

resource "panos_loopback_interface" "loopback_1_778cd1b0" {
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

resource "panos_tunnel_interface" "tunnel_1_9b43be36" {
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

resource "panos_aggregate_interface" "ae1_8812c5e7" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1"
  layer2 = {}
}

resource "panos_aggregate_layer3_subinterface" "ae1_101_3f3d0490" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1.101"
  parent = panos_aggregate_interface.ae1_8812c5e7.name
  tag = 101
  ip = [
    {
      name = "172.16.1.1/24"
    }
  ]
}

resource "panos_aggregate_layer3_subinterface" "ae1_101_20_53aa9a22" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ae1.101.20"
  parent = panos_aggregate_layer3_subinterface.ae1_101_3f3d0490.name
  tag = 20
  ip = [
    {
      name = "172.16.20.1/24"
    }
  ]
}

