# Service Objects

resource "panos_service" "tcp_8080_c71b2c49" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "TCP-8080"
  description = "Custom HTTP port"
  protocol = {
    tcp = {
      destination_port = "8080"
    }
  }
}

resource "panos_service" "udp_514_dfa9165d" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "UDP-514"
  protocol = {
    udp = {
      destination_port = "514"
    }
  }
}

