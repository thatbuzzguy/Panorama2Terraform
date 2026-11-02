# Service Objects

resource "panos_service" "vsys_service_b8cc0680" {
  location = {
    vsys = {
      name = "vsys2"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "Vsys-Service"
  protocol = {
    tcp = {
      destination_port = "7002"
    }
  }
}

