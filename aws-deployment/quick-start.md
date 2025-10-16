# Kepler on AWS c5.metal - Quick Start Guide

## One-Command Deployment (Recommended)

```bash
cd aws-deployment/scripts
./deploy-automated-stack.sh
```

**Wait**: ~15-20 minutes for complete deployment

**Access metrics**:
```bash
# Get IP from output, then:
curl -k https://<PUBLIC_IP>:30443/metrics | grep kepler_node_cpu
```

## What You Get

 **Kepler v0.11.2** - Collecting real CPU/memory/process metrics via eBPF
 **Model Server** - ML-based power estimation (AWS EC2 models)
 **HTTPS Endpoint** - Secure metrics access on port 30443
 **HTTP Endpoint** - Plain metrics access on port 30080
 **Zero Manual Config** - All AWS RAPL workarounds included

## Files You Need

| File | Purpose |
|------|---------|
| `templates/kepler-k3s-automated-stack.yaml` | CloudFormation template with everything |
| `scripts/deploy-automated-stack.sh` | One-command deployment |
| `scripts/stop-stack.sh` | Stop instance (save $) |
| `scripts/start-stack.sh` | Start instance |
| `scripts/delete-stack.sh` | Delete everything |

## Key Metrics Endpoints

```bash
# After deployment completes (check k3s-instance-info.txt for IP):

# Node CPU usage (real data)
curl -k -s https://<IP>:30443/metrics | grep kepler_node_cpu_usage_ratio

# Power consumption (model-based estimation)
curl -k -s https://<IP>:30443/metrics | grep kepler_node_cpu_watts

# Per-pod power
curl -k -s https://<IP>:30443/metrics | grep kepler_pod_cpu_watts

# Process CPU time (real data)
curl -k -s https://<IP>:30443/metrics | grep kepler_process_cpu_seconds_total
```

## Monitoring Deployment

```bash
# SSH to instance
ssh -i oss-korea.pem ubuntu@<PUBLIC_IP>

# Watch installation logs
tail -f /var/log/user-data.log

# Check completion
cat /home/ubuntu/kepler-info.txt
```

## Cost Management

- **Cost**: ~$4.08/hour
- **Budget**: $344.70 = ~84 hours
- **Stop when idle**: `./stop-stack.sh`
- **Delete when done**: `./delete-stack.sh`

## Demo Workload

```bash
# SSH to instance
ssh -i oss-korea.pem ubuntu@<PUBLIC_IP>

# Deploy CPU-intensive workload
kubectl run stress --image=polinux/stress -- stress --cpu 8 --timeout 60s

# Watch power consumption change in real-time
watch -n 2 "curl -k -s https://localhost:30443/metrics | grep kepler_node_cpu_watts"
```

## Troubleshooting

**Metrics not available yet?**
- Wait 15 minutes after stack creation completes
- Check: `tail -f /var/log/user-data.log`

**Connection refused?**
- Verify security group has port 30443 open
- Check: `kubectl get pods -n kepler-system`

**Need to re-deploy?**
```bash
./delete-stack.sh
./deploy-automated-stack.sh
```

## Documentation

- **Technical Details**: See `kepler-deployment-summary.md`
- **Automated Setup**: See `automated-deployment.md`
- **General Info**: See `readme.md`

## What Was Automated

All the troubleshooting we did is now automated:

1.  RAPL workaround (fake CPU meter + model server)
2.  Model server deployment
3.  HTTPS configuration with TLS
4.  Security group rules
5.  Helm values configuration
6.  cert-manager installation
7.  Kepler v0.11.2 deployment

**Result**: Zero manual troubleshooting needed!

---

**Next**: Run `./deploy-automated-stack.sh` and wait for metrics!
