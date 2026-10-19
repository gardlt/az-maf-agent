@description('Temporary isolated worker only; never a learner application name.')
param name string = 'ca-maf-stop-dev-eus2-01'
param environmentId string
param image string
param registryLoginServer string
param pullIdentityId string
param revisionSuffix string = 'drill-a'
param location string = resourceGroup().location

resource worker 'Microsoft.App/containerApps@2025-01-01' = {
  name: name
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Multiple'
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
      // Image pulling is allowed but the worker receives no identity token endpoint.
      identitySettings: [{ identity: pullIdentityId, lifecycle: 'None' }]
    }
    template: {
      revisionSuffix: revisionSuffix
      containers: [{
        name: 'synthetic-worker'
        image: image
        command: ['python', '-c', loadTextContent('../fixtures/unresponsive-worker.py')]
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}
output id string = worker.id
