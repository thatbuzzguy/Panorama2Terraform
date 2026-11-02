# Address Objects

resource "panos_address" "vsys_duplicate_e8ae6906" {
  location = {
    vsys = {
      name = "vsys2"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "Vsys-Duplicate"
  description = "vsys2 copy of a shared name"
  ip_netmask = "10.20.2.10/32"
}

