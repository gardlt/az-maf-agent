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
@description('Enable public HTTPS ingress only after private validation.')
param externalIngress bool = false
@description('Absolute path to an approved configuration file included in the container image.')
param agentConfigPath string = '/app/config/offline.json'
param location string = resourceGroup().location

var entraBase = environment().authentication.loginEndpoint
var entraIssuer = endsWith(entraBase, '/') ? '${entraBase}${tenantId}/v2.0' : '${entraBase}/${tenantId}/v2.0'

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
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
        env: [
          { name: 'AGENT_CONFIG', value: agentConfigPath }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
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
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

resource auth 'Microsoft.App/containerApps/authConfigs@2025-01-01' = {
  name: 'current'
  parent: app
  properties: {
    platform: { enabled: true }
    globalValidation: { unauthenticatedClientAction: 'Return401', excludedPaths: [] }
    httpSettings: { requireHttps: true }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: { clientId: apiClientId, clientSecretSettingName: 'easyauth-client-secret', openIdIssuer: entraIssuer }
        validation: { allowedAudiences: [audience], jwtClaimChecks: { allowedClientApplications: [cliClientId] } }
      }
    }
  }
}
output appId string = app.id
output workloadPrincipalId string = app.identity.principalId
