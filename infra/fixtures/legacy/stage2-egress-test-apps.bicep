@description('Existing separate Stage 2 VNet-integrated Container Apps environment ID.')
param managedEnvironmentId string
@description('Environment default domain, read after foundation deployment.')
param environmentDefaultDomain string
@description('Private Azure Container Registry hostname.')
param registryLoginServer string
@description('Existing image-pull user-assigned identity ID.')
param pullIdentityId string
@description('Digest-pinned agent image.')
param agentImage string
@description('Digest-pinned TMDB MCP image.')
param mcpImage string
param tenantId string
param agentAudience string
param allowedUsers string
param mcpAudience string
@secure()
param tmdbApiReadAccessToken string
param location string = resourceGroup().location

var agentName = 'ca-az-maf-agent-nettest'
var mcpName = 'ca-az-maf-mcp-nettest'

resource agent 'Microsoft.App/containerApps@2025-01-01' = {
  name: agentName
  location: location
  identity: { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
      ingress: { external: true, targetPort: 8000, transport: 'http', allowInsecure: false }
    }
    template: {
      containers: [{
        name: 'agent-api'
        image: agentImage
        env: [
          { name: 'AGENT_CONFIG', value: '/app/config/foundry-stage1.json' }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_AUDIENCE', value: agentAudience }
          { name: 'ENTRA_ALLOWED_USERS', value: allowedUsers }
          { name: 'ENABLE_MOVIE_MCP', value: 'true' }
          { name: 'MCP_ENDPOINT', value: 'https://${mcpName}.internal.${environmentDefaultDomain}/mcp' }
          { name: 'MCP_AUDIENCE', value: mcpAudience }
          { name: 'ENABLE_MOVIE_MODEL_TOOLS', value: 'true' }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

resource mcp 'Microsoft.App/containerApps@2025-01-01' = {
  name: mcpName
  location: location
  identity: { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [{ name: 'tmdb-api-read-access-token', value: tmdbApiReadAccessToken }]
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
      ingress: { external: false, targetPort: 8000, transport: 'http', allowInsecure: false }
    }
    template: {
      containers: [{
        name: 'movie-mcp'
        image: mcpImage
        env: [
          { name: 'MOVIE_MCP_MODE', value: 'http' }
          { name: 'MCP_TENANT_ID', value: tenantId }
          { name: 'MCP_AUDIENCE', value: mcpAudience }
          { name: 'MCP_ALLOWED_AGENT_OID', value: agent.identity.principalId }
          { name: 'TMDB_API_READ_ACCESS_TOKEN', secretRef: 'tmdb-api-read-access-token' }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

output agentPrincipalId string = agent.identity.principalId
output agentUrl string = 'https://${agentName}.${environmentDefaultDomain}'
output mcpPrincipalId string = mcp.identity.principalId
output mcpUrl string = 'https://${mcpName}.internal.${environmentDefaultDomain}/mcp'
