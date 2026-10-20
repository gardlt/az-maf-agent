param appName string
param location string = resourceGroup().location
param identity object
@secure()
param properties object
resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  identity: identity
  properties: properties
}
output appId string = app.id
output workloadPrincipalId string = app.identity.?principalId ?? ''
