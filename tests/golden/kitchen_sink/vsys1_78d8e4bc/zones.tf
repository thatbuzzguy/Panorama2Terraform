# Zone Configurations

resource "panos_zone" "vsys_zone1_9fb942fb" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "vsys-zone1"
  network = {
    layer3 = [ "ethernet1/1" ]
  }
}

