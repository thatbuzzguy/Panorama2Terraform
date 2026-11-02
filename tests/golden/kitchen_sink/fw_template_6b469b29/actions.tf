# Commit actions (F6.7): one `panos_commit` block per unit the manifest names.
# The block names the fact its own unit declares, and no fact another unit owns.
# Actions need Terraform 1.14 or later, which the `terraform` block declares (§12).

action "panos_commit" "fw_template_6b469b29" {
  config {
    templates = ["FW-Template"]
  }
}

