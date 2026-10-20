param vnetName string
param appSubnetCidr string
param nsgId string
param routeTableId string
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {name: vnetName}
resource appSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-apps'
  properties: {
    addressPrefix: appSubnetCidr
    networkSecurityGroup: { id: nsgId }
    routeTable: { id: routeTableId }
    delegations: [{ name: 'container-apps', properties: { serviceName: 'Microsoft.App/environments' } }]
  }
}
output id string = appSubnet.id
