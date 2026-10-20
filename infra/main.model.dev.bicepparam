using './main.bicep'

// Deploy in the existing application resource group rg-maf-dev-eus2-01.
param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = 'crmafdevmako261018'
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'

param deploymentTarget = 'model'
// Only this model module targets the existing shared Foundry resource group.
param foundryResourceGroupName = 'rg-homelab-foundry'
param foundryAccountName = 'aif-homelab-rv6t99la'
param modelDeploymentName = 'gpt-5-mini'
param modelName = 'gpt-5-mini'
param modelVersion = '2025-08-07'
param modelCapacity = 30
