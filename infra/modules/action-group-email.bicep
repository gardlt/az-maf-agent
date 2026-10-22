param name string
param emailAddress string
param receiverName string = 'containment-operator'
param location string = 'global'

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: name
  location: location
  properties: {
    groupShortName: take(replace(name, '-', ''), 12)
    enabled: true
    emailReceivers: [
      {
        name: receiverName
        emailAddress: emailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

output id string = actionGroup.id
