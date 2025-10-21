# Power Hotspot Detection Tools

**Inspired by Kepler PR #2250**: https://github.com/sustainable-computing-io/kepler/pull/2250

## Overview

These MCP tools answer the critical question:

> **"Which nodes or containers are consuming the most power, and what preventive actions should we take?"**

The tools combine Kepler's power metrics with Korean regulatory compliance standards to provide actionable insights for sustainable Kubernetes operations.

## New MCP Tools

### 1. `identify_power_hotspots`

**Purpose**: Identify high-power consumers and generate preventive action recommendations.

**Use Case**: "I want to know which containers are consuming too much power and what I should do about it."

**Parameters**:
- `namespace` (optional): Target namespace, or `null` for cluster-wide analysis
- `power_threshold_watts` (default: 1.0): Minimum power to be considered a hotspot
- `include_compliance_check` (default: true): Flag non-compliant workloads as hotspots

**Returns**:
```json
{
  "namespace": "default",
  "threshold_watts": 1.0,
  "summary": {
    "total_hotspots": 3,
    "total_power_watts": 15.5,
    "total_preventive_actions": 8,
    "high_priority_actions": 2,
    "potential_power_savings_watts": 4.65,
    "potential_co2_reduction_kg_month": 12.8
  },
  "hotspots": [
    {
      "rank": 1,
      "name": "high-power-app",
      "namespace": "production",
      "power_watts": 8.2,
      "carbon_compliant": false,
      "pue_compliant": true,
      "monthly_emissions_kg": 8.5,
      "efficiency_score": 35.0
    }
  ],
  "preventive_actions": [
    {
      "action_type": "alert",
      "priority": "high",
      "resource": "production/high-power-app",
      "reason": "High power consumption: 8.20W",
      "estimated_savings_watts": 0,
      "estimated_co2_reduction_kg_month": 0,
      "implementation_steps": [
        "Monitor pod resource utilization",
        "Check for inefficient code or resource leaks",
        "Review application logs for anomalies"
      ]
    },
    {
      "action_type": "rightsizing",
      "priority": "medium",
      "resource": "production/high-power-app",
      "reason": "Low efficiency score: 35.0/100",
      "estimated_savings_watts": 2.46,
      "estimated_co2_reduction_kg_month": 7.6,
      "implementation_steps": [
        "Analyze actual vs requested resources",
        "Reduce CPU/memory requests if over-provisioned",
        "Consider vertical pod autoscaling",
        "Update deployment with optimized resource limits"
      ]
    }
  ],
  "recommendation": "⚠️  URGENT: 3 power hotspot(s) detected..."
}
```

**Example Usage**:
```python
# Identify hotspots in production namespace
result = await identify_power_hotspots(
    namespace="production",
    power_threshold_watts=2.0,
    include_compliance_check=True
)

print(f"Found {result['summary']['total_hotspots']} hotspots")
print(f"High priority actions: {result['summary']['high_priority_actions']}")

for action in result['preventive_actions']:
    print(f"\n{action['priority'].upper()}: {action['action_type']}")
    print(f"Resource: {action['resource']}")
    print(f"Steps:")
    for step in action['implementation_steps']:
        print(f"  - {step}")
```

---

### 2. `list_top_power_consumers`

**Purpose**: Rank workloads by power consumption or efficiency.

**Use Case**: "Show me the top 10 power-hungry containers in my cluster."

**Parameters**:
- `namespace` (optional): Filter by namespace
- `limit` (default: 10): Number of results
- `sort_by` (default: "power"): Sort by "power" (highest first) or "efficiency" (lowest first)

