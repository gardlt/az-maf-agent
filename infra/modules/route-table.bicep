param routeTableName string
param nextHopIp string
param location string = resourceGroup().location
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
        nextHopIpAddress: nextHopIp
      }
    }]
  }
}
output id string = routes.id
