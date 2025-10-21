#!/bin/bash
set -e

# ============================================================================
# Region Migration Script for Kepler K3s Deployment
# ============================================================================
# Use this script to deploy in a different region due to capacity issues
#
# Usage:
#   ./migrate-to-new-region.sh us-west-2
#   ./migrate-to-new-region.sh ap-northeast-1
#
# Recommended regions:
#   - us-west-2 (Oregon) - Best for US demos
#   - us-east-2 (Ohio) - Close to us-east-1
#   - ap-northeast-1 (Tokyo) - Best for Asia/Korea demos
#   - eu-west-1 (Ireland) - Best for Europe
# ============================================================================

# Check if region argument provided
if [ -z "$1" ]; then
    echo "Usage: $0 <region>"
    echo ""
    echo "Recommended regions:"
    echo "  us-west-2        (Oregon - best US availability)"
    echo "  us-east-2        (Ohio - close to us-east-1)"
    echo "  ap-northeast-1   (Tokyo - close to Korea for OSS Korea demo)"
    echo "  eu-west-1        (Ireland)"
    echo ""
    echo "Example:"
    echo "  $0 us-west-2"
    exit 1
fi

# Configuration
export TARGET_REGION="$1"
export AWS_PROFILE="mgonzalezo"
export STACK_NAME="kepler-k3s-automated"
export KEY_NAME="oss-korea"

echo "=========================================="
echo "Kepler K3s Region Migration"
echo "=========================================="
echo "Target Region: $TARGET_REGION"
echo "AWS Profile: $AWS_PROFILE"
echo "Stack Name: $STACK_NAME"
echo "=========================================="
echo ""

# Step 1: Check c5.metal availability in target region
echo "Step 1/8: Checking c5.metal availability in $TARGET_REGION..."
AVAILABLE_AZS=$(aws ec2 describe-instance-type-offerings \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --location-type availability-zone \
  --filters Name=instance-type,Values=c5.metal \
  --query 'InstanceTypeOfferings[*].Location' \
  --output text)

if [ -z "$AVAILABLE_AZS" ]; then
    echo "❌ ERROR: c5.metal not available in $TARGET_REGION"
    echo ""
    echo "Try these alternatives:"
    echo "  1. Different region"
    echo "  2. Different instance type (m5.metal, r5.metal)"
    echo ""
    exit 1
fi

echo "✅ c5.metal available in: $AVAILABLE_AZS"
echo ""

# Step 2: Get or create VPC
echo "Step 2/8: Getting VPC in $TARGET_REGION..."
VPC_ID=$(aws ec2 describe-vpcs \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text 2>/dev/null || echo "None")

if [ "$VPC_ID" = "None" ]; then
    echo "No default VPC found. Creating one..."
    aws ec2 create-default-vpc \
      --profile $AWS_PROFILE \
      --region $TARGET_REGION

    VPC_ID=$(aws ec2 describe-vpcs \
      --profile $AWS_PROFILE \
      --region $TARGET_REGION \
      --filters "Name=isDefault,Values=true" \
      --query 'Vpcs[0].VpcId' \
      --output text)
fi

echo "✅ Using VPC: $VPC_ID"
echo ""

# Step 3: Check/import SSH key
echo "Step 3/8: Checking SSH key pair in $TARGET_REGION..."
if aws ec2 describe-key-pairs \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --key-names $KEY_NAME &>/dev/null; then
    echo "✅ Key pair '$KEY_NAME' already exists in $TARGET_REGION"
else
    echo "Key pair not found. Importing..."

    # Check if private key exists
    if [ ! -f "../oss-korea.pem" ]; then
        echo "❌ ERROR: oss-korea.pem not found in parent directory"
        echo "Please ensure oss-korea.pem is in the project root"
        exit 1
    fi

    # Generate public key
    ssh-keygen -y -f ../oss-korea.pem > /tmp/oss-korea.pub

    # Import to new region
    aws ec2 import-key-pair \
      --profile $AWS_PROFILE \
      --region $TARGET_REGION \
      --key-name $KEY_NAME \
      --public-key-material fileb:///tmp/oss-korea.pub

    rm /tmp/oss-korea.pub
    echo "✅ Key pair imported successfully"
fi
echo ""

# Step 4: Create CloudFormation stack
echo "Step 4/8: Creating CloudFormation stack..."
echo "This will take 10-15 minutes..."
echo ""

