targetScope = 'resourceGroup'
param location string = 'eastus2'
param insightsIngestionHost string
module controlled './modules/controlled-egress.bicep' = {
  name: 'controlled-egress-dev'
  params: {
    environmentName: 'cae-maf-dev-eus2-02'
    vnetName: 'vnet-maf-dev-eus2-01'
    firewallName: 'afw-maf-dev-eus2-01'
    firewallPolicyName: 'afwp-maf-dev-eus2-01'
    routeTableName: 'rt-maf-apps-dev-eus2-01'
    nsgName: 'nsg-maf-apps-dev-eus2-01'
    logsName: 'law-maf-dev-eus2-01'
    registryLoginServer: 'crmafdevmako261018.azurecr.io'
    registryDataEndpoint: 'crmafdevmako261018.eastus2.data.azurecr.io'
    memoryBlobHost: 'stmafmemdevmako261019.blob.${environment().suffixes.storage}'
    foundryHost: 'aif-homelab-rv6t99la.openai.azure.com'
    insightsIngestionHost: insightsIngestionHost
    location: location
  }
}
output environmentId string = controlled.outputs.environmentId
output firewallId string = controlled.outputs.firewallId
