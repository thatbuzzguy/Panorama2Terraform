# Zone Configurations

resource "panos_zone" "trust_cf2b6e16" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1_c0c4e030.name, panos_ethernet_interface.ethernet1_2_d9d5f535.name ]
    zone_protection_profile = "ZPP-Default"
  }
}

resource "panos_zone" "lan2_5911aadd" {
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

