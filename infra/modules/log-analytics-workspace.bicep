param logsName string
param location string = resourceGroup().location
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logsName
  location: location
  properties: { retentionInDays: 30, sku: { name: 'PerGB2018' } }
}
output id string = logs.id
output name string = logs.name
