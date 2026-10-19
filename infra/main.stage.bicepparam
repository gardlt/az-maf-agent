using './main.bicep'

// Set these values in the shell or azd environment before deployment.
param resourceGroupName = 'rg-maf-stage-eus2-01'
param location = 'eastus2'
param environmentName = 'cae-maf-stage-eus2-01'
param registryName = readEnvironmentVariable('MAF_REGISTRY_NAME')
param pullIdentityName = 'id-maf-stage-eus2-01'
param logsName = 'law-maf-stage-eus2-01'
param agentAppName = 'ca-maf-agent-stage-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-stage-eus2-01'
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
