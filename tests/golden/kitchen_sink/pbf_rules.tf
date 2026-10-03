# Policy-Based Forwarding Rules
# Note: PBF rules require careful configuration with virtual routers
# Manual Terraform configuration is required

# Rule: PBF-Forward
#   Action: Forward to 10.0.0.1 via ethernet1/1
#   Description: Forward to next hop

# Rule: PBF-Discard
#   Action: discard

