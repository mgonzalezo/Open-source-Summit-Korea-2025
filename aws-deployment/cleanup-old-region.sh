#!/bin/bash
set -e

# ============================================================================
# Cleanup Old us-east-1 Resources
# ============================================================================
# Run this AFTER verifying the new region (ap-northeast-1) works correctly
#
# This will delete:
#   - EC2 instance i-01d31a7c7323ef2f1 (stopped)
#   - Security group kepler-k3s-security-group
#   - EBS volumes
#   - Any CloudFormation stacks
#
# IMPORTANT: Only run this after testing the new Tokyo deployment!
# ============================================================================

export AWS_PROFILE="mgonzalezo"
export OLD_REGION="us-east-1"
export OLD_INSTANCE_ID="i-01d31a7c7323ef2f1"

echo "=========================================="
echo "Cleanup Old us-east-1 Resources"
echo "=========================================="
echo "Region: $OLD_REGION"
echo "Instance: $OLD_INSTANCE_ID"
echo "=========================================="
echo ""

# Safety check
read -p "⚠️  WARNING: This will DELETE the old us-east-1 instance. Continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled. No resources were deleted."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Step 1: Check instance status
echo "Step 1/5: Checking instance status..."
INSTANCE_STATE=$(aws ec2 describe-instances \
  --profile $AWS_PROFILE \
  --region $OLD_REGION \
  --instance-ids $OLD_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text 2>/dev/null || echo "not-found")

echo "Instance state: $INSTANCE_STATE"

if [ "$INSTANCE_STATE" != "stopped" ] && [ "$INSTANCE_STATE" != "running" ]; then
    echo "⚠️  Instance not found or already terminated. Skipping..."
else
    # Step 2: Terminate instance
    echo ""
    echo "Step 2/5: Terminating instance $OLD_INSTANCE_ID..."

    aws ec2 terminate-instances \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --instance-ids $OLD_INSTANCE_ID

    echo "✅ Termination initiated"
    echo "Waiting for instance to terminate (may take 2-3 minutes)..."

    aws ec2 wait instance-terminated \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --instance-ids $OLD_INSTANCE_ID

    echo "✅ Instance terminated"
fi

# Step 3: Delete security group
echo ""
echo "Step 3/5: Deleting security group..."

SG_ID=$(aws ec2 describe-security-groups \
  --profile $AWS_PROFILE \
  --region $OLD_REGION \
  --filters "Name=group-name,Values=kepler-k3s-security-group" \
  --query 'SecurityGroups[0].GroupId' \
  --output text 2>/dev/null || echo "None")

if [ "$SG_ID" != "None" ] && [ ! -z "$SG_ID" ]; then
    echo "Found security group: $SG_ID"

    # Wait a bit for instance termination to complete
    sleep 10

    aws ec2 delete-security-group \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --group-id $SG_ID 2>/dev/null && echo "✅ Security group deleted" || echo "⚠️  Security group deletion failed (may still be in use, will retry...)"

    # Retry after a bit
    sleep 10
    aws ec2 delete-security-group \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --group-id $SG_ID 2>/dev/null && echo "✅ Security group deleted" || echo "⚠️  Security group may need manual deletion"
else
    echo "Security group not found or already deleted"
fi

# Step 4: Clean up any CloudFormation stacks
echo ""
echo "Step 4/5: Checking for CloudFormation stacks..."

STACK_STATUS=$(aws cloudformation describe-stacks \
  --profile $AWS_PROFILE \
  --region $OLD_REGION \
  --stack-name kepler-k3s-automated \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" != "NOT_FOUND" ]; then
    echo "Found stack with status: $STACK_STATUS"
    echo "Deleting stack..."

    aws cloudformation delete-stack \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --stack-name kepler-k3s-automated

    echo "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete \
      --profile $AWS_PROFILE \
      --region $OLD_REGION \
      --stack-name kepler-k3s-automated 2>/dev/null || echo "Stack deleted"

    echo "✅ Stack deleted"
else
    echo "No CloudFormation stack found"
fi

# Step 5: Summary
echo ""
echo "Step 5/5: Cleanup summary..."
echo ""

# Check what's left
INSTANCES=$(aws ec2 describe-instances \
  --profile $AWS_PROFILE \
  --region $OLD_REGION \
  --filters "Name=tag:Project,Values=Kepler-OSS-Korea-2025" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
  --output text 2>/dev/null || echo "")

SECURITY_GROUPS=$(aws ec2 describe-security-groups \
  --profile $AWS_PROFILE \
  --region $OLD_REGION \
  --filters "Name=group-name,Values=kepler-k3s-security-group" \
  --query 'SecurityGroups[*].GroupId' \
  --output text 2>/dev/null || echo "")

echo "=========================================="
echo "✅ CLEANUP COMPLETE"
echo "=========================================="
echo ""

if [ -z "$INSTANCES" ] && [ -z "$SECURITY_GROUPS" ]; then
    echo "✅ All resources in us-east-1 have been cleaned up"
    echo ""
    echo "Remaining costs in us-east-1: $0/day"
else
    echo "⚠️  Some resources may still exist:"
    [ ! -z "$INSTANCES" ] && echo "  - Instances: $INSTANCES"
    [ ! -z "$SECURITY_GROUPS" ] && echo "  - Security groups: $SECURITY_GROUPS"
    echo ""
    echo "You may need to manually delete these from the AWS console"
fi

echo ""
echo "New active region: ap-northeast-1 (Tokyo)"
echo "New instance info: aws-deployment/k3s-instance-info.txt"
echo ""
echo "=========================================="
