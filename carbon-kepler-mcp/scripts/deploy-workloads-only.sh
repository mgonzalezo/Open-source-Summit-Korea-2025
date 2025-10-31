#!/bin/bash
#
# Deploy ONLY Demo Workloads (not MCP server)
# Use this if MCP is already deployed and you just want to deploy/redeploy test workloads
#

set -e

echo "========================================="
echo "Deploying Demo Workloads"
echo "========================================="
echo ""

# Find the carbon-kepler-mcp directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$(dirname "$SCRIPT_DIR")"

# Verify we found the right directory
if [ ! -f "$MCP_DIR/test-workloads/high-power-app.yaml" ]; then
    echo "ERROR: Cannot find test-workloads/high-power-app.yaml"
    echo "MCP directory: $MCP_DIR"
    exit 1
fi

echo "MCP directory: $MCP_DIR"
export KUBECONFIG=/home/ubuntu/.kube/config

# Deploy demo workloads
echo "Deploying test workloads from test-workloads/high-power-app.yaml..."
kubectl apply -f "$MCP_DIR/test-workloads/high-power-app.yaml"

echo ""
echo "Waiting for demo workload pods to start..."
sleep 15
kubectl get pods -n demo-workloads

echo ""
echo "========================================="
echo "✅ Workloads Deployed"
echo "========================================="
echo ""
echo "Demo Workloads:"
kubectl get pods -n demo-workloads -o wide
echo ""
echo "To check power consumption:"
echo "  kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c 'from src.kepler_client import KeplerClient; kc = KeplerClient(); print(kc.list_pods(\"demo-workloads\"))'"
echo ""
