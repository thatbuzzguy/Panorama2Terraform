# Service Groups

resource "panos_service_group" "web_services" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "Web-Services"
  description = "Web related services"
  services = ["service-http", "service-https", "TCP-8080"]
}

