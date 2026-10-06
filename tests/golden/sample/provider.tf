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
  # Credentials come from variables.tf. Set the values in
  # terraform.tfvars (do not commit it) or via the TF_VAR_*
  # environment variables.
  hostname = var.panos_hostname
  username = var.panos_username
  password = var.panos_password
}
