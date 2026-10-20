param vnetName string
param vnetCidr string
param firewallSubnetCidr string
param managementSubnetCidr string
param location string = resourceGroup().location
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
output id string = vnet.id
