# Application Filters
# Note: Application filters may require manual configuration of all attributes

resource "panos_application_filter" "high_risk_web" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "high-risk-web"
  category = ["web-proxy", "file-transfer"]
  risk = ["high"]
  evasive = true
}

