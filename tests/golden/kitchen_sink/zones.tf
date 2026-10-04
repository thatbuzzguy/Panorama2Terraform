# Zone Configurations

resource "panos_zone" "trust" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1.name, panos_ethernet_interface.ethernet1_2.name ]
    zone_protection_profile = "ZPP-Default"
  }
}

resource "panos_zone" "lan2" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "lan2"
  network = {
    layer2 = [ "ethernet1/3" ]
  }
}

