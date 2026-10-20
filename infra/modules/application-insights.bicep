param name string
param workspaceId string
param location string = resourceGroup().location
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceId
    DisableLocalAuth: true
    IngestionMode: 'LogAnalytics'
    RetentionInDays: 30
  }
}
output connectionString string = insights.properties.ConnectionString
output id string = insights.id
