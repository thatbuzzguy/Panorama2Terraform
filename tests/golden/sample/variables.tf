# Variables for Palo Alto Configuration
variable "panos_hostname" {
  description = "Hostname or IP of the Palo Alto firewall/Panorama"
  type        = string
  sensitive   = true
}

variable "panos_username" {
  description = "Username for authentication"
  type        = string
  sensitive   = true
}

variable "panos_password" {
  description = "Password for authentication"
  type        = string
  sensitive   = true
}

variable "device_group" {
  description = "Device group name for Panorama"
  type        = string
  default     = "shared"
}
