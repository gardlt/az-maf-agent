param environmentName string
param registryName string
@allowed(['Basic', 'Standard', 'Premium'])
param registrySku string = 'Basic'
param pullIdentityName string
param logsName string
param assignAcrPullRole bool = false
param location string = resourceGroup().location
module logs '../modules/log-analytics-workspace.bicep' = {
  name: 'workspace'
  params: {logsName: logsName, location: location}
}
module registry '../modules/container-registry.bicep' = {
  name: 'registry'
  params: {registryName: registryName, registrySku: registrySku, location: location}
}
module identity '../modules/managed-identity.bicep' = {
  name: 'pull-identity'
  params: {pullIdentityName: pullIdentityName, location: location}
}
module pullRole '../modules/registry-pull-role.bicep' = if (assignAcrPullRole) {
  name: 'registry-pull-access'
  params: {registryName: registryName, pullIdentityName: pullIdentityName}
  dependsOn: [registry, identity]
}
module environment '../modules/managed-environment.bicep' = {
  name: 'managed-environment'
  params: {environmentName: environmentName, logsName: logsName, location: location}
  dependsOn: [logs]
}
output managedEnvironmentId string = environment.outputs.id
output registryLoginServer string = registry.outputs.loginServer
output pullIdentityId string = identity.outputs.id
output pullIdentityPrincipalId string = identity.outputs.principalId
output pullIdentityClientId string = identity.outputs.clientId
output environmentDefaultDomain string = environment.outputs.defaultDomain
output workspaceId string = logs.outputs.id
