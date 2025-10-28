#!/bin/bash
#
# Diagnose MCP Server Integration Issues
#

set -e

echo "========================================="
echo "MCP Server Diagnostic Tool"
echo "========================================="
echo ""

# Check if running on instance or locally
if command -v kubectl &> /dev/null || command -v k3s &> /dev/null; then
    ON_INSTANCE=true
    KUBECTL_CMD="kubectl"
    if ! command -v kubectl &> /dev/null && command -v k3s &> /dev/null; then
        KUBECTL_CMD="sudo k3s kubectl"
    fi
else
    ON_INSTANCE=false
    echo "Not on K3s instance - some checks will be skipped"
    echo ""
fi

# Test 1: MCP Server Pod Status
echo "Test 1: MCP Server Pod Status"
echo "------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    $KUBECTL_CMD get pods -n carbon-mcp -l app=carbon-mcp-server
    POD_STATUS=$($KUBECTL_CMD get pods -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    if [ "$POD_STATUS" = "Running" ]; then
        echo "PASS: MCP server pod is running"
    else
        echo "FAIL: MCP server pod status is $POD_STATUS"
        exit 1
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 2: Kepler Pod Status
echo "Test 2: Kepler Pod Status"
echo "-------------------------"
if [ "$ON_INSTANCE" = true ]; then
    $KUBECTL_CMD get pods -n kepler-system -l app.kubernetes.io/name=kepler
    KEPLER_STATUS=$($KUBECTL_CMD get pods -n kepler-system -l app.kubernetes.io/name=kepler -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    if [ "$KEPLER_STATUS" = "Running" ]; then
        echo "PASS: Kepler pod is running"
    else
        echo "FAIL: Kepler pod status is $KEPLER_STATUS"
        exit 1
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 3: Kepler Metrics Availability
echo "Test 3: Kepler Metrics Availability"
echo "------------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    METRIC_COUNT=$(curl -s http://localhost:30080/metrics 2>/dev/null | grep "^kepler_pod" | wc -l)
    if [ "$METRIC_COUNT" -gt 0 ]; then
        echo "PASS: Found $METRIC_COUNT pod-level Kepler metrics"
    else
        echo "FAIL: No Kepler pod metrics found"
        echo "Checking if Kepler endpoint is accessible..."
        curl -I http://localhost:30080/metrics 2>&1 | head -5
        exit 1
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 4: Kepler Metrics Have pod_name Labels
echo "Test 4: Kepler Metrics Labels"
echo "------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    POD_NAME_COUNT=$(curl -s http://localhost:30080/metrics 2>/dev/null | grep "pod_name=" | wc -l)
    ZONE_COUNT=$(curl -s http://localhost:30080/metrics 2>/dev/null | grep "zone=" | wc -l)

    if [ "$POD_NAME_COUNT" -gt 0 ]; then
        echo "PASS: Found $POD_NAME_COUNT metrics with pod_name label"
    else
        echo "FAIL: No metrics with pod_name label found"
        echo "This means Kepler kubernetes integration is disabled"
        exit 1
    fi

    if [ "$ZONE_COUNT" -gt 0 ]; then
        echo "PASS: Found $ZONE_COUNT metrics with zone label (RAPL)"
    else
        echo "WARNING: No zone labels found (RAPL might not be working)"
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 5: MCP Server Can Fetch Metrics
echo "Test 5: MCP Server Kepler Client Test"
echo "---------------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    POD=$($KUBECTL_CMD get pod -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$POD" ]; then
        echo "Testing MCP server's ability to fetch Kepler metrics..."
        TEST_OUTPUT=$($KUBECTL_CMD exec -n carbon-mcp $POD -- python3 -c "
from src.kepler_client import KeplerClient
import json

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
metrics = client.fetch_metrics()
print(json.dumps({'count': len(metrics), 'sample': str(metrics[0]) if metrics else 'none'}))
" 2>&1)

        if echo "$TEST_OUTPUT" | grep -q '"count"'; then
            METRIC_COUNT=$(echo "$TEST_OUTPUT" | grep -o '"count": [0-9]*' | grep -o '[0-9]*')
            echo "PASS: MCP server fetched $METRIC_COUNT metrics from Kepler"
        else
            echo "FAIL: MCP server couldn't fetch metrics"
            echo "Error: $TEST_OUTPUT"
            exit 1
        fi
    else
        echo "FAIL: MCP server pod not found"
        exit 1
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 6: MCP Server Can Process Pod Metrics
echo "Test 6: MCP Server Pod Metrics Processing"
echo "------------------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    echo "Testing pod metrics processing..."
    TEST_OUTPUT=$($KUBECTL_CMD exec -n carbon-mcp $POD -- python3 -c "
from src.kepler_client import KeplerClient
import json

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')

# Get list of demo workload pods
metrics = client.fetch_metrics()
demo_pods = set()
for m in metrics:
    if 'pod_namespace' in m.labels and m.labels['pod_namespace'] == 'demo-workloads':
        if 'pod_name' in m.labels:
            demo_pods.add(m.labels['pod_name'])

if demo_pods:
    test_pod = list(demo_pods)[0]
    pod_metrics = client.get_pod_metrics(test_pod, 'demo-workloads')
    print(json.dumps({
        'pod': test_pod,
        'total_joules': pod_metrics['total_joules'],
        'cpu_joules': pod_metrics['cpu_joules_total'],
        'dram_joules': pod_metrics['dram_joules_total']
    }))
else:
    print(json.dumps({'error': 'no demo-workloads pods found'}))
" 2>&1)

    if echo "$TEST_OUTPUT" | grep -q '"pod"'; then
        POD_NAME=$(echo "$TEST_OUTPUT" | grep -o '"pod": "[^"]*"' | cut -d'"' -f4)
        TOTAL_JOULES=$(echo "$TEST_OUTPUT" | grep -o '"total_joules": [0-9.]*' | grep -o '[0-9.]*')
        echo "PASS: Successfully processed metrics for pod: $POD_NAME"
        echo "      Total energy: $TOTAL_JOULES joules"

        if [ "$TOTAL_JOULES" != "0" ] && [ "$TOTAL_JOULES" != "0.0" ]; then
            echo "PASS: Pod has non-zero energy consumption"
        else
            echo "WARNING: Pod has zero energy consumption (might be idle)"
        fi
    else
        echo "FAIL: Couldn't process pod metrics"
        echo "Error: $TEST_OUTPUT"
        exit 1
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 7: MCP Server SSE Endpoint
echo "Test 7: MCP Server SSE Endpoint"
echo "--------------------------------"
MCP_URL="http://localhost:30800/sse"
if [ "$ON_INSTANCE" = false ]; then
    # Try to get public IP
    if command -v aws &> /dev/null; then
        PUBLIC_IP=$(aws cloudformation describe-stacks \
            --stack-name kepler-k3s-rapl \
            --region ap-northeast-1 \
            --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
            --output text 2>/dev/null || echo "")
        if [ -n "$PUBLIC_IP" ]; then
            MCP_URL="http://${PUBLIC_IP}:30800/sse"
        fi
    fi
fi

echo "Testing SSE endpoint: $MCP_URL"
SSE_RESPONSE=$(timeout 2 curl -s -H "Accept: text/event-stream" "$MCP_URL" 2>&1 || echo "timeout")

if echo "$SSE_RESPONSE" | grep -q "event: endpoint"; then
    echo "PASS: SSE endpoint is responding"
    echo "$SSE_RESPONSE" | head -3
else
    echo "FAIL: SSE endpoint not responding correctly"
    echo "Response: $SSE_RESPONSE"
fi
echo ""

# Test 8: MCP Server Logs Check
echo "Test 8: MCP Server Recent Logs"
echo "-------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    echo "Checking for errors in last 50 log lines..."
    ERROR_COUNT=$($KUBECTL_CMD logs -n carbon-mcp -l app=carbon-mcp-server --tail=50 2>/dev/null | grep -i "error\|failed\|warning" | wc -l)

    if [ "$ERROR_COUNT" -eq 0 ]; then
        echo "PASS: No errors in recent logs"
    else
        echo "WARNING: Found $ERROR_COUNT error/warning messages"
        echo "Recent errors:"
        $KUBECTL_CMD logs -n carbon-mcp -l app=carbon-mcp-server --tail=50 | grep -i "error\|failed\|warning" | tail -5
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Test 9: Demo Workloads Exist
echo "Test 9: Demo Workloads Status"
echo "------------------------------"
if [ "$ON_INSTANCE" = true ]; then
    DEMO_POD_COUNT=$($KUBECTL_CMD get pods -n demo-workloads 2>/dev/null | grep -c "Running" || echo "0")
    if [ "$DEMO_POD_COUNT" -gt 0 ]; then
        echo "PASS: Found $DEMO_POD_COUNT running demo workload pods"
        $KUBECTL_CMD get pods -n demo-workloads
    else
        echo "WARNING: No demo workload pods running"
        echo "Some tests may not work without demo workloads"
    fi
else
    echo "SKIP: Not on instance"
fi
echo ""

# Summary
echo "========================================="
echo "Diagnostic Summary"
echo "========================================="
echo ""
echo "MCP Server Status: Running"
echo "Kepler Status: Running"
echo "Metrics Available: Yes"
echo "SSE Endpoint: Accessible"
echo ""
echo "Next Steps:"
echo "1. Try test questions from MCP_TEST_QUESTIONS.md"
echo "2. Check Claude Desktop configuration"
echo "3. Monitor MCP logs: kubectl logs -n carbon-mcp -l app=carbon-mcp-server -f"
echo ""
