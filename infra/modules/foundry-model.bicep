targetScope = 'resourceGroup'

@description('Existing Foundry account; this module does not create an account or alter RBAC.')
param accountName string
param deploymentName string = 'gpt-5-mini'
param modelName string = 'gpt-5-mini'
param modelVersion string = '2025-08-07'
@minValue(1)
param capacity int = 30

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource routine 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.Default'
  }
}

output deploymentName string = routine.name
