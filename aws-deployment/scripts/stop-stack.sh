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
echo -e "${BLUE}Stop Kepler Bare-Metal Instance${NC}"
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

if [ "$CURRENT_STATE" == "stopped" ]; then
    echo -e "${YELLOW}Instance is already stopped${NC}"
    exit 0
fi

if [ "$CURRENT_STATE" != "running" ]; then
    echo -e "${YELLOW}Instance is in '$CURRENT_STATE' state, cannot stop${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  This will stop the instance (you'll only pay for EBS storage)${NC}"
read -p "Continue? [y/N]: " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo -e "${RED}Cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Stopping instance...${NC}"

aws ec2 stop-instances \
    --profile $PROFILE \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --output json > /dev/null

echo -e "${GREEN}✓ Stop command sent${NC}"
echo ""
echo -e "${BLUE}Waiting for instance to stop...${NC}"

aws ec2 wait instance-stopped \
    --profile $PROFILE \
    --region $REGION \
    --instance-ids $INSTANCE_ID

echo -e "${GREEN}✓ Instance stopped successfully${NC}"
echo ""
echo -e "${YELLOW}To restart: ./start-stack.sh${NC}"
echo -e "${YELLOW}To delete completely: ./delete-stack.sh${NC}"
