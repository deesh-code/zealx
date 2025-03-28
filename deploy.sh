#!/bin/bash
# ZealX Backend Cloud Deployment Script

set -e

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "███████╗███████╗ █████╗ ██╗     ██╗  ██╗"
echo "╚══███╔╝██╔════╝██╔══██╗██║     ╚██╗██╔╝"
echo "  ███╔╝ █████╗  ███████║██║      ╚███╔╝ "
echo " ███╔╝  ██╔══╝  ██╔══██║██║      ██╔██╗ "
echo "███████╗███████╗██║  ██║███████╗██╔╝ ██╗"
echo "╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
echo -e "Cloud Deployment Script${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create a .env file based on .env.example${NC}"
    exit 1
fi

# Load environment variables
source .env

# Check cloud provider
CLOUD_PROVIDER=${CLOUD_PROVIDER:-"aws"}
echo -e "${GREEN}Deploying to ${CLOUD_PROVIDER}...${NC}"

# Function to deploy to AWS
deploy_to_aws() {
    echo -e "${BLUE}Preparing AWS deployment...${NC}"
    
    # Check AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo -e "${RED}AWS credentials not found in .env file${NC}"
        exit 1
    fi
    
    # Configure AWS CLI
    aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
    aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    aws configure set default.region ${CLOUD_REGION:-"us-east-1"}
    
    echo -e "${GREEN}AWS configured successfully${NC}"
    
    # Create ECR repository if it doesn't exist
    REPO_NAME="zealx-backend"
    if ! aws ecr describe-repositories --repository-names $REPO_NAME &> /dev/null; then
        echo -e "${YELLOW}Creating ECR repository: $REPO_NAME${NC}"
        aws ecr create-repository --repository-name $REPO_NAME
    fi
    
    # Get ECR repository URI
    ECR_REPO=$(aws ecr describe-repositories --repository-names $REPO_NAME --query 'repositories[0].repositoryUri' --output text)
    
    # Login to ECR
    echo -e "${BLUE}Logging in to ECR...${NC}"
    aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
    
    # Build and push Docker image
    echo -e "${BLUE}Building Docker image...${NC}"
    docker build -t $REPO_NAME .
    
    # Tag the image
    docker tag $REPO_NAME:latest $ECR_REPO:latest
    
    # Push the image
    echo -e "${BLUE}Pushing image to ECR...${NC}"
    docker push $ECR_REPO:latest
    
    echo -e "${GREEN}Image pushed successfully to ECR${NC}"
    
    # Deploy to ECS or EKS based on configuration
    if [ "${DEPLOY_TO_ECS:-true}" = true ]; then
        deploy_to_ecs $ECR_REPO
    else
        echo -e "${YELLOW}EKS deployment not implemented yet${NC}"
    fi
}

