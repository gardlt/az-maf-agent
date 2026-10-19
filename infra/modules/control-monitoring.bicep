param name string
param workspaceId string
param location string = resourceGroup().location
param assignRuntimeRole bool = false
param runtimePrincipalId string = ''

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceId
    DisableLocalAuth: true
    IngestionMode: 'LogAnalytics'
    RetentionInDays: 30
  }
}
resource publisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignRuntimeRole) {
  name: guid(insights.id, runtimePrincipalId, 'metrics-publisher')
  scope: insights
  properties: {
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}
output connectionString string = insights.properties.ConnectionString
output id string = insights.id
