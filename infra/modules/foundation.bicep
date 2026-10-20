@description('Container Apps environment name.')
param environmentName string
@description('Globally unique Basic Azure Container Registry name.')
param registryName string
@allowed(['Basic', 'Standard', 'Premium'])
param registrySku string = 'Basic'
@description('User-assigned identity used only to pull images.')
param pullIdentityName string
@description('Log Analytics workspace name.')
param logsName string
@description('Create the registry pull role assignment. Existing scoped environments can disable this after bootstrap.')
param assignAcrPullRole bool = true
param location string = resourceGroup().location

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logsName
  location: location
  properties: { retentionInDays: 30, sku: { name: 'PerGB2018' } }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: registryName
  location: location
  sku: { name: registrySku }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    dataEndpointEnabled: registrySku == 'Premium'
    encryption: { status: 'disabled' }
    policies: { azureADAuthenticationAsArmPolicy: { status: 'enabled' } }
  }
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: pullIdentityName
  location: location
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignAcrPullRole) {
  name: guid(registry.id, pullIdentity.id, 'acrpull')
  scope: registry
  properties: {
    principalId: pullIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }
}

output managedEnvironmentId string = environment.id
output registryLoginServer string = registry.properties.loginServer
output pullIdentityId string = pullIdentity.id
output pullIdentityPrincipalId string = pullIdentity.properties.principalId
output environmentDefaultDomain string = environment.properties.defaultDomain
