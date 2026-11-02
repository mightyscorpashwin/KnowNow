using '../main.bicep'

param environmentName = 'dev'
param staticWebAppLocation = readEnvironmentVariable('KNOWNOW_SWA_LOCATION', 'eastasia')
param openAiLocation = readEnvironmentVariable('KNOWNOW_OPENAI_LOCATION', 'eastus2')
param enablePrivateNetworking = false
param reviewerEmails = readEnvironmentVariable('KNOWNOW_REVIEWER_EMAILS', '')
param reviewerGroupId = readEnvironmentVariable('KNOWNOW_REVIEWER_GROUP_ID', '')
param deployerPrincipalId = readEnvironmentVariable('KNOWNOW_DEPLOYER_PRINCIPAL_ID', '')
param deployerPrincipalType = readEnvironmentVariable('KNOWNOW_DEPLOYER_PRINCIPAL_TYPE', 'ServicePrincipal')
