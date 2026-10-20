@description('Parallel dev foundation; does not modify the working environment or registry.')
param environmentName string
param vnetName string
param firewallName string
param firewallPolicyName string
param routeTableName string
param nsgName string
param logsName string
param registryLoginServer string
@description('Premium ACR dedicated data endpoint; enable before app cutover. No shared Blob wildcard is allowed.')
param registryDataEndpoint string
param memoryBlobHost string
param foundryHost string
param insightsIngestionHost string
param location string = resourceGroup().location
param vnetCidr string = '10.83.0.0/24'
param firewallSubnetCidr string = '10.83.0.0/26'
param managementSubnetCidr string = '10.83.0.64/26'
param appSubnetCidr string = '10.83.0.128/27'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logsName
}
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [vnetCidr] }
    subnets: [
      { name: 'AzureFirewallSubnet', properties: { addressPrefix: firewallSubnetCidr } }
      { name: 'AzureFirewallManagementSubnet', properties: { addressPrefix: managementSubnetCidr } }
    ]
  }
}
resource firewallIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'pip-${firewallName}'
  location: location
  sku: { name: 'Standard', tier: 'Regional' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}
resource managementIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'pip-${firewallName}-mgmt'
  location: location
  sku: { name: 'Standard', tier: 'Regional' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}
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
resource firewall 'Microsoft.Network/azureFirewalls@2024-05-01' = {
  name: firewallName
  location: location
  properties: {
    sku: { name: 'AZFW_VNet', tier: 'Basic' }
    firewallPolicy: { id: policy.id }
    ipConfigurations: [{
      name: 'data'
      properties: {
        publicIPAddress: { id: firewallIp.id }
        subnet: { id: '${vnet.id}/subnets/AzureFirewallSubnet' }
      }
    }]
    managementIpConfiguration: {
      name: 'management'
      properties: {
        publicIPAddress: { id: managementIp.id }
        subnet: { id: '${vnet.id}/subnets/AzureFirewallManagementSubnet' }
      }
    }
  }
  dependsOn: [rules]
}
resource routes 'Microsoft.Network/routeTables@2024-05-01' = {
  name: routeTableName
  location: location
  properties: {
    disableBgpRoutePropagation: true
    routes: [{
      name: 'default-via-firewall'
      properties: {
        addressPrefix: '0.0.0.0/0'
        nextHopType: 'VirtualAppliance'
        nextHopIpAddress: firewall.properties.ipConfigurations[0].properties.privateIPAddress
      }
    }]
  }
}
resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'allow-environment-internal'
        properties: {
          priority: 100, direction: 'Outbound', access: 'Allow', protocol: '*'
          sourceAddressPrefix: appSubnetCidr, destinationAddressPrefix: appSubnetCidr
          sourcePortRange: '*', destinationPortRange: '*'
        }
      }
      {
        name: 'allow-platform-dns'
        properties: {
          priority: 110, direction: 'Outbound', access: 'Allow', protocol: '*'
          sourceAddressPrefix: appSubnetCidr, destinationAddressPrefix: '168.63.129.16'
          sourcePortRange: '*', destinationPortRange: '53'
        }
      }
      {
        name: 'allow-https-through-required-route'
        properties: {
          priority: 120, direction: 'Outbound', access: 'Allow', protocol: 'Tcp'
          sourceAddressPrefix: appSubnetCidr, destinationAddressPrefix: '*'
          sourcePortRange: '*', destinationPortRange: '443'
        }
      }
      {
        name: 'deny-other-outbound'
        properties: {
          priority: 400, direction: 'Outbound', access: 'Deny', protocol: '*'
          sourceAddressPrefix: '*', destinationAddressPrefix: '*'
          sourcePortRange: '*', destinationPortRange: '*'
        }
      }
    ]
  }
}
resource appSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-apps'
  properties: {
    addressPrefix: appSubnetCidr
    networkSecurityGroup: { id: nsg.id }
    routeTable: { id: routes.id }
    delegations: [{ name: 'container-apps', properties: { serviceName: 'Microsoft.App/environments' } }]
  }
}
resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  properties: {
    vnetConfiguration: { infrastructureSubnetId: appSubnet.id, internal: false }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }
}
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'firewall-to-existing-workspace'
  scope: firewall
  properties: {
    workspaceId: logs.id
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      { category: 'AzureFirewallApplicationRule', enabled: true }
      { category: 'AzureFirewallNetworkRule', enabled: true }
    ]
  }
}
output environmentId string = managedEnvironment.id
output environmentDefaultDomain string = managedEnvironment.properties.defaultDomain
output firewallId string = firewall.id
output appSubnetId string = appSubnet.id
