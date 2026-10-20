using './main.bicep'

// Deploy in the existing application resource group rg-maf-dev-eus2-01.
param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = 'crmafdevmako261018'
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'

param deploymentTarget = 'access'
// Explicit bootstrap flags default false. No ordinary CI grants roles.
param enableMemory = true
param enableGuardrails = true
param memoryAccountName = 'stmafmemdevmako261019'
param memoryCleanupJobName = 'job-maf-memory-dev-eus2-01'
param foundryResourceGroupName = 'rg-homelab-foundry'
param foundryAccountName = 'aif-homelab-rv6t99la'
param agentIdentityObjectId = readEnvironmentVariable('MAF_AGENT_IDENTITY_OBJECT_ID', '')
param operatorPrincipalId = readEnvironmentVariable('MAF_OPERATOR_OBJECT_ID', '')
