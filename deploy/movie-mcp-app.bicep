@description('Existing Container Apps environment resource ID.')
param managedEnvironmentId string
param appName string = 'ca-az-maf-movie-mcp'
@description('MCP image reference pinned by sha256 digest.')
param image string
param registryLoginServer string
param pullIdentityId string
param tenantId string
@description('Entra v2 MCP API application ID, used as token audience.')
param mcpAudience string
@description('Object ID of the agent Container App system identity.')
param allowedAgentOid string
param location string = resourceGroup().location

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  identity: { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
      ingress: { external: false, targetPort: 8000, transport: 'http', allowInsecure: false }
    }
    template: {
      containers: [{
        name: 'movie-mcp'
        image: image
        env: [
          { name: 'MOVIE_MCP_MODE', value: 'http' }
          { name: 'MCP_TENANT_ID', value: tenantId }
          { name: 'MCP_AUDIENCE', value: mcpAudience }
          { name: 'MCP_ALLOWED_AGENT_OID', value: allowedAgentOid }
        ]
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

output appId string = app.id
output workloadPrincipalId string = app.identity.principalId
