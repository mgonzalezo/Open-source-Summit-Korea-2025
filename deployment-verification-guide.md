# Deployment Verification Guide

Complete step-by-step verification commands for Kepler K3s RAPL + MCP Server deployment.

---

## Phase 1: CloudFormation Stack Deployment

### 1.1 Create the Stack
```bash
cd aws-deployment/scripts
./create-stack.sh
```

### 1.2 Monitor Stack Creation
```bash
# Watch stack events in real-time
aws cloudformation describe-stack-events \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'StackEvents[0:10].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
  --output table

# Check overall stack status
aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].StackStatus' \
  --output text
```

### 1.3 Get Stack Outputs
```bash
# Get instance information
aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs' \
  --output table

# Extract specific values
PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
  --output text)

echo "Instance IP: $PUBLIC_IP"
```

---

## Phase 2: Instance and OS Verification

### 2.1 SSH Connection Test
```bash
# SSH into the instance
ssh -i oss-korea-ap.pem ubuntu@$PUBLIC_IP

# If connection fails, check security group
aws ec2 describe-security-groups \
  --region ap-northeast-1 \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=kepler-k3s-rapl" \
  --query 'SecurityGroups[0].IpPermissions' \
  --output table
```

### 2.2 Monitor User Data Installation (on instance)
```bash
# Watch installation progress
tail -f /var/log/cloud-init-output.log

# Check if user-data script completed
sudo systemctl status cloud-final.service

# Check for errors
grep -i error /var/log/cloud-init-output.log
```

### 2.3 Verify RAPL Module Installation
```bash
# Check kernel modules are loaded
lsmod | grep -E 'msr|rapl'

# Expected output:
# intel_rapl_msr         16384  0
# intel_rapl_common      40960  1 intel_rapl_msr
# msr                    16384  0

# Verify RAPL zones are exposed
ls -la /sys/class/powercap/intel-rapl:*/

# Expected output: 4 RAPL zones on c5.metal
# intel-rapl:0 (package-0)
# intel-rapl:0:0 (core)
# intel-rapl:0:1 (dram)
# intel-rapl:1 (package-1)
# intel-rapl:1:0 (core)
# intel-rapl:1:1 (dram)

# Read current energy values
cat /sys/class/powercap/intel-rapl:0/energy_uj
cat /sys/class/powercap/intel-rapl:0:0/energy_uj  # CPU
cat /sys/class/powercap/intel-rapl:0:1/energy_uj  # DRAM
```

### 2.4 Verify System Resources
```bash
# Check CPU (should be 96 vCPUs on c5.metal)
lscpu | grep -E 'CPU\(s\)|Model name'

# Check memory
free -h

# Check disk space
df -h
```

---

## Phase 3: K3s Kubernetes Verification

### 3.1 Check K3s Service Status
```bash
# K3s service should be running
sudo systemctl status k3s

# Check K3s version
k3s --version

# Verify kubectl works
kubectl version --short
```

### 3.2 Verify Cluster Health
```bash
# Check nodes (should see 1 node Ready)
kubectl get nodes -o wide

# Check all namespaces
kubectl get namespaces

# Check all pods across all namespaces
kubectl get pods -A

# Check for any failing pods
kubectl get pods -A | grep -v Running | grep -v Completed
```

### 3.3 Verify Kepler Namespace and Resources
```bash
# Check if kepler-system namespace exists
kubectl get namespace kepler-system

# Get all resources in kepler-system
kubectl get all -n kepler-system

# Expected resources:
# - DaemonSet: kepler
# - Service: kepler
# - Pod: kepler-xxxxx (1 running pod)
```

---

## Phase 4: Kepler Deployment Verification

### 4.1 Check Kepler Pod Status
```bash
# Get Kepler pod details
kubectl get pods -n kepler-system -l app.kubernetes.io/name=kepler -o wide

# Check pod is running on the node
kubectl describe pod -n kepler-system -l app.kubernetes.io/name=kepler

# Look for:
# - Status: Running
# - Containers Ready: 1/1
# - Restarts: 0 or low number
```

### 4.2 Check Kepler Logs
```bash
# View Kepler logs
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler --tail=100

# Look for successful RAPL initialization:
# - "RAPL MSR available"
# - "Package power is available"
# - "DRAM power is available"

# Check for errors
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler | grep -i error

# Follow logs in real-time
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler -f
```

