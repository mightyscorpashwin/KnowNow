// Python Function App on a Linux App Service plan (B1).
// A dedicated plan is used because it is a supported Static Web Apps linked
// backend and runs Durable Functions timers reliably with Always On.
param location string
param tags object
param planName string
param name string
param identityId string
param identityClientId string
param storageAccountName string
param appInsightsConnectionString string
@description('Subnet for VNet integration; empty to disable.')
param subnetId string = ''
param appSettings object = {}
param skuName string = 'B1'

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'linux'
  sku: { name: skuName }
  properties: { reserved: true }
}

var baseSettings = {
  FUNCTIONS_EXTENSION_VERSION: '~4'
  FUNCTIONS_WORKER_RUNTIME: 'python'
  APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
  // Identity-based connection to host storage (no account keys)
  AzureWebJobsStorage__accountName: storageAccountName
  AzureWebJobsStorage__credential: 'managedidentity'
  AzureWebJobsStorage__clientId: identityClientId
  // Lets DefaultAzureCredential pick the user-assigned identity
  AZURE_CLIENT_ID: identityClientId
  // The pipeline ships pre-built packages; no build on the server
  SCM_DO_BUILD_DURING_DEPLOYMENT: 'false'
  ENABLE_ORYX_BUILD: 'false'
}

resource site 'Microsoft.Web/sites@2024-04-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identityId}': {} }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    keyVaultReferenceIdentity: identityId
    virtualNetworkSubnetId: empty(subnetId) ? null : subnetId
    vnetRouteAllEnabled: !empty(subnetId)
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
    }
  }
}

resource settings 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: site
  name: 'appsettings'
  properties: union(baseSettings, appSettings)
}

output id string = site.id
output name string = site.name
output defaultHostname string = site.properties.defaultHostName
