# Ethernet Interface Configurations
# Note: These are reference configurations. Adjust for your hardware platform.

resource "panos_ethernet_interface" "ethernet1_1" {
  name = "ethernet1/1"
  mode = "layer3"
  comment = "Trust uplink"
  static_ips = ["192.168.1.1/24"]
  management_profile = "Management1"
}

resource "panos_layer2_subinterface" "ethernet1_2" {
  name = "ethernet1/2"
}

