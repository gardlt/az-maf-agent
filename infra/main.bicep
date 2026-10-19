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
