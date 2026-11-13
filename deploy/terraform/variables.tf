variable "one_endpoint" {
  description = "Open Nebula endpoint URL"
  type        = string
  default     = "https://nuada.zcu.cz/RPC2"
}

variable "one_username" {
  description = "OpenNebula username"
  type        = string
  sensitive   = true
}

variable "one_password" {
  description = "OpenNebula authentication token"
  type        = string
  sensitive   = true
}
variable "vm_ssh_pubkey" {
  description = "SSH public key used for login as root into the VM instance"
  type        = string
}
variable "vm_startup_script" {
  description = "VM Startup script"
  type        = string
}
variable "vm_imagedatastore_id" {
  description = "Open Nebula datastore ID"
  default     = 101 # => nuada_pool
  type        = string
}

variable "vm_existing_image_id" {
  description = "If set, reuse an existing OpenNebula image ID instead of creating a new image resource."
  type        = number
  default     = null
}
variable "vm_network_id" {
  description = "ID of the virtual network to attach to the virtual machine"
  #default = 3 # => "vlan173"
  default = 1 # => "vlan121 (aether)"
}
variable "vm_image_name" {
  description = "VM OS image name"
}
variable "vm_image_url" {
  description = "VM OS image URL"
}

variable "vm_count" {
  description = "Number of VMs to create"
  default     = 1
}

variable "vm_name_prefix" {
  description = "VM name prefix"
  default     = "nvd-mirror"
}

variable "vm_cpu" {
  description = "Number of CPU units"
  type        = number
  default     = 2
}

variable "vm_vcpu" {
  description = "Number of virtual CPUs"
  type        = number
  default     = 2
}

variable "vm_memory" {
  description = "VM memory in MB"
  type        = number
  default     = 4096
}

variable "vm_disk_size" {
  description = "VM disk size in MB"
  type        = number
  default     = 25000
}
