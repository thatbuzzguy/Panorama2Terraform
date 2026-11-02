# Service Groups

resource "panos_service_group" "web_services_e83d34e8" {
  location = {
    shared = {}
  }
  name = "Web-Services"
  members = ["service-http", panos_service.tcp_8080_2a1f3529.name]
}

