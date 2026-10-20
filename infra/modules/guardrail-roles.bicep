param accountName string
param runtimePrincipalId string
param cleanupPrincipalId string
param operatorPrincipalId string
resource account 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {name: accountName}
resource service 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {parent: account, name: 'default'}
resource policy 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {parent: service, name: 'guardrail-policy'}
resource state 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {parent: service, name: 'guardrail-state'}
resource audit 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {parent: service, name: 'guardrail-audit'}
resource sessions 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {parent: service, name: 'agent-sessions'}
resource auditWriterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'maf-metadata-audit-writer-v1')
  properties: {
    roleName: 'MAF ${resourceGroup().name} metadata audit writer'
    description: 'Can create audit blobs; cannot delete blobs/containers or change retention. Existing blob overwrite is blocked by the container immutability policy.'
    type: 'CustomRole'
    assignableScopes: [resourceGroup().id]
    permissions: [{
      actions: []
      notActions: []
      dataActions: ['Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write']
      notDataActions: []
    }]
  }
}
resource runtimePolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(policy.id, runtimePrincipalId, 'reader')
  scope: policy
  properties: { principalId: runtimePrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1') }
}
resource runtimeState 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(state.id, runtimePrincipalId, 'writer')
  scope: state
  properties: { principalId: runtimePrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
resource runtimeSessions 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sessions.id, runtimePrincipalId, 'writer')
  scope: sessions
  properties: { principalId: runtimePrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
resource runtimeAudit 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(audit.id, runtimePrincipalId, 'append-writer')
  scope: audit
  properties: { principalId: runtimePrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: auditWriterRole.id }
}
resource cleanupSessions 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sessions.id, cleanupPrincipalId, 'cleanup')
  scope: sessions
  properties: { principalId: cleanupPrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
resource operatorPolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(policy.id, operatorPrincipalId, 'operator')
  scope: policy
  properties: { principalId: operatorPrincipalId, principalType: 'User', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
resource operatorState 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(state.id, operatorPrincipalId, 'operator')
  scope: state
  properties: { principalId: operatorPrincipalId, principalType: 'User', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
resource operatorAudit 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(audit.id, operatorPrincipalId, 'operator')
  scope: audit
  properties: { principalId: operatorPrincipalId, principalType: 'User', roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') }
}
