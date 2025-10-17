# AWS Bare-Metal Deployment for Kepler

Deploy Kepler on AWS bare-metal EC2 instances with automated CloudFormation templates. This setup provides energy monitoring using ML-based power estimation for cloud environments where RAPL is not exposed.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Managing Your Stack](#managing-your-stack)
- [Cost Management](#cost-management)
- [Architecture](#architecture)
- [Documentation](#documentation)

## Overview

This deployment creates a fully automated Kepler environment that works around AWS bare-metal limitations:

### What Gets Deployed

- **Bare-metal EC2 instance** (c5.metal, m5.metal, etc.)
- **K3s cluster** - Lightweight Kubernetes distribution
- **Kepler v0.11.2** - Energy monitoring with eBPF metrics
- **Model Server** - ML-based power estimation for AWS environments
- **HTTPS/HTTP endpoints** - Secure metrics access
- **Security Group** - Configured for Kubernetes and Kepler access
- **Elastic IP** - Consistent SSH and API access
- **IAM Role** - CloudWatch and SSM permissions

### Key Features

- **Automated deployment** - Zero manual configuration
- **Real metrics collection** - eBPF-based CPU, memory, process tracking
- **ML power estimation** - When hardware RAPL unavailable
- **HTTPS access** - TLS-secured metrics endpoint
- **Cost efficient** - Stop/start capability

## Quick Start

### 1. Deploy Everything (Automated)

```bash
cd aws-deployment/scripts
scripts/create-stack.sh
```

**What happens:**
- CloudFormation stack creation (~5 minutes)
- K3s cluster installation (~3 minutes)
- Kepler + Model Server deployment (~7 minutes)
- HTTPS configuration (~2 minutes)

**Total time:** ~15-20 minutes

### 2. Access Metrics

```bash
# Get the IP from deployment output
curl -k https://<PUBLIC_IP>:30443/metrics | grep kepler_node_cpu
```

## Deployment Options

### Option 1: Fully Automated (Recommended)

```bash
scripts/create-stack.sh
```

**Includes:**
- K3s cluster
- Kepler v0.11.2
- Model Server
- HTTPS proxy
- All configurations

**Best for:** Quick testing and development

### Option 2: Manual Setup

```bash
# Deploy infrastructure only
scripts/create-stack.sh

# SSH and manually run
ssh -i oss-korea.pem ubuntu@<PUBLIC_IP>
scripts/setup-kepler-automated.sh
```

**Best for:** Development, customization

## Managing Your Stack

### Check Status
```bash
aws cloudformation describe-stacks --stack-name kepler-k3s-stack --profile mgonzalezo
```

### Stop Instance (Save Costs)
```bash
# Get instance ID from stack
INSTANCE_ID=$(aws cloudformation describe-stack-resources \
  --stack-name kepler-k3s-stack \
  --query 'StackResources[?ResourceType==`AWS::EC2::Instance`].PhysicalResourceId' \
  --output text \
  --profile mgonzalezo)

# Stop instance
aws ec2 stop-instances --instance-ids $INSTANCE_ID --profile mgonzalezo
# Saves ~$4.08/hour, keeps all data
```

### Start Instance
```bash
# Get instance ID and start
INSTANCE_ID=$(aws cloudformation describe-stack-resources \
  --stack-name kepler-k3s-stack \
  --query 'StackResources[?ResourceType==`AWS::EC2::Instance`].PhysicalResourceId' \
  --output text \
  --profile mgonzalezo)

aws ec2 start-instances --instance-ids $INSTANCE_ID --profile mgonzalezo
# Resumes from where you left off
```

### Delete Everything
```bash
scripts/delete-stack.sh
# Complete cleanup, frees all resources
```

## Cost Management

### Pricing (us-east-1)

| Instance Type | vCPUs | RAM    | Hourly Cost | Budget ($344.70) |
|---------------|-------|--------|-------------|------------------|
| **c5.metal**  | 96    | 192 GB | $4.08       | ~84 hours        |
| m5.metal      | 96    | 384 GB | $4.61       | ~74 hours        |
| r5.metal      | 96    | 768 GB | $6.05       | ~57 hours        |

**Recommendation:** Use **c5.metal** for best value.

### Cost Saving

**When running:** $4-6/hour
**When stopped:** Only EBS storage (~$10/month)

```bash
# Always stop when not in use
INSTANCE_ID=$(aws cloudformation describe-stack-resources \
  --stack-name kepler-k3s-stack \
  --query 'StackResources[?ResourceType==`AWS::EC2::Instance`].PhysicalResourceId' \
  --output text \
  --profile mgonzalezo)
aws ec2 stop-instances --instance-ids $INSTANCE_ID --profile mgonzalezo

# Check stack status
aws cloudformation describe-stacks --stack-name kepler-k3s-stack --profile mgonzalezo
```

## Architecture

### Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│           AWS CloudFormation Stack                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │   EC2 Bare-Metal Instance (c5.metal)          │ │
│  │   ┌───────────────────────────────────────┐   │ │
│  │   │  K3s Lightweight Kubernetes           │   │ │
│  │   │  ┌─────────────────────────────────┐  │   │ │
│  │   │  │  Namespace: kepler-system       │  │   │ │
│  │   │  │  ┌───────────────────────────┐  │  │   │ │
│  │   │  │  │  Kepler v0.11.2          │  │  │   │ │
│  │   │  │  │  - eBPF metrics          │  │  │   │ │
│  │   │  │  │  - Fake meter (init)     │  │  │   │ │
│  │   │  │  └───────────────────────────┘  │  │   │ │
│  │   │  │  ┌───────────────────────────┐  │  │   │ │
│  │   │  │  │  HTTPS Proxy (Nginx)     │  │  │   │ │
│  │   │  │  │  - TLS termination       │  │  │   │ │
│  │   │  │  │  - Port 30443            │  │  │   │ │
│  │   │  │  └───────────────────────────┘  │  │   │ │
│  │   │  │  ┌───────────────────────────┐  │  │   │ │
│  │   │  │  │  cert-manager v1.18.2    │  │  │   │ │
│  │   │  │  └───────────────────────────┘  │  │   │ │
│  │   │  └─────────────────────────────────┘  │   │ │
│  │   │  ┌─────────────────────────────────┐  │   │ │
│  │   │  │  Namespace: kepler-model-server │  │   │ │
│  │   │  │  ┌───────────────────────────┐  │  │   │ │
│  │   │  │  │  Model Server (latest)   │  │  │   │ │
│  │   │  │  │  - AWS EC2 models        │  │  │   │ │
│  │   │  │  │  - ML power estimation   │  │  │   │ │
│  │   │  │  └───────────────────────────┘  │  │   │ │
│  │   │  └─────────────────────────────────┘  │   │ │
│  │   └───────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  Security Group │ Elastic IP │ IAM Role            │
└─────────────────────────────────────────────────────┘
```

### Data Flow

```
Hardware (c5.metal CPU)
        ↓
eBPF Probes → Real Metrics
        ↓         (CPU cycles, instructions, cache)
   Kepler Pod
        ↓
    ┌───┴───┐
    ↓       ↓
Fake Meter  Model Server → ML Estimation
(Init only)              (Power in Watts)
    ↓       ↓
    └───┬───┘
        ↓
  Prometheus Metrics
        ↓
  HTTPS Endpoint (30443)
```

### Why K3s Instead of Kind?

| Feature | K3s | Kind |
|---------|-----|------|
| **Resource usage** | Low | Medium |
| **Bare-metal support** | Excellent | Issues with AppArmor |
| **Production ready** | Yes | Dev/testing only |
| **Boot time** | Fast (~30s) | Slow (~2min) |
| **AWS compatibility** | Perfect | AppArmor conflicts |

**Decision:** K3s is better for AWS bare-metal deployments.

## Documentation

### Quick Reference
- **[quick-start.md](quick-start.md)** - One-page cheat sheet

### Technical Details
- **[kepler-deployment-summary.md](kepler-deployment-summary.md)** - Complete technical guide
  - AWS limitations explained
  - RAPL vs Model Server
  - Key points
  - Verification commands

### Automation Guide
- **[automated-deployment.md](automated-deployment.md)** - How automation works
  - What was automated
  - Why each component
  - Troubleshooting guide

### Instance Information
- **k3s-instance-info.txt** - Generated after deployment (gitignored - contains sensitive data)
  - IP addresses
  - Access commands
  - Metrics endpoints

## Prerequisites

### 1. AWS Account Requirements

- **Active AWS Account** with billing enabled
- **AWS Credits**: ~$344 USD (provides ~84 hours of c5.metal)
- **vCPU Quota**: Minimum 96 vCPUs for Standard instances

Check quota:
```bash
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --region us-east-1
```

Request increase if needed:
```bash
aws service-quotas request-service-quota-increase \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --desired-value 96 \
  --region us-east-1
```

### 2. AWS CLI Configuration

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo scripts/aws/install

# Configure credentials
aws configure
```

### 3. SSH Key Pair

```bash
# Create key pair
aws ec2 create-key-pair \
  --key-name oss-korea \
  --region us-east-1 \
  --query 'KeyMaterial' \
  --output text > oss-korea.pem

# Set permissions
chmod 400 oss-korea.pem
```

## Security Notes

- **SSH access:** Currently 0.0.0.0/0 (change for production!)
- **Metrics endpoints:** Publicly accessible (demo only)
- **TLS certificates:** Self-signed (use -k with curl)
- **EBS encryption:** Enabled by default
- **IAM role:** Minimal required permissions

**For production:** Restrict access in CloudFormation template.

## Troubleshooting

### Stack won't create?
```bash
# Check quota
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A

# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name kepler-k3s-stack
```

### Metrics not available?
```bash
# SSH to instance
ssh -i oss-korea.pem ubuntu@<PUBLIC_IP>

# Check installation logs
tail -f /var/log/user-data.log

# Check pods
kubectl get pods -A

# Check specific logs
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler
```

### Need to re-deploy?
```bash
scripts/delete-stack.sh
scripts/create-stack.sh
```

## Folder Structure

```
aws-deployment/
├── readme.md                          # This file
├── quick-start.md                     # One-page reference
├── automated-deployment.md            # Automation details
├── kepler-deployment-summary.md       # Technical guide
├── scripts/
│   ├── create-stack.sh               # Create CloudFormation stack
│   └── delete-stack.sh               # Delete stack
├── templates/
│   └── kepler-k3s-stack.yaml         # CloudFormation template
└── k3s-instance-info.txt             # Generated (gitignored)
```

## Resources

### Kepler
- [Official Documentation](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [Model Server](https://github.com/sustainable-computing-io/kepler-model-server)

### K3s
- [Official Website](https://k3s.io/)
- [Documentation](https://docs.k3s.io/)
- [GitHub](https://github.com/k3s-io/k3s)

### AWS
- [CloudFormation Docs](https://docs.aws.amazon.com/cloudformation/)
- [EC2 Instance Types](https://aws.amazon.com/ec2/instance-types/)
- [Service Quotas](https://docs.aws.amazon.com/servicequotas/)

---

**Created for:** Open Source Summit Korea 2025

**Architecture:** AWS c5.metal → K3s → Kepler v0.11.2 + Model Server

**License:** Apache 2.0

**Author:** Marco Gonzalez
