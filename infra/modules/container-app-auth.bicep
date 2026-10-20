param appName string
param properties object
resource app 'Microsoft.App/containerApps@2025-01-01' existing = { name: appName }
resource auth 'Microsoft.App/containerApps/authConfigs@2025-01-01' = {
  parent: app
  name: 'current'
  properties: properties
}
