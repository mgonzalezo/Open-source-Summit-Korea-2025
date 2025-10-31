#!/bin/bash
#
# Deploy Non-Compliant Workloads for Demo
# These workloads consume high CPU/memory and will show as non-compliant in MCP
#

set -e

echo "========================================="
echo "Deploying Non-Compliant Demo Workloads"
echo "========================================="
echo ""

# Find the carbon-kepler-mcp directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$MCP_DIR/test-workloads/extreme-power-workloads.yaml" ]; then
    echo "ERROR: Cannot find test-workloads/extreme-power-workloads.yaml"
    echo "MCP directory: $MCP_DIR"
    exit 1
fi

echo "MCP directory: $MCP_DIR"
export KUBECONFIG=${KUBECONFIG:-~/.kube/config}

# Deploy extreme power workloads
echo "Deploying extreme power workloads..."
kubectl apply -f "$MCP_DIR/test-workloads/extreme-power-workloads.yaml"

echo ""
echo "Waiting for pods to start..."
sleep 20

echo ""
echo "========================================="
echo "✅ Non-Compliant Workloads Deployed"
echo "========================================="
echo ""
echo "Namespace: non-compliant-workloads"
kubectl get pods -n non-compliant-workloads -o wide

echo ""
echo "Workload Types Deployed:"
echo "  1. extreme-cpu-burner (3 replicas) - 8 CPU workers each"
echo "  2. heavy-memory-cpu-combo (2 replicas) - 6 CPU + 2GB memory"
echo "  3. intense-crypto-miner (2 replicas) - Multi-process SHA256/512 hashing"
echo "  4. inefficient-ml-training (2 replicas) - Inefficient matrix operations"
echo "  5. wasteful-over-provisioned (3 replicas) - Requests 4 CPUs but idle"
echo ""
echo "Total: 12 high-power pods that should trigger non-compliance alerts"
echo ""
echo "To check power consumption after ~60 seconds:"
echo "  kubectl exec -n carbon-mcp deploy/carbon-mcp-server -- python -c \\"
echo "    \"from src.kepler_client import KeplerClient; \\"
echo "    kc = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics'); \\"
echo "    pods = kc.list_pods('non-compliant-workloads'); \\"
echo "    for p in pods[:5]: \\"
echo "        power = kc.get_pod_power_watts(p['pod'], 'non-compliant-workloads'); \\"
echo "        print(f\\\"{p['pod']}: {power['total_watts']:.2f}W\\\")\""
echo ""
echo "To clean up these workloads:"
echo "  kubectl delete namespace non-compliant-workloads"
echo ""
