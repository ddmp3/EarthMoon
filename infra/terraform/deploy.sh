#!/bin/bash
# Azure deployment (DEV): Terraform infrastructure, API image, front-end build.
# Works for the first deployment and for updates: the script can be re-run.
#   ./deploy.sh          asks for confirmation before applying
#   ./deploy.sh --yes    applies without asking (deployment already decided)
set -euo pipefail

SUBSCRIPTION="dev"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"
TAG="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
ASSUME_YES="${1:-}"

for cmd in terraform az docker npm; do
  command -v "$cmd" >/dev/null || { echo "Error: $cmd is not installed."; exit 1; }
done

az account show >/dev/null 2>&1 || { echo "Error: run 'az login' first."; exit 1; }
# Target the subscription without changing the user's default one (no 'az account set').
ARM_SUBSCRIPTION_ID="$(az account show --subscription "$SUBSCRIPTION" --query id -o tsv | tr -d '\r')"
export ARM_SUBSCRIPTION_ID
echo "Subscription: $SUBSCRIPTION ($ARM_SUBSCRIPTION_ID)"

cd "$TF_DIR"
terraform init -input=false
terraform validate

# Step 1: everything except the Container App, so the registry exists before the image is pushed.
BASE_TARGETS=(
  -target=azurerm_resource_group.main
  -target=azurerm_log_analytics_workspace.main
  -target=azurerm_container_registry.main
  -target=azurerm_container_app_environment.main
  -target=azurerm_static_web_app.main
)
terraform plan -input=false "${BASE_TARGETS[@]}"
if [ "$ASSUME_YES" != "--yes" ]; then
  read -r -p "Apply these changes, then deploy the API and the front end? (yes/no): " CONFIRM
  [ "$CONFIRM" = "yes" ] || { echo "Deployment cancelled."; exit 0; }
fi
terraform apply -input=false -auto-approve "${BASE_TARGETS[@]}"

ACR_NAME=$(terraform output -raw container_registry_name)
ACR_SERVER=$(terraform output -raw container_registry_login_server)
IMAGE="$ACR_SERVER/analogues-api:$TAG"

# Step 2: API image (context = repository root, the image embeds data/).
az acr login --name "$ACR_NAME" --subscription "$SUBSCRIPTION"
docker build --platform linux/amd64 -f "$ROOT_DIR/apps/api/Dockerfile" -t "$IMAGE" "$ROOT_DIR"
docker push "$IMAGE"

# Step 3: the Container App, created directly with our image (no placeholder image on the wrong port).
terraform apply -input=false -auto-approve -var "api_image=$IMAGE"
RG=$(terraform output -raw resource_group_name)
APP_NAME=$(terraform output -raw container_app_name)
API_URL=$(terraform output -raw api_url)
WEB_URL=$(terraform output -raw web_url)
# Update: Terraform ignores image changes (lifecycle), so the new revision is pushed here.
az containerapp update --name "$APP_NAME" --resource-group "$RG" --subscription "$SUBSCRIPTION" --image "$IMAGE" --output none

# Step 4: the front end, with the real API address and the security headers.
cd "$ROOT_DIR/apps/web"
npm ci
VITE_API_URL="$API_URL" npm run build
sed "s#__API_ORIGIN__#$API_URL#" staticwebapp.config.template.json > dist/staticwebapp.config.json
SWA_CLI_DEPLOYMENT_TOKEN=$(terraform -chdir="$TF_DIR" output -raw web_deployment_token)
export SWA_CLI_DEPLOYMENT_TOKEN
npx --yes @azure/static-web-apps-cli@2.0.10 deploy ./dist --env production

echo "API: $API_URL"
echo "Web: $WEB_URL"
echo "Verify: python3 tools/validation/e2e.py --web $WEB_URL --api $API_URL"
echo "Delete the resources when the project is over: terraform -chdir=$TF_DIR destroy"
