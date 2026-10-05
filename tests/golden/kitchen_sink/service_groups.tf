# Service Groups

resource "panos_service_group" "web_services_1823fba2" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Services"
  members = ["service-http", panos_service.tcp_8080_c71b2c49.name]
}

