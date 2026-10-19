targetScope = 'subscription'
param resourceGroupName string
param location string
param environmentName string
param registryName string
param pullIdentityName string
param logsName string

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = { name: resourceGroupName, location: location }
module foundation './foundation.bicep' = {
  name: 'stage1Foundation'
  scope: group
  params: { environmentName: environmentName, registryName: registryName, pullIdentityName: pullIdentityName, logsName: logsName, location: location }
}
output managedEnvironmentId string = foundation.outputs.managedEnvironmentId
output registryLoginServer string = foundation.outputs.registryLoginServer
output pullIdentityId string = foundation.outputs.pullIdentityId
