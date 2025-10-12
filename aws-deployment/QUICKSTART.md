# Quick Start Guide - AWS Bare-Metal Kepler Deployment

Get Kepler running on AWS bare-metal in under 15 minutes!

## ⚡ Prerequisites Checklist

- [ ] AWS Account with billing enabled
- [ ] AWS CLI installed and configured
- [ ] SSH key pair created in AWS (`oss-korea` recommended)
- [ ] vCPU quota ≥ 96 (request increase if needed)
- [ ] ~$344 USD in AWS credits or budget

## 🚀 5-Step Deployment

### Step 1: Check vCPU Quota

```bash
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME
```

**If quota < 96:** Request increase (see [README.md](README.md#requesting-vcpu-increase))

### Step 2: Create SSH Key (if needed)

```bash
aws ec2 create-key-pair \
  --key-name oss-korea \
  --region us-east-1 \
  --profile YOUR_PROFILE_NAME \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/oss-korea.pem

chmod 400 ~/.ssh/oss-korea.pem
```

### Step 3: Deploy Stack

```bash
cd aws-deployment/scripts
./deploy-stack.sh
```

**Time:** ~5-10 minutes

**What it does:**
- Creates bare-metal EC2 instance (c5.metal)
- Configures security group
- Assigns Elastic IP
- Installs Docker, kubectl, Helm, Kind
- Returns SSH connection details

### Step 4: Connect and Setup Kepler

```bash
# SSH to instance (use IP from deploy output)
ssh -i ~/.ssh/oss-korea.pem ubuntu@<PUBLIC_IP>

# Wait for initial setup to complete
tail -f /var/log/user-data.log
# Press Ctrl+C when you see "Setup completed"

# Run Kepler setup
./setup-kepler.sh
```

**Time:** ~3-5 minutes

### Step 5: Verify Installation

```bash
# Check all pods are running
kubectl get pods -A

# Access Kepler metrics
kubectl port-forward -n kepler-operator svc/kepler-operator 28282:28282 &
curl http://localhost:28282/metrics | grep kepler_
```

## 🎯 You're Done!

Kepler is now running with real RAPL hardware monitoring.

## 💰 Cost Management

**When done working:**
```bash
./stop-stack.sh  # Saves $4-6/hour
```

**Resume work:**
```bash
./start-stack.sh
```

**Check costs:**
```bash
./check-stack.sh
```

**Complete cleanup:**
```bash
./delete-stack.sh
```

## 🔧 Troubleshooting

### Quota Error
```
Error: vCPU limit exceeded
```
**Solution:** Request quota increase (takes 1-2 days)

### Cannot SSH
```bash
# Check instance state
./check-stack.sh

# Verify key permissions
chmod 400 ~/.ssh/oss-korea.pem
```

### Setup Fails
```bash
# Check logs on instance
tail -f /var/log/user-data.log

# Manually run setup
./setup-kepler.sh
```

## 📚 Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [docs/CLOUDFORMATION-README.md](docs/CLOUDFORMATION-README.md) for advanced usage
- Explore Kepler metrics and dashboards

## ⚠️ Remember

- **Stop instance when not using** - saves ~$4-6/hour
- **Delete stack after presentation** - complete cleanup
- **Monitor costs regularly** - use `./check-stack.sh`

---

**Estimated Total Time:** ~15 minutes (excluding quota approval if needed)

**Cost:** ~$4.08/hour (c5.metal in us-east-1)

**Credits Remaining:** Track with `./check-stack.sh`
