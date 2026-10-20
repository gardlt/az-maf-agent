param name string
param location string = resourceGroup().location
param properties object
resource alert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
 name: name
 location: location
 properties: properties
}
