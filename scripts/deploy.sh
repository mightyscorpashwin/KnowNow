#!/usr/bin/env bash
# One-command install of a KnowNow environment from your own machine.
# The Azure DevOps pipeline does the same steps; use this for a first try-out.
#
# Usage: scripts/deploy.sh <resource-group> <region> [dev|test|prod]
# Needs: Azure CLI (signed in), Python 3.11+, Node.js 20+, zip, jq.
# Optional env: KNOWNOW_REVIEWER_EMAILS="you@company.com"
set -euo pipefail

RG="${1:?resource group required}"
LOCATION="${2:?region required, e.g. centralindia}"
ENV_NAME="${3:-dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for tool in az python3 npm zip jq; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done

echo "== 1/5 Resource group $RG in $LOCATION"
az group create -n "$RG" -l "$LOCATION" --tags app=knownow "environment=$ENV_NAME" -o none

echo "== 2/5 Infrastructure (Bicep)"
export KNOWNOW_DEPLOYER_PRINCIPAL_ID
KNOWNOW_DEPLOYER_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
export KNOWNOW_DEPLOYER_PRINCIPAL_TYPE=User
OUT=$(az deployment group create -g "$RG" -n knownow \
  -p "$ROOT/infra/env/$ENV_NAME.bicepparam" --query properties.outputs -o json)
FUNC=$(echo "$OUT" | jq -r .functionAppName.value)
SWA=$(echo "$OUT" | jq -r .staticWebAppName.value)
HOST=$(echo "$OUT" | jq -r .staticWebAppHostname.value)

echo "== 3/5 API -> $FUNC"
cp -r "$ROOT/api" "$WORK/api"
rm -rf "$WORK/api/tests" "$WORK/api/.venv"
# Linux wheels, so this works from macOS and Windows too
python3 -m pip install -q -r "$WORK/api/requirements.txt" \
  --target "$WORK/api/.python_packages/lib/site-packages" \
  --platform manylinux2014_x86_64 --python-version 3.11 --only-binary=:all: --implementation cp
(cd "$WORK/api" && zip -qr "$WORK/api.zip" .)
az functionapp deployment source config-zip -g "$RG" -n "$FUNC" --src "$WORK/api.zip" -o none

echo "== 4/5 Web -> $SWA"
(cd "$ROOT/web" && npm install --no-audit --no-fund && npm run build)
TENANT=$(az account show --query tenantId -o tsv)
sed "s/__TENANT_ID__/$TENANT/g" "$ROOT/web/public/staticwebapp.config.json" > "$ROOT/web/dist/staticwebapp.config.json"
TOKEN=$(az staticwebapp secrets list -n "$SWA" -g "$RG" --query properties.apiKey -o tsv)
npx --yes @azure/static-web-apps-cli@2 deploy "$ROOT/web/dist" --deployment-token "$TOKEN" --env production

echo "== 5/5 Single sign-on"
"$ROOT/scripts/setup-sso.sh" "$RG" "$ENV_NAME"

echo
echo "KnowNow is live at https://$HOST/"
echo "Next: sign in as a reviewer, open Review, and draft the Azure pages."
