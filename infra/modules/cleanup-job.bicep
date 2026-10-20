param jobName string
param managedEnvironmentId string
param image string
param registryLoginServer string
param pullIdentityId string
param memoryAccountName string
param memoryContainerName string = 'preferences'
param sessionAccountName string = ''
param location string = resourceGroup().location

resource job 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${pullIdentityId}': {} } }
  properties: {
    environmentId: managedEnvironmentId
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 600
      replicaRetryLimit: 1
      scheduleTriggerConfig: { cronExpression: '17 * * * *', parallelism: 1, replicaCompletionCount: 1 }
      registries: [{ server: registryLoginServer, identity: pullIdentityId }]
    }
    template: {
      containers: [{
        name: 'memory-cleanup'
        image: image
        command: ['python', '-m', 'az_maf_agent.memory_cleanup']
        env: [
          { name: 'SESSION_ACCOUNT', value: sessionAccountName }
          { name: 'SESSION_CONFIG', value: '/app/config/foundry-stage1.json' }
          { name: 'MEMORY_ACCOUNT', value: memoryAccountName }
          { name: 'MEMORY_CONTAINER', value: memoryContainerName }
          { name: 'MEMORY_POLICY', value: '/app/config/memory-policy.json' }
        ]
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
      }]
    }
  }
}
output principalId string = job.identity.principalId
output jobId string = job.id
