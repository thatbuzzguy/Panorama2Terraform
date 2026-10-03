# Service Groups

resource "panos_service_group" "web_services" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "Web-Services"
  description = "Web services"
  services = ["service-http", "TCP-8080"]
}

