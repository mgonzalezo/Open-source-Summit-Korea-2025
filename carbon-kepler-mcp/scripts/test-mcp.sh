#!/bin/bash
#
# Test MCP server tools via HTTP
#

set -e

MCP_ENDPOINT="${MCP_ENDPOINT:-http://localhost:30800}"
WORKLOAD="${WORKLOAD:-kepler}"
NAMESPACE="${NAMESPACE:-kepler-system}"

echo "========================================="
echo "Testing MCP Server Tools"
echo "========================================="
echo "Endpoint: $MCP_ENDPOINT"
echo "Workload: $WORKLOAD"
echo "Namespace: $NAMESPACE"
echo ""

echo "1. Testing assess_workload_compliance..."
curl -s -X POST "${MCP_ENDPOINT}/tools/assess_workload_compliance" \
  -H "Content-Type: application/json" \
  -d "{
    \"workload_name\": \"$WORKLOAD\",
    \"namespace\": \"$NAMESPACE\",
    \"standard\": \"KR_CARBON_2050\",
    \"region\": \"ap-northeast-2\"
  }" | jq '.'

echo ""
echo "2. Testing list_workloads_by_compliance..."
curl -s -X POST "${MCP_ENDPOINT}/tools/list_workloads_by_compliance" \
  -H "Content-Type: application/json" \
  -d "{
    \"namespace\": \"$NAMESPACE\",
    \"standard\": \"KR_CARBON_2050\"
  }" | jq '.'

echo ""
echo "✅ MCP server tests complete!"
