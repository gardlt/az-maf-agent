@description('Existing Foundry account; deploy this module in its resource group.')
param foundryAccountName string
@description('Entra agent identity service principal object ID, not blueprint ID.')
param agentPrincipalId string

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}
var foundryUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
resource inferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, agentPrincipalId, foundryUserRole)
  scope: foundry
  properties: {
    principalId: agentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: foundryUserRole
  }
}
output assignmentId string = inferenceRole.id
