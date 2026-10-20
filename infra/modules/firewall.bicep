param firewallName string
param firewallPolicyId string
param vnetId string
param publicIpId string
param managementPublicIpId string
param location string = resourceGroup().location
resource firewall 'Microsoft.Network/azureFirewalls@2024-05-01' = {
  name: firewallName
  location: location
  properties: {
    sku: { name: 'AZFW_VNet', tier: 'Basic' }
    firewallPolicy: { id: firewallPolicyId }
    ipConfigurations: [{
      name: 'data'
      properties: {
        publicIPAddress: { id: publicIpId }
        subnet: { id: '${vnetId}/subnets/AzureFirewallSubnet' }
      }
    }]
    managementIpConfiguration: {
      name: 'management'
      properties: {
        publicIPAddress: { id: managementPublicIpId }
        subnet: { id: '${vnetId}/subnets/AzureFirewallManagementSubnet' }
      }
    }
  }
}
output id string = firewall.id
output privateIp string = firewall.properties.ipConfigurations[0].properties.privateIPAddress
