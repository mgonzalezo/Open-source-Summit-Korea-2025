#!/bin/bash
#
# Deploy Kepler K3s Stack with Automated Setup
# This script deploys a fully configured Kepler environment with RAPL
#

set -e

# Configuration
STACK_NAME="kepler-k3s-rapl"
REGION="ap-northeast-1"
PROFILE="${AWS_PROFILE:-mgonzalezo}"
KEY_NAME="oss-korea"
INSTANCE_TYPE="c5.metal"
VOLUME_SIZE="100"
AUTO_INSTALL="true"  # Set to "false" to manually run setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Kepler K3s Automated Deployment"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Stack Name:     $STACK_NAME"
echo "  Region:         $REGION"
echo "  Instance Type:  $INSTANCE_TYPE"
echo "  SSH Key:        $KEY_NAME"
echo "  Volume Size:    ${VOLUME_SIZE}GB"
echo "  Auto Install:   $AUTO_INSTALL"
echo ""

# Get default VPC
echo -e "${YELLOW}Getting default VPC...${NC}"
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --region $REGION \
  --profile $PROFILE \
  --query "Vpcs[0].VpcId" \
  --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
  echo -e "${RED}❌ No default VPC found in $REGION${NC}"
  echo "Please specify a VPC ID manually or create a default VPC."
  exit 1
fi

echo -e "${GREEN}✅ Using VPC: $VPC_ID${NC}"

# Check if key pair exists
echo -e "${YELLOW}Verifying SSH key pair...${NC}"
KEY_CHECK=$(aws ec2 describe-key-pairs \
  --key-names $KEY_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "KeyPairs[0].KeyName" \
  --output text 2>/dev/null || echo "None")

if [ "$KEY_CHECK" == "None" ]; then
  echo -e "${RED}❌ SSH key '$KEY_NAME' not found in $REGION${NC}"
  echo "Available keys:"
  aws ec2 describe-key-pairs --region $REGION --profile $PROFILE --query "KeyPairs[*].KeyName" --output table
  exit 1
fi

echo -e "${GREEN}✅ SSH key verified: $KEY_NAME${NC}"

# Check for existing stack
echo -e "${YELLOW}Checking for existing stack...${NC}"
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "Stacks[0].StackStatus" \
  --output text 2>/dev/null || echo "NONE")

if [ "$STACK_STATUS" != "NONE" ]; then
  echo -e "${YELLOW}⚠️  Stack '$STACK_NAME' already exists with status: $STACK_STATUS${NC}"

  if [[ "$STACK_STATUS" == *"IN_PROGRESS"* ]]; then
    echo -e "${RED}❌ Stack operation in progress. Please wait for it to complete.${NC}"
    exit 1
  fi

  read -p "Do you want to delete and recreate it? (yes/no): " CONFIRM
  if [ "$CONFIRM" == "yes" ]; then
    echo -e "${YELLOW}Deleting existing stack...${NC}"
    aws cloudformation delete-stack \
      --stack-name $STACK_NAME \
      --region $REGION \
      --profile $PROFILE

    echo "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete \
      --stack-name $STACK_NAME \
      --region $REGION \
      --profile $PROFILE

    echo -e "${GREEN}✅ Stack deleted${NC}"
  else
    echo "Aborted."
    exit 0
  fi
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEMPLATE_PATH="$SCRIPT_DIR/../templates/kepler-k3s-automated-stack.yaml"

if [ ! -f "$TEMPLATE_PATH" ]; then
  echo -e "${RED}❌ Template not found: $TEMPLATE_PATH${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Template found: $TEMPLATE_PATH${NC}"

# Deploy stack
echo ""
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
echo "This will take approximately 5-10 minutes."
echo ""

aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://$TEMPLATE_PATH \
  --region $REGION \
  --profile $PROFILE \
  --parameters \
    ParameterKey=KeyName,ParameterValue=$KEY_NAME \
    ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE \
    ParameterKey=VolumeSize,ParameterValue=$VOLUME_SIZE \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=AutoInstallKepler,ParameterValue=$AUTO_INSTALL \
  --tags \
    Key=Project,Value=Kepler-OSS-Korea-2025 \
    Key=ManagedBy,Value=CloudFormation \
    Key=Environment,Value=Demo \
  --capabilities CAPABILITY_NAMED_IAM

echo -e "${GREEN}✅ Stack creation initiated${NC}"
echo ""
echo "Waiting for stack to complete..."
echo "(This may take 5-10 minutes)"

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ Stack Created Successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Get stack outputs
echo "Retrieving stack information..."
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" \
  --output text)

PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" \
  --output text)

HTTPS_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "Stacks[0].Outputs[?OutputKey=='HTTPSMetricsURL'].OutputValue" \
  --output text)

HTTP_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query "Stacks[0].Outputs[?OutputKey=='HTTPMetricsURL'].OutputValue" \
  --output text)

echo ""
echo "Instance Information:"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP:   $PUBLIC_IP"
echo ""
echo "SSH Access:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""

if [ "$AUTO_INSTALL" == "true" ]; then
  echo -e "${YELLOW}Kepler is being installed automatically...${NC}"
  echo "This will take an additional 10-15 minutes."
  echo ""
  echo "To monitor installation progress:"
  echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
  echo "  tail -f /var/log/user-data.log"
  echo ""
  echo "Once complete, deployment info will be at:"
  echo "  /home/ubuntu/kepler-info.txt"
  echo ""
  echo "Wait approximately 15 minutes, then test:"
  echo "  curl -k $HTTPS_URL | grep kepler_node_cpu"
else
  echo "To install Kepler manually:"
  echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
  echo "  ./setup-kepler-automated.sh"
fi

echo ""
echo "Metrics Endpoints (will be available after ~15 minutes):"
echo "  HTTPS: $HTTPS_URL"
echo "  HTTP:  $HTTP_URL"
echo ""
echo "Test Command:"
echo "  curl -k -s $HTTPS_URL | grep kepler_node_cpu_usage_ratio"
echo ""
echo "Save this information:"
cat > $SCRIPT_DIR/../k3s-instance-info.txt << EOF
Kepler K3s Deployment Information
==================================

Stack Name:    $STACK_NAME
Instance ID:   $INSTANCE_ID
Instance Type: $INSTANCE_TYPE
Public IP:     $PUBLIC_IP
Region:        $REGION

SSH Access:
  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP

Metrics Endpoints:
  HTTPS: $HTTPS_URL
  HTTP:  $HTTP_URL

Test Metrics:
  curl -k -s $HTTPS_URL | grep kepler_node_cpu_usage_ratio
  curl -k -s $HTTPS_URL | grep kepler_node_cpu_watts

Check Installation Status:
  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP
  tail -f /var/log/user-data.log
  cat /home/ubuntu/kepler-info.txt

Kubernetes Access:
  kubectl get pods -n kepler-system
  kubectl get pods -n kepler-model-server
  kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler

Management Scripts:
  ./stop-stack.sh   - Stop instance (save costs)
  ./start-stack.sh  - Start instance
  ./delete-stack.sh - Delete everything

Deployed: $(date)
EOF

echo -e "${GREEN}✅ Deployment information saved to: k3s-instance-info.txt${NC}"
echo ""
echo -e "${YELLOW}⏰ Wait ~15 minutes for Kepler installation to complete, then test the metrics endpoint.${NC}"
echo ""
