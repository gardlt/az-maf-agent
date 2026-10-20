param accountName string
param containerName string = 'preferences'
param principalIds array
resource account 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: accountName }
resource service 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = { parent: account, name: 'default' }
resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: service, name: containerName }
resource roles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in principalIds: {
  name: guid(container.id, principalId, 'memory-blob-data-contributor')
  scope: container
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}]
