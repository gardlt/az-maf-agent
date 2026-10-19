@description('Separate Stage 2 network-test environment; does not alter the current Stage 1 environment.')
param environmentName string = 'cae-az-maf-stage2-nettest'
param vnetName string = 'vnet-az-maf-stage2-nettest'
param subnetName string = 'snet-az-maf-stage2-apps'
param nsgName string = 'nsg-az-maf-stage2-apps'
param location string = resourceGroup().location

@description('Non-overlapping address space reserved for this short-lived network test.')
param vnetCidr string = '10.82.0.0/24'
param appSubnetCidr string = '10.82.0.0/27'

@description('Exact /32 public IP of the test-owned destination. Recheck its DNS and environment static IP before deployment.')
param blockedDestinationCidr string

@description('Existing Log Analytics workspace in this resource group.')
param logAnalyticsWorkspaceName string = 'law-az-maf-stage1'

resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'deny-test-owned-destination-https'
        properties: {
          description: 'Stage 2 negative egress test; deny the existing test app public IP on HTTPS.'
          priority: 100
          direction: 'Outbound'
          access: 'Deny'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: appSubnetCidr
          destinationAddressPrefix: blockedDestinationCidr
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [vnetCidr] }
  }
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: subnetName
  properties: {
    addressPrefix: appSubnetCidr
    networkSecurityGroup: { id: nsg.id }
    delegations: [
      {
        name: 'container-apps'
        properties: { serviceName: 'Microsoft.App/environments' }
      }
    ]
  }
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: subnet.id
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output environmentId string = environment.id
output subnetId string = subnet.id
output networkSecurityGroupId string = nsg.id
