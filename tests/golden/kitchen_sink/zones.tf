# Zone Configurations

resource "panos_zone" "trust" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "trust"
  mode = "layer3"
  interfaces = ["ethernet1/1", "ethernet1/2"]
  zone_protection_profile = "ZPP-Default"
}

resource "panos_zone" "lan2" {
  location {
    template {
      name = "Shared"
    }
  }
  name = "lan2"
  mode = "layer2"
  interfaces = ["ethernet1/3"]
}

