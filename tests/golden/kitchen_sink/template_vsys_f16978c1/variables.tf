# Variables for Palo Alto Configuration
# The run declares the names it names: the site values `site_data.py` maps, the reference-only
# names, and the facts the tool cannot read. Set the values in terraform.tfvars (do not commit
# it) or via the TF_VAR_* environment variables. The run declares no key, because the provider
# reads PANOS_API_KEY from the environment (docs/CODEBASE_ASSEMBLY.md §11).
variable "hostname" {
  description = "A fact the tool cannot read (F6.10.4, docs/CODEBASE_ASSEMBLY.md §11): the run names the variable and the operator supplies the value"
  type        = string
}

