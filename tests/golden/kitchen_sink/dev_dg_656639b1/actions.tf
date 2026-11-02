# Commit and push actions (F6.7, F6.10.4): one block per action the pinned schema declares, for
# each unit the manifest names. The block names the fact its own unit declares, and no fact
# another unit owns. The push block states no `devices`, because the tool names no serial, so
# the provider pushes to all devices in the target.
# Actions need Terraform 1.14 or later, which the `terraform` block declares (§12).

action "panos_commit" "dev_dg_66a86129" {
  config {
    device_groups = ["Dev-DG"]
  }
}

action "panos_push_to_devices" "dev_dg_66a86129" {
  config {
    name = "Dev-DG"
    type = "device_group"
  }
}