# Function to deploy to ECS
deploy_to_ecs() {
    ECR_REPO=$1
    CLUSTER_NAME="zealx-cluster"
    SERVICE_NAME="zealx-service"
    TASK_FAMILY="zealx-task"
    
    echo -e "${BLUE}Deploying to ECS...${NC}"
    
    # Create ECS cluster if it doesn't exist
    if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --query 'clusters[0].clusterName' --output text &> /dev/null; then
        echo -e "${YELLOW}Creating ECS cluster: $CLUSTER_NAME${NC}"
        aws ecs create-cluster --cluster-name $CLUSTER_NAME
    fi
    
    # Create task definition
    echo -e "${BLUE}Creating ECS task definition...${NC}"
    
    # Configure ADX settings in container definition
    ADX_ENV_VARS=$(cat <<EOF
        {
            "name": "ADX_ENABLED",
            "value": "${ADX_ENABLED:-true}"
        },
        {
            "name": "ADX_MONITORING_INTERVAL",
            "value": "${ADX_MONITORING_INTERVAL:-60}"
        },
        {
            "name": "ADX_MAX_MONITORING_INTERVAL",
            "value": "${ADX_MAX_MONITORING_INTERVAL:-300}"
        },
        {
            "name": "ADX_IDLE_TIMEOUT",
            "value": "${ADX_IDLE_TIMEOUT:-300}"
        },
        {
            "name": "ADX_CPU_THRESHOLD",
            "value": "${ADX_CPU_THRESHOLD:-80.0}"
        },
        {
            "name": "ADX_MEMORY_THRESHOLD",
            "value": "${ADX_MEMORY_THRESHOLD:-80.0}"
        },
        {
            "name": "ADX_BATTERY_THRESHOLD",
            "value": "${ADX_BATTERY_THRESHOLD:-20.0}"
        }
EOF
    )
    
    # Create task definition JSON
    TASK_DEF=$(cat <<EOF
{
    "family": "$TASK_FAMILY",
    "networkMode": "awsvpc",
    "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "zealx-app",
            "image": "$ECR_REPO:latest",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 8000,
                    "hostPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                $ADX_ENV_VARS,
                {
                    "name": "POSTGRES_HOST",
                    "value": "${POSTGRES_HOST}"
                },
                {
                    "name": "POSTGRES_PORT",
                    "value": "${POSTGRES_PORT}"
                },
                {
                    "name": "POSTGRES_DB",
                    "value": "${POSTGRES_DB}"
                },
                {
                    "name": "REDIS_HOST",
                    "value": "${REDIS_HOST}"
                },
                {
                    "name": "REDIS_PORT",
                    "value": "${REDIS_PORT}"
                }
            ],
            "secrets": [
                {
                    "name": "POSTGRES_USER",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/postgres_user"
                },
                {
                    "name": "POSTGRES_PASSWORD",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/postgres_password"
                },
                {
                    "name": "SECRET_KEY",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/secret_key"
                },
                {
                    "name": "REDIS_PASSWORD",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/redis_password"
                },
                {
                    "name": "CLOUDFLARE_API_KEYS",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/cloudflare_api_keys"
                },
                {
                    "name": "CLOUDFLARE_ACCOUNT_IDS",
                    "valueFrom": "arn:aws:ssm:${CLOUD_REGION}:${AWS_ACCOUNT_ID}:parameter/zealx/cloudflare_account_ids"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/zealx",
                    "awslogs-region": "${CLOUD_REGION}",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ],
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "cpu": "1024",
    "memory": "2048"
}
EOF
)
    
    # Register task definition
    aws ecs register-task-definition --cli-input-json "$TASK_DEF"
    
    # Create service if it doesn't exist
    if ! aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].serviceName' --output text &> /dev/null; then
        echo -e "${YELLOW}Creating ECS service: $SERVICE_NAME${NC}"
        
        # Create security group for the service
        SG_ID=$(aws ec2 create-security-group --group-name zealx-sg --description "Security group for ZealX" --vpc-id $VPC_ID --query 'GroupId' --output text)
        
        # Allow inbound traffic on port 8000
        aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0
        
        # Create the service
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name $SERVICE_NAME \
            --task-definition $TASK_FAMILY \
            --desired-count 1 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
            --health-check-grace-period-seconds 120
    else
        # Update the service with the new task definition
        echo -e "${BLUE}Updating ECS service...${NC}"
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --task-definition $TASK_FAMILY \
            --force-new-deployment
    fi
    
    echo -e "${GREEN}Deployment to ECS completed successfully${NC}"
}

# Function to deploy to GCP
deploy_to_gcp() {
    echo -e "${BLUE}Preparing GCP deployment...${NC}"
    
    # Check gcloud CLI is installed
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}Google Cloud SDK is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Authenticate with GCP
    echo -e "${BLUE}Authenticating with GCP...${NC}"
    echo $GCP_SERVICE_ACCOUNT_KEY > gcp-key.json
    gcloud auth activate-service-account --key-file=gcp-key.json
    
    # Set GCP project
    gcloud config set project $GCP_PROJECT_ID
    
    # Build and push Docker image to GCR
    echo -e "${BLUE}Building and pushing Docker image to GCR...${NC}"
    gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/zealx-backend
    
    # Deploy to Cloud Run
    echo -e "${BLUE}Deploying to Cloud Run...${NC}"
    gcloud run deploy zealx-backend \
        --image gcr.io/$GCP_PROJECT_ID/zealx-backend \
        --platform managed \
        --region ${CLOUD_REGION:-"us-central1"} \
        --memory 2Gi \
        --cpu 1 \
        --min-instances 1 \
        --max-instances ${CLOUD_MAX_INSTANCES:-5} \
        --port 8000 \
        --set-env-vars="ADX_ENABLED=${ADX_ENABLED:-true},ADX_MONITORING_INTERVAL=${ADX_MONITORING_INTERVAL:-60},ADX_MAX_MONITORING_INTERVAL=${ADX_MAX_MONITORING_INTERVAL:-300},ADX_IDLE_TIMEOUT=${ADX_IDLE_TIMEOUT:-300},ADX_CPU_THRESHOLD=${ADX_CPU_THRESHOLD:-80.0},ADX_MEMORY_THRESHOLD=${ADX_MEMORY_THRESHOLD:-80.0},ADX_BATTERY_THRESHOLD=${ADX_BATTERY_THRESHOLD:-20.0}" \
        --allow-unauthenticated
    
    # Clean up
    rm gcp-key.json
    
    echo -e "${GREEN}Deployment to GCP completed successfully${NC}"
}