### 4.3 Verify Kepler Configuration
```bash
# Get Kepler ConfigMap
kubectl get configmap -n kepler-system

# Describe Kepler DaemonSet
kubectl describe daemonset kepler -n kepler-system

# Check mounted volumes (should include /sys, /proc)
kubectl get pod -n kepler-system -l app.kubernetes.io/name=kepler -o jsonpath='{.items[0].spec.volumes[*].name}' | tr ' ' '\n'

# Verify host paths mounted
kubectl get pod -n kepler-system -l app.kubernetes.io/name=kepler -o yaml | grep -A5 hostPath
```

### 4.4 Verify Kepler Service
```bash
# Check Kepler service
kubectl get svc -n kepler-system

# Get service details
kubectl describe svc kepler -n kepler-system

# Check endpoints
kubectl get endpoints -n kepler-system
```

---

## Phase 5: Kepler Metrics Verification

### 5.1 Test Metrics Endpoint (HTTP)
```bash
# From your local machine
HTTP_URL=$(aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`HTTPMetricsURL`].OutputValue' \
  --output text)

echo "HTTP Metrics URL: $HTTP_URL"

# Test basic connectivity
curl -s "$HTTP_URL" | head -20

# Check for Kepler metrics
curl -s "$HTTP_URL" | grep "^kepler_" | head -10
```

### 5.2 Test Metrics Endpoint (HTTPS)
```bash
# Get HTTPS URL
HTTPS_URL=$(aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`HTTPSMetricsURL`].OutputValue' \
  --output text)

echo "HTTPS Metrics URL: $HTTPS_URL"

# Test with self-signed cert (-k flag)
curl -k -s "$HTTPS_URL" | head -20
```

### 5.3 Verify Native Watts Metrics Availability
```bash
# Check for node-level watts metrics (native from Kepler v0.11.2+)
curl -s "$HTTP_URL" | grep "kepler_node_cpu_watts"

# Expected output (example):
# kepler_node_cpu_watts{zone="package"} 45.67
# kepler_node_cpu_watts{zone="dram"} 12.34

# Check for pod-level watts metrics
curl -s "$HTTP_URL" | grep "kepler_pod_cpu_watts" | head -5

# Expected output shows watts by zone (package = CPU socket, dram = memory):
# kepler_pod_cpu_watts{pod_name="xxx",pod_namespace="default",zone="package"} X.XX
# kepler_pod_cpu_watts{pod_name="xxx",pod_namespace="default",zone="dram"} X.XX
```

### 5.4 Verify Metrics Format
```bash
# Save metrics to file for analysis
curl -s "$HTTP_URL" > kepler-metrics.txt

# Count total Kepler metrics
grep "^kepler_" kepler-metrics.txt | wc -l

# List all unique Kepler metric names
grep "^kepler_" kepler-metrics.txt | cut -d'{' -f1 | sort -u

# Verify watts metrics have proper labels
grep "kepler_pod_cpu_watts" kepler-metrics.txt | head -3
# Should show labels like: pod_name, pod_namespace, zone (package or dram)

grep "kepler_node_cpu_watts" kepler-metrics.txt
# Should show zone labels: zone="package" and zone="dram"
```

---

## Phase 6: Clone Repository and Deploy Workloads

### 6.1 Clone Repository (on instance)
```bash
# SSH into the instance
ssh -i oss-korea-ap.pem ubuntu@$PUBLIC_IP

# Clone the repository
cd ~
git clone https://github.com/mgonzalezo/Open-source-Summit-Korea-2025.git
cd Open-source-Summit-Korea-2025

# Verify repository structure
ls -la carbon-kepler-mcp/
```

### 6.2 Deploy Standard Demo Workloads
```bash
# Deploy standard power-consuming workloads
cd ~/Open-source-Summit-Korea-2025/carbon-kepler-mcp
./scripts/deploy-workloads-only.sh

# This deploys 5 workload types to demo-workloads namespace:
# 1. high-power-cpu-burner (3 replicas) - CPU intensive stress test
# 2. memory-intensive-app (2 replicas) - Memory stress test
# 3. inefficient-fibonacci (2 replicas) - Inefficient Python code
# 4. crypto-miner-simulation (1 replica) - CPU-intensive hashing
# 5. over-provisioned-idle (2 replicas) - Wasteful idle pods

# Verify all pods are running
kubectl get pods -n demo-workloads

# Expected: 10 pods total, all should reach Running status within 30 seconds
```

