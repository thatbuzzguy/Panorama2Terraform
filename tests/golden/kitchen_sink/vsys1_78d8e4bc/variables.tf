# Variables for Palo Alto Configuration
# The run declares the names it names: the site values `site_data.py` maps, the reference-only
# names, and the facts the tool cannot read. Set the values in terraform.tfvars (do not commit
# it) or via the TF_VAR_* environment variables. The run declares no key, because the provider
# reads PANOS_API_KEY from the environment (docs/CODEBASE_ASSEMBLY.md §11).
# Site values (F6.6): one variable per value `resource_mapping.VALUE_VARIABLES` maps.
# The values are in site.auto.tfvars, which Terraform loads automatically.

variable "fw_2_example_com" {
  description = "Site value (F6.6), read from site.auto.tfvars"
  type        = string
}

variable "hostname" {
  description = "A fact the tool cannot read (F6.10.4, docs/CODEBASE_ASSEMBLY.md §11): the run names the variable and the operator supplies the value"
  type        = string
}

variable "target" {
  description = "A fact the tool cannot read (F6.10.4, docs/CODEBASE_ASSEMBLY.md §11): the run names the variable and the operator supplies the value"
  type        = string
}

variable "vsys_cert" {
  description = "Sensitive protocol value (F7.1, F7.7): the reference prints, so no file states the value, and the operator supplies it"
  type        = string
  sensitive   = true
}

