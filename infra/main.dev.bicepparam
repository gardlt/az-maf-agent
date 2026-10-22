using './main.bicep'

param location = 'eastus2'
param environmentName = 'cae-maf-dev-eus2-01'
param registryName = readEnvironmentVariable('MAF_REGISTRY_NAME')
param registrySku = readEnvironmentVariable('MAF_REGISTRY_SKU', 'Basic')
param pullIdentityName = 'id-maf-dev-eus2-01'
param logsName = 'law-maf-dev-eus2-01'
param agentAppName = 'ca-maf-agent-dev-eus2-01'
param movieMcpAppName = 'ca-maf-movie-mcp-dev-eus2-01'
param webAppName = 'ca-maf-web-dev-eus2-01'
param enableWeb = bool(readEnvironmentVariable('MAF_ENABLE_WEB', 'false'))
param webImage = readEnvironmentVariable('MAF_WEB_IMAGE', '')
param agentImage = readEnvironmentVariable('MAF_AGENT_IMAGE', '')
param mcpImage = readEnvironmentVariable('MAF_MCP_IMAGE', '')
param tenantId = readEnvironmentVariable('MAF_TENANT_ID')
param agentAudience = readEnvironmentVariable('MAF_AGENT_AUDIENCE')
param allowedUsers = readEnvironmentVariable('MAF_ALLOWED_USERS')
param apiClientId = readEnvironmentVariable('MAF_API_CLIENT_ID')
param cliClientId = readEnvironmentVariable('MAF_CLI_CLIENT_ID')
param webClientId = readEnvironmentVariable('MAF_WEB_CLIENT_ID', '')
param authClientSecret = readEnvironmentVariable('MAF_AUTH_CLIENT_SECRET')
param mcpAudience = readEnvironmentVariable('MAF_MCP_AUDIENCE')
param tmdbApiReadAccessToken = readEnvironmentVariable('TMDB_API_READ_ACCESS_TOKEN')

// Enabled after operator bootstrap and Stage 4 acceptance.
param enableMemory = true
param memoryCleanupJobName = 'job-maf-memory-dev-eus2-01'
param memoryAccountName = 'stmafmemdevmako261019'
param memoryCleanupAlertName = 'al-maf-memory-cleanup-dev-eus2-01'

// Stage 5 stores/roles were bootstrapped separately. Policy starts globally stopped.
param enableGuardrails = true
param alertEmail = readEnvironmentVariable('MAF_ALERT_EMAIL', '')
param controlActionGroupName = 'ag-maf-control-dev-eus2-01'

// Directory objects and grants are bootstrapped separately; disabled until configured.
param enableAgentIdentity = bool(readEnvironmentVariable('MAF_ENABLE_AGENT_IDENTITY', 'false'))
param agentBlueprintClientId = readEnvironmentVariable('MAF_AGENT_BLUEPRINT_CLIENT_ID', '')
param agentIdentityClientId = readEnvironmentVariable('MAF_AGENT_IDENTITY_CLIENT_ID', '')
param agentIdentityObjectId = readEnvironmentVariable('MAF_AGENT_IDENTITY_OBJECT_ID', '')
param enableAgentTracing = bool(readEnvironmentVariable('MAF_ENABLE_AGENT_TRACING', 'false'))
param agentObservabilityName = readEnvironmentVariable('MAF_AGENT_OBSERVABILITY_NAME', 'az-maf-agent')

param enableApprovedSkills = true
