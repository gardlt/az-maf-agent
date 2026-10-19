targetScope = 'subscription'

@description('Resource group for this environment.')
param resourceGroupName string
@description('Azure region for all regional resources.')
param location string
@description('Container Apps managed environment name.')
param environmentName string
@description('Globally unique alphanumeric Azure Container Registry name.')
param registryName string
param pullIdentityName string
param logsName string
param agentAppName string
param movieMcpAppName string
@description('Digest-pinned agent image.')
param agentImage string
@description('Digest-pinned movie MCP image.')
param mcpImage string
param tenantId string
param agentAudience string
param allowedUsers string
param apiClientId string
param cliClientId string
@secure()
param authClientSecret string
param mcpAudience string
@secure()
param tmdbApiReadAccessToken string
@description('Enable governed movie preferences only for approved environments.')
param enableMemory bool = false
param memoryAccountName string = 'stmafmem${uniqueString(subscription().subscriptionId, agentAppName)}'
param memoryCleanupJobName string = 'job-${agentAppName}-memory'
@description('Operator bootstrap only. Ordinary CI must leave false.')
param bootstrapMemoryRoles bool = false

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

module foundation './modules/foundation.bicep' = {
  name: 'foundation'
  scope: resourceGroup
  params: {
    environmentName: environmentName
    registryName: registryName
    pullIdentityName: pullIdentityName
    logsName: logsName
    location: location
  }
}

module agent './modules/container-app.bicep' = {
  name: 'agent'
  scope: resourceGroup
  params: {
    managedEnvironmentId: foundation.outputs.managedEnvironmentId
    appName: agentAppName
    image: agentImage
    registryLoginServer: foundation.outputs.registryLoginServer
    pullIdentityId: foundation.outputs.pullIdentityId
    tenantId: tenantId
    audience: agentAudience
    allowedUsers: allowedUsers
    apiClientId: apiClientId
    cliClientId: cliClientId
    authClientSecret: authClientSecret
    externalIngress: true
    enableMovieMcp: true
    movieMcpEndpoint: 'https://${movieMcpAppName}.internal.${foundation.outputs.environmentDefaultDomain}/mcp'
    movieMcpAudience: mcpAudience
    enableMemory: enableMemory
    memoryAccountName: enableMemory ? memory!.outputs.accountName : ''
    memoryAllowedUsers: enableMemory ? allowedUsers : ''
    enableMovieModelTools: true
    location: location
  }
}

module movieMcp './modules/movie-mcp-app.bicep' = {
  name: 'movieMcp'
  scope: resourceGroup
  params: {
    managedEnvironmentId: foundation.outputs.managedEnvironmentId
    appName: movieMcpAppName
    image: mcpImage
    registryLoginServer: foundation.outputs.registryLoginServer
    pullIdentityId: foundation.outputs.pullIdentityId
    tenantId: tenantId
    mcpAudience: mcpAudience
    allowedAgentOid: foundation.outputs.pullIdentityPrincipalId
    tmdbApiReadAccessToken: tmdbApiReadAccessToken
    location: location
  }
}

output resourceGroupId string = resourceGroup.id
output agentId string = agent.outputs.appId
output movieMcpId string = movieMcp.outputs.appId
output agentPrincipalId string = agent.outputs.workloadPrincipalId
output movieMcpPrincipalId string = movieMcp.outputs.workloadPrincipalId

module memory './modules/memory-storage.bicep' = if (enableMemory) {
  name: 'memory-storage'
  scope: resourceGroup
  params: {
    accountName: memoryAccountName
    location: location
    softDeleteDays: 0
    enableVersioning: false
  }
}
module memoryCleanup './modules/memory-cleanup-job.bicep' = if (enableMemory) {
  name: 'memory-cleanup'
  scope: resourceGroup
  params: {
    jobName: memoryCleanupJobName
    managedEnvironmentId: foundation.outputs.managedEnvironmentId
    image: agentImage
    registryLoginServer: foundation.outputs.registryLoginServer
    pullIdentityId: foundation.outputs.pullIdentityId
    memoryAccountName: memory!.outputs.accountName
    location: location
  }
}
module memoryRoles './modules/memory-rbac.bicep' = if (enableMemory && bootstrapMemoryRoles) {
  name: 'memory-roles'
  scope: resourceGroup
  params: {
    accountName: memory!.outputs.accountName
    principalIds: [agent.outputs.workloadPrincipalId, memoryCleanup!.outputs.principalId]
  }
}
output memoryStorageAccount string = enableMemory ? memory!.outputs.accountName : ''
output memoryCleanupPrincipalId string = enableMemory ? memoryCleanup!.outputs.principalId : ''
