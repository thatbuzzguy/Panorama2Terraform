# Ethernet Interface Configurations
# Note: These are reference configurations. Adjust for your hardware platform.

resource "panos_ethernet_interface" "ethernet1_1_6ba52c24" {
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

resource "panos_ethernet_layer3_subinterface" "ethernet1_1_0_d8f6b026" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1.0"
  parent = panos_ethernet_interface.ethernet1_1_6ba52c24.name
  tag = 0
}

resource "panos_ethernet_interface" "ethernet1_2_7a4a904a" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/2"
  layer2 = {}
}

