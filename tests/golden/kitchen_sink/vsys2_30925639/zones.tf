# Zone Configurations

resource "panos_zone" "vsys_zone2_f258359b" {
  location = {
    vsys = {
      name = "vsys2"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "vsys-zone2"
  network = {
    layer3 = [ "ethernet1/2" ]
  }
}

