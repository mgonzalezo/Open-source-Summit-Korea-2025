# Kepler Bare-Metal CloudFormation Stack

This CloudFormation stack automates the deployment of a bare-metal EC2 instance with Kind and Kepler pre-configured for the Open Source Summit Korea 2025 presentation.

## 📋 Overview

The stack creates:
- **Bare-metal EC2 instance** (c5.metal, m5.metal, etc.) with RAPL support
- **Security Group** with required ports (SSH, K8s API, HTTP/S, Kepler metrics)
- **Elastic IP** for consistent access
- **IAM Role** with CloudWatch and SSM permissions
- **Automated setup** scripts for Docker, Kind, kubectl, and Helm

## 🚀 Quick Start

### 1. Deploy the Stack

```bash
./deploy-stack.sh
```

This interactive script will:
- Check for SSH keys (create one if needed)
- Let you choose instance type
- Deploy the CloudFormation stack
- Wait for completion
- Display SSH connection details

**Expected deployment time:** 5-10 minutes

### 2. Connect to Instance

```bash
# Use the SSH command provided by deploy-stack.sh
ssh -i ~/.ssh/your-key.pem ubuntu@<PUBLIC_IP>
```

### 3. Setup Kepler

Once connected to the instance:

```bash
# Check that setup is complete
tail -f /var/log/user-data.log

# When ready, run the setup script
./setup-kepler.sh
```

This will:
- Create a Kind cluster with proper mounts
- Install cert-manager
- Install Kepler Operator
- Verify all components

**Expected setup time:** 3-5 minutes

### 4. Verify Installation

```bash
# Check all pods
kubectl get pods -A

# Access Kepler metrics
kubectl port-forward -n kepler-operator svc/kepler-operator 28282:28282 &
curl http://localhost:28282/metrics | grep kepler
```

## 🛠 Management Scripts

### Check Stack Status
```bash
./check-stack.sh
```
Displays:
- Stack status
- Instance state
- Public IP
- Uptime and cost estimates
- Available actions

### Stop Instance (Save Costs)
```bash
./stop-stack.sh
```
- Stops the EC2 instance
- You only pay for EBS storage (~$10/month for 100GB)
- Can be restarted anytime

### Start Instance
```bash
./start-stack.sh
```
- Starts a stopped instance
- Resumes billing
- Same IP address (Elastic IP)

### Delete Stack (Complete Cleanup)
```bash
./delete-stack.sh
```
- **Permanently deletes** all resources
- Requires typing "delete" to confirm
- Cannot be undone!

## 💰 Cost Management

### Hourly Rates (us-east-1)
- **c5.metal**: ~$4.08/hour (96 vCPU, 192 GB RAM) ✅ Recommended
- **m5.metal**: ~$4.61/hour (96 vCPU, 384 GB RAM)
- **m5d.metal**: ~$5.42/hour (96 vCPU, 384 GB RAM, NVMe SSD)
- **r5.metal**: ~$6.05/hour (96 vCPU, 768 GB RAM)

### Budget Planning with $344.70 Credits

| Instance Type | Hours Available | Days Available |
|---------------|----------------|----------------|
| c5.metal      | ~84 hours      | ~3.5 days      |
| m5.metal      | ~74 hours      | ~3.1 days      |
| m5d.metal     | ~63 hours      | ~2.6 days      |
| r5.metal      | ~57 hours      | ~2.4 days      |

### Cost-Saving Tips

1. **Stop when not using:**
   ```bash
   ./stop-stack.sh
   ```
   Storage cost: ~$10/month vs ~$4-6/hour when running

2. **Use check-stack.sh regularly:**
   ```bash
   ./check-stack.sh
   ```
   Shows current costs and uptime

3. **Set a CloudWatch alarm** (optional):
   ```bash
   # Create a billing alarm for $100
   aws cloudwatch put-metric-alarm \
     --alarm-name kepler-cost-alarm \
     --alarm-description "Alert when estimated charges exceed $100" \
     --metric-name EstimatedCharges \
     --namespace AWS/Billing \
     --statistic Maximum \
     --period 21600 \
     --evaluation-periods 1 \
     --threshold 100 \
     --comparison-operator GreaterThanThreshold
   ```

