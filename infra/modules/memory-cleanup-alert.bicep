param name string
param workspaceId string
param location string = resourceGroup().location

@description('Portal alert only; no notification recipients are configured by this module.')
resource heartbeat 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: name
  location: location
  properties: {
    displayName: 'Memory cleanup has no successful execution in 20 hours'
    description: 'Investigate before the 24-hour expiry cleanup target is breached. No preference contents are queried.'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT1H'
    windowSize: 'P1D'
    scopes: [workspaceId]
    autoMitigate: true
    criteria: {
      allOf: [{
        query: 'ContainerAppConsoleLogs_CL | where TimeGenerated > ago(20h) | where Log_s has "memory_cleanup_completed" | summarize Successes=count() | where Successes == 0'
        timeAggregation: 'Count'
        operator: 'GreaterThan'
        threshold: 0
        failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 }
      }]
    }
  }
}
