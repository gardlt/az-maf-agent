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

@description('Portal alert; notification recipients are intentionally not configured.')
resource faults 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${name}-faults'
  location: location
  properties: {
    displayName: 'Agent control denial, budget, outage, or unresolved effect'
    description: 'Inspect metadata-only control_fault categories; authorization remains enforced in the application.'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [workspaceId]
    autoMitigate: true
    criteria: {
      allOf: [{
        query: 'ContainerAppConsoleLogs_CL | where TimeGenerated > ago(5m) | extend Signal=parse_json(Log_s) | where Signal.event == "control_fault" | project TimeGenerated, Category=tostring(Signal.category)'
        timeAggregation: 'Count'
        operator: 'GreaterThan'
        threshold: 0
        failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 }
      }]
    }
  }
}