### 6.3 Deploy Non-Compliant High-Power Workloads
```bash
# Deploy extreme power workloads for compliance testing
cd ~/Open-source-Summit-Korea-2025/carbon-kepler-mcp
./scripts/deploy-non-compliant-workloads.sh

# This deploys 5 workload types to non-compliant-workloads namespace:
# 1. extreme-cpu-burner (3 replicas) - 8 CPU workers each
# 2. heavy-memory-cpu-combo (2 replicas) - 6 CPU + 2GB memory
# 3. intense-crypto-miner (2 replicas) - Multi-process hashing
# 4. inefficient-ml-training (2 replicas) - Inefficient matrix ops
# 5. wasteful-over-provisioned (3 replicas) - Requests 4 CPUs but idle

# Verify all pods are running
kubectl get pods -n non-compliant-workloads

# Expected: 12 pods total, all should reach Running status
```

### 6.4 Verify Kepler Tracks All Workloads
```bash
# Wait for metrics to accumulate (Kepler updates every 5 seconds)
sleep 30

# Check demo-workloads metrics
curl -s http://localhost:30080/metrics | grep 'pod_namespace="demo-workloads"' | grep "kepler_pod_cpu_watts" | head -10

# Check non-compliant-workloads metrics
curl -s http://localhost:30080/metrics | grep 'pod_namespace="non-compliant-workloads"' | grep "kepler_pod_cpu_watts" | head -10

# Expected output shows real-time power consumption in watts:
# kepler_pod_cpu_watts{...,pod_name="high-power-cpu-burner-xxx",pod_namespace="demo-workloads",zone="package"} 4.05
# kepler_pod_cpu_watts{...,pod_name="high-power-cpu-burner-xxx",pod_namespace="demo-workloads",zone="dram"} 0.42
```

---

## Phase 7: MCP Server Setup

### 7.1 Build Docker Image (on instance)
```bash
# Navigate to MCP directory
cd ~/Open-source-Summit-Korea-2025/carbon-kepler-mcp

# Build the Docker image and import to K3s containerd
sudo ./scripts/build.sh

# This script will:
# 1. Build Docker image: localhost:5000/carbon-kepler-mcp:latest
# 2. Automatically import it into K3s containerd
# 3. Verify the image is available

# Verify image exists in containerd
sudo k3s ctr images ls | grep carbon-kepler-mcp
```

### 7.2 Deploy MCP Server to K3s
```bash
# Deploy using the deploy script
cd ~/Open-source-Summit-Korea-2025/carbon-kepler-mcp
sudo ./scripts/deploy.sh

# The deploy script will:
# 1. Check if image exists in K3s containerd (import if missing)
# 2. Apply Kubernetes manifests
# 3. Wait for deployment to be ready
# 4. Display pod and service status

# Alternative: Build and deploy in one command
sudo ./scripts/build-and-deploy.sh
```

### 7.3 Verify MCP Deployment
```bash
# Check deployment status
sudo kubectl get all -n carbon-mcp

# Expected output:
# pod/carbon-mcp-server-xxxxx   1/1   Running   0   XXs
# service/carbon-mcp-server     NodePort   10.43.x.x   <none>   8000:30800/TCP
# deployment.apps/carbon-mcp-server   1/1   1   1   XXs
```

---

## Phase 8: MCP Server Verification

### 8.1 Check MCP Server Logs
```bash
# View MCP server logs (running in Kubernetes)
kubectl logs -n carbon-mcp deploy/carbon-mcp-server

# Look for successful startup messages:
# - "kepler_client_initialized" with note about using native watts
# - "mcp_server_initialized"
# - Tool registrations (8 tools total)

# Check for errors
kubectl logs -n carbon-mcp deploy/carbon-mcp-server | grep -i error

# Follow logs in real-time
kubectl logs -n carbon-mcp deploy/carbon-mcp-server -f

# Check if server is responding to requests
kubectl logs -n carbon-mcp deploy/carbon-mcp-server --tail=50
```

### 8.2 Verify MCP Tools Registration
```bash
# The MCP server uses FastMCP which auto-registers tools
# Check the pod logs for successful initialization
kubectl logs -n carbon-mcp deploy/carbon-mcp-server | grep -i "initialized\|tool"

# Alternatively, test that tools are accessible by checking server health
kubectl get pods -n carbon-mcp

# Expected MCP tools (8 total):
# 1. assess_workload_compliance
# 2. compare_optimization_impact
# 3. list_workloads_by_compliance
# 4. get_regional_comparison
# 5. calculate_optimal_schedule
# 6. identify_power_hotspots
# 7. list_top_power_consumers
# 8. get_power_consumption_summary

# Test tool accessibility via SSE endpoint
curl -m 5 -H "Accept: text/event-stream" http://localhost:30800/sse 2>&1 | head -20
```

