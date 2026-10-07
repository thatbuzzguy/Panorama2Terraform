# Service Groups

resource "panos_service_group" "web_services_f4f2eb99" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Services"
  members = ["service-http", panos_service.tcp_8080_5820960d.name]
}