# Function to deploy to Azure
deploy_to_azure() {
    echo -e "${BLUE}Preparing Azure deployment...${NC}"
    
    # Check Azure CLI is installed
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Azure CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Login to Azure
    echo -e "${BLUE}Logging in to Azure...${NC}"
    az login
    
    # Create resource group if it doesn't exist
    RESOURCE_GROUP="zealx-rg"
    LOCATION=${CLOUD_REGION:-"eastus"}
    
    if ! az group show --name $RESOURCE_GROUP &> /dev/null; then
        echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP${NC}"
        az group create --name $RESOURCE_GROUP --location $LOCATION
    fi
    
    # Create Azure Container Registry if it doesn't exist
    ACR_NAME="zealxregistry"
    
    if ! az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
        echo -e "${YELLOW}Creating Azure Container Registry: $ACR_NAME${NC}"
        az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic --admin-enabled true
    fi
    
    # Get ACR credentials
    ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
    
    # Build and push Docker image to ACR
    echo -e "${BLUE}Building and pushing Docker image to ACR...${NC}"
    az acr build --registry $ACR_NAME --image zealx-backend:latest .
    
    # Create App Service Plan if it doesn't exist
    APP_SERVICE_PLAN="zealx-plan"
    
    if ! az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP &> /dev/null; then
        echo -e "${YELLOW}Creating App Service Plan: $APP_SERVICE_PLAN${NC}"
        az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku P1V2 --is-linux
    fi
    
    # Create Web App if it doesn't exist
    WEBAPP_NAME="zealx-app"
    
    if ! az webapp show --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
        echo -e "${YELLOW}Creating Web App: $WEBAPP_NAME${NC}"
        az webapp create --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --deployment-container-image-name ${ACR_NAME}.azurecr.io/zealx-backend:latest
    fi
    
    # Configure Web App settings
    echo -e "${BLUE}Configuring Web App settings...${NC}"
    az webapp config appsettings set --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP --settings \
        ADX_ENABLED=${ADX_ENABLED:-true} \
        ADX_MONITORING_INTERVAL=${ADX_MONITORING_INTERVAL:-60} \
        ADX_MAX_MONITORING_INTERVAL=${ADX_MAX_MONITORING_INTERVAL:-300} \
        ADX_IDLE_TIMEOUT=${ADX_IDLE_TIMEOUT:-300} \
        ADX_CPU_THRESHOLD=${ADX_CPU_THRESHOLD:-80.0} \
        ADX_MEMORY_THRESHOLD=${ADX_MEMORY_THRESHOLD:-80.0} \
        ADX_BATTERY_THRESHOLD=${ADX_BATTERY_THRESHOLD:-20.0} \
        POSTGRES_HOST=${POSTGRES_HOST} \
        POSTGRES_PORT=${POSTGRES_PORT} \
        POSTGRES_USER=${POSTGRES_USER} \
        POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
        POSTGRES_DB=${POSTGRES_DB} \
        SECRET_KEY=${SECRET_KEY} \
        WEBSITES_PORT=8000
    
    # Update Web App with latest image
    echo -e "${BLUE}Updating Web App with latest image...${NC}"
    az webapp config container set --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP \
        --docker-custom-image-name ${ACR_NAME}.azurecr.io/zealx-backend:latest \
        --docker-registry-server-url https://${ACR_NAME}.azurecr.io \
        --docker-registry-server-user $ACR_USERNAME \
        --docker-registry-server-password $ACR_PASSWORD
    
    echo -e "${GREEN}Deployment to Azure completed successfully${NC}"
}

# Deploy based on cloud provider
case $CLOUD_PROVIDER in
    aws)
        deploy_to_aws
        ;;
    gcp)
        deploy_to_gcp
        ;;
    azure)
        deploy_to_azure
        ;;
    *)
        echo -e "${RED}Unsupported cloud provider: $CLOUD_PROVIDER${NC}"
        echo -e "${YELLOW}Supported providers: aws, gcp, azure${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}ZealX Backend deployment completed successfully!${NC}"
echo -e "${BLUE}ADX (Adaptive Execution Mode) is enabled to optimize performance and battery usage.${NC}"
echo -e "${YELLOW}Remember to monitor your cloud resources and costs.${NC}"
