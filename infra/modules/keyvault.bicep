// Key Vault (RBAC mode). Holds the SSO client secret created by scripts/setup-sso.sh.
param location string
param tags object
param name string
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: publicNetworkAccess == 'Disabled' ? 'Deny' : 'Allow'
    }
  }
}

output id string = vault.id
output name string = vault.name
