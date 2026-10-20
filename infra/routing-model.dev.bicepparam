using './modules/foundry-routing-model.bicep'

// Deploy to rg-homelab-foundry, where the existing dev inference account lives.
param accountName = 'aif-homelab-rv6t99la'
param deploymentName = 'gpt-5-mini'
param modelVersion = '2025-08-07'
param capacity = 30
