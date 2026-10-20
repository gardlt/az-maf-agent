using './main.bicep'

// Deploy in the existing application resource group rg-maf-dev-eus2-01.
param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = 'crmafdevmako261018'
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'

param deploymentTarget = 'containment'
param containmentImage = readEnvironmentVariable('MAF_CONTAINMENT_IMAGE')
param containmentWorkerName = 'ca-maf-stop-dev-eus2-01'
param containmentRevisionSuffix = 'drill-a'
