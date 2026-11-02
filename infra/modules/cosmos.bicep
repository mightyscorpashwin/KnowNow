// Cosmos DB for NoSQL, serverless. Local (key) auth is disabled.
param location string
param tags object
param name string
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string

var databaseName = 'knownow'

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: publicNetworkAccess
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    capabilities: [{ name: 'EnableServerless' }]
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: { id: databaseName }
  }
}

// Topics and sub-topics (the catalogue)
resource catalog 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: 'catalog'
  properties: {
    resource: {
      id: 'catalog'
      partitionKey: { paths: ['/topicId'], kind: 'Hash' }
    }
  }
}

// Generated pages, with status draft -> approved / rejected
resource pages 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: 'pages'
  properties: {
    resource: {
      id: 'pages'
      partitionKey: { paths: ['/topicId'], kind: 'Hash' }
    }
  }
}

output id string = account.id
output name string = account.name
output endpoint string = account.properties.documentEndpoint
output databaseName string = databaseName
