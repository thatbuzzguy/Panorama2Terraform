# Application Groups

resource "panos_application_group" "web_apps" {
  name = "web-apps"
  applications = ["http", "https"]
}

