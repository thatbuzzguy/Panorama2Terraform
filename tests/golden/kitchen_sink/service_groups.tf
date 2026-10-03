# Service Groups

resource "panos_service_group" "web_services" {
  name = "Web-Services"
  description = "Web services"
  services = ["service-http", "TCP-8080"]
}

