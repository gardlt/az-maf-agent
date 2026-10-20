targetScope = 'resourceGroup'

@description('Azure region for all regional resources.')
param location string = resourceGroup().location
@description('Container Apps managed environment name.')
param environmentName string
@description('Globally unique alphanumeric Azure Container Registry name.')
param registryName string
@allowed(['Basic', 'Standard', 'Premium'])
param registrySku string = 'Basic'
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
param memoryCleanupJobName string = 'job-memory-${uniqueString(agentAppName)}'
@description('Operator bootstrap only. Ordinary CI must leave false.')
param bootstrapMemoryRoles bool = false
param memoryCleanupAlertName string = 'al-memory-${uniqueString(agentAppName)}'
@description('Requires separately bootstrapped stopped policy and operator-approved runtime roles.')
param enableGuardrails bool = false
param controlAccountName string = memoryAccountName
param controlInsightsName string = 'appi-${agentAppName}'

@description('Use the separately provisioned Entra Agent ID for inference and MCP reads.')
param enableAgentIdentity bool = false
param agentBlueprintClientId string = ''
param agentIdentityClientId string = ''
param agentIdentityObjectId string = ''
@description('Emit explicit content-free generative AI traces to the existing Insights resource.')
param enableAgentTracing bool = false
param agentObservabilityName string = 'az-maf-agent'

module foundation './modules/foundation.bicep' = {
  name: 'foundation'
  params: {
    environmentName: environmentName
    registryName: registryName
    registrySku: registrySku
    pullIdentityName: pullIdentityName
    logsName: logsName
    assignAcrPullRole: false
    location: location
  }
}

module agent './modules/container-app.bicep' = {
  name: 'agent'
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
    movieMcpIdentityClientId: '4eafecc0-0b7b-44b9-a478-02926e56bd89'
    enableAgentIdentity: enableAgentIdentity
    agentBlueprintClientId: agentBlueprintClientId
    agentIdentityClientId: agentIdentityClientId
    enableAgentTracing: enableAgentTracing
    agentObservabilityName: agentObservabilityName
    enableGuardrails: enableGuardrails
    controlAccountName: enableGuardrails ? controlAccountName : ''
    applicationInsightsConnectionString: enableGuardrails ? controlMonitoring!.outputs.connectionString : ''
    enableMemory: enableMemory
    memoryAccountName: enableMemory ? memory!.outputs.accountName : ''
    memoryAllowedUsers: enableMemory ? allowedUsers : ''
    enableMovieModelTools: true
    agentConfigPath: '/app/config/foundry-stage1.json'
    enableApprovedSkills: true
    skillControlResourceId: resourceGroup().id
    location: location
  }
}

module movieMcp './modules/movie-mcp-app.bicep' = {
  name: 'movieMcp'
  params: {
    managedEnvironmentId: foundation.outputs.managedEnvironmentId
    appName: movieMcpAppName
    image: mcpImage
    registryLoginServer: foundation.outputs.registryLoginServer
    pullIdentityId: foundation.outputs.pullIdentityId
    tenantId: tenantId
    mcpAudience: mcpAudience
    allowedAgentOid: enableAgentIdentity ? agentIdentityObjectId : foundation.outputs.pullIdentityPrincipalId
    tmdbApiReadAccessToken: tmdbApiReadAccessToken
    location: location
  }
}

output agentId string = agent.outputs.appId
output movieMcpId string = movieMcp.outputs.appId
output agentPrincipalId string = agent.outputs.workloadPrincipalId
output movieMcpPrincipalId string = movieMcp.outputs.workloadPrincipalId

module memory './modules/memory-storage.bicep' = if (enableMemory) {
  name: 'memory-storage'
  params: {
    accountName: memoryAccountName
    location: location
    softDeleteDays: 0
    enableVersioning: false
  }
}
module memoryCleanup './modules/memory-cleanup-job.bicep' = if (enableMemory) {
  name: 'memory-cleanup'
  params: {
    jobName: memoryCleanupJobName
    managedEnvironmentId: foundation.outputs.managedEnvironmentId
    image: agentImage
    registryLoginServer: foundation.outputs.registryLoginServer
    pullIdentityId: foundation.outputs.pullIdentityId
    memoryAccountName: memory!.outputs.accountName
    sessionAccountName: enableGuardrails ? controlAccountName : ''
    location: location
  }
}
module memoryRoles './modules/memory-rbac.bicep' = if (enableMemory && bootstrapMemoryRoles) {
  name: 'memory-roles'
  params: {
    accountName: memory!.outputs.accountName
    principalIds: [agent.outputs.workloadPrincipalId, memoryCleanup!.outputs.principalId]
  }
}
output memoryStorageAccount string = enableMemory ? memory!.outputs.accountName : ''
output memoryCleanupPrincipalId string = enableMemory ? memoryCleanup!.outputs.principalId : ''

module memoryHealth './modules/memory-cleanup-alert.bicep' = if (enableMemory) {
  name: 'memory-health'
  params: {
    name: memoryCleanupAlertName
    requireSessionCycle: enableGuardrails
    workspaceId: resourceId('Microsoft.OperationalInsights/workspaces', logsName)
    location: location
  }
  dependsOn: [foundation]
}

module controlStorage './modules/guardrail-storage.bicep' = if (enableGuardrails) {
  name: 'guardrail-storage'
  params: {
    accountName: controlAccountName
    assignRoles: false
  }
  dependsOn: [memory]
}
module controlMonitoring './modules/control-monitoring.bicep' = if (enableGuardrails) {
  name: 'control-monitoring'
  params: {
    name: controlInsightsName
    workspaceId: resourceId('Microsoft.OperationalInsights/workspaces', logsName)
    location: location
  }
  dependsOn: [foundation]
}
