param name string
param runtimePrincipalId string
resource insights 'Microsoft.Insights/components@2020-02-02' existing = { name: name }
resource publisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, runtimePrincipalId, 'metrics-publisher')
  scope: insights
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}
