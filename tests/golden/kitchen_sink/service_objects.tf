# Service Objects

resource "panos_service" "tcp_8080_2a1f3529" {
  location = {
    shared = {}
  }
  name = "TCP-8080"
  description = "Custom HTTP port"
  protocol = {
    tcp = {
      destination_port = "8080"
    }
  }
  tags = [panos_administrative_tag.web_4d6aa528.name]
}

resource "panos_service" "udp_514_9f438708" {
  location = {
    shared = {}
  }
  name = "UDP-514"
  protocol = {
    udp = {
      destination_port = "514"
    }
  }
}

resource "panos_service" "dual_protocol_80d74303" {
  location = {
    shared = {}
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
  tags = [panos_administrative_tag.web_4d6aa528.name]
}

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

