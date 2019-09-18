import sys
sys.path.append('/usr/local/lib/python2.7/dist-packages')
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from st2common.runners.base_action import Action


class MyEchoAction(Action):

    def run(self, Subcription_id, Group_Name, Location, VM_Name, Client_Id, Secret, Tenant_Id):
        
        #Defining Variables for VM creation 
        SUBSCRIPTION_ID = Subcription_id
        GROUP_NAME = Group_Name
        LOCATION = Location
        VM_NAME = VM_Name
        
        #Function for Creation Availability Set for Virtual Machine 
        def create_availability_set(compute_client):
            avset_params = {
                'location': LOCATION,
                'sku': {'name': 'Aligned'},
                'platform_fault_domain_count': 2
            }
            availability_set_result = compute_client.availability_sets.create_or_update(
                GROUP_NAME,
                'myAVSet',
                avset_params
            )
            
        #Function for Creation Group for Virtual Machine 
        def create_resource_group(resource_group_client):
            resource_group_params = {'location': LOCATION}
            resource_group_result = resource_group_client.resource_groups.create_or_update(
                GROUP_NAME,
                resource_group_params
            )
            
        #Function to get credentials for Authentication 
        def get_credentials():
            credentials = ServicePrincipalCredentials(
                client_id=Client_Id,
                secret=Secret,
                tenant=Tenant_Id
            )
            return credentials
        
        #Function To create Public IP address  
        def create_public_ip_address(network_client):
            public_ip_addess_params = {
                'location': LOCATION,
                'public_ip_allocation_method': 'Dynamic'
            }
            creation_result = network_client.public_ip_addresses.create_or_update(
                GROUP_NAME,
                'myIPAddress',
                public_ip_addess_params
            )
            return creation_result.result()
        #Function to create Vnet for virtual machine  
        def create_vnet(network_client):
            vnet_params = {
                'location': LOCATION,
                'address_space': {
                    'address_prefixes': ['10.0.0.0/16']
                }
            }
            creation_result = network_client.virtual_networks.create_or_update(
                GROUP_NAME,
                'myVNet',
                vnet_params
            )
            return creation_result.result()
        
        #Function to create Subnet for virtual machine 
        def create_subnet(network_client):
            subnet_params = {
                'address_prefix': '10.0.0.0/24'
            }
            creation_result = network_client.subnets.create_or_update(
                GROUP_NAME,
                'myVNet',
                'mySubnet',
                subnet_params
            )
            return creation_result.result()
        
        #Function to create nic for virtual machine 
        def create_nic(network_client):
            subnet_info = network_client.subnets.get(
                GROUP_NAME,
                'myVNet',
                'mySubnet'
            )
            publicIPAddress = network_client.public_ip_addresses.get(
                GROUP_NAME,
                'myIPAddress'
            )
            nic_params = {
                'location': LOCATION,
                'ip_configurations': [{
                    'name': 'myIPConfig',
                    'public_ip_address': publicIPAddress,
                    'subnet': {
                        'id': subnet_info.id
                    }
                }]
            }
            creation_result = network_client.network_interfaces.create_or_update(
                GROUP_NAME,
                'myNic',
                nic_params
            )
            return creation_result.result()
        
        #Function to create the virtual machine using above resources 
        def create_vm(network_client, compute_client):
            nic = network_client.network_interfaces.get(
                GROUP_NAME,
                'myNic'
            )
            avset = compute_client.availability_sets.get(
                GROUP_NAME,
                'myAVSet'
            )
            vm_parameters = {
                'location': LOCATION,
                'os_profile': {
                    'computer_name': VM_NAME,
                    'admin_username': 'azureuser',
                    'admin_password': 'Azure12345678'
                },
                'hardware_profile': {
                    'vm_size': 'Standard_A0'
                },
                'storage_profile': {
                    'image_reference': {
                        'publisher': 'MicrosoftWindowsServer',
                        'offer': 'WindowsServer',
                        'sku': '2012-R2-Datacenter',
                        'version': 'latest'
                    }
                },
                'network_profile': {
                    'network_interfaces': [{
                        'id': nic.id
                    }]
                },
                'availability_set': {
                    'id': avset.id
                }
            }
            creation_result = compute_client.virtual_machines.create_or_update(
                GROUP_NAME,
                VM_NAME,
                vm_parameters
            )
            return creation_result.result()

        credentials = get_credentials()
        
        #Defining Management Clients for creating and managing resources for azure 
        resource_group_client = ResourceManagementClient(
            credentials,
            SUBSCRIPTION_ID
        )
        network_client = NetworkManagementClient(
            credentials,
            SUBSCRIPTION_ID
        )
        compute_client = ComputeManagementClient(
            credentials,
            SUBSCRIPTION_ID
        )
        #Calling all above defined function to create resources and finally Virtual Machine 
        create_resource_group(resource_group_client)
        create_availability_set(compute_client)
        creation_result = create_public_ip_address(network_client)
        creation_result = create_vnet(network_client)
        creation_result = create_subnet(network_client)
        creation_result = create_nic(network_client)
        creation_result = create_vm(network_client, compute_client)
        print("VM created Successfully")
