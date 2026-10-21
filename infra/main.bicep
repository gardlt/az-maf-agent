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
param agentAppName string = 'ca-agent-${uniqueString(environmentName)}'
param movieMcpAppName string = 'ca-mcp-${uniqueString(environmentName)}'
@description('Digest-pinned agent image.')
param agentImage string = ''
@description('Digest-pinned movie MCP image.')
param mcpImage string = ''
param tenantId string = ''
param agentAudience string = ''
param allowedUsers string = ''
param apiClientId string = ''
param cliClientId string = ''
@description('Optional approved Entra SPA client. Empty retains CLI-only access.')
param webClientId string = ''
@secure()
param authClientSecret string = ''
param mcpAudience string = ''
@secure()
param tmdbApiReadAccessToken string = ''
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

@allowed(['all', 'foundation', 'agent', 'movie-mcp', 'memory', 'controls', 'network', 'model', 'access', 'containment'])
param deploymentTarget string = 'all'
@description('Privileged bootstrap only. Ordinary CI never changes role assignments.')
param bootstrapAcrPullRole bool = false
param bootstrapControlRoles bool = false
param bootstrapSkillRole bool = false
param bootstrapFoundryRole bool = false
param bootstrapMonitoringRole bool = false
param operatorPrincipalId string = ''
param enableApprovedSkills bool = false
param agentConfigPath string = '/app/config/foundry-stage1.json'
param foundryResourceGroupName string = resourceGroup().name
param foundryAccountName string = ''
param modelDeploymentName string = 'gpt-5-mini'
param modelName string = 'gpt-5-mini'
param modelVersion string = '2025-08-07'
param modelCapacity int = 30
@description('Explicit parallel-network profile; never switches working application traffic.')
param network object = {}
param containmentWorkerName string = 'ca-maf-stop-dev-eus2-01'
param containmentImage string = ''
param containmentRevisionSuffix string = 'drill-a'

var deployFoundation = contains(['all', 'foundation'], deploymentTarget)
var deployAgent = contains(['all', 'agent'], deploymentTarget)
var deployMcp = contains(['all', 'movie-mcp'], deploymentTarget)
var deployMemory = enableMemory && contains(['all', 'memory'], deploymentTarget)
var deployControls = enableGuardrails && contains(['all', 'controls'], deploymentTarget)
var deployAccess = contains(['all', 'access'], deploymentTarget)

resource existingEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {name: environmentName}
resource existingRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {name: registryName}
resource existingPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {name: pullIdentityName}
resource existingInsights 'Microsoft.Insights/components@2020-02-02' existing = {name: controlInsightsName}
resource existingAgent 'Microsoft.App/containerApps@2025-01-01' existing = {name: agentAppName}
resource existingCleanup 'Microsoft.App/jobs@2025-01-01' existing = {name: memoryCleanupJobName}

var managedEnvironmentId = deployFoundation ? foundation!.outputs.managedEnvironmentId : existingEnvironment.id
var registryLoginServer = deployFoundation ? foundation!.outputs.registryLoginServer : existingRegistry.properties.loginServer
var pullIdentityId = deployFoundation ? foundation!.outputs.pullIdentityId : existingPullIdentity.id
var pullIdentityPrincipalId = deployFoundation ? foundation!.outputs.pullIdentityPrincipalId : existingPullIdentity.properties.principalId
var pullIdentityClientId = deployFoundation ? foundation!.outputs.pullIdentityClientId : existingPullIdentity.properties.clientId
var environmentDefaultDomain = deployFoundation ? foundation!.outputs.environmentDefaultDomain : existingEnvironment.properties.defaultDomain
var workspaceId = resourceId('Microsoft.OperationalInsights/workspaces', logsName)
var runtimePrincipalId = deployAgent ? agent!.outputs.workloadPrincipalId : existingAgent.identity.principalId
var cleanupPrincipalId = deployAgent && enableMemory ? agent!.outputs.cleanupPrincipalId : existingCleanup.identity.principalId

