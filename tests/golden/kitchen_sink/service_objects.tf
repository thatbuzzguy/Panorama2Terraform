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
  tags = [panos_administrative_tag.web_dc16804d.name]
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

resource "panos_service" "dual_protocol_bea0744b" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Dual-Protocol"
  description = "Dual protocol service"
  protocol = {
    tcp = {
      destination_port = "80,443"
      source_port = "1024-65535"
      override = {
        halfclose_timeout = 120
        timeout = 1800
        timewait_timeout = 120
      }
    }
  }
  # NOTE: udp leg not emitted, v2 takes one protocol only: destination_port=53, timeout=120
  tags = [panos_administrative_tag.web_dc16804d.name]
}

