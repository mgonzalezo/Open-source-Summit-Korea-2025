#!/bin/bash
#
# Deploy Carbon-Aware Kepler MCP Server to K3s
#

set -e

# Configuration
NAMESPACE="carbon-mcp"
PUBLIC_IP="${PUBLIC_IP:-}"

echo "========================================="
echo "Deploying Carbon-Aware Kepler MCP Server"
echo "========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -k k8s/

echo ""
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=120s \
    deployment/carbon-mcp-server -n $NAMESPACE

echo ""
echo "✅ Deployment complete!"
echo ""

# Get pod status
echo "Pod status:"
kubectl get pods -n $NAMESPACE

echo ""
echo "Service:"
kubectl get svc -n $NAMESPACE

echo ""
echo "========================================="
echo "Access Information"
echo "========================================="

NODE_PORT=$(kubectl get svc carbon-mcp-server -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

if [ -n "$PUBLIC_IP" ]; then
    echo "HTTP Access: http://$PUBLIC_IP:$NODE_PORT"
else
    echo "HTTP Access: http://<NODE_IP>:$NODE_PORT"
    echo "(Set PUBLIC_IP environment variable for exact URL)"
fi

echo ""
echo "To test MCP server:"
echo "  curl http://<NODE_IP>:$NODE_PORT/tools"
echo ""
echo "To view logs:"
echo "  kubectl logs -n $NAMESPACE -l app=carbon-mcp-server -f"
