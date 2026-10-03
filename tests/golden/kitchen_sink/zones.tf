# Zone Configurations

resource "panos_zone" "trust" {
  name = "trust"
  mode = "layer3"
  interfaces = ["ethernet1/1", "ethernet1/2"]
  zone_protection_profile = "ZPP-Default"
}

resource "panos_zone" "lan2" {
  name = "lan2"
  mode = "layer2"
  interfaces = ["ethernet1/3"]
}

