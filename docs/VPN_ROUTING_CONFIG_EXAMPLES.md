# Input Shapes: VPN And Routing

These are the XML shapes the converter reads for routing and VPN, with the path
each parse method uses and what the run produces for that shape. The generated
examples are real output, taken from `tests/golden/kitchen_sink/`. The document
index is in [README.md](README.md).

Each shape sits inside a scope the export declares — `shared`, a device group
entry, a template entry, or a device entry. The scope decides the `location`
block, and the report section. The path below is written from the config root,
so it shows the parent the parser needs.

## BGP

Path the parser reads:

```
network/virtual-router/entry/protocol/bgp
devices/entry/<device>/network/virtual-router/entry/protocol/bgp
```

Example shape:

```xml
<protocol>
  <bgp>
    <enable>yes</enable>
    <router-id>1.1.1.1</router-id>
    <local-as>65001</local-as>
    <peer-group>
      <entry name="ISP-Peers">
        <type>ebgp</type>
      </entry>
    </peer-group>
    <peer>
      <entry name="ISP1">
        <peer-as>65000</peer-as>
        <enable>yes</enable>
        <peer-address>
          <ip>203.0.113.2</ip>
        </peer-address>
        <local-address>
          <interface>ethernet1/2</interface>
          <ip>203.0.113.1/30</ip>
        </local-address>
        <peer-group>ISP-Peers</peer-group>
      </entry>
    </peer>
    <redist-rules>
      <entry name="redist-static">
        <enable>yes</enable>
        <address-family-identifier>ip</address-family-identifier>
      </entry>
    </redist-rules>
  </bgp>
</protocol>
```

What the run produces: no `.tf` file. The provider has no BGP resource that
accepts a router ID, an AS number, or peer data, so the captured values go to
`MANUAL_SETUP_REPORT.txt` with the router ID, the AS, the peer groups and the
peers. The parser reads `redist-rules` into the model, but the report prints
only the router, peer groups and peers. That gap is recorded in
[`../backlog.md`](../backlog.md).

## OSPF

Path the parser reads:

```
network/virtual-router/entry/protocol/ospf
devices/entry/<device>/network/virtual-router/entry/protocol/ospf
```

Example shape:

```xml
<protocol>
  <ospf>
    <enable>yes</enable>
    <router-id>1.1.1.1</router-id>
    <area>
      <entry name="0.0.0.0">
        <type>
          <normal/>
        </type>
      </entry>
    </area>
    <interface>
      <entry name="ethernet1/1">
        <enable>yes</enable>
        <passive>no</passive>
        <link-type>broadcast</link-type>
        <metric>10</metric>
      </entry>
    </interface>
  </ospf>
</protocol>
```

What the run produces: no `.tf` file. The captured router ID, areas and
interfaces go to `MANUAL_SETUP_REPORT.txt`. Configure OSPF on the target after
the apply, and use a different router ID for each virtual router.

## IKE crypto profile

Path the parser reads:

```
network/ike/crypto-profiles/ike-crypto-profiles/entry
```

Example shape:

```xml
<ike>
  <crypto-profiles>
    <ike-crypto-profiles>
      <entry name="IKE-DEFAULT">
        <encryption>
          <member>aes256</member>
        </encryption>
        <authentication>
          <member>sha256</member>
        </authentication>
        <dh-group>
          <member>group14</member>
        </dh-group>
        <lifetime>
          <hours>24</hours>
        </lifetime>
      </entry>
    </ike-crypto-profiles>
  </crypto-profiles>
</ike>
```

What the run produces: a `panos_ike_crypto_profile` resource in `vpn.tf`.
The member lists stay lists, and `lifetime` becomes a nested block.

```hcl
resource "panos_ike_crypto_profile" "ike_profile_ike_default_c43fed03" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IKE-DEFAULT"
  encryption = ["aes256"]
  hash = ["sha256"]
  dh_group = ["group14"]
  lifetime = {
    hours = 24
  }
}
```

## IPsec crypto profile

Path the parser reads:

```
network/ike/crypto-profiles/ipsec-crypto-profiles/entry
```

Example shape:

```xml
<crypto-profiles>
  <ipsec-crypto-profiles>
    <entry name="IPSEC-DEFAULT">
      <esp>
        <encryption>
          <member>aes256</member>
        </encryption>
        <authentication>
          <member>sha256</member>
        </authentication>
      </esp>
      <dh-group>group14</dh-group>
      <lifetime>
        <hours>1</hours>
        <kilobytes>4608000</kilobytes>
      </lifetime>
    </entry>
  </ipsec-crypto-profiles>
</crypto-profiles>
```

