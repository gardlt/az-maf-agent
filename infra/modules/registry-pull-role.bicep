param registryName string
param pullIdentityName string
resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = { name: registryName }
resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = { name: pullIdentityName }
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pullIdentity.id, 'acrpull')
  scope: registry
  properties: {
    principalId: pullIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}
