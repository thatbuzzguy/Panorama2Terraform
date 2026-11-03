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
