# Zone Configurations

resource "panos_zone" "trust_f07da922" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1_6ba52c24.name, panos_ethernet_interface.ethernet1_2_7a4a904a.name ]
    zone_protection_profile = "ZPP-Default"
  }
}

resource "panos_zone" "lan2_75d2cebe" {
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

