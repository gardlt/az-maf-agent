using './main.bicep'

// Set these values in the shell or azd environment before deployment.
param location = 'eastus2'
param environmentName = 'cae-maf-stage-eus2-01'
param registryName = readEnvironmentVariable('MAF_REGISTRY_NAME')
param registrySku = readEnvironmentVariable('MAF_REGISTRY_SKU', 'Basic')
param pullIdentityName = 'id-maf-stage-eus2-01'
param logsName = 'law-maf-stage-eus2-01'
param agentAppName = 'ca-maf-agent-stage-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-stage-eus2-01'
param agentImage = readEnvironmentVariable('MAF_AGENT_IMAGE', '')
param mcpImage = readEnvironmentVariable('MAF_MCP_IMAGE', '')
param tenantId = readEnvironmentVariable('MAF_TENANT_ID')
param agentAudience = readEnvironmentVariable('MAF_AGENT_AUDIENCE')
param allowedUsers = readEnvironmentVariable('MAF_ALLOWED_USERS')
param apiClientId = readEnvironmentVariable('MAF_API_CLIENT_ID')
param cliClientId = readEnvironmentVariable('MAF_CLI_CLIENT_ID')
param authClientSecret = readEnvironmentVariable('MAF_AUTH_CLIENT_SECRET')
param mcpAudience = readEnvironmentVariable('MAF_MCP_AUDIENCE')
param tmdbApiReadAccessToken = readEnvironmentVariable('TMDB_API_READ_ACCESS_TOKEN')

// Directory objects and grants are bootstrapped separately; disabled until configured.
param enableAgentIdentity = bool(readEnvironmentVariable('MAF_ENABLE_AGENT_IDENTITY', 'false'))
param agentBlueprintClientId = readEnvironmentVariable('MAF_AGENT_BLUEPRINT_CLIENT_ID', '')
param agentIdentityClientId = readEnvironmentVariable('MAF_AGENT_IDENTITY_CLIENT_ID', '')
param agentIdentityObjectId = readEnvironmentVariable('MAF_AGENT_IDENTITY_OBJECT_ID', '')
param enableAgentTracing = bool(readEnvironmentVariable('MAF_ENABLE_AGENT_TRACING', 'false'))
param agentObservabilityName = readEnvironmentVariable('MAF_AGENT_OBSERVABILITY_NAME', 'az-maf-agent')
