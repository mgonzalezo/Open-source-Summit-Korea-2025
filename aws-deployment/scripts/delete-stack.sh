#!/bin/bash
set -e

# Configuration
STACK_NAME="kepler-baremetal-stack"
REGION="us-east-1"
PROFILE="${AWS_PROFILE:-default}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}=========================================${NC}"
echo -e "${RED}Delete Kepler Bare-Metal Stack${NC}"
echo -e "${RED}=========================================${NC}"
echo ""

# Check if stack exists
aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME &>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Stack '$STACK_NAME' not found${NC}"
    exit 0
fi

# Get stack details
INSTANCE_ID=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
    --output text 2>/dev/null)

echo -e "${YELLOW}⚠️  WARNING: This will permanently delete:${NC}"
echo "  - EC2 Instance ($INSTANCE_ID)"
echo "  - EBS Volumes"
echo "  - Elastic IP"
echo "  - Security Group"
echo "  - IAM Role and Instance Profile"
echo ""
echo -e "${RED}⚠️  This action CANNOT be undone!${NC}"
echo ""
read -p "Type 'delete' to confirm: " CONFIRM

if [ "$CONFIRM" != "delete" ]; then
    echo -e "${GREEN}Cancelled - nothing was deleted${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Deleting CloudFormation stack...${NC}"

aws cloudformation delete-stack \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME

echo -e "${GREEN}✓ Deletion initiated${NC}"
echo ""
echo -e "${BLUE}Waiting for stack deletion to complete...${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}"

aws cloudformation wait stack-delete-complete \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}✓ Stack deleted successfully!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo -e "${GREEN}All resources have been removed${NC}"
else
    echo -e "${RED}Stack deletion failed${NC}"
    echo "Check AWS Console for details"
    exit 1
fi
