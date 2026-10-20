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


resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {name: logsName}
module vnet '../modules/virtual-network.bicep' = {
 name: 'vnet'
 params: {vnetName: vnetName, vnetCidr: vnetCidr, firewallSubnetCidr: firewallSubnetCidr, managementSubnetCidr: managementSubnetCidr, location: location}
}
module dataIp '../modules/public-ip.bicep' = {
 name: 'firewall-public-ip'
 params: {name: 'pip-${firewallName}', location: location}
}
module managementIp '../modules/public-ip.bicep' = {
 name: 'firewall-management-ip'
 params: {name: 'pip-${firewallName}-mgmt', location: location}
}
module policy '../modules/firewall-policy.bicep' = {
 name: 'firewall-policy'
 params: {
  firewallPolicyName: firewallPolicyName
  registryLoginServer: registryLoginServer
  registryDataEndpoint: registryDataEndpoint
  memoryBlobHost: memoryBlobHost
  foundryHost: foundryHost
  insightsIngestionHost: insightsIngestionHost
  appSubnetCidr: appSubnetCidr
  location: location
 }
}
module firewall '../modules/firewall.bicep' = {
 name: 'firewall'
 params: {firewallName: firewallName, firewallPolicyId: policy.outputs.id, vnetId: vnet.outputs.id, publicIpId: dataIp.outputs.id, managementPublicIpId: managementIp.outputs.id, location: location}
}
module routes '../modules/route-table.bicep' = {
 name: 'routes'
 params: {routeTableName: routeTableName, nextHopIp: firewall.outputs.privateIp, location: location}
}
module nsg '../modules/network-security-group.bicep' = {
 name: 'security-group'
 params: {nsgName: nsgName, appSubnetCidr: appSubnetCidr, location: location}
}
module subnet '../modules/delegated-subnet.bicep' = {
 name: 'app-subnet'
 params: {vnetName: vnetName, appSubnetCidr: appSubnetCidr, nsgId: nsg.outputs.id, routeTableId: routes.outputs.id}
}
module managedEnvironment '../modules/managed-environment.bicep' = {
 name: 'network-environment'
 params: {environmentName: environmentName, logsName: logsName, infrastructureSubnetId: subnet.outputs.id, workloadProfiles: [{name: 'Consumption', workloadProfileType: 'Consumption'}], location: location}
}
module diagnostics '../modules/firewall-diagnostics.bicep' = {
 name: 'firewall-diagnostics'
 params: {firewallName: firewallName, workspaceId: logs.id}
 dependsOn: [firewall]
}
output environmentId string = managedEnvironment.outputs.id
output environmentDefaultDomain string = managedEnvironment.outputs.defaultDomain
output firewallId string = firewall.outputs.id
output appSubnetId string = subnet.outputs.id
