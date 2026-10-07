# PBF Path Monitoring Profiles (F2.9: real v2 resources)

resource "panos_monitor_profile" "pm_branch_070d8f1d" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "PM-Branch"
  interval = 10
  threshold = 5
  action = "wait-recover"
}

