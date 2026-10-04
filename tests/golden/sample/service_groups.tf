# Service Groups

resource "panos_service_group" "web_services_a7310519" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Services"
  members = ["service-http", "service-https", panos_service.tcp_8080_6d614c3a.name]
}

