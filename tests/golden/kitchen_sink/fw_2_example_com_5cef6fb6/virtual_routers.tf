# Router Configurations
# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)

# Source: device-specific
# Type: Virtual Router (Legacy)
resource "panos_virtual_router" "vr_device_level_7cfc3546" {
  location = {
    ngfw = {
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "vr-device-level"
  interfaces = ["ethernet1/1"]
}

