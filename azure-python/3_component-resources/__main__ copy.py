## Exercise 1: Move the VirtualNetwork, PublicIpAddress and NetworkInterface resources to a component resource.
## It should take as input parameters: 
## - resource group name 
## It should provide the following outputs: 
## - NetworkInterface ID
## - Public IP Address (Hint: Move/modify the block of code used to get the public IP address to the component resource.)
# Component Resources Doc: https://www.pulumi.com/docs/intro/concepts/resources/#components
# Example Code: https://github.com/pulumi/examples/blob/master/azure-py-virtual-data-center/spoke.py

## Exercise 2: Add the "protect" resource option to the "network" resource and do a `pulumi up` and then a `pulumi destroy`
## Note how the component resource children get the protect option enabled.
## Note how you can't destroy the stack as long as protect is true.
# Doc: https://www.pulumi.com/docs/intro/concepts/resources/#protect
# Doc: https://www.pulumi.com/docs/reference/cli/pulumi_state_unprotect/

import base64
from pulumi import Config, Output, export
import pulumi_azure_native.compute as compute
import pulumi_azure_native.network as network
import pulumi_azure_native.resources as resources
import pulumi_random as random

config = Config()
username = config.get("username") or "webserver"

# Get secretified password from config and protect it going forward, or create one using the 'random' provider.
password=config.get_secret("password")
if not password:
    rando_password=random.RandomPassword('password',
        length=16,
        special=True,
        override_special='@_#',
        )
    password=rando_password.result 

resource_group = resources.ResourceGroup("server")

net = network.VirtualNetwork(
    "server-network",
    resource_group_name=resource_group.name,
    address_space=network.AddressSpaceArgs(
        address_prefixes=["10.0.0.0/16"],
    ),
    subnets=[network.SubnetArgs(
        name="default",
        address_prefix="10.0.1.0/24",
    )])

public_ip = network.PublicIPAddress(
    "server-ip",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IPAllocationMethod.DYNAMIC)

network_iface = network.NetworkInterface(
    "server-nic",
    resource_group_name=resource_group.name,
    ip_configurations=[network.NetworkInterfaceIPConfigurationArgs(
        name="webserveripcfg",
        subnet=network.SubnetArgs(id=net.subnets[0].id),
        private_ip_allocation_method=network.IPAllocationMethod.DYNAMIC,
        public_ip_address=network.PublicIPAddressArgs(id=public_ip.id),
    )])

init_script = """#!/bin/bash

echo "Hello, World!" > index.html
nohup python -m SimpleHTTPServer 80 &"""

vm = compute.VirtualMachine(
    "server-vm",
    resource_group_name=resource_group.name,
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(id=network_iface.id),
        ],
    ),
    hardware_profile=compute.HardwareProfileArgs(
        vm_size=compute.VirtualMachineSizeTypes.STANDARD_A0,
    ),
    os_profile=compute.OSProfileArgs(
        computer_name="hostname",
        admin_username=username,
        admin_password=password,
        custom_data=base64.b64encode(init_script.encode("ascii")).decode("ascii"),
        linux_configuration=compute.LinuxConfigurationArgs(
            disable_password_authentication=False,
        ),
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            create_option=compute.DiskCreateOptionTypes.FROM_IMAGE,
        ),
        image_reference=compute.ImageReferenceArgs(
            publisher="canonical",
            offer="UbuntuServer",
            sku="16.04-LTS",
            version="latest",
        ),
    ))

combined_output = Output.all(vm.id, public_ip.name, resource_group.name)
public_ip_addr = combined_output.apply(
    lambda lst: network.get_public_ip_address(
        public_ip_address_name=lst[1], 
        resource_group_name=lst[2]))
export("public_ip", public_ip_addr.ip_address)