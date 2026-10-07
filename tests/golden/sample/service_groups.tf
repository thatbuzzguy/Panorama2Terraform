# Service Groups

resource "panos_service_group" "web_services_04509c40" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Services"
  members = ["service-http", "service-https", panos_service.tcp_8080_6c1b4915.name]
}

