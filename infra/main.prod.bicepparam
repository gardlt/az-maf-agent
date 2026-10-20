using './main.bicep'

// Production values come from the protected GitHub prod environment or an
// equivalent azd environment. No credentials belong in this file.
param resourceGroupName = 'rg-maf-prod-eus2-01'
param location = 'eastus2'
param environmentName = 'cae-maf-prod-eus2-01'
param registryName = readEnvironmentVariable('MAF_REGISTRY_NAME')
param registrySku = readEnvironmentVariable('MAF_REGISTRY_SKU', 'Basic')
param pullIdentityName = 'id-maf-prod-eus2-01'
param logsName = 'law-maf-prod-eus2-01'
param agentAppName = 'ca-maf-agent-prod-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-prod-eus2-01'
param agentImage = readEnvironmentVariable('MAF_AGENT_IMAGE')
param mcpImage = readEnvironmentVariable('MAF_MCP_IMAGE')
param tenantId = readEnvironmentVariable('MAF_TENANT_ID')
param agentAudience = readEnvironmentVariable('MAF_AGENT_AUDIENCE')
param allowedUsers = readEnvironmentVariable('MAF_ALLOWED_USERS')
param apiClientId = readEnvironmentVariable('MAF_API_CLIENT_ID')
param cliClientId = readEnvironmentVariable('MAF_CLI_CLIENT_ID')
param authClientSecret = readEnvironmentVariable('MAF_AUTH_CLIENT_SECRET')
param mcpAudience = readEnvironmentVariable('MAF_MCP_AUDIENCE')
param tmdbApiReadAccessToken = readEnvironmentVariable('TMDB_API_READ_ACCESS_TOKEN')