### 8.3 Test MCP Server Connectivity
```bash
# On the instance - test locally
curl -m 2 -H "Accept: text/event-stream" http://localhost:30800/sse

# From your local machine - get public IP
# For NodePort services, use the EC2 instance public IP
export AWS_PROFILE=mgonzalezo  # or your profile name
PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
  --output text)

echo "MCP Server URL: http://$PUBLIC_IP:30800/sse"

# Test from local machine
curl -m 2 -H "Accept: text/event-stream" "http://$PUBLIC_IP:30800/sse"

# Or use the test script
cd carbon-kepler-mcp
export PUBLIC_IP=$PUBLIC_IP
./scripts/test-mcp.sh
```

### 8.4 Verify MCP Can Access Kepler Metrics and Use Native Watts

**IMPORTANT: First verify the Kepler endpoint is correct**
```bash
# Check MCP is using the correct Kepler endpoint
kubectl get deployment -n carbon-mcp carbon-mcp-server -o yaml | grep KEPLER_ENDPOINT

# Should show: value: "http://kepler-http.kepler-system.svc.cluster.local:28282/metrics"
# If it shows "http://kepler.kepler-system..." (without -http), you need to redeploy
```

**Test native watts metrics:**
```bash
# 1. Test node-level watts metrics (shows actual power consumption)
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
node_metrics = kc.get_node_metrics()
print(f'Node Power Consumption:')
print(f'  Package: {node_metrics[\"cpu_watts_package\"]:.2f}W')
print(f'  DRAM: {node_metrics[\"cpu_watts_dram\"]:.2f}W')
print(f'  Total: {node_metrics[\"cpu_watts_total\"]:.2f}W')
"

# Expected output shows real watts values:
# Node Power Consumption:
#   Package: 45.67W
#   DRAM: 12.34W
#   Total: 58.01W

# 2. List all pods with their namespaces
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
pods = kc.list_pods()
print(f'Total pods tracked: {len(pods)}')
print(f'\nFirst 5 pods:')
for pod in pods[:5]:
    print(f'  {pod[\"namespace\"]}/{pod[\"pod\"]}')
"

# 3. Get actual power metrics for demo workload pods
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
pods = kc.list_pods('demo-workloads')
print(f'Demo workload pods: {len(pods)}\n')
for pod_info in pods[:3]:  # Show first 3
    pod_name = pod_info['pod']
    power = kc.get_pod_power_watts(pod_name, 'demo-workloads')
    print(f'{pod_name}:')
    print(f'  CPU: {power[\"cpu_watts\"]:.2f}W')
    print(f'  DRAM: {power[\"dram_watts\"]:.2f}W')
    print(f'  Total: {power[\"total_watts\"]:.2f}W')
"

# Expected output shows actual watts values for each pod
```

---

## Phase 9: Claude Desktop Integration

### 9.1 Configure Claude Desktop (on local machine)
```bash
# Edit Claude Desktop config
# Location: ~/.config/Claude/claude_desktop_config.json (Linux)
#           ~/Library/Application Support/Claude/claude_desktop_config.json (Mac)

# Add MCP server configuration
cat > /tmp/mcp-config.json <<EOF
{
  "mcpServers": {
    "carbon-kepler": {
      "command": "ssh",
      "args": [
        "-i", "oss-korea-ap.pem",
        "ubuntu@$PUBLIC_IP",
        "cd ~/carbon-kepler-mcp && python3 -m src.mcp_server"
      ],
      "transport": "sse"
    }
  }
}
EOF

# Merge with existing config (manual step)
```

### 9.2 Test Claude Desktop Connection
```bash
# Restart Claude Desktop application

# In Claude Desktop chat, test MCP tools:
# "List all available MCP tools"
# "What power consumption tools are available?"
# "Get power consumption summary for my cluster"
```

---

## Phase 10: End-to-End Test

