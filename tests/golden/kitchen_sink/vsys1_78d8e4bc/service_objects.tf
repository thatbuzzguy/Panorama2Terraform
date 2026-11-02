# Service Objects

resource "panos_service" "vsys_service_b90169ce" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "Vsys-Service"
  protocol = {
    tcp = {
      destination_port = "7001"
    }
  }
}

