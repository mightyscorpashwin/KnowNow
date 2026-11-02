#!/usr/bin/env bash
# Sets up Entra ID single sign-on for one KnowNow environment:
#   1. creates (or reuses) an app registration with the Static Web App's
#      redirect URI and group claims,
#   2. creates a client secret and keeps it in Key Vault,
#   3. sets AZURE_CLIENT_ID / AZURE_CLIENT_SECRET on the Static Web App.
#
# Usage: scripts/setup-sso.sh <resource-group> <environment>
# Needs: Azure CLI signed in with rights to create app registrations
#        (Application Developer role or equivalent).
set -euo pipefail

RG="${1:?resource group required}"
ENV_NAME="${2:-dev}"

outputs() {
  az deployment group show -g "$RG" -n knownow --query "properties.outputs.$1.value" -o tsv
}

SWA_NAME=$(outputs staticWebAppName)
SWA_HOST=$(outputs staticWebAppHostname)
KV_NAME=$(outputs keyVaultName)
DISPLAY_NAME="KnowNow (${ENV_NAME})"
REDIRECT="https://${SWA_HOST}/.auth/login/aad/callback"

echo "Static Web App: $SWA_NAME ($SWA_HOST)"

APP_ID=$(az ad app list --display-name "$DISPLAY_NAME" --query "[0].appId" -o tsv)
if [[ -z "$APP_ID" ]]; then
  echo "Creating app registration '$DISPLAY_NAME'"
  APP_ID=$(az ad app create \
    --display-name "$DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    --web-redirect-uris "$REDIRECT" \
    --enable-id-token-issuance true \
    --query appId -o tsv)
  az ad sp create --id "$APP_ID" -o none
else
  echo "Reusing app registration $APP_ID"
  az ad app update --id "$APP_ID" --web-redirect-uris "$REDIRECT" --enable-id-token-issuance true
fi

# Send security-group IDs in the token so reviewer groups work.
az ad app update --id "$APP_ID" --set groupMembershipClaims=SecurityGroup

SECRET=$(az ad app credential reset --id "$APP_ID" --append \
  --display-name "swa-${ENV_NAME}" --years 1 --query password -o tsv)

if az keyvault secret set --vault-name "$KV_NAME" --name sso-client-secret --value "$SECRET" -o none 2>/dev/null; then
  echo "Client secret stored in Key Vault $KV_NAME"
else
  echo "WARNING: could not write to Key Vault $KV_NAME (private network or missing role). Continuing." >&2
fi

az staticwebapp appsettings set -n "$SWA_NAME" -g "$RG" \
  --setting-names "AZURE_CLIENT_ID=$APP_ID" "AZURE_CLIENT_SECRET=$SECRET" -o none

echo "Single sign-on configured. Sign in at https://${SWA_HOST}/"
echo "The client secret expires in 1 year; re-run this script to rotate it."
