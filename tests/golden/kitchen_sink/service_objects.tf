# Service Objects

resource "panos_service_object" "tcp_8080" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "TCP-8080"
  description = "Custom HTTP port"
  protocol = "tcp"
  destination_port = "8080"
}

resource "panos_service_object" "udp_514" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "UDP-514"
  protocol = "udp"
  destination_port = "514"
}

