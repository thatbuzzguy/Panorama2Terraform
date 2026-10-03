# Service Objects

resource "panos_service_object" "tcp_8080" {
  name = "TCP-8080"
  description = "Custom HTTP port"
  protocol = "tcp"
  destination_port = "8080"
}

resource "panos_service_object" "tcp_3306" {
  name = "TCP-3306"
  description = "MySQL Database"
  protocol = "tcp"
  destination_port = "3306"
}

resource "panos_service_object" "udp_514" {
  name = "UDP-514"
  description = "Syslog"
  protocol = "udp"
  destination_port = "514"
}

