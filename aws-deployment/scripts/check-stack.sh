#!/bin/bash

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
echo -e "${BLUE}Kepler Stack Status${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if stack exists
STACK_STATUS=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null)

if [ -z "$STACK_STATUS" ]; then
    echo -e "${YELLOW}Stack '$STACK_NAME' not found${NC}"
    echo ""
    echo -e "${BLUE}To create the stack, run:${NC}"
    echo -e "${GREEN}./deploy-stack.sh${NC}"
    exit 0
fi

echo -e "Stack Status:    ${GREEN}$STACK_STATUS${NC}"

# Get instance details
INSTANCE_ID=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
    --output text 2>/dev/null)

PUBLIC_IP=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
    --output text 2>/dev/null)

INSTANCE_TYPE=$(aws cloudformation describe-stacks \
    --profile $PROFILE \
    --region $REGION \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`InstanceType`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$INSTANCE_ID" ]; then
    INSTANCE_STATE=$(aws ec2 describe-instances \
        --profile $PROFILE \
        --region $REGION \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)

    echo -e "Instance ID:     ${GREEN}$INSTANCE_ID${NC}"
    echo -e "Instance Type:   ${GREEN}$INSTANCE_TYPE${NC}"
    echo -e "Instance State:  ${YELLOW}$INSTANCE_STATE${NC}"
    echo -e "Public IP:       ${GREEN}$PUBLIC_IP${NC}"

    # Calculate uptime
    LAUNCH_TIME=$(aws ec2 describe-instances \
        --profile $PROFILE \
        --region $REGION \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].LaunchTime' \
        --output text)

    if [ -n "$LAUNCH_TIME" ]; then
        echo -e "Launch Time:     ${GREEN}$LAUNCH_TIME${NC}"
    fi

    echo ""
    echo -e "${BLUE}=========================================${NC}"

    if [ "$INSTANCE_STATE" == "running" ]; then
        echo -e "${GREEN}✓ Instance is RUNNING${NC}"
        echo ""
        echo -e "${BLUE}SSH Command:${NC}"
        echo -e "${GREEN}ssh -i ~/.ssh/*.pem ubuntu@${PUBLIC_IP}${NC}"
        echo ""
        echo -e "${BLUE}Available Actions:${NC}"
        echo "  ./stop-stack.sh  - Stop instance (save costs)"
        echo "  ./delete-stack.sh - Delete everything"

        # Estimate costs
        case $INSTANCE_TYPE in
            c5.metal) HOURLY_COST="4.08" ;;
            m5.metal) HOURLY_COST="4.61" ;;
            m5d.metal) HOURLY_COST="5.42" ;;
            r5.metal) HOURLY_COST="6.05" ;;
            *) HOURLY_COST="4-6" ;;
        esac

        echo ""
        echo -e "${YELLOW}💰 Cost Information:${NC}"
        echo -e "   Hourly Rate: ~\$${HOURLY_COST}/hour"

        if [ -n "$LAUNCH_TIME" ]; then
            LAUNCH_EPOCH=$(date -d "$LAUNCH_TIME" +%s)
            NOW_EPOCH=$(date +%s)
            UPTIME_HOURS=$(( (NOW_EPOCH - LAUNCH_EPOCH) / 3600 ))
            UPTIME_MINS=$(( ((NOW_EPOCH - LAUNCH_EPOCH) % 3600) / 60 ))

            if [ "$HOURLY_COST" != "4-6" ]; then
                TOTAL_COST=$(echo "$UPTIME_HOURS + ($UPTIME_MINS / 60)" | bc -l | xargs printf "%.2f" | xargs -I {} echo "{} * $HOURLY_COST" | bc -l | xargs printf "%.2f")
                echo -e "   Uptime: ${UPTIME_HOURS}h ${UPTIME_MINS}m"
                echo -e "   Estimated Cost So Far: ~\$${TOTAL_COST}"
            fi
        fi

    elif [ "$INSTANCE_STATE" == "stopped" ]; then
        echo -e "${YELLOW}⚠️  Instance is STOPPED${NC}"
        echo ""
        echo -e "${BLUE}Available Actions:${NC}"
        echo "  ./start-stack.sh - Start instance"
        echo "  ./delete-stack.sh - Delete everything"

    else
        echo -e "${YELLOW}Instance is in state: $INSTANCE_STATE${NC}"
    fi
fi

echo ""
