param environmentName string
param logsName string
param location string = resourceGroup().location
param infrastructureSubnetId string = ''
param workloadProfiles array = []
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = { name: logsName }
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: union({
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }, empty(infrastructureSubnetId) ? {} : {vnetConfiguration: {infrastructureSubnetId: infrastructureSubnetId, internal: false}}, empty(workloadProfiles) ? {} : {workloadProfiles: workloadProfiles})
}
output id string = environment.id
output defaultDomain string = environment.properties.defaultDomain
