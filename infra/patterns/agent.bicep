@description('Existing Container Apps environment resource ID.')
param managedEnvironmentId string
param appName string
@description('Image reference pinned by sha256 digest.')
param image string
param registryLoginServer string
param pullIdentityId string
param tenantId string
@description('Microsoft Entra v2 access-token audience: the API application (client) ID.')
param audience string
param allowedUsers string
param apiClientId string
param cliClientId string
param webClientId string = ''
@secure()
param authClientSecret string
@description('Enable the private movie MCP integration.')
param enableMovieMcp bool = false
param movieMcpEndpoint string = ''
param movieMcpAudience string = ''
param movieMcpIdentityClientId string = ''
@description('Allow the live model to select the bounded movie read tools.')
param enableMovieModelTools bool = false
@description('Enable the reviewed read-only Markdown skills. Requires workload Reader access to the control resource.')
param enableApprovedSkills bool = false
param skillControlResourceId string = ''
@description('Enable only after the memory lifecycle and hosted checks pass.')
param enableMemory bool = false
param memoryAccountName string = ''
param memoryContainerName string = 'preferences'
param memoryAllowedUsers string = ''
@description('Enable only after operator bootstrap and hosted validation.')
param enableGuardrails bool = false
param controlAccountName string = ''
param applicationInsightsConnectionString string = ''
@description('Enable public HTTPS ingress only after private validation.')
param externalIngress bool = false
@description('Absolute path to an approved configuration file included in the container image.')
param agentConfigPath string = '/app/config/offline.json'
@description('Use the separately provisioned Entra Agent ID for inference and MCP reads.')
param enableAgentIdentity bool = false
param agentBlueprintClientId string = ''
param agentIdentityClientId string = ''
@description('Emit explicit content-free generative AI traces to the existing Insights resource.')
param enableAgentTracing bool = false
param agentObservabilityName string = 'az-maf-agent'
param location string = resourceGroup().location

param cleanupJobName string = 'job-memory-${uniqueString(appName)}'
param cleanupAlertName string = 'al-memory-${uniqueString(appName)}'
param cleanupWorkspaceId string = ''
param sessionAccountName string = ''

var entraBase = environment().authentication.loginEndpoint
var entraIssuer = endsWith(entraBase, '/') ? '${entraBase}${tenantId}/v2.0' : '${entraBase}/${tenantId}/v2.0'

module app '../modules/container-app.bicep' = {
  name: 'agent-container-app'
  params: {
    appName: appName
    location: location
    identity: { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
    properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [{ name: 'easyauth-client-secret', value: authClientSecret }]
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
      ingress: { external: externalIngress, targetPort: 8000, transport: 'http', allowInsecure: false }
    }
    template: {
      containers: [{
        name: 'agent-api'
        image: image
        env: concat([
          { name: 'APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL', value: 'true' }
          { name: 'APPLICATIONINSIGHTS_SDKSTATS_DISABLED', value: 'true' }
          { name: 'APPLICATIONINSIGHTS_OPENTELEMETRY_RESOURCE_METRIC_DISABLED', value: 'true' }
          { name: 'APPLICATIONINSIGHTS_CONTROLPLANE_DISABLED', value: 'true' }
          { name: 'ENABLE_GUARDRAILS', value: toLower(string(enableGuardrails)) }
          { name: 'ENABLE_SHARED_SESSIONS', value: toLower(string(enableGuardrails)) }
          { name: 'CONTROL_ACCOUNT', value: controlAccountName }
          { name: 'SESSION_ACCOUNT', value: controlAccountName }
          { name: 'ENABLE_MEMORY', value: toLower(string(enableMemory)) }
          { name: 'MEMORY_BACKEND', value: 'azure_blob' }
          { name: 'MEMORY_POLICY', value: '/app/config/memory-policy.json' }
          { name: 'MEMORY_ACCOUNT', value: memoryAccountName }
          { name: 'MEMORY_CONTAINER', value: memoryContainerName }
          { name: 'MEMORY_ALLOWED_USERS', value: memoryAllowedUsers }
          { name: 'AGENT_CONFIG', value: agentConfigPath }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENABLE_ENTRA_AGENT_ID', value: toLower(string(enableAgentIdentity)) }
          { name: 'AGENT_BLUEPRINT_CLIENT_ID', value: agentBlueprintClientId }
          { name: 'AGENT_IDENTITY_CLIENT_ID', value: agentIdentityClientId }
          { name: 'ENABLE_AGENT_TRACING', value: toLower(string(enableAgentTracing)) }
          { name: 'AGENT_OBSERVABILITY_NAME', value: agentObservabilityName }
          { name: 'ENTRA_AUDIENCE', value: audience }
          { name: 'ENTRA_ALLOWED_USERS', value: allowedUsers }
          { name: 'ENABLE_MOVIE_MCP', value: toLower(string(enableMovieMcp)) }
          { name: 'MCP_ENDPOINT', value: movieMcpEndpoint }
          { name: 'MCP_AUDIENCE', value: movieMcpAudience }
          { name: 'MCP_IDENTITY_CLIENT_ID', value: movieMcpIdentityClientId }
          { name: 'ENABLE_MOVIE_MODEL_TOOLS', value: toLower(string(enableMovieModelTools)) }
          { name: 'SKILL_BUNDLE', value: enableApprovedSkills ? '/app/skills' : '' }
          { name: 'SKILL_CONTROL_RESOURCE_ID', value: skillControlResourceId }
          { name: 'SKILL_ALLOWED_USERS', value: enableApprovedSkills ? allowedUsers : '' }
        ], empty(applicationInsightsConnectionString) ? [] : [{ name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }])
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
  }
}
module auth '../modules/container-app-auth.bicep' = {
  name: 'authentication'
  params: { appName: appName, properties: {
    platform: { enabled: true }
    globalValidation: { unauthenticatedClientAction: 'Return401', excludedPaths: [] }
    httpSettings: { requireHttps: true }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: { clientId: apiClientId, clientSecretSettingName: 'easyauth-client-secret', openIdIssuer: entraIssuer }
        validation: { allowedAudiences: [audience], jwtClaimChecks: { allowedClientApplications: empty(webClientId) ? [cliClientId] : [cliClientId, webClientId] } }
      }
    }
  } }
  dependsOn: [app]
}
output appId string = app.outputs.appId
output workloadPrincipalId string = app.outputs.workloadPrincipalId

module cleanup '../modules/cleanup-job.bicep' = if (enableMemory) {
 name: 'memory-cleanup'
 params: {jobName: cleanupJobName, managedEnvironmentId: managedEnvironmentId, image: image, registryLoginServer: registryLoginServer, pullIdentityId: pullIdentityId, memoryAccountName: memoryAccountName, sessionAccountName: sessionAccountName, location: location}
}
module health './memory-cleanup-monitor.bicep' = if (enableMemory) {
 name: 'memory-health'
 params: {name: cleanupAlertName, workspaceId: cleanupWorkspaceId, requireSessionCycle: enableGuardrails, location: location}
}
output cleanupPrincipalId string = enableMemory ? cleanup!.outputs.principalId : ''
