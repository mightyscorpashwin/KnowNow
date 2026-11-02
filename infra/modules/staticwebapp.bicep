// Static Web App (Standard) hosting the React front end. The Function App is
// linked as its backend, so /api/* is proxied with the signed-in user's
// identity and the Function App only accepts traffic from this site.
param location string
param tags object
param name string
param backendResourceId string
param backendRegion string

resource site 'Microsoft.Web/staticSites@2024-04-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    stagingEnvironmentPolicy: 'Disabled'
    allowConfigFileUpdates: true
  }
}

resource backend 'Microsoft.Web/staticSites/linkedBackends@2024-04-01' = {
  parent: site
  name: 'api'
  properties: {
    backendResourceId: backendResourceId
    region: backendRegion
  }
}

output id string = site.id
output name string = site.name
output defaultHostname string = site.properties.defaultHostname