module foundation './patterns/shared-foundation.bicep' = if (deployFoundation) {
  name: 'foundation'
  params: {
    environmentName: environmentName
    registryName: registryName
    registrySku: registrySku
    pullIdentityName: pullIdentityName
    logsName: logsName
    assignAcrPullRole: bootstrapAcrPullRole
    location: location
  }
}

module agent './patterns/agent.bicep' = if (deployAgent) {
  name: 'agent'
  params: {
    managedEnvironmentId: managedEnvironmentId
    appName: agentAppName
    image: agentImage
    registryLoginServer: registryLoginServer
    pullIdentityId: pullIdentityId
    tenantId: tenantId
    audience: agentAudience
    allowedUsers: allowedUsers
    apiClientId: apiClientId
    cliClientId: cliClientId
    webClientId: webClientId
    authClientSecret: authClientSecret
    externalIngress: true
    enableMovieMcp: true
    movieMcpEndpoint: 'https://${movieMcpAppName}.internal.${environmentDefaultDomain}/mcp'
    movieMcpAudience: mcpAudience
    movieMcpIdentityClientId: pullIdentityClientId
    enableAgentIdentity: enableAgentIdentity
    agentBlueprintClientId: agentBlueprintClientId
    agentIdentityClientId: agentIdentityClientId
    enableAgentTracing: enableAgentTracing
    agentObservabilityName: agentObservabilityName
    enableGuardrails: enableGuardrails
    controlAccountName: enableGuardrails ? controlAccountName : ''
    applicationInsightsConnectionString: enableGuardrails ? (deployControls ? controlMonitoring!.outputs.connectionString : existingInsights.properties.ConnectionString) : ''
    enableMemory: enableMemory
    memoryAccountName: enableMemory ? memoryAccountName : ''
    memoryAllowedUsers: enableMemory ? allowedUsers : ''
    enableMovieModelTools: true
    agentConfigPath: agentConfigPath
    enableApprovedSkills: enableApprovedSkills
    skillControlResourceId: resourceGroup().id
    cleanupJobName: memoryCleanupJobName
    cleanupAlertName: memoryCleanupAlertName
    cleanupWorkspaceId: workspaceId
    sessionAccountName: enableGuardrails ? controlAccountName : ''
    location: location
  }
  dependsOn: [memory, controlStorage]
}

module movieMcp './patterns/movie-mcp.bicep' = if (deployMcp) {
  name: 'movieMcp'
  params: {
    managedEnvironmentId: managedEnvironmentId
    appName: movieMcpAppName
    image: mcpImage
    registryLoginServer: registryLoginServer
    pullIdentityId: pullIdentityId
    tenantId: tenantId
    mcpAudience: mcpAudience
    allowedAgentOid: enableAgentIdentity ? agentIdentityObjectId : pullIdentityPrincipalId
    tmdbApiReadAccessToken: tmdbApiReadAccessToken
    location: location
  }
}

output resourceGroupId string = resourceGroup().id
output agentId string = deployAgent ? agent!.outputs.appId : ''
output movieMcpId string = deployMcp ? movieMcp!.outputs.appId : ''
output agentPrincipalId string = deployAgent ? agent!.outputs.workloadPrincipalId : ''
output movieMcpPrincipalId string = deployMcp ? movieMcp!.outputs.workloadPrincipalId : ''

module memory './modules/storage-account.bicep' = if (deployMemory) {
  name: 'memory-storage'
  params: {
    accountName: memoryAccountName
    location: location
    softDeleteDays: 0
    enableVersioning: false
  }
}
module memoryRoles './modules/blob-data-roles.bicep' = if (enableMemory && bootstrapMemoryRoles && deployAccess) {
  name: 'memory-roles'
  params: {
    accountName: memoryAccountName
    principalIds: [runtimePrincipalId, cleanupPrincipalId]
  }
  dependsOn: [memory]
}
output memoryStorageAccount string = enableMemory ? memoryAccountName : ''
output memoryCleanupPrincipalId string = deployAgent && enableMemory ? agent!.outputs.cleanupPrincipalId : ''

