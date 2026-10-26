# Zone Configurations

resource "panos_zone" "trust_c2dcfb60" {
  location = {
    vsys = {
      name = "vsys1"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1_d74b05bd.name, panos_ethernet_interface.ethernet1_2_ff1cc5a5.name ]
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

resource "panos_zone" "vsys_zone1_9fb942fb" {
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

resource "panos_zone" "vsys_zone2_f258359b" {
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