4. **Delete when completely done:**
   ```bash
   ./delete-stack.sh
   ```

## 📁 Files Created by CloudFormation

### On EC2 Instance

```
/home/ubuntu/
├── README.md                 # Quick reference guide
├── kind-config.yaml         # Kind cluster configuration
├── setup-kepler.sh          # Main setup script
├── cleanup-cluster.sh       # Delete Kind cluster
└── .bash_aliases            # Helpful aliases (k, kgp, kgn)
```

### In Repository

```
.
├── kepler-baremetal-stack.yaml   # CloudFormation template
├── deploy-stack.sh               # Deploy script
├── start-stack.sh                # Start stopped instance
├── stop-stack.sh                 # Stop running instance
├── delete-stack.sh               # Delete everything
├── check-stack.sh                # Check status and costs
└── CLOUDFORMATION-README.md      # This file
```

## 🔧 Troubleshooting

### Stack Creation Failed

```bash
# Check stack events
aws cloudformation describe-stack-events \
   \
  --region us-east-1 \
  --stack-name kepler-baremetal-stack \
  --max-items 20
```

### Cannot SSH to Instance

1. **Check security group:**
   ```bash
   aws ec2 describe-security-groups \
      \
     --region us-east-1 \
     --group-names kepler-kind-security-group
   ```

2. **Verify instance is running:**
   ```bash
   ./check-stack.sh
   ```

3. **Check SSH key permissions:**
   ```bash
   chmod 400 ~/.ssh/your-key.pem
   ```

### Setup Script Fails

1. **Check user-data logs:**
   ```bash
   ssh -i ~/.ssh/your-key.pem ubuntu@<PUBLIC_IP>
   tail -f /var/log/user-data.log
   ```

2. **Manually run setup:**
   ```bash
   ./setup-kepler.sh
   ```

### Kepler Operator Not Working

1. **Check cert-manager:**
   ```bash
   kubectl get pods -n cert-manager
   ```

2. **Check Kepler operator logs:**
   ```bash
   kubectl logs -n kepler-operator -l app.kubernetes.io/name=kepler-operator
   ```

3. **Verify RAPL is available:**
   ```bash
   ls -la /sys/class/powercap/
   ```

## 🎯 Production vs Testing

### This Setup (Bare-Metal)
✅ Real hardware power monitoring (RAPL)
✅ Accurate energy metrics
✅ Production-like environment
✅ Suitable for demos and presentations

### Alternative (VM/Cloud)
⚠️ No direct hardware access
⚠️ Estimated metrics only
⚠️ Fake CPU meter required
✅ Much cheaper

## 📚 Additional Resources

### Kepler Documentation
- [Official Documentation](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [CNCF Project Page](https://landscape.cncf.io/project=kepler)

### CloudFormation
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [Stack Management](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacks.html)

### Kind
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/)

## 🤝 Support

For issues related to:
- **This CloudFormation setup**: Open an issue in this repository
- **Kepler**: Visit the [Kepler GitHub](https://github.com/sustainable-computing-io/kepler)
- **AWS**: Check [AWS Support](https://console.aws.amazon.com/support)

## ⚠️ Important Reminders

1. **Always stop or delete when done** to avoid unexpected charges
2. **Use `./check-stack.sh`** regularly to monitor costs
3. **Budget ~$4-6/hour** for running instances
4. **Set billing alarms** in AWS Console
5. **Your SSH key is stored** in `~/.ssh/` - keep it safe!

## 📝 Example Workflow

```bash
# Day 1: Deploy
./deploy-stack.sh
# ... work on Kepler demo ...
./stop-stack.sh

# Day 2: Continue work
./check-stack.sh
./start-stack.sh
# ... more demo work ...
./stop-stack.sh

# Day 3: Presentation day
./start-stack.sh
# ... give presentation ...
./stop-stack.sh

# After event: Cleanup
./delete-stack.sh
```

---

**Created for Open Source Summit Korea 2025**
**License:** Apache 2.0
