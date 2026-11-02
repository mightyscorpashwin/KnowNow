// KnowNow – Azure infrastructure (resource-group scope)
// Deploy:  az deployment group create -g <rg> -f infra/main.bicep -p infra/env/dev.bicepparam

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------
@description('Environment name, used in resource names and tags.')
@allowed(['dev', 'test', 'prod'])
param environmentName string

@description('Region for most resources. Defaults to the resource group region.')
param location string = resourceGroup().location

@description('Region for Static Web Apps (only some regions host the Standard plan).')
@allowed(['westus2', 'centralus', 'eastus2', 'westeurope', 'eastasia'])
param staticWebAppLocation string = 'eastasia'

@description('Region for Azure OpenAI. Must offer the chosen model for GlobalStandard deployments.')
param openAiLocation string = location

@description('Azure OpenAI model to deploy for drafting content.')
param openAiModelName string = 'gpt-5.4-mini'

@description('Model version. Check the Azure OpenAI model list for your region before changing.')
param openAiModelVersion string = '2026-03-17'

@description('Deployment capacity in thousands of tokens per minute.')
@minValue(1)
param openAiCapacity int = 50

@description('Put Cosmos DB, Storage, Azure OpenAI and Key Vault behind private endpoints.')
param enablePrivateNetworking bool = false

@description('Comma-separated e-mail addresses allowed to review and publish content.')
param reviewerEmails string = ''

@description('Object ID of an Entra ID security group whose members may review content (optional).')
param reviewerGroupId string = ''

@description('Object ID of the pipeline service principal or user running the deployment. Gets Key Vault secret write access for the SSO setup script.')
param deployerPrincipalId string = ''

@allowed(['ServicePrincipal', 'User'])
param deployerPrincipalType string = 'ServicePrincipal'

@description('NCRONTAB schedule for the content refresh job (default: Mondays 02:00 UTC).')
param contentRefreshSchedule string = '0 0 2 * * 1'

param tags object = {}

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var token = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var baseName = 'knownow-${environmentName}'
var allTags = union(tags, {
  app: 'knownow'
  environment: environmentName
})

var names = {
  logAnalytics: 'log-${baseName}'
  appInsights: 'appi-${baseName}'
  identity: 'id-${baseName}'
  storage: take('stknownow${environmentName}${token}', 24)
  cosmos: 'cosmos-${baseName}-${take(token, 6)}'
  openAi: 'oai-${baseName}-${take(token, 6)}'
  keyVault: take('kv-knownow-${environmentName}-${token}', 24)
  plan: 'asp-${baseName}'
  functionApp: 'func-${baseName}-${take(token, 6)}'
  staticWebApp: 'swa-${baseName}-${take(token, 6)}'
  vnet: 'vnet-${baseName}'
}

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: allTags
    logAnalyticsName: names.logAnalytics
    appInsightsName: names.appInsights
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: names.identity
  location: location
  tags: allTags
}

module network 'modules/network.bicep' = if (enablePrivateNetworking) {
  name: 'network'
  params: {
    location: location
    tags: allTags
    vnetName: names.vnet
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    tags: allTags
    name: names.storage
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: location
    tags: allTags
    name: names.cosmos
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

module openAi 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    location: openAiLocation
    tags: allTags
    name: names.openAi
    modelName: openAiModelName
    modelVersion: openAiModelVersion
    capacity: openAiCapacity
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    tags: allTags
    name: names.keyVault
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

// Private endpoints (one per service sub-resource)
// Resource IDs are built from names so the loop can be evaluated up front.
var storageId = resourceId('Microsoft.Storage/storageAccounts', names.storage)
var privateEndpointTargets = [
  { name: 'cosmos', id: resourceId('Microsoft.DocumentDB/databaseAccounts', names.cosmos), group: 'Sql', zone: 'privatelink.documents.azure.com' }
  { name: 'openai', id: resourceId('Microsoft.CognitiveServices/accounts', names.openAi), group: 'account', zone: 'privatelink.openai.azure.com' }
  { name: 'blob', id: storageId, group: 'blob', zone: 'privatelink.blob.${environment().suffixes.storage}' }
  { name: 'queue', id: storageId, group: 'queue', zone: 'privatelink.queue.${environment().suffixes.storage}' }
  { name: 'table', id: storageId, group: 'table', zone: 'privatelink.table.${environment().suffixes.storage}' }
  { name: 'vault', id: resourceId('Microsoft.KeyVault/vaults', names.keyVault), group: 'vault', zone: 'privatelink.vaultcore.azure.net' }
]

module privateEndpoints 'modules/private-endpoint.bicep' = [
  for target in privateEndpointTargets: if (enablePrivateNetworking) {
    name: 'pe-${target.name}'
    params: {
      location: location
      tags: allTags
      name: 'pe-${baseName}-${target.name}'
      subnetId: enablePrivateNetworking ? network!.outputs.privateEndpointSubnetId : ''
      vnetId: enablePrivateNetworking ? network!.outputs.vnetId : ''
      targetResourceId: target.id
      groupId: target.group
      privateDnsZoneName: target.zone
    }
    dependsOn: [cosmos, openAi, storage, keyVault]
  }
]

module functionApp 'modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    tags: allTags
    planName: names.plan
    name: names.functionApp
    identityId: identity.id
    identityClientId: identity.properties.clientId
    storageAccountName: storage.outputs.name
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    subnetId: enablePrivateNetworking ? network!.outputs.appSubnetId : ''
    appSettings: {
      COSMOS_ENDPOINT: cosmos.outputs.endpoint
      COSMOS_DATABASE: cosmos.outputs.databaseName
      AZURE_OPENAI_ENDPOINT: openAi.outputs.endpoint
      AZURE_OPENAI_DEPLOYMENT: openAi.outputs.deploymentName
      STORAGE_BLOB_ENDPOINT: storage.outputs.blobEndpoint
      LEARN_MCP_URL: 'https://learn.microsoft.com/api/mcp'
      REVIEWER_EMAILS: reviewerEmails
      REVIEWER_GROUP_ID: reviewerGroupId
      CONTENT_REFRESH_SCHEDULE: contentRefreshSchedule
      KNOWNOW_ENVIRONMENT: environmentName
    }
  }
  dependsOn: [privateEndpoints]
}

module staticWebApp 'modules/staticwebapp.bicep' = {
  name: 'staticwebapp'
  params: {
    location: staticWebAppLocation
    tags: allTags
    name: names.staticWebApp
    backendResourceId: functionApp.outputs.id
    backendRegion: location
  }
}

module roles 'modules/roles.bicep' = {
  name: 'roles'
  params: {
    principalId: identity.properties.principalId
    storageAccountName: storage.outputs.name
    cosmosAccountName: cosmos.outputs.name
    openAiAccountName: openAi.outputs.name
    keyVaultName: keyVault.outputs.name
    deployerPrincipalId: deployerPrincipalId
    deployerPrincipalType: deployerPrincipalType
  }
}

// ---------------------------------------------------------------------------
// Outputs (used by the pipeline and scripts)
// ---------------------------------------------------------------------------
output functionAppName string = functionApp.outputs.name
output staticWebAppName string = staticWebApp.outputs.name
output staticWebAppHostname string = staticWebApp.outputs.defaultHostname
output keyVaultName string = keyVault.outputs.name
output cosmosEndpoint string = cosmos.outputs.endpoint
output openAiEndpoint string = openAi.outputs.endpoint
output appInsightsName string = names.appInsights
