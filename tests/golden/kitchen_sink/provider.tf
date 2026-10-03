# Palo Alto Networks PAN-OS Provider Configuration
# Supported provider range: v2 series, baseline 2.0.14 (the latest 2.x
# release and the version the conformance and validate gates verify).
terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.14"
    }
  }
}

provider "panos" {
  # Configure these variables or use environment variables:
  # PANOS_HOSTNAME, PANOS_USERNAME, PANOS_PASSWORD
  # hostname = var.panos_hostname
  # username = var.panos_username
  # password = var.panos_password
}
