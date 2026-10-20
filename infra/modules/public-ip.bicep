param name string
param location string = resourceGroup().location
resource firewallIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: name
  location: location
  sku: { name: 'Standard', tier: 'Regional' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}
output id string = firewallIp.id
