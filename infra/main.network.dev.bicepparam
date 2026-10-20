using './main.bicep'

// Deploy in the existing application resource group rg-maf-dev-eus2-01.
param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = 'crmafdevmako261018'
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'

param deploymentTarget = 'network'
// Parallel foundation only; this never moves the agent or MCP.
param network = {
  environmentName: 'cae-maf-dev-eus2-02'
  vnetName: 'vnet-maf-dev-eus2-01'
  firewallName: 'afw-maf-dev-eus2-01'
  firewallPolicyName: 'afwp-maf-dev-eus2-01'
  routeTableName: 'rt-maf-apps-dev-eus2-01'
  nsgName: 'nsg-maf-apps-dev-eus2-01'
  registryDataEndpoint: 'crmafdevmako261018.eastus2.data.azurecr.io'
  memoryBlobHost: readEnvironmentVariable('MAF_MEMORY_BLOB_HOST', 'stmafmemdevmako261019.blob.core.windows.net')
  foundryHost: 'aif-homelab-rv6t99la.openai.azure.com'
  insightsIngestionHost: readEnvironmentVariable('MAF_INSIGHTS_INGESTION_HOST')
}
