#!/bin/bash
#
# Stop the Kepler K3s EC2 instance to save costs
#
# Usage: ./stop-instance.sh
#

set -e

STACK_NAME="kepler-k3s-rapl"
PROFILE="${AWS_PROFILE:-default}"
REGION="ap-northeast-1"

echo "=================================================="
echo "Stop Kepler K3s Instance"
echo "=================================================="
echo ""

# Get instance ID from CloudFormation stack
echo "Getting instance ID from stack: $STACK_NAME"
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text)

if [ -z "$INSTANCE_ID" ]; then
  echo "ERROR: Could not find instance ID in stack outputs"
  exit 1
fi

echo "Instance ID: $INSTANCE_ID"
echo ""

# Check current state
echo "Checking current instance state..."
CURRENT_STATE=$(aws ec2 describe-instances \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

echo "   Current state: $CURRENT_STATE"

if [ "$CURRENT_STATE" == "stopped" ]; then
  echo "Instance is already stopped"
  exit 0
fi

if [ "$CURRENT_STATE" == "stopping" ]; then
  echo "Instance is already stopping"
  exit 0
fi

# Stop the instance
echo ""
echo "Stopping instance..."
aws ec2 stop-instances \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --output table

echo ""
echo "Stop command sent successfully"
echo ""
echo "Waiting for instance to stop (this may take 1-2 minutes)..."

# Wait for instance to stop
aws ec2 wait instance-stopped \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID"

echo ""
echo "=================================================="
echo "Instance stopped successfully"
echo "=================================================="
echo ""
echo "Cost Savings:"
echo "   - Running:  ~\$4.90/hour (\$117.50/day)"
echo "   - Stopped:  ~\$0.33/day (storage only)"
echo "   - Savings:  ~\$117/day when stopped"
echo ""
echo "To restart the instance, run:"
echo "   ./scripts/start-instance.sh"
echo ""
