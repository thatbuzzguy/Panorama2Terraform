# Application Groups

resource "panos_application_group" "web_apps_3ba1eab8" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "web-apps"
  members = ["http", "https"]
}

