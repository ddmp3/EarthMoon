#!/bin/bash
# Déploiement Azure (DEV) : infrastructure Terraform, image de l'API, build du front.
# Premier déploiement comme mises à jour : le script est relançable.
#   ./deploy.sh          demande une confirmation avant d'appliquer
#   ./deploy.sh --yes    applique sans demander (déploiement déjà décidé)
set -euo pipefail

SUBSCRIPTION="dev"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"
TAG="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
ASSUME_YES="${1:-}"

for cmd in terraform az docker npm; do
  command -v "$cmd" >/dev/null || { echo "Erreur : $cmd n'est pas installé."; exit 1; }
done

az account show >/dev/null 2>&1 || { echo "Erreur : lancez d'abord 'az login'."; exit 1; }
# On cible la souscription sans changer celle par défaut de l'utilisateur (pas de 'az account set').
ARM_SUBSCRIPTION_ID="$(az account show --subscription "$SUBSCRIPTION" --query id -o tsv | tr -d '\r')"
export ARM_SUBSCRIPTION_ID
echo "Souscription : $SUBSCRIPTION ($ARM_SUBSCRIPTION_ID)"

cd "$TF_DIR"
terraform init -input=false
terraform validate

# Étape 1 : tout sauf la Container App, pour que le registre existe avant de pousser l'image.
BASE_TARGETS=(
  -target=azurerm_resource_group.main
  -target=azurerm_log_analytics_workspace.main
  -target=azurerm_container_registry.main
  -target=azurerm_container_app_environment.main
  -target=azurerm_static_web_app.main
)
terraform plan -input=false "${BASE_TARGETS[@]}"
if [ "$ASSUME_YES" != "--yes" ]; then
  read -r -p "Appliquer ces changements, puis déployer l'API et le front ? (yes/no) : " CONFIRM
  [ "$CONFIRM" = "yes" ] || { echo "Déploiement annulé."; exit 0; }
fi
terraform apply -input=false -auto-approve "${BASE_TARGETS[@]}"

ACR_NAME=$(terraform output -raw container_registry_name)
ACR_SERVER=$(terraform output -raw container_registry_login_server)
IMAGE="$ACR_SERVER/analogues-api:$TAG"

# Étape 2 : image de l'API (contexte = racine du dépôt, l'image embarque data/).
az acr login --name "$ACR_NAME" --subscription "$SUBSCRIPTION"
docker build --platform linux/amd64 -f "$ROOT_DIR/apps/api/Dockerfile" -t "$IMAGE" "$ROOT_DIR"
docker push "$IMAGE"

# Étape 3 : la Container App, créée directement avec notre image (pas d'image de démonstration sur un mauvais port).
terraform apply -input=false -auto-approve -var "api_image=$IMAGE"
RG=$(terraform output -raw resource_group_name)
APP_NAME=$(terraform output -raw container_app_name)
API_URL=$(terraform output -raw api_url)
WEB_URL=$(terraform output -raw web_url)
# Mise à jour : Terraform ignore les changements d'image (lifecycle), on pousse donc la nouvelle révision ici.
az containerapp update --name "$APP_NAME" --resource-group "$RG" --subscription "$SUBSCRIPTION" --image "$IMAGE" --output none

# Étape 4 : le front, avec l'adresse réelle de l'API et les en-têtes de sécurité.
cd "$ROOT_DIR/apps/web"
npm ci
VITE_API_URL="$API_URL" npm run build
sed "s#__API_ORIGIN__#$API_URL#" staticwebapp.config.template.json > dist/staticwebapp.config.json
SWA_CLI_DEPLOYMENT_TOKEN=$(terraform -chdir="$TF_DIR" output -raw web_deployment_token)
export SWA_CLI_DEPLOYMENT_TOKEN
npx --yes @azure/static-web-apps-cli@2.0.10 deploy ./dist --env production

echo "API : $API_URL"
echo "Web : $WEB_URL"
echo "Vérifier : python3 tools/validation/e2e.py --web $WEB_URL --api $API_URL"
echo "Supprimer les ressources quand le projet est terminé : terraform -chdir=$TF_DIR destroy"
