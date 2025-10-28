#!/bin/bash
#
# Start the Kepler K3s EC2 instance
#
# Usage: ./start-instance.sh
#

set -e

STACK_NAME="kepler-k3s-rapl"
PROFILE="${AWS_PROFILE:-default}"
REGION="ap-northeast-1"

echo "=================================================="
echo "Start Kepler K3s Instance"
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

if [ "$CURRENT_STATE" == "running" ]; then
  echo "Instance is already running"

  # Get and display IP
  PUBLIC_IP=$(aws ec2 describe-instances \
    --profile "$PROFILE" \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

  echo ""
  echo "Public IP: $PUBLIC_IP"
  echo ""
  echo "SSH command:"
  echo "   ssh -i oss-korea-ap.pem ubuntu@$PUBLIC_IP"
  exit 0
fi

if [ "$CURRENT_STATE" == "pending" ]; then
  echo "Instance is already starting"
else
  # Start the instance
  echo ""
  echo "Starting instance..."
  aws ec2 start-instances \
    --profile "$PROFILE" \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --output table

  echo ""
  echo "Start command sent successfully"
fi

echo ""
echo "Waiting for instance to start (this may take 1-2 minutes)..."

# Wait for instance to be running
aws ec2 wait instance-running \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID"

# Get new public IP (changes after stop/start)
PUBLIC_IP=$(aws ec2 describe-instances \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

# Update k3s-instance-info.txt if it exists
if [ -f "k3s-instance-info.txt" ]; then
  echo "Updating k3s-instance-info.txt with new IP..."
  sed -i.bak "s/Public IP:.*/Public IP:     $PUBLIC_IP/" k3s-instance-info.txt
fi

echo ""
echo "=================================================="
echo "Instance started successfully"
echo "=================================================="
echo ""
echo "New Public IP: $PUBLIC_IP"
echo ""
echo "IMPORTANT: Wait ~3 minutes for K3s to fully start"
echo ""
echo "SSH command:"
echo "   ssh -i oss-korea-ap.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Check K3s status:"
echo "   ssh -i oss-korea-ap.pem ubuntu@$PUBLIC_IP 'sudo kubectl get pods -A'"
echo ""
echo "Remember to stop the instance when done to save costs"
echo "   ./scripts/stop-instance.sh"
echo ""
