@description('Existing dedicated dev account; this module does not change preference backup settings.')
param accountName string
resource account 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: accountName }
resource service 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = { parent: account, name: 'default' }
resource policy 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = { parent: service, name: 'guardrail-policy', properties: { publicAccess: 'None' } }
resource state 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = { parent: service, name: 'guardrail-state', properties: { publicAccess: 'None' } }
resource audit 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = { parent: service, name: 'guardrail-audit', properties: { publicAccess: 'None' } }
resource sessions 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = { parent: service, name: 'agent-sessions', properties: { publicAccess: 'None' } }
resource retention 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: audit
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: 30
    allowProtectedAppendWrites: false
    allowProtectedAppendWritesAll: false
  }
}
resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: account
  name: 'default'
  properties: {
    policy: {
      rules: [for prefix in ['guardrail-audit/events/', 'guardrail-policy/approvals/']: {
        name: 'retire-${split(prefix, '/')[0]}'
        enabled: true
        type: 'Lifecycle'
        definition: {
          filters: { blobTypes: ['blockBlob'], prefixMatch: [prefix] }
          actions: { baseBlob: { delete: { daysAfterModificationGreaterThan: 30 } } }
        }
      }]
    }
  }
}
output auditContainerId string = audit.id
output policyContainerId string = policy.id
output stateContainerId string = state.id
output sessionsContainerId string = sessions.id
