# Address Objects

resource "panos_address" "vsys_duplicate_a082f4ca" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "Vsys-Duplicate"
  description = "vsys1 copy of a shared name"
  ip_netmask = "10.20.1.10/32"
}

