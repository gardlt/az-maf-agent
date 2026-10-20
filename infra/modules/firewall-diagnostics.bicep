param firewallName string
param workspaceId string
resource firewall 'Microsoft.Network/azureFirewalls@2024-05-01' existing = {name: firewallName}
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'firewall-to-existing-workspace'
  scope: firewall
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      { category: 'AzureFirewallApplicationRule', enabled: true }
      { category: 'AzureFirewallNetworkRule', enabled: true }
    ]
  }
}
