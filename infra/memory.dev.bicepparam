using './modules/memory-storage.bicep'

param accountName = readEnvironmentVariable('MAF_MEMORY_ACCOUNT_NAME')
param containerName = 'preferences'
param location = 'eastus2'
// Approved dev policy: no recoverable versions, blob soft delete, or container soft delete.
param softDeleteDays = 0
param enableVersioning = false
param assignDataRole = readEnvironmentVariable('MAF_MEMORY_BOOTSTRAP_RBAC', 'false') == 'true'
param workloadPrincipalId = readEnvironmentVariable('MAF_MEMORY_PRINCIPAL_ID', '')