aws cloudformation create-stack \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --stack-name $STACK_NAME \
  --template-body file://templates/kepler-k3s-automated-stack.yaml \
  --parameters \
    ParameterKey=InstanceType,ParameterValue=c5.metal \
    ParameterKey=KeyName,ParameterValue=$KEY_NAME \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=SSHLocation,ParameterValue=0.0.0.0/0 \
    ParameterKey=VolumeSize,ParameterValue=100 \
    ParameterKey=AutoInstallKepler,ParameterValue=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags \
    Key=Project,Value=Kepler-OSS-Korea-2025 \
    Key=Environment,Value=Demo \
    Key=Region,Value=$TARGET_REGION

echo "✅ Stack creation initiated"
echo ""

# Step 5: Wait for stack creation
echo "Step 5/8: Waiting for stack creation to complete..."
echo "(This typically takes 10-15 minutes - grab a coffee! ☕)"
echo ""

if ! aws cloudformation wait stack-create-complete \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --stack-name $STACK_NAME; then

    echo "❌ Stack creation failed!"
    echo ""
    echo "Checking errors..."
    aws cloudformation describe-stack-events \
      --profile $AWS_PROFILE \
      --region $TARGET_REGION \
      --stack-name $STACK_NAME \
      --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
      --output table
    exit 1
fi

echo "✅ Stack created successfully!"
echo ""

# Step 6: Get outputs
echo "Step 6/8: Retrieving instance information..."

INSTANCE_ID=$(aws cloudformation describe-stacks \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text)

INSTANCE_IP=$(aws cloudformation describe-stacks \
  --profile $AWS_PROFILE \
  --region $TARGET_REGION \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
  --output text)

echo "✅ Instance ID: $INSTANCE_ID"
echo "✅ Public IP: $INSTANCE_IP"
echo ""

# Step 7: Save configuration
echo "Step 7/8: Saving configuration..."

cat > k3s-instance-info.txt << EOF
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$INSTANCE_IP
REGION=$TARGET_REGION
PROFILE=$AWS_PROFILE
STACK_NAME=$STACK_NAME
EOF

echo "✅ Configuration saved to k3s-instance-info.txt"
echo ""

# Step 8: Update scripts
echo "Step 8/8: Updating start/stop scripts with new region..."

# Backup original scripts
cp scripts/start-instance.sh scripts/start-instance.sh.backup
cp scripts/stop-instance.sh scripts/stop-instance.sh.backup

# Update region in scripts
sed -i.tmp "s/REGION=.*/REGION=\"$TARGET_REGION\"/" scripts/start-instance.sh
sed -i.tmp "s/REGION=.*/REGION=\"$TARGET_REGION\"/" scripts/stop-instance.sh

rm -f scripts/*.tmp

echo "✅ Scripts updated (backups saved with .backup extension)"
echo ""

# Final summary
echo "=========================================="
echo "✅ MIGRATION COMPLETE!"
echo "=========================================="
echo ""
echo "Instance Details:"
echo "  Region:      $TARGET_REGION"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP:   $INSTANCE_IP"
echo ""
echo "Next Steps:"
echo ""
echo "1. Wait 2-3 minutes for instance to fully boot"
echo ""
echo "2. Test SSH connection:"
echo "   ssh -i ../oss-korea.pem ubuntu@$INSTANCE_IP"
echo ""
echo "3. Verify Kepler installation:"
echo "   ssh -i ../oss-korea.pem ubuntu@$INSTANCE_IP \"sudo kubectl get pods -A\""
echo ""
echo "4. Deploy Carbon-Kepler MCP server:"
echo "   rsync -avz -e \"ssh -i ../oss-korea.pem\" ../carbon-kepler-mcp/ ubuntu@$INSTANCE_IP:~/carbon-kepler-mcp/"
echo "   ssh -i ../oss-korea.pem ubuntu@$INSTANCE_IP"
echo "   cd carbon-kepler-mcp && sudo docker build -t carbon-kepler-mcp:latest ."
echo "   sudo kubectl apply -f k8s/"
echo ""
echo "5. Update Claude Desktop config:"
echo "   Edit ~/.config/Claude/claude_desktop_config.json"
echo "   Change URL to: http://$INSTANCE_IP:8000/sse"
echo ""
echo "6. Update demo documentation:"
echo "   Find and replace old IP with: $INSTANCE_IP"
echo ""
echo "Configuration saved to: k3s-instance-info.txt"
echo "Original scripts backed up with .backup extension"
echo ""
echo "=========================================="
