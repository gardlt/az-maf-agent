param name string
param workspaceId string
param location string = resourceGroup().location
param assignRuntimeRole bool = false
param runtimePrincipalId string = ''

module insights '../modules/application-insights.bicep' = {
 name: 'insights'
 params: {name: name, workspaceId: workspaceId, location: location}
}
module publisher '../modules/insights-publisher-role.bicep' = if (assignRuntimeRole) {
 name: 'metrics-access'
 params: {name: name, runtimePrincipalId: runtimePrincipalId}
 dependsOn: [insights]
}
module faults '../modules/scheduled-query-rule.bicep' = {
 name: 'fault-alert'
 params: {
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
}
output connectionString string = insights.outputs.connectionString
output id string = insights.outputs.id
