#!/bin/bash
set -e

# Configuration
STACK_NAME="kepler-baremetal-stack"
REGION="us-east-1"
PROFILE="mgonzalezo"
TEMPLATE_FILE="../templates/kepler-baremetal-stack.yaml"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Kepler Bare-Metal Stack Deployment${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --profile $PROFILE --region $REGION &>/dev/null; then
    echo -e "${RED}Error: AWS CLI not configured for profile '$PROFILE'${NC}"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --profile $PROFILE --query Account --output text)
echo -e "${GREEN}✓ AWS Account:${NC} $ACCOUNT_ID"
echo -e "${GREEN}✓ Region:${NC} $REGION"
echo -e "${GREEN}✓ Profile:${NC} $PROFILE"
echo ""

# Check for existing SSH key
echo -e "${YELLOW}Checking for SSH keys...${NC}"
KEYS=$(aws ec2 describe-key-pairs --profile $PROFILE --region $REGION --query 'KeyPairs[*].KeyName' --output text)

if [ -z "$KEYS" ]; then
    echo -e "${RED}No SSH key pairs found in $REGION${NC}"
    echo -e "${YELLOW}Creating a new key pair...${NC}"
    KEY_NAME="kepler-demo-key"
    aws ec2 create-key-pair \
        --profile $PROFILE \
        --region $REGION \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text > ~/.ssh/${KEY_NAME}.pem
    chmod 400 ~/.ssh/${KEY_NAME}.pem
    echo -e "${GREEN}✓ Created new key pair: $KEY_NAME${NC}"
    echo -e "${GREEN}✓ Saved to: ~/.ssh/${KEY_NAME}.pem${NC}"
else
    echo -e "${GREEN}Available SSH keys:${NC}"
    echo "$KEYS" | tr '\t' '\n' | nl
    echo ""
    echo -e "${YELLOW}Enter the name of the SSH key to use:${NC}"
    read -p "Key name: " KEY_NAME

    # Validate key exists
    if ! echo "$KEYS" | grep -q "$KEY_NAME"; then
        echo -e "${RED}Error: Key '$KEY_NAME' not found${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Select instance type:${NC}"
echo "1) c5.metal  (96 vCPU, 192 GB RAM) - ~\$4.08/hour - Recommended"
echo "2) m5.metal  (96 vCPU, 384 GB RAM) - ~\$4.61/hour"
echo "3) m5d.metal (96 vCPU, 384 GB RAM, NVMe SSD) - ~\$5.42/hour"
echo "4) r5.metal  (96 vCPU, 768 GB RAM) - ~\$6.05/hour"
read -p "Choice [1-4]: " INSTANCE_CHOICE

case $INSTANCE_CHOICE in
    1) INSTANCE_TYPE="c5.metal" ;;
    2) INSTANCE_TYPE="m5.metal" ;;
    3) INSTANCE_TYPE="m5d.metal" ;;
    4) INSTANCE_TYPE="r5.metal" ;;
    *)
        echo -e "${YELLOW}Invalid choice, using c5.metal${NC}"
        INSTANCE_TYPE="c5.metal"
        ;;
esac

echo ""
read -p "Enter EBS volume size in GB [100]: " VOLUME_SIZE
VOLUME_SIZE=${VOLUME_SIZE:-100}

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Deployment Summary${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e "Stack Name:     ${GREEN}$STACK_NAME${NC}"
echo -e "Instance Type:  ${GREEN}$INSTANCE_TYPE${NC}"
echo -e "SSH Key:        ${GREEN}$KEY_NAME${NC}"
echo -e "Volume Size:    ${GREEN}${VOLUME_SIZE}GB${NC}"
echo -e "Region:         ${GREEN}$REGION${NC}"
echo ""
echo -e "${YELLOW}⚠️  This will incur AWS charges!${NC}"
echo -e "${YELLOW}⚠️  Estimated cost: ~\$4-6 per hour${NC}"
echo ""
read -p "Continue with deployment? [y/N]: " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Deploying CloudFormation stack...${NC}"

aws cloudformation create-stack \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --template-body file://$TEMPLATE_FILE \
    --parameters \
        ParameterKey=KeyName,ParameterValue=$KEY_NAME \
        ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE \
        ParameterKey=VolumeSize,ParameterValue=$VOLUME_SIZE \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags \
        Key=Project,Value=Kepler-OSS-Korea-2025 \
        Key=ManagedBy,Value=CloudFormation

echo -e "${GREEN}✓ Stack creation initiated${NC}"
echo ""
echo -e "${BLUE}Waiting for stack to complete...${NC}"
echo -e "${YELLOW}This may take 5-10 minutes...${NC}"

aws cloudformation wait stack-create-complete \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}✓ Stack deployed successfully!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""

    # Get outputs
    PUBLIC_IP=$(aws cloudformation describe-stacks \
        --profile $PROFILE \
        --region $REGION \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
        --output text)

    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --profile $PROFILE \
        --region $REGION \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text)

    echo -e "${BLUE}Instance Details:${NC}"
    echo -e "Instance ID:  ${GREEN}$INSTANCE_ID${NC}"
    echo -e "Public IP:    ${GREEN}$PUBLIC_IP${NC}"
    echo ""
    echo -e "${BLUE}SSH Command:${NC}"
    echo -e "${GREEN}ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@${PUBLIC_IP}${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Wait 2-3 minutes for instance initialization"
    echo "2. SSH into the instance using the command above"
    echo "3. Check setup progress: tail -f /var/log/user-data.log"
    echo "4. Run: ./setup-kepler.sh"
    echo "5. Read README.md for more details"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to stop/terminate when done to save credits!${NC}"
    echo -e "${YELLOW}⚠️  Use ./stop-stack.sh to stop or ./delete-stack.sh to delete${NC}"
else
    echo -e "${RED}Stack creation failed${NC}"
    echo "Check AWS Console for details"
    exit 1
fi
