"""Provisions an AKS cluster and deploys an Apache helm chart."""

import base64

from pulumi_azure_native import resources, containerservice
import pulumi
import pulumi_azuread as azuread
import pulumi_kubernetes as k8s
from pulumi import Config
from pulumi_random import RandomPassword
from pulumi_tls import PrivateKey

config = Config()
k8s_version = config.get('k8sVersion') or '1.18.14'
password = config.getSecret('password') or RandomPassword('pw',
    length=20, special=True)

generated_key_pair = PrivateKey('ssh-key',
    algorithm='RSA', rsa_bits=4096)
ssh_public_key = generated_key_pair.public_key_openssh

admin_username = config.get('adminUserName') or 'testuser'

node_count = config.get_int('nodeCount') or 2
node_size = config.get('nodeSize') or 'Standard_D2_v2'

resource_group = resources.ResourceGroup('rg')

ad_app = azuread.Application('app', display_name='app')
ad_sp = azuread.ServicePrincipal('service-principal',
    application_id=ad_app.application_id)
ad_sp_password = azuread.ServicePrincipalPassword('sp-password',
    service_principal_id=ad_sp.id,
    value=config.password,
    end_date='2099-01-01T00:00:00Z')

k8s_cluster = containerservice.ManagedCluster('cluster',
    resource_group_name=resource_group.name,
    addon_profiles={
        'KubeDashboard': {
            'enabled': True,
        },
    },
    agent_pool_profiles=[{
        'count': config.node_count,
        'max_pods': 110,
        'mode': 'System',
        'name': 'agentpool',
        'node_labels': {},
        'os_disk_size_gb': 30,
        'os_type': 'Linux',
        'type': 'VirtualMachineScaleSets',
        'vm_size': config.node_size,
    }],
    dns_prefix=resource_group.name,
    enable_rbac=True,
    kubernetes_version=config.k8s_version,
    linux_profile={
        'admin_username': config.admin_username,
        'ssh': {
            'publicKeys': [{
                'keyData': config.ssh_public_key,
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

pulumi.export('cluster_name', k8s_cluster.name)
pulumi.export('kubeconfig', kubeconfig)
pulumi.export('apache_service_ip', apache_service_ip)