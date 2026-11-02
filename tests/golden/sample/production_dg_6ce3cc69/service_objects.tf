# Service Objects

resource "panos_service" "tcp_8080_ac444d1f" {
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

resource "panos_service" "tcp_3306_2d089705" {
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

resource "panos_service" "udp_514_5860f2c2" {
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