module controlStorage './modules/guardrail-storage.bicep' = if (deployControls) {
  name: 'guardrail-storage'
  params: {
    accountName: controlAccountName
  }
  dependsOn: [memory]
}
module controlMonitoring './patterns/control-monitoring.bicep' = if (deployControls) {
  name: 'control-monitoring'
  params: {
    name: controlInsightsName
    workspaceId: resourceId('Microsoft.OperationalInsights/workspaces', logsName)
    location: location
  }
  dependsOn: [foundation]
}

module controlRoles './modules/guardrail-roles.bicep' = if (enableGuardrails && bootstrapControlRoles && deployAccess) {
 name: 'control-access'
 params: {accountName: controlAccountName, runtimePrincipalId: runtimePrincipalId, cleanupPrincipalId: cleanupPrincipalId, operatorPrincipalId: operatorPrincipalId}
 dependsOn: [controlStorage]
}
module skillRole './modules/skill-control-role.bicep' = if (bootstrapSkillRole && deployAccess) {
 name: 'skill-access'
 params: {principalId: runtimePrincipalId}
}
module foundryRole './modules/foundry-role.bicep' = if (bootstrapFoundryRole && deployAccess) {
 name: 'foundry-access'
 scope: resourceGroup(foundryResourceGroupName)
 params: {foundryAccountName: foundryAccountName, agentPrincipalId: agentIdentityObjectId}
}
module model './modules/foundry-model.bicep' = if (deploymentTarget == 'model') {
 name: 'foundry-model'
 scope: resourceGroup(foundryResourceGroupName)
 params: {accountName: foundryAccountName, deploymentName: modelDeploymentName, modelName: modelName, modelVersion: modelVersion, capacity: modelCapacity}
}
module controlledNetwork './patterns/controlled-egress.bicep' = if (deploymentTarget == 'network') {
 name: 'controlled-egress'
 params: {
  environmentName: network.?environmentName ?? ''
  vnetName: network.?vnetName ?? ''
  firewallName: network.?firewallName ?? ''
  firewallPolicyName: network.?firewallPolicyName ?? ''
  routeTableName: network.?routeTableName ?? ''
  nsgName: network.?nsgName ?? ''
  logsName: logsName
  registryLoginServer: '${registryName}.azurecr.io'
  registryDataEndpoint: network.?registryDataEndpoint ?? ''
  memoryBlobHost: network.?memoryBlobHost ?? ''
  foundryHost: network.?foundryHost ?? ''
  insightsIngestionHost: network.?insightsIngestionHost ?? ''
  location: location
 }
}
module containment './fixtures/containment-test-worker.bicep' = if (deploymentTarget == 'containment') {
 name: 'containment-fixture'
 params: {name: containmentWorkerName, environmentId: managedEnvironmentId, image: containmentImage, registryLoginServer: registryLoginServer, pullIdentityId: pullIdentityId, revisionSuffix: containmentRevisionSuffix, location: location}
}
output parallelEnvironmentId string = deploymentTarget == 'network' ? controlledNetwork!.outputs.environmentId : ''
output modelDeployment string = deploymentTarget == 'model' ? model!.outputs.deploymentName : ''

module monitoringRole './modules/insights-publisher-role.bicep' = if (bootstrapMonitoringRole && deployAccess) {
 name: 'monitoring-access'
 params: {name: controlInsightsName, runtimePrincipalId: runtimePrincipalId}
}
module existingRegistryPullRole './modules/registry-pull-role.bicep' = if (bootstrapAcrPullRole && deploymentTarget == 'access') {
 name: 'existing-registry-pull-access'
 params: {registryName: registryName, pullIdentityName: pullIdentityName}
}
