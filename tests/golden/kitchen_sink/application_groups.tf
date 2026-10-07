# Application Groups

resource "panos_application_group" "web_apps_95018688" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "web-apps"
  members = ["http", "https"]
}

