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

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Start Kepler Bare-Metal Instance${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Get instance ID from stack
INSTANCE_ID=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}Error: Stack '$STACK_NAME' not found${NC}"
    exit 1
fi

# Get current state
CURRENT_STATE=$(aws ec2 describe-instances \
    --profile $PROFILE \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

echo -e "Instance ID:     ${GREEN}$INSTANCE_ID${NC}"
echo -e "Current State:   ${YELLOW}$CURRENT_STATE${NC}"
echo ""

if [ "$CURRENT_STATE" == "running" ]; then
    echo -e "${GREEN}Instance is already running${NC}"

    PUBLIC_IP=$(aws cloudformation describe-stacks \
        --profile $PROFILE \
        --region $REGION \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
        --output text)

    echo ""
    echo -e "${BLUE}SSH Command:${NC}"
    echo -e "${GREEN}ssh -i ~/.ssh/*.pem ubuntu@${PUBLIC_IP}${NC}"
    exit 0
fi

if [ "$CURRENT_STATE" != "stopped" ]; then
    echo -e "${YELLOW}Instance is in '$CURRENT_STATE' state, cannot start${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  This will start the instance and resume billing${NC}"
read -p "Continue? [y/N]: " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo -e "${RED}Cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting instance...${NC}"

aws ec2 start-instances \
    --profile $PROFILE \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --output json > /dev/null

echo -e "${GREEN}✓ Start command sent${NC}"
echo ""
echo -e "${BLUE}Waiting for instance to start...${NC}"

aws ec2 wait instance-running \
    --profile $PROFILE \
    --region $REGION \
    --instance-ids $INSTANCE_ID

echo -e "${GREEN}✓ Instance started successfully${NC}"
echo ""

# Get Public IP
PUBLIC_IP=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
    --output text)

echo -e "${BLUE}Instance Details:${NC}"
echo -e "Instance ID:  ${GREEN}$INSTANCE_ID${NC}"
echo -e "Public IP:    ${GREEN}$PUBLIC_IP${NC}"
echo ""
echo -e "${BLUE}SSH Command:${NC}"
echo -e "${GREEN}ssh -i ~/.ssh/*.pem ubuntu@${PUBLIC_IP}${NC}"
echo ""
echo -e "${YELLOW}⚠️  Billing has resumed! Remember to stop when done.${NC}"
