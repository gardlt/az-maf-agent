@description('Reviewed in-place Premium upgrade; preserves repositories, identity grants, and public endpoint access.')
param registryName string
param location string = resourceGroup().location
resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: registryName
  location: location
  sku: { name: 'Premium' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    encryption: { status: 'disabled' }
    policies: { azureADAuthenticationAsArmPolicy: { status: 'enabled' } }
    publicNetworkAccess: 'Enabled'
    dataEndpointEnabled: true
  }
}
output loginServer string = registry.properties.loginServer
output dataEndpoints array = registry.properties.dataEndpointHostNames
