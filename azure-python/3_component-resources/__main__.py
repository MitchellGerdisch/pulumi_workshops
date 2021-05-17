# Builds a static website using Azure CDN, and Storage Account
#
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

import pulumi
import pulumi_azure_native.cdn as cdn
import pulumi_azure_native.resources as resources
import pulumi_azure_native.storage as storage

resource_group = resources.ResourceGroup("resourceGroup")

profile = cdn.Profile(
    "profile",
    resource_group_name=resource_group.name,
    sku=cdn.SkuArgs(
        name=cdn.SkuName.STANDARD_MICROSOFT,
    ))

storage_account = storage.StorageAccount(
    "storageaccount",
    access_tier=storage.AccessTier.HOT,
    enable_https_traffic_only=True,
    encryption=storage.EncryptionArgs(
        key_source=storage.KeySource.MICROSOFT_STORAGE,
        services=storage.EncryptionServicesArgs(
            blob=storage.EncryptionServiceArgs(
                enabled=True,
            ),
            file=storage.EncryptionServiceArgs(
                enabled=True,
            ),
        ),
    ),
    kind=storage.Kind.STORAGE_V2,
    network_rule_set=storage.NetworkRuleSetArgs(
        bypass=storage.Bypass.AZURE_SERVICES,
        default_action=storage.DefaultAction.ALLOW,
    ),
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(
        name=storage.SkuName.STANDARD_LRS,
    ))

endpoint_origin = storage_account.primary_endpoints.apply(
    lambda primary_endpoints: primary_endpoints.web.replace("https://", "").replace("/", ""))

endpoint = cdn.Endpoint(
    "endpoint",
    endpoint_name=storage_account.name.apply(lambda sa: f"cdn-endpnt-{sa}"),
    is_http_allowed=False,
    is_https_allowed=True,
    origin_host_header=endpoint_origin,
    origins=[cdn.DeepCreatedOriginArgs(
        host_name=endpoint_origin,
        https_port=443,
        name="origin-storage-account",
    )],
    profile_name=profile.name,
    query_string_caching_behavior=cdn.QueryStringCachingBehavior.NOT_SET,
    resource_group_name=resource_group.name)

# Enable static website support
static_website = storage.StorageAccountStaticWebsite(
    "staticWebsite",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    index_document="index.html",
    error404_document="404.html")

# Upload the files
index_html = storage.Blob(
    "index_html",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=static_website.container_name,
    source=pulumi.FileAsset("./wwwroot/index.html"),
    content_type="text/html")
notfound_html = storage.Blob(
    "notfound_html",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=static_website.container_name,
    source=pulumi.FileAsset("./wwwroot/404.html"),
    content_type="text/html")

# Web endpoint to the website
pulumi.export("staticEndpoint", storage_account.primary_endpoints.web)

# CDN endpoint to the website.
# Allow it some time after the deployment to get ready.
pulumi.export("cdnEndpoint", endpoint.host_name.apply(lambda host_name: f"https://{host_name}"))