### 10.1 Test MCP with Demo Workloads
```bash
# Get actual pod names from demo-workloads
POD_NAME=$(kubectl get pods -n demo-workloads -l app=cpu-burner -o jsonpath='{.items[0].metadata.name}')
echo "Testing pod: $POD_NAME"

# Test MCP watts query
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
result = kc.get_pod_power_watts('$POD_NAME', 'demo-workloads')
print(f'Pod: $POD_NAME')
print(f'  CPU: {result[\"cpu_watts\"]:.2f}W')
print(f'  DRAM: {result[\"dram_watts\"]:.2f}W')
print(f'  Total: {result[\"total_watts\"]:.2f}W')
print(f'  Status: {result[\"measurement_status\"]}')
"

# Expected output:
# Pod: high-power-cpu-burner-789756c966-xxxxx
#   CPU: 4.05W
#   DRAM: 0.42W
#   Total: 4.47W
#   Status: active
```

### 10.2 Monitor Power Consumption Across All Workloads
```bash
# Monitor node-level power (includes all workloads)
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
node_metrics = kc.get_node_metrics()
print(f'Node Total Power: {node_metrics[\"cpu_watts_total\"]:.2f}W')
print(f'  Package: {node_metrics[\"cpu_watts_package\"]:.2f}W')
print(f'  DRAM: {node_metrics[\"cpu_watts_dram\"]:.2f}W')
"

# List top 5 power consumers from demo-workloads
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
pods = kc.list_pods('demo-workloads')
print(f'\nTop Demo Workloads (first 5 of {len(pods)}):')
for pod_info in pods[:5]:
    pod_name = pod_info['pod']
    power = kc.get_pod_power_watts(pod_name, 'demo-workloads')
    print(f'  {pod_name}: {power[\"total_watts\"]:.2f}W')
"
```

### 10.3 Cleanup Demo Workloads (Optional)
```bash
# Delete demo workloads
kubectl delete namespace demo-workloads

# Delete non-compliant workloads
kubectl delete namespace non-compliant-workloads

# Verify deletion
kubectl get namespaces | grep -E 'demo-workloads|non-compliant'
```

---

## Troubleshooting Commands

### Stack Issues
```bash
# View stack events for errors
aws cloudformation describe-stack-events \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]' \
  --output table

# Delete and recreate stack
./delete-stack.sh
./create-stack.sh
```

### Kepler Issues
```bash
# Restart Kepler pod
kubectl delete pod -n kepler-system -l app.kubernetes.io/name=kepler

# Check Kepler service endpoints
kubectl get endpoints -n kepler-system kepler

# Port-forward to test locally
kubectl port-forward -n kepler-system svc/kepler 9102:9102
curl http://localhost:9102/metrics
```

### MCP Server Issues
```bash
# Check pod status
kubectl get pods -n carbon-mcp

# If pod shows ErrImageNeverPull or ImagePullBackOff
# Import Docker image into K3s containerd manually:
docker save localhost:5000/carbon-kepler-mcp:latest | sudo k3s ctr images import -

# Verify image is in containerd
sudo k3s ctr images ls | grep carbon-kepler-mcp

# Restart deployment
kubectl rollout restart deployment -n carbon-mcp carbon-mcp-server

# Check logs
kubectl logs -n carbon-mcp -l app=carbon-mcp-server -f

# Delete and redeploy if needed
kubectl delete deployment -n carbon-mcp carbon-mcp-server
cd ~/carbon-kepler-mcp
./scripts/deploy.sh
```

### Kepler Endpoint Issues (Watts Showing as 0.0)

**Problem**: MCP returns `{'cpu_watts': 0.0, 'dram_watts': 0.0, 'total_watts': 0.0}` for all pods.

**Root Cause**: MCP is using the wrong Kepler service endpoint.

**Solution**:
```bash
# 1. Verify Kepler services exist
kubectl get svc -n kepler-system

# Expected output should show:
# kepler        ClusterIP   10.43.x.x    <none>   28282/TCP
# kepler-http   NodePort    10.43.x.x    <none>   28282:30080/TCP

# 2. Test Kepler endpoints
# Test NodePort (from EC2 instance)
curl -s http://localhost:30080/metrics | grep "kepler_pod_cpu_watts" | head -5

# Test internal service (from inside cluster)
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -s http://kepler-http.kepler-system.svc.cluster.local:28282/metrics | grep "kepler_pod_cpu_watts" | head -5

# 3. Verify MCP deployment has correct endpoint
kubectl get deployment -n carbon-mcp carbon-mcp-server -o yaml | grep KEPLER_ENDPOINT

# Should show:
# - name: KEPLER_ENDPOINT
#   value: "http://kepler-http.kepler-system.svc.cluster.local:28282/metrics"

# 4. If using wrong endpoint, redeploy MCP
cd ~/Open-source-Summit-Korea-2025
git pull
cd carbon-kepler-mcp
./scripts/build-and-deploy.sh

# 5. Verify watts are now working
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "
from src.kepler_client import KeplerClient
kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics')
result = kc.get_node_metrics()
print(f'Node Total: {result[\"cpu_watts_total\"]:.2f}W')
"
```

