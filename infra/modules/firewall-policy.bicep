param firewallPolicyName string
param registryLoginServer string
param registryDataEndpoint string
param memoryBlobHost string
param foundryHost string
param insightsIngestionHost string
param appSubnetCidr string = '10.83.0.128/27'
param location string = resourceGroup().location
resource policy 'Microsoft.Network/firewallPolicies@2024-05-01' = {
  name: firewallPolicyName
  location: location
  properties: {
    sku: { tier: 'Basic' }
    threatIntelMode: 'Alert'
  }
}
resource rules 'Microsoft.Network/firewallPolicies/ruleCollectionGroups@2024-05-01' = {
  parent: policy
  name: 'approved-egress'
  properties: {
    priority: 100
    ruleCollections: [
      {
        name: 'platform-service-dependencies'
        priority: 100
        ruleCollectionType: 'FirewallPolicyFilterRuleCollection'
        action: { type: 'Allow' }
        rules: [{
          name: 'platform-identity-monitor-registry'
          ruleType: 'NetworkRule'
          sourceAddresses: [appSubnetCidr]
          destinationAddresses: ['AzureActiveDirectory', 'AzureMonitor', 'MicrosoftContainerRegistry', 'AzureFrontDoor.FirstParty']
          destinationPorts: ['443']
          ipProtocols: ['TCP']
        }]
      }
      {
        name: 'approved-https-hosts'
        priority: 200
        ruleCollectionType: 'FirewallPolicyFilterRuleCollection'
        action: { type: 'Allow' }
        rules: [{
          name: 'runtime-and-platform-fqdns'
          ruleType: 'ApplicationRule'
          sourceAddresses: [appSubnetCidr]
          protocols: [{ protocolType: 'Https', port: 443 }]
          targetFqdns: [
            'mcr.microsoft.com'
            '*.data.mcr.microsoft.com'
            'packages.aks.azure.com'
            'acs-mirror.azureedge.net'
            registryLoginServer
            registryDataEndpoint
            'login.microsoft.com'
            replace(replace(environment().authentication.loginEndpoint, 'https://', ''), '/', '')
            'api.themoviedb.org'
            memoryBlobHost
            foundryHost
            insightsIngestionHost
            replace(replace(environment().resourceManager, 'https://', ''), '/', '')
          ]
        }]
      }
    ]
  }
}
output id string = policy.id
