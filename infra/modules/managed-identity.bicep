param pullIdentityName string
param location string = resourceGroup().location
resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: pullIdentityName
  location: location
}
output id string = pullIdentity.id
output principalId string = pullIdentity.properties.principalId
output clientId string = pullIdentity.properties.clientId
