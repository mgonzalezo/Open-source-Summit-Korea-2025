# AWS Bare-Metal Deployment for Kepler

Deploy Kepler on AWS bare-metal EC2 instances with automated CloudFormation templates. This setup provides real hardware power monitoring (RAPL) for accurate energy metrics.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Managing Your Stack](#managing-your-stack)
- [Cost Management](#cost-management)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This deployment creates:
- **Bare-metal EC2 instance** (c5.metal, m5.metal, etc.) with RAPL support
- **Security Group** configured for Kubernetes and Kepler access
- **Elastic IP** for consistent SSH access
- **IAM Role** with CloudWatch and SSM permissions
- **Automated setup** with Docker, Kind, kubectl, Helm, and cert-manager
- **Pre-configured scripts** for Kepler Operator installation

### Architecture

```
┌─────────────────────────────────────────────────┐
│           AWS CloudFormation Stack              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │   EC2 Bare-Metal Instance (c5.metal)    │   │
│  │   ┌─────────────────────────────────┐   │   │
│  │   │  Kind Kubernetes Cluster        │   │   │
│  │   │  ┌──────────────────────────┐   │   │   │
│  │   │  │  cert-manager            │   │   │   │
│  │   │  ├──────────────────────────┤   │   │   │
│  │   │  │  Kepler Operator         │   │   │   │
│  │   │  │  (Energy Monitoring)     │   │   │   │
│  │   │  └──────────────────────────┘   │   │   │
│  │   └─────────────────────────────────┘   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Security Group │ Elastic IP │ IAM Role        │
└─────────────────────────────────────────────────┘
```

## 🚀 Prerequisites

### 1. AWS Account Requirements

- **Active AWS Account** with billing enabled
- **AWS Credits**: ~$344 USD (provides ~84 hours of c5.metal usage)
- **vCPU Quota**: Minimum 96 vCPUs for Standard instances
  - Check current limit: `aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A`
  - Request increase if needed (see [Requesting vCPU Increase](#requesting-vcpu-increase))

### 2. AWS CLI Configuration

```bash
# Install AWS CLI (if not already installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS profile
aws configure --profile YOUR_PROFILE_NAME
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

### 3. SSH Key Pair

Create an SSH key pair in AWS:

```bash
# Create a new key pair
aws ec2 create-key-pair \
  --key-name oss-korea \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/oss-korea.pem

# Set proper permissions
chmod 400 ~/.ssh/oss-korea.pem
```

### 4. Requesting vCPU Increase

If you encounter quota limits, request an increase:

**Option A: AWS Console**
1. Go to [AWS Service Quotas Console](https://console.aws.amazon.com/servicequotas/)
2. Select "Amazon Elastic Compute Cloud (Amazon EC2)"
3. Search for "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances"
4. Click "Request quota increase"
5. Request **96 vCPUs** (or 128 for flexibility)
6. Processing time: Usually instant to 2 business days

**Option B: AWS CLI**
```bash
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --desired-value 96 \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME
```

## 🚀 Quick Start

### 1. Deploy the Stack

```bash
cd aws-deployment/scripts
./deploy-stack.sh
```

The script will:
- Check for SSH keys
- Let you select instance type (c5.metal recommended)
- Configure volume size
- Deploy the CloudFormation stack
- Wait for completion (~5-10 minutes)
- Display connection details

### 2. Connect to Instance

```bash
# Use the SSH command provided by deploy-stack.sh
ssh -i ~/.ssh/oss-korea.pem ubuntu@<PUBLIC_IP>
```

### 3. Setup Kepler

Once connected to the EC2 instance:

```bash
# Check that initial setup is complete
tail -f /var/log/user-data.log

# When ready, run the Kepler setup script
./setup-kepler.sh
```

This will:
- Create Kind cluster with proper host mounts
- Install cert-manager v1.18.2
- Install Kepler Operator via Helm
- Verify all components are running

**Setup time:** ~3-5 minutes

### 4. Verify Installation

```bash
# Check all pods are running
kubectl get pods -A

# Access Kepler metrics
kubectl port-forward -n kepler-operator svc/kepler-operator 28282:28282 &
curl http://localhost:28282/metrics | grep kepler
```

## 📁 Deployment Options

### Instance Types

| Instance Type | vCPUs | RAM    | Hourly Cost* | Hours with $344 |
|---------------|-------|--------|--------------|-----------------|
| **c5.metal**  | 96    | 192 GB | ~$4.08       | ~84 hours       |
| m5.metal      | 96    | 384 GB | ~$4.61       | ~74 hours       |
| m5d.metal     | 96    | 384 GB | ~$5.42       | ~63 hours       |
| r5.metal      | 96    | 768 GB | ~$6.05       | ~57 hours       |

*Prices for us-east-1 region

**Recommendation:** Use **c5.metal** for best cost/performance ratio.

### Configuration Parameters

Edit `scripts/deploy-stack.sh` or pass parameters:

```bash
# Custom deployment
INSTANCE_TYPE="m5.metal" \
VOLUME_SIZE="200" \
KEY_NAME="your-key" \
./deploy-stack.sh
```

## 🛠 Managing Your Stack

### Check Stack Status

```bash
./check-stack.sh
```

Shows:
- Stack status
- Instance state (running/stopped)
- Public IP address
- Uptime and cost estimates
- Available management actions

### Stop Instance (Save Costs)

```bash
./stop-stack.sh
```

- Stops the EC2 instance
- **Saves ~$4-6/hour**
- Only pay for EBS storage (~$10/month for 100GB)
- Can be restarted anytime
- **Elastic IP preserved**

### Start Instance

```bash
./start-stack.sh
```

- Restarts a stopped instance
- Resumes hourly billing
- Same IP address and configuration

### Delete Stack (Complete Cleanup)

```bash
./delete-stack.sh
```

⚠️ **WARNING:** This permanently deletes:
- EC2 Instance
- EBS Volumes
- Elastic IP
- Security Group
- IAM Roles

Requires typing "delete" to confirm.

## 💰 Cost Management

### Hourly Costs

**When Running:**
- Instance: $4-6/hour
- EBS: Included
- Elastic IP: Free (while attached)
- Data transfer: Minimal

**When Stopped:**
- Instance: $0
- EBS: ~$10/month for 100GB
- Elastic IP: Free (while attached)

### Budget Tracking

```bash
# Check current costs
./check-stack.sh

# View AWS billing
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity DAILY \
  --metrics BlendedCost \
  --profile YOUR_PROFILE_NAME
```

### Cost-Saving Best Practices

1. **Stop when not using:**
   ```bash
   ./stop-stack.sh  # Saves $4-6/hour
   ```

2. **Monitor regularly:**
   ```bash
   ./check-stack.sh  # Shows uptime and costs
   ```

3. **Set billing alarms** (AWS Console → CloudWatch → Alarms)

4. **Delete after presentation:**
   ```bash
   ./delete-stack.sh  # Complete cleanup
   ```

## 📂 Folder Structure

```
aws-deployment/
├── README.md                          # This file
├── scripts/
│   ├── deploy-stack.sh               # Deploy CloudFormation stack
│   ├── check-stack.sh                # Check status and costs
│   ├── start-stack.sh                # Start stopped instance
│   ├── stop-stack.sh                 # Stop running instance
│   └── delete-stack.sh               # Delete entire stack
├── templates/
│   └── kepler-baremetal-stack.yaml   # CloudFormation template
└── docs/
    └── CLOUDFORMATION-README.md      # Detailed documentation
```

## 🔧 Troubleshooting

### Common Issues

#### 1. vCPU Quota Exceeded

**Error:** `You have requested more vCPU capacity than your current vCPU limit`

**Solution:**
```bash
# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --desired-value 96 \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME
```

Processing time: Usually instant to 2 business days.

#### 2. Stack Creation Failed

**Check events:**
```bash
aws cloudformation describe-stack-events \
  --stack-name kepler-baremetal-stack \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME \
  --max-items 20
```

**Common causes:**
- Missing SSH key
- Insufficient vCPU quota
- VPC configuration issues

#### 3. Cannot SSH to Instance

**Verify:**
```bash
# Check instance state
./check-stack.sh

# Verify security group
aws ec2 describe-security-groups \
  --group-names kepler-kind-security-group \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME

# Check key permissions
chmod 400 ~/.ssh/oss-korea.pem
```

#### 4. Kepler Setup Fails

**Check logs:**
```bash
# On EC2 instance
tail -f /var/log/user-data.log

# Check Kind cluster
kind get clusters
kubectl get nodes

# Check cert-manager
kubectl get pods -n cert-manager
```

### Getting Help

1. **Check logs:** `/var/log/user-data.log` on EC2 instance
2. **Review CloudFormation events:** AWS Console → CloudFormation → Events
3. **Kepler documentation:** https://sustainable-computing.io/
4. **AWS Support:** https://console.aws.amazon.com/support

## 📊 What Gets Installed

### On EC2 Instance (via user-data)

- **Docker** - Container runtime
- **kubectl** - Kubernetes CLI
- **Helm 3** - Package manager
- **Kind** - Kubernetes in Docker
- **Additional tools** - jq, git, make

### Helper Scripts on Instance

- `setup-kepler.sh` - Creates Kind cluster and installs Kepler
- `cleanup-cluster.sh` - Deletes Kind cluster
- `README.md` - Quick reference guide
- `.bash_aliases` - Helpful aliases (k, kgp, kgn)

### Kubernetes Components

- **cert-manager v1.18.2** - Certificate management
- **Kepler Operator** - Energy monitoring
- **Kind cluster** - Single control-plane node

## 🎯 Use Cases

### For Presentations/Demos
1. Deploy stack before presentation
2. Stop instance when practicing
3. Start for live demo
4. Delete after event

### For Development
1. Deploy stack
2. Develop/test Kepler configurations
3. Stop overnight
4. Resume next day

### For Testing
1. Deploy with different configurations
2. Collect real RAPL metrics
3. Compare with estimated metrics
4. Document findings

## 📚 Additional Resources

### Kepler
- [Official Documentation](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [CNCF Project Page](https://landscape.cncf.io/project=kepler)

### AWS
- [CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [EC2 Instance Types](https://aws.amazon.com/ec2/instance-types/)
- [Service Quotas](https://docs.aws.amazon.com/servicequotas/)

### Kind
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Quick Start Guide](https://kind.sigs.k8s.io/docs/user/quick-start/)

## ⚠️ Important Notes

1. **Always stop or delete** when done to avoid unexpected charges
2. **Monitor costs regularly** using `./check-stack.sh`
3. **Budget ~$4-6/hour** for running instances
4. **Set billing alarms** in AWS Console
5. **Keep SSH key safe** - stored in `~/.ssh/`
6. **vCPU quota** must be at least 96 for c5.metal

## 🔐 Security Considerations

- **SSH access** restricted to specified CIDR (default: 0.0.0.0/0 - **change in production!**)
- **IAM role** has minimal required permissions
- **Security group** allows only necessary ports
- **EBS encryption** enabled by default
- **SSH key** required for access

**For production:** Restrict SSH access to specific IP addresses in the CloudFormation template.

## 📝 Example Workflow

```bash
# Day 1: Deploy and setup
cd aws-deployment/scripts
./deploy-stack.sh
# ... SSH and run ./setup-kepler.sh ...
./stop-stack.sh

# Day 2: Resume work
./check-stack.sh
./start-stack.sh
# ... work on demo ...
./stop-stack.sh

# Presentation day
./start-stack.sh
# ... give presentation ...
./stop-stack.sh

# After event: Cleanup
./delete-stack.sh
```

---

**Created for Open Source Summit Korea 2025**

**License:** Apache 2.0

**Maintained by:** Marco Gonzalez
