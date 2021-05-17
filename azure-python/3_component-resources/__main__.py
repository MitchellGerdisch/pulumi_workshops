# Builds a static website using Azure CDN, and Storage Account
#
## Exercise 1: Move the CDN resources into a "frontend" component resource class. 
## It should take as input parameters: 
## - resource group name 
## - origin endpoint
## It should provide the following outputs: 
## - CDN URL 
# Component Resources Doc: https://www.pulumi.com/docs/intro/concepts/resources/#components
# Example Code: https://github.com/pulumi/examples/blob/master/azure-py-virtual-data-center/spoke.py

## Exercise 2: Add the "protect" resource option to the "frontend" resource and do a `pulumi up` and then a `pulumi destroy`
# Doc: https://www.pulumi.com/docs/intro/concepts/resources/#protect
# Note how the protect flag is propagated to the component resource's children. 
# To destroy the stack you can set the flag to false or remove the protect flag and 
# then do another `pulumi up` and then `pulumi destroy`.
# Or, see: https://www.pulumi.com/docs/reference/cli/pulumi_state_unprotect/ 
# For a way to remove protect for a stack state before running `pulumi destroy`

import pulumi
import pulumi_azure_native.cdn as cdn
import pulumi_azure_native.resources as resources
import pulumi_azure_native.storage as storage

base_name = pulumi.get("base_name") or "component"
resource_group = resources.ResourceGroup(f"{base_name}-rg")

profile = cdn.Profile(
    f"{base_name}-profile",
    resource_group_name=resource_group.name,
    sku=cdn.SkuArgs(
        name=cdn.SkuName.STANDARD_MICROSOFT,
    ))

storage_account = storage.StorageAccount(
    f"{base_name}-sa",
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

# Get the base endpoint for the eventual storage account based website by stripping away the URL stuff.
# The CDN will be configured to front this endpoint.
endpoint_origin = storage_account.primary_endpoints.apply(
    lambda primary_endpoints: primary_endpoints.web.replace("https://", "").replace("/", ""))

# Create a CDN endpoint that points at the storage account hosted website.
endpoint = cdn.Endpoint(
    f"{base_name}-endpoint",
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
    f"{base_name}-staticWebsite",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    index_document="index.html",
    error404_document="404.html")

# Upload the website files to storage.
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
# Azure takes a bit of time to set up the CDN.
# So you may need to refresh a few times before it is ready. 
pulumi.export("cdnEndpoint", endpoint.host_name.apply(lambda host_name: f"https://{host_name}"))