What the run produces: a `panos_ipsec_crypto_profile` resource in `vpn.tf`. An
`ah` block instead of `esp` selects the `ah` protocol.

```hcl
resource "panos_ipsec_crypto_profile" "ipsec_profile_ipsec_default_c8e40af6" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IPSEC-DEFAULT"
  dh_group = "group14"
  esp = {
    encryption = [ "aes256" ]
    authentication = [ "sha256" ]
  }
  lifetime = {
    hours = 1
  }
  lifesize = {
    kb = 4608000
  }
}
```

## IKE gateway

Path the parser reads:

```
network/ike/gateway/entry
```

Example shape:

```xml
<gateway>
  <entry name="Branch-Office-IKE-GW">
    <authentication>
      <pre-shared-key>
        <key/>
      </pre-shared-key>
    </authentication>
    <protocol>
      <ikev2>
        <ike-crypto-profile>IKE-DEFAULT</ike-crypto-profile>
      </ikev2>
    </protocol>
    <local-address>
      <interface>ethernet1/2</interface>
    </local-address>
    <peer-address>
      <fqdn>branch.example.com</fqdn>
    </peer-address>
    <local-id>
      <id>local.example.com</id>
    </local-id>
    <peer-id>
      <id>peer.example.com</id>
    </peer-id>
  </entry>
</gateway>
```

What the run produces: a `panos_ike_gateway` resource in `vpn.tf`. The crypto
profile reference resolves to the resource the same run declared. The parser
records the authentication type (`pre-shared-key` or `certificate`) and always
writes the placeholder key `***CHANGE_ME***`, even when the export carries a key.

```hcl
resource "panos_ike_gateway" "ike_gw_ike_gw_branch_4b617d92" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IKE-GW-Branch"
  protocol = {
    version = "ikev2"
    ikev2 = {
      ike_crypto_profile = panos_ike_crypto_profile.ike_profile_ike_default_c43fed03.name
    }
  }
  peer_address = {
    fqdn = "branch.example.com"
  }
  authentication = {
    pre_shared_key = {
      key = "***CHANGE_ME***"
    }
  }  # *** CHANGE THIS KEY ***
  local_id = {
    id = "local.example.com"
  }
  peer_id = {
    id = "peer.example.com"
  }
}
```

## IPsec tunnel and proxy id

Path the parser reads:

```
network/tunnel/ipsec/entry
```

Example shape:

```xml
<tunnel>
  <ipsec>
    <entry name="Branch-Office-Tunnel">
      <tunnel-interface>tunnel.1</tunnel-interface>
      <auto-key>
        <ike-gateway>
          <entry name="Branch-Office-IKE-GW"/>
        </ike-gateway>
        <ipsec-crypto-profile>IPSEC-DEFAULT</ipsec-crypto-profile>
        <proxy-id>
          <entry name="proxy-1">
            <local>10.0.0.0/8</local>
            <remote>192.168.0.0/16</remote>
            <protocol>
              <number>17</number>
            </protocol>
          </entry>
        </proxy-id>
      </auto-key>
    </entry>
  </ipsec>
</tunnel>
```

What the run produces: one `panos_ipsec_tunnel` resource in `vpn.tf`. Provider
v2 has no standalone proxy-id resource, so each proxy-id is written inside its
tunnel. A `manual-key` tunnel is not emitted; it is reported.

```hcl
resource "panos_ipsec_tunnel" "tunnel_tun_branch_666031d0" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "TUN-Branch"
  tunnel_interface = "tunnel.1"
  auto_key = {
    ike_gateway = [
      {
        name = panos_ike_gateway.ike_gw_ike_gw_branch_4b617d92.name
      }
    ]
    ipsec_crypto_profile = panos_ipsec_crypto_profile.ipsec_profile_ipsec_default_c8e40af6.name
    proxy_id = [
      {
        name = "proxy-1"
        local = "10.0.0.0/8"
        remote = "192.168.0.0/16"
        protocol = {
          number = 17
        }
      }
    ]
  }
}
```

## Pre-shared keys

A Panorama export does not carry pre-shared keys. The converter writes the
placeholder `***CHANGE_ME***` and lists every gateway in
`VPN_MIGRATION_REPORT.txt`, with the actions:

1. Get the real keys from your key management system.
2. Put them in the output, or reference them through a variable, before apply.
3. Do not commit real keys.

The post-run gate reports a placeholder as WARN, so a run that contains one
still exits 0. The gate lists the placeholders in `SANITY_REPORT.txt`.