**Important Notes**:

- The correct service name is `kepler-http`, NOT `kepler`
- The deployment YAML is version-controlled in git, so this fix persists across redeployments
- Always use `http://kepler-http.kepler-system.svc.cluster.local:28282/metrics` for in-cluster access
- Use `http://localhost:30080/metrics` for NodePort access from the EC2 instance

**Persistence Guarantee**:

The Kepler endpoint configuration is stored in `carbon-kepler-mcp/k8s/deployment.yaml` in the git repository. This means:

1. **After cluster rebuild**: Pull from git and redeploy - configuration is correct
2. **After MCP update**: Configuration persists in version control
3. **No manual intervention needed**: The fix is permanent in the codebase

### RAPL Issues
```bash
# Reload RAPL modules
sudo modprobe -r intel_rapl_msr intel_rapl_common msr
sudo modprobe msr
sudo modprobe intel_rapl_common
sudo modprobe intel_rapl_msr

# Verify modules loaded
lsmod | grep rapl

# Check dmesg for RAPL errors
dmesg | grep -i rapl
```

---

## Success Criteria Checklist

- [ ] CloudFormation stack status: `CREATE_COMPLETE`
- [ ] Instance accessible via SSH
- [ ] RAPL modules loaded (msr, intel_rapl_common, intel_rapl_msr)
- [ ] RAPL zones visible in /sys/class/powercap/
- [ ] K3s service running
- [ ] Kepler pod running in kepler-system namespace
- [ ] Kepler metrics endpoint accessible (HTTP/HTTPS)
- [ ] Node-level native watts metrics available (`kepler_node_cpu_watts`)
- [ ] Pod-level native watts metrics available (`kepler_pod_cpu_watts`)
- [ ] Watts metrics showing zone labels (package, dram)
- [ ] Test workload tracked by Kepler with real-time watts
- [ ] Demo workloads deployed and running (5 types)
- [ ] MCP server running without errors
- [ ] All 8 MCP tools registered
- [ ] MCP using native watts (no joules-to-watts conversion)
- [ ] MCP can fetch and display pod/node watts metrics
- [ ] Power hotspot detection working with watts
- [ ] Claude Desktop connected to MCP server (optional)
- [ ] End-to-end test successful (workload compliance assessment)

---

## Quick Reference

### Important URLs
```bash
# Get from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name kepler-k3s-rapl \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs' \
  --output table
```

### Important Ports
- **30080**: Kepler HTTP metrics (NodePort)
- **30443**: Kepler HTTPS metrics (NodePort)
- **28282**: Kepler internal service port
- **30800**: MCP Server (NodePort)

### Important Files
- **Instance**: `/var/log/cloud-init-output.log` - Installation log
- **Instance**: `/home/ubuntu/kepler-info.txt` - Deployment summary
- **Kubernetes**: MCP server logs via `kubectl logs -n carbon-mcp deploy/carbon-mcp-server`
- **Local**: `aws-deployment/k3s-instance-info.txt` - Stack info

### Key Commands
```bash
# Stack status
aws cloudformation describe-stacks --stack-name kepler-k3s-rapl --region ap-northeast-1

# Get public IP
aws cloudformation describe-stacks --stack-name kepler-k3s-rapl --region ap-northeast-1 --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' --output text

# SSH to instance
ssh -i oss-korea-ap.pem ubuntu@<PUBLIC_IP>

# Check Kepler watts metrics (native)
curl -s http://<PUBLIC_IP>:30800/metrics | grep "kepler_node_cpu_watts"
curl -s http://<PUBLIC_IP>:30800/metrics | grep "kepler_pod_cpu_watts"

# View Kepler logs
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler -f

# Test MCP native watts
kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c "from src.kepler_client import KeplerClient; kc = KeplerClient('http://kepler-http.kepler-system.svc.cluster.local:28282/metrics'); print(kc.get_node_metrics())"
```
