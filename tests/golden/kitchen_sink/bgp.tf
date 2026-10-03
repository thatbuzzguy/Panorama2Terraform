# BGP Configuration
# Note: BGP configuration requires careful validation.
# Verify all peer addresses and AS numbers before applying.

resource "panos_bgp" "default" {
  virtual_router = panos_virtual_router.default.name
  enable = true
  router_id = "10.0.0.1"
  as_number = "65001"
}

resource "panos_bgp_peer_group" "pg_pg_branch" {
  virtual_router = panos_virtual_router.default.name
  name = "PG-Branch"
  type = "external"
  depends_on = [panos_bgp.default]
}

resource "panos_bgp_peer" "peer_10_55_0_2" {
  virtual_router = panos_virtual_router.default.name
  bgp_peer_group = "PG-Branch"
  name = "10.55.0.2"
  enable = true
  peer_as = "65002"
  local_address_ip = "10.55.0.1"
  peer_address_ip = "10.55.0.2"
  depends_on = [panos_bgp.default]
}

