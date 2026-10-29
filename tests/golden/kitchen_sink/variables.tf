# Variables for Palo Alto Configuration
# Set the values in terraform.tfvars (do not commit it) or via the
# TF_VAR_panos_hostname / TF_VAR_panos_username / TF_VAR_panos_password
# environment variables.
variable "panos_hostname" {
  description = "Hostname or IP of the Palo Alto firewall or Panorama"
  type        = string
}

variable "panos_username" {
  description = "Username for authentication"
  type        = string
}

variable "panos_password" {
  description = "Password for authentication"
  type        = string
  sensitive   = true
}
# Site values (F6.6): one variable per value `resource_mapping.VALUE_VARIABLES` maps.
# The values are in site.auto.tfvars, which Terraform loads automatically.

variable "fw_2_example_com" {
  description = "Site value (F6.6), read from site.auto.tfvars"
  type        = string
}

