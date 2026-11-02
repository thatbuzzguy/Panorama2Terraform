# Application Groups

resource "panos_application_group" "web_apps_7808a3ce" {
  location = {
    shared = {}
  }
  name = "web-apps"
  members = ["http", "https"]
}

