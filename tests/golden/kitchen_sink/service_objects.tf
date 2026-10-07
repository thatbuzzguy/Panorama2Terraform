# Service Objects

resource "panos_service" "tcp_8080_5820960d" {
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

resource "panos_service" "udp_514_a28d1460" {
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

