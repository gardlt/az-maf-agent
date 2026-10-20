param nsgName string
param appSubnetCidr string
param location string = resourceGroup().location
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
output id string = nsg.id
