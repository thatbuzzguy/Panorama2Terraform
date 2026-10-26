# Service Groups

resource "panos_service_group" "web_services_31481778" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Services"
  members = ["service-http", "service-https", panos_service.tcp_8080_ac444d1f.name]
}

