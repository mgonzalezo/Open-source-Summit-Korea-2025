#!/bin/bash
#
# Deploy Carbon-Aware Kepler MCP Server to K3s
#

set -e

# Configuration
NAMESPACE="carbon-mcp"
PUBLIC_IP="${PUBLIC_IP:-}"
IMAGE_NAME="carbon-kepler-mcp"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-localhost:5000}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "========================================="
echo "Deploying Carbon-Aware Kepler MCP Server"
echo "========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found. Please install kubectl."
    exit 1
fi

# Ensure image is in K3s containerd
if command -v k3s &> /dev/null; then
    echo "Checking if image exists in K3s containerd..."
    if ! sudo k3s ctr images ls | grep -q "$FULL_IMAGE"; then
        echo "Image not found in containerd. Importing from Docker..."
        if sudo docker images | grep -q "${REGISTRY}/${IMAGE_NAME}"; then
            sudo docker save "$FULL_IMAGE" | sudo k3s ctr images import -
            echo "Image imported into K3s containerd"
        else
            echo "WARNING: Docker image $FULL_IMAGE not found"
            echo "Please run './scripts/build.sh' first to build the image"
        fi
    else
        echo "Image already exists in K3s containerd"
    fi
    echo ""
fi

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -k k8s/

echo ""
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=120s \
    deployment/carbon-mcp-server -n $NAMESPACE

echo ""
echo "Deployment complete"
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
