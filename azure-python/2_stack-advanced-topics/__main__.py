## Exercise 1: Create and use a configuration secret for a password.
## NOTE: The code as written now will fail since there is a reference to a password variable that is not set.
## The goal of this exercise is to address that by storing the password in the stack config as a secret
## And then getting the value in the code.
# Config Doc: https://www.pulumi.com/docs/intro/concepts/config/ 
# Secrets Doc: https://www.pulumi.com/docs/intro/concepts/secrets/

## Exercise 2: Get the kubeconfig value from the K8s stack, programmatically set it as a secret and make it a stack output.
## Exercise 2a: See the secret output's value.
# Programmatic Secrets Doc: https://www.pulumi.com/docs/intro/concepts/secrets/#programmatically-creating-secrets
# Stack Outputs Doc: https://www.pulumi.com/docs/intro/concepts/stack/#outputs
# Seeing Stack Secret Outputs Doc: https://www.pulumi.com/docs/reference/cli/pulumi_stack/

## Exercise 3: Make the code more modular and readable by moving config and related set up to it's own file
## and move the cluster decalration and related bits to it's own file. 
## Hint: This is simply using python constructs to create a more modular code base.

import base64
import pulumi
from pulumi import Config
from pulumi_tls import PrivateKey
from pulumi_azure_native import resources, containerservice
import pulumi_azuread as azuread
import pulumi_kubernetes as k8s

config = Config()
k8s_version = config.get('k8sVersion') or '1.18.14'
admin_username = config.get('adminUserName') or 'testuser'
node_count = config.get_int('nodeCount') or 2
node_size = config.get('nodeSize') or 'Standard_D2_v2'

generated_key_pair = PrivateKey('ssh-key',
    algorithm='RSA', rsa_bits=4096)
ssh_public_key = generated_key_pair.public_key_openssh

resource_group = resources.ResourceGroup('rg')

ad_app = azuread.Application('app', display_name='app')
ad_sp = azuread.ServicePrincipal('service-principal',
    application_id=ad_app.application_id)
ad_sp_password = azuread.ServicePrincipalPassword('sp-password',
    service_principal_id=ad_sp.id,
    value=password,
    end_date='2099-01-01T00:00:00Z')

k8s_cluster = containerservice.ManagedCluster('cluster',
    resource_group_name=resource_group.name,
    addon_profiles={
        'KubeDashboard': {
            'enabled': True,
        },
    },
    agent_pool_profiles=[{
        'count': node_count,
        'max_pods': 2,
        'mode': 'System',
        'name': 'agentpool',
        'node_labels': {},
        'os_disk_size_gb': 30,
        'os_type': 'Linux',
        'type': 'VirtualMachineScaleSets',
        'vm_size': node_size,
    }],
    dns_prefix=resource_group.name,
    enable_rbac=True,
    kubernetes_version=k8s_version,
    linux_profile={
        'admin_username': admin_username,
        'ssh': {
            'publicKeys': [{
                'keyData': ssh_public_key,
            }],
        },
    },
    node_resource_group='node-resource-group',
    service_principal_profile={
        'client_id': ad_app.application_id,
        'secret': ad_sp_password.value,
    })

creds = pulumi.Output.all(resource_group.name, k8s_cluster.name).apply(
    lambda args:
    containerservice.list_managed_cluster_user_credentials(
        resource_group_name=args[0],
        resource_name=args[1]))

kubeconfig = creds.kubeconfigs[0].value.apply(
    lambda enc: base64.b64decode(enc).decode())

k8s_provider = k8s.Provider('k8s-provider', kubeconfig=kubeconfig)

apache = Chart('apache-chart',
    ChartOpts(
        chart='apache',
        version='8.3.2',
        fetch_opts={'repo': 'https://charts.bitnami.com/bitnami'}),
    ResourceOptions(provider=k8s_provider))

apache_service_ip = apache.get_resource('v1/Service', 'apache-chart').apply(
    lambda res: res.status.load_balancer.ingress[0].ip)

pulumi.export('resource_group_name', resource_group.name)
pulumi.export('cluster_name', k8s_cluster.name)
pulumi.export('apache_service_ip', f'http://{apache_service_ip}')