**Returns**:
```json
{
  "namespace": "all",
  "sort_by": "power",
  "limit": 10,
  "summary": {
    "total_consumers": 10,
    "total_power_watts": 25.3,
    "average_power_watts": 2.53,
    "compliance_rate_percent": 70.0,
    "top_3_consumers": [...]
  },
  "consumers": [
    {
      "rank": 1,
      "name": "ml-training-job",
      "namespace": "ai-workloads",
      "power_watts": 12.5,
      "status": "NON_COMPLIANT",
      "carbon_compliant": false,
      "pue_compliant": true,
      "monthly_emissions_kg": 15.2,
      "efficiency_score": 25.0
    }
  ]
}
```

**Example Usage**:
```python
# Get top 5 least efficient workloads
result = await list_top_power_consumers(
    namespace="production",
    limit=5,
    sort_by="efficiency"
)

for consumer in result['consumers']:
    print(f"#{consumer['rank']}: {consumer['name']}")
    print(f"  Power: {consumer['power_watts']:.2f}W")
    print(f"  Efficiency: {consumer['efficiency_score']:.1f}/100")
    print(f"  Status: {consumer['status']}")
```

---

### 3. `get_power_consumption_summary`

**Purpose**: Quick overview of power usage across a namespace or cluster.

**Use Case**: "Give me a quick summary of power consumption in my cluster."

**Parameters**:
- `namespace` (optional): Target namespace, or `null` for cluster-wide

**Returns**:
```json
{
  "namespace": "production",
  "total_consumers": 25,
  "total_power_watts": 45.8,
  "average_power_watts": 1.83,
  "compliance_rate_percent": 68.0,
  "top_3_consumers": [
    {
      "name": "ml-training-job",
      "namespace": "production",
      "power_watts": 12.5,
      "compliant": false
    }
  ]
}
```

**Example Usage**:
```python
# Get cluster-wide summary
summary = await get_power_consumption_summary()

print(f"Total Power: {summary['total_power_watts']:.2f}W")
print(f"Compliance Rate: {summary['compliance_rate_percent']:.1f}%")
print(f"\nTop 3 Consumers:")
for consumer in summary['top_3_consumers']:
    print(f"  - {consumer['name']}: {consumer['power_watts']:.2f}W")
```

---

## Preventive Action Types

The `identify_power_hotspots` tool recommends four types of preventive actions:

### 1. **Alert** (High Priority)
- **Trigger**: Power consumption > 5.0W
- **Purpose**: Immediate notification of abnormal power usage
- **Actions**:
  - Monitor resource utilization
  - Check for code inefficiencies or leaks
  - Review application logs

### 2. **Rightsizing** (Medium Priority)
- **Trigger**: Efficiency score < 50/100
- **Purpose**: Optimize resource allocation
- **Expected Savings**: ~30% power reduction
- **Actions**:
  - Analyze actual vs requested resources
  - Reduce over-provisioned CPU/memory
  - Implement vertical pod autoscaling

### 3. **Temporal Shift** (Medium Priority)
- **Trigger**: Carbon non-compliant workload
- **Purpose**: Schedule workloads during cleaner grid hours
- **Expected Savings**: ~15% CO2 reduction
- **Actions**:
  - Identify deferrable/batch workloads
  - Schedule for off-peak hours (2am-6am KST)
  - Implement Kubernetes CronJobs

### 4. **Regional Migration** (Low Priority)
- **Trigger**: Monthly emissions > 10 kg
- **Purpose**: Move workloads to regions with cleaner grids
- **Expected Savings**: Up to 88% CO2 reduction (Seoul→Stockholm)
- **Actions**:
  - Evaluate latency tolerance
  - Consider multi-region deployments
  - Implement carbon-aware load balancing

---

## Comparison with Kepler PR #2250

