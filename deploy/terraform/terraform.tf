terraform {
  required_providers {
    opennebula = {
      source  = "OpenNebula/opennebula"
      version = "1.4"
    }
  }
}

provider "opennebula" {
  endpoint = var.one_endpoint
  username = var.one_username
  password = var.one_password
}

resource "opennebula_image" "os-image" {
  count        = var.vm_existing_image_id == null ? 1 : 0
  name         = var.vm_image_name
  datastore_id = var.vm_imagedatastore_id
  persistent   = false
  path         = var.vm_image_url
  permissions  = "600"
}

resource "opennebula_virtual_machine" "nvd_mirror" {
  count       = var.vm_count
  name        = "${var.vm_name_prefix}-${count.index + 1}"
  description = "NVD Mirror Kubernetes node"

  cpu         = var.vm_cpu
  vcpu        = var.vm_vcpu
  memory      = var.vm_memory

  context = {
    NETWORK        = "YES"
    HOSTNAME       = "$NAME"
    SSH_PUBLIC_KEY = var.vm_ssh_pubkey
    START_SCRIPT   = var.vm_startup_script
    #START_SCRIPT_BASE64 = ""
  }
  os {
    arch = "x86_64"
    boot = "disk0"
  }
disk {
  image_id = var.vm_existing_image_id != null ? var.vm_existing_image_id : opennebula_image.os-image[0].id
  target   = "vda"
  size     = var.vm_disk_size
}

#  graphics {
#   listen = "0.0.0.0"
#    type   = "vnc"
#  }

  nic {
    network_id = var.vm_network_id
  }
}

# ------- OUTPUTS ------------

output "vm_ips" {
  value = opennebula_virtual_machine.nvd_mirror[*].ip
}
