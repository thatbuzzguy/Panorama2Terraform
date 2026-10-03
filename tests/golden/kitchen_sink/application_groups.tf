# Application Groups

resource "panos_application_group" "web_apps" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "web-apps"
  applications = ["http", "https"]
}

