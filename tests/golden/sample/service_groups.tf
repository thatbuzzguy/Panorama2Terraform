# Service Groups

resource "panos_service_group" "web_services" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Services"
  members = ["service-http", "service-https", panos_service.tcp_8080.name]
}