| Feature | Kepler PR #2250 | This Implementation |
|---------|-----------------|---------------------|
| **list_top_consumers** | ✅ Basic power ranking | ✅ Enhanced with compliance & efficiency scoring |
| **get_resource_power** | ✅ Zone-level details | ⏳ Planned (requires container-level metrics) |
| **search_resources** | ✅ Advanced filtering | ⏳ Planned |
| **Preventive Actions** | ❌ Not included | ✅ **NEW**: 4 action types with implementation steps |
| **Korean Compliance** | ❌ Not included | ✅ **NEW**: Carbon Neutrality Act + PUE standards |
| **CO2 Estimation** | ❌ Not included | ✅ **NEW**: Monthly emissions & reduction potential |
| **Efficiency Scoring** | ❌ Not included | ✅ **NEW**: 0-100 score based on power & compliance |

---

## Testing

### Test the Tools Directly

```bash
# SSH to your AWS instance
ssh -i oss-korea.pem ubuntu@57.182.90.243

# Create test script
cat > ~/test_hotspot_tools.py << 'EOF'
import asyncio
import json
from src.kepler_client import KeplerClient
from src.power_hotspot_tools import PowerHotspotDetector

async def test():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(
        kepler_client=client,
        carbon_intensity_gco2_kwh=424.0,
        pue_target=1.4
    )

    print("=== Identifying Power Hotspots ===\n")
    hotspots, actions = detector.identify_power_hotspots(
        namespace=None,
        power_threshold_watts=0.0001,
        compliance_check=True
    )

    print(f"Found {len(hotspots)} hotspots")
    print(f"Generated {len(actions)} preventive actions\n")

    print("Top 3 Hotspots:")
    for h in hotspots[:3]:
        print(f"  {h.rank}. {h.namespace}/{h.name}")
        print(f"     Power: {h.power_watts:.6f}W")
        print(f"     Efficiency: {h.power_efficiency_score:.1f}/100")

    print("\nTop 3 Actions:")
    for a in actions[:3]:
        print(f"  [{a.priority.upper()}] {a.action_type}")
        print(f"     Resource: {a.resource}")
        print(f"     Reason: {a.reason}")

asyncio.run(test())
EOF

# Copy to pod and run
sudo kubectl cp ~/test_hotspot_tools.py carbon-mcp/deployment/carbon-mcp-server:/app/
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 /app/test_hotspot_tools.py
```

---

## Integration with OSS Korea 2025 Demo

### Demo Flow

1. **Show the Problem**:
   ```
   "As a platform engineer, I need to know which containers are wasting power
   and violating Korean environmental regulations."
   ```

2. **Use the Tool**:
   ```python
   result = await identify_power_hotspots(
       namespace="production",
       power_threshold_watts=1.0
   )
   ```

3. **Show the Results**:
   - 🔴 X hotspots detected
   - ⚠️ Y high-priority actions required
   - 💰 Potential savings: Z watts, W kg CO2/month

4. **Implement Actions**:
   - Walk through 1-2 preventive actions
   - Show Kubernetes manifests being updated
   - Demonstrate compliance improvement

---

## Future Enhancements

When Kepler PR #2250 is merged, we can:

1. **Replace Prometheus parsing** with direct Kepler MCP calls
2. **Add zone-level power details** (package, core, DRAM, GPU)
3. **Implement advanced filtering** (power ranges, name patterns)
4. **Support process and VM-level** analysis (beyond just pods)
5. **Real-time power tracking** via Kepler's MCP streaming

---

## Korean Regulatory Alignment

These tools directly support compliance with:

- **탄소중립 녹색성장 기본법** (Carbon Neutrality Act 2050)
  - Target: 424 gCO2eq/kWh grid intensity
  - Tool: Flags non-compliant workloads, estimates CO2 reduction

- **에너지이용 합리화법** (Energy Use Rationalization Act)
  - Target: PUE ≤ 1.4 for green data centers
  - Tool: Calculates PUE, recommends efficiency improvements

---

## References

- **Kepler PR #2250**: https://github.com/sustainable-computing-io/kepler/pull/2250
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Korean Carbon Neutrality Act**: 2050 carbon neutrality goal
- **Green Data Center Standards**: PUE ≤ 1.4 target
