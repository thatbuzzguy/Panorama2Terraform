# Certificate entries (F7.14)

resource "panos_certificate_import" "vsys_cert_47923f51" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = var.fw_2_example_com
    }
  }
  name = "Vsys-Cert"
  local = {
    pem = {
      certificate = "vsys-pem-value"
      passphrase = var.vsys_cert
      private_key = var.vsys_cert
    }
  }
}

