param registryName string
@allowed(['Basic', 'Standard', 'Premium'])
param registrySku string = 'Basic'
param location string = resourceGroup().location
resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: registryName
  location: location
  sku: { name: registrySku }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    dataEndpointEnabled: registrySku == 'Premium'
    encryption: { status: 'disabled' }
    policies: { azureADAuthenticationAsArmPolicy: { status: 'enabled' } }
  }
}
output id string = registry.id
output loginServer string = registry.properties.loginServer
