param managedEnvironmentId string
param appName string
@description('Digest-pinned static UI and API-proxy image.')
param image string
param registryLoginServer string
param pullIdentityId string
@description('Fixed HTTPS upstream host of the authenticated agent API.')
param agentApiHost string
param location string = resourceGroup().location

module app '../modules/container-app.bicep' = {
  name: 'web-container-app'
  params: {
    appName: appName
    location: location
    identity: { type: 'UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
    properties: {
      managedEnvironmentId: managedEnvironmentId
      configuration: {
        activeRevisionsMode: 'Single'
        registries: [{ server: registryLoginServer, identity: pullIdentityId }]
        identitySettings: [{ identity: pullIdentityId, lifecycle: 'None' }]
        ingress: { external: true, targetPort: 8080, transport: 'http', allowInsecure: false }
      }
      template: {
        containers: [{
          name: 'web'
          image: image
          env: [{ name: 'AGENT_API_HOST', value: agentApiHost }]
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          probes: [{ type: 'Readiness', httpGet: { path: '/', port: 8080 }, initialDelaySeconds: 2, periodSeconds: 5 }]
        }]
        scale: { minReplicas: 0, maxReplicas: 1 }
      }
    }
  }
}
output appId string = app.outputs.appId
