#!/bin/bash
#
# Deploy MCP Server and Demo Workloads to Kepler K3s Cluster
# Run this after the CloudFormation stack has created the base K3s + Kepler installation
#

set -e

echo "========================================="
echo "Deploying MCP Server and Demo Workloads"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "../../carbon-kepler-mcp/Dockerfile" ]; then
    echo "ERROR: Must run from Open-source-Summit-Korea-2025/aws-deployment/scripts/"
    echo "Current directory: $(pwd)"
    exit 1
fi

export KUBECONFIG=/home/ubuntu/.kube/config

# Deploy demo workloads
echo "1. Deploying demo workloads..."
kubectl create namespace demo-workloads 2>/dev/null || true

# Check if demo-workloads.yaml exists in k8s directory
if [ -f "../../carbon-kepler-mcp/k8s/demo-workloads.yaml" ]; then
    kubectl apply -f ../../carbon-kepler-mcp/k8s/demo-workloads.yaml
else
    echo "Creating demo workloads from inline manifest..."
    cat > /tmp/demo-workloads.yaml << 'EOF'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-power-cpu-burner
  namespace: demo-workloads
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cpu-burner
  template:
    metadata:
      labels:
        app: cpu-burner
        power-profile: high
    spec:
      containers:
      - name: stress-cpu
        image: polinux/stress
        resources:
          requests:
            cpu: "800m"
            memory: "256Mi"
          limits:
            cpu: "2000m"
            memory: "512Mi"
        command: ["stress"]
        args: ["--cpu", "4", "--timeout", "0"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-intensive-app
  namespace: demo-workloads
spec:
  replicas: 2
  selector:
    matchLabels:
      app: memory-app
  template:
    metadata:
      labels:
        app: memory-app
        power-profile: medium
    spec:
      containers:
      - name: stress-memory
        image: polinux/stress
        resources:
          requests:
            cpu: "200m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        command: ["stress"]
        args: ["--vm", "4", "--vm-bytes", "256M", "--timeout", "0"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crypto-miner-simulation
  namespace: demo-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crypto-miner
  template:
    metadata:
      labels:
        app: crypto-miner
        power-profile: high
    spec:
      containers:
      - name: cpu-intensive-hash
        image: polinux/stress
        resources:
          requests:
            cpu: "500m"
            memory: "256Mi"
          limits:
            cpu: "1000m"
            memory: "512Mi"
        command: ["stress"]
        args: ["--cpu", "2", "--timeout", "0"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inefficient-fibonacci
  namespace: demo-workloads
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fibonacci
  template:
    metadata:
      labels:
        app: fibonacci
        power-profile: medium
    spec:
      containers:
      - name: python-inefficient
        image: polinux/stress
        resources:
          requests:
            cpu: "300m"
            memory: "128Mi"
          limits:
            cpu: "600m"
            memory: "256Mi"
        command: ["stress"]
        args: ["--cpu", "2", "--timeout", "0"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: over-provisioned-idle
  namespace: demo-workloads
spec:
  replicas: 2
  selector:
    matchLabels:
      app: over-provisioned
  template:
    metadata:
      labels:
        app: over-provisioned
        power-profile: low
    spec:
      containers:
      - name: over-provisioned
        image: nginx:alpine
        resources:
          requests:
            cpu: "1000m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
EOF
    kubectl apply -f /tmp/demo-workloads.yaml
fi

echo "Waiting for demo workload pods to start..."
sleep 15
kubectl get pods -n demo-workloads

# Build and deploy MCP server
echo ""
echo "2. Building MCP server Docker image..."
cd ../../carbon-kepler-mcp

# Build Docker image
docker build -t carbon-kepler-mcp:latest .

# Import into K3s containerd
echo "Importing image into K3s..."
docker save carbon-kepler-mcp:latest | sudo k3s ctr images import -

# Deploy to Kubernetes
echo ""
echo "3. Deploying MCP server to Kubernetes..."
kubectl create namespace carbon-mcp 2>/dev/null || true
kubectl apply -f k8s/

# Wait for MCP server
echo "Waiting for MCP server to be ready..."
kubectl wait --for=condition=ready pod -l app=carbon-mcp-server -n carbon-mcp --timeout=300s || true

echo ""
echo "========================================="
echo "✅ Deployment Complete"
echo "========================================="
echo ""
echo "Demo Workloads:"
kubectl get pods -n demo-workloads
echo ""
echo "MCP Server:"
kubectl get pods -n carbon-mcp
kubectl get svc -n carbon-mcp
echo ""
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
NODE_PORT=$(kubectl get svc carbon-mcp-server -n carbon-mcp -o jsonpath='{.spec.ports[0].nodePort}')
echo "MCP SSE Endpoint: http://$INSTANCE_IP:$NODE_PORT/sse"
echo ""
echo "To configure Claude Desktop, update your config with:"
echo "{\"mcpServers\": {\"carbon-kepler\": {\"command\": \"node\", \"args\": [\"<path-to-bridge>\", \"http://$INSTANCE_IP:$NODE_PORT/sse\"]}}}"
echo ""
