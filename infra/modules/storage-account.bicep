@description('Approved globally unique storage account name for preference documents.')
param accountName string
param containerName string = 'preferences'
param location string = resourceGroup().location
@description('Explicit lifecycle decision: 0 disables blob soft delete. Review backup expiry and restore fencing before enabling retention.')
@minValue(0)
@maxValue(30)
param softDeleteDays int
@description('Explicit backup decision. Restoring versions requires deletion fencing before serving data.')
param enableVersioning bool

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: accountName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    defaultToOAuthAuthentication: true
    encryption: {
      keySource: 'Microsoft.Storage'
      services: { blob: { enabled: true, keyType: 'Account' } }
    }
  }
}

resource service 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: enableVersioning
    deleteRetentionPolicy: softDeleteDays > 0 ? { enabled: true, days: max(1, softDeleteDays) } : { enabled: false }
    containerDeleteRetentionPolicy: softDeleteDays > 0 ? { enabled: true, days: max(1, softDeleteDays) } : { enabled: false }
  }
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: service
  name: containerName
  properties: { publicAccess: 'None' }
}



output accountName string = storage.name
output containerName string = container.name
output containerId string = container.id
output blobOrigin string = storage.properties.primaryEndpoints.blob
