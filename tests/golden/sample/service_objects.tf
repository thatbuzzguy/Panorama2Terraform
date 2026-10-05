# Service Objects

resource "panos_service" "tcp_8080_6d614c3a" {
  location = {
    device_group = {
      name = "Production-DG"
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

resource "panos_service" "tcp_3306_19605a6d" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "TCP-3306"
  description = "MySQL Database"
  protocol = {
    tcp = {
      destination_port = "3306"
    }
  }
}

resource "panos_service" "udp_514_b9e903e0" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "UDP-514"
  description = "Syslog"
  protocol = {
    udp = {
      destination_port = "514"
    }
  }
}

