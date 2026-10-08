# Zone Configurations

resource "panos_zone" "trust_cf2b6e16" {
  location = {
    vsys = {
      name = "vsys1"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1_5dadf948.name, panos_ethernet_interface.ethernet1_2_e93e63ea.name ]
    zone_protection_profile = "ZPP-Default"
  }
}

resource "panos_zone" "lan2_5911aadd" {
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

resource "panos_zone" "vsys_zone1_ac659874" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = "fw-2.example.com"
    }
  }
  name = "vsys-zone1"
  network = {
    layer3 = [ "ethernet1/1" ]
  }
}

resource "panos_zone" "vsys_zone2_00aed559" {
  location = {
    vsys = {
      name = "vsys2"
      ngfw_device = "fw-2.example.com"
    }
  }
  name = "vsys-zone2"
  network = {
    layer3 = [ "ethernet1/2" ]
  }
}

