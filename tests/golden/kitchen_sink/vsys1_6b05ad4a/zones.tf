# Zone Configurations

resource "panos_zone" "trust_c2dcfb60" {
  location = {
    vsys = {
      name = "vsys1"
    }
  }
  name = "trust"
  network = {
    layer3 = [ "ethernet1/1", "ethernet1/2" ]
    zone_protection_profile = "ZPP-Default"
  }
}

resource "panos_zone" "lan2_e91e6402" {
  location = {
    vsys = {
      name = "vsys1"
    }
  }
  name = "lan2"
  network = {
    layer2 = [ "ethernet1/3" ]
  }
}

