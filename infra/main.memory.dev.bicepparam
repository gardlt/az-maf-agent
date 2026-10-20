using './main.bicep'

// Deploy in the existing application resource group rg-maf-dev-eus2-01.
param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = 'crmafdevmako261018'
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'

param deploymentTarget = 'memory'
param enableMemory = true
param memoryAccountName = readEnvironmentVariable('MAF_MEMORY_ACCOUNT_NAME', 'stmafmemdevmako261019')
