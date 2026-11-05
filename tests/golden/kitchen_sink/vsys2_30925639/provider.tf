# Palo Alto Networks PAN-OS Provider Configuration
# Supported provider range: v2 series, baseline 2.0.14 (the latest 2.x
# release and the version the conformance and validate gates verify).
# Terraform 1.14 minimum: an `action` block is 1.14 syntax (F6.7).
terraform {
  required_version = ">= 1.14"
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.14"
    }
  }
}

provider "panos" {
  # The Panorama host this unit plans against. The run names the variable and holds no
  # value for it, so the operator supplies it in terraform.tfvars (do not commit that
  # file). The provider reads PANOS_API_KEY from the environment, so the
  # block states no key.
  hostname = var.hostname
  # The NGFW serial for the device this unit plans against. The run names the
  # variable and holds no value for it, so the operator supplies the serial.
  target = var.target
}
