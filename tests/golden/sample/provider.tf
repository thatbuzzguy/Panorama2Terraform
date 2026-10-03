# Palo Alto Networks PAN-OS Provider Configuration
terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.7"
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
