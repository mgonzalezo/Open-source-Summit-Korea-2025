# Custom Demo Queries for OSS Korea 2025

This file shows how to customize the queries/questions you ask the MCP server for your demo.

## Understanding MCP "Questions"

The MCP server doesn't use conversational questions. Instead, you call **functions** that are like asking specific questions:

| Function Call | What You're "Asking" |
|---------------|---------------------|
| `client.list_pods()` | "Which pods have power metrics?" |
| `client.get_pod_metrics(name, ns)` | "How much power is this pod using?" |
| `client.get_node_metrics()` | "What's the total node power?" |
| `detector.identify_power_hotspots()` | "Which workloads are consuming too much power?" |
| `detector.list_top_power_consumers()` | "Rank all workloads by power usage" |
| `detector.get_power_consumption_summary()` | "Give me cluster-wide power statistics" |

---

## Custom Query 1: "Which pods in demo-workloads are using the most power?"

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
from src.kepler_client import KeplerClient

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')

# Get all pods in demo-workloads namespace
pods = client.list_pods(namespace='demo-workloads')

print(f'📊 Power Consumption in demo-workloads namespace\n')
print(f'Found {len(pods)} pods\n')

# Collect power data
pod_power = []
for pod_info in pods:
    metrics = client.get_pod_metrics(pod_info['pod'], pod_info['namespace'])
    pod_power.append((pod_info['pod'], metrics.get('cpu_watts', 0.0)))

# Sort by power (highest first)
pod_power.sort(key=lambda x: x[1], reverse=True)

print('Top 5 Power Consumers:')
for i, (pod_name, power) in enumerate(pod_power[:5], 1):
    print(f'  {i}. {pod_name}: {power:.9f} W')
" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## Custom Query 2: "What's the total power consumption across the entire cluster?"

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def query():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    # Get cluster-wide summary
    summary = detector.get_power_consumption_summary(namespace=None)

    print(f'\n🌍 Cluster-Wide Power Summary\n')
    print(f'  Total Workloads: {summary[\"total_consumers\"]}')
    print(f'  Total Power: {summary[\"total_power_watts\"]:.6f} W')
    print(f'  Average Power per Pod: {summary[\"average_power_watts\"]:.6f} W')
    print(f'  Compliance Rate: {summary[\"compliance_rate_percent\"]:.1f}%\n')

    print(f'Top 3 Power Consumers:')
    for c in summary['top_3_consumers']:
        status = '✅' if c['compliant'] else '❌'
        print(f'  {c[\"namespace\"]}/{c[\"name\"]}: {c[\"power_watts\"]:.6f} W {status}')

asyncio.run(query())
" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## Custom Query 3: "Are any workloads violating Korean environmental regulations?"

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def query():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    # Check compliance for all workloads
    hotspots, actions = detector.identify_power_hotspots(
        namespace='demo-workloads',
        power_threshold_watts=0.1,
        compliance_check=True
    )

    print(f'\n🇰🇷 Korean Regulatory Compliance Check\n')
    print(f'  Standards:')
    print(f'    - 탄소중립 녹색성장 기본법: 424 gCO2eq/kWh')
    print(f'    - 에너지이용 합리화법: PUE ≤ 1.4\n')

    compliant = [h for h in hotspots if h.carbon_compliant and h.pue_compliant]
    non_compliant = [h for h in hotspots if not (h.carbon_compliant and h.pue_compliant)]

    print(f'  Compliant Workloads: {len(compliant)} ✅')
    print(f'  Non-Compliant Workloads: {len(non_compliant)} ❌')
    print(f'  Compliance Rate: {(len(compliant)/len(hotspots)*100) if hotspots else 100:.1f}%\n')

    if non_compliant:
        print(f'⚠️  Non-Compliant Workloads:')
        for h in non_compliant[:5]:
            print(f'    {h.namespace}/{h.name}: {h.power_watts:.6f} W')
    else:
        print(f'✅ All workloads are compliant!')

    if actions:
        print(f'\n🔧 Recommended Actions: {len(actions)}')
        for i, a in enumerate(actions[:3], 1):
            print(f'  {i}. {a.action_type}: {a.resource}')

asyncio.run(query())
" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## Custom Query 4: "Show me the carbon footprint of my workloads"

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
from src.kepler_client import KeplerClient

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')

# Korean grid carbon intensity
CARBON_INTENSITY = 424.0  # gCO2eq/kWh

pods = client.list_pods(namespace='demo-workloads')

print(f'\n🌱 Carbon Footprint Analysis\n')
print(f'Grid: Seoul, Korea ({CARBON_INTENSITY} gCO2eq/kWh)\n')

total_monthly_emissions = 0
pod_emissions = []

for pod_info in pods:
    metrics = client.get_pod_metrics(pod_info['pod'], pod_info['namespace'])
    power_watts = metrics.get('cpu_watts', 0.0)

    # Calculate monthly emissions
    # Power (W) × Grid Intensity (gCO2/kWh) × Hours/month (730) ÷ 1000
    monthly_kg = (power_watts * CARBON_INTENSITY * 730) / 1000
    total_monthly_emissions += monthly_kg

    pod_emissions.append((pod_info['pod'], power_watts, monthly_kg))

# Sort by emissions
pod_emissions.sort(key=lambda x: x[2], reverse=True)

print(f'Pod Carbon Footprint (Top 5):')
for pod_name, power, emissions in pod_emissions[:5]:
    print(f'  {pod_name}')
    print(f'    Power: {power:.6f} W | Emissions: {emissions:.9f} kg CO2/month')

print(f'\n📊 Total Cluster Emissions: {total_monthly_emissions:.6f} kg CO2/month')
print(f'   Annual Projection: {total_monthly_emissions * 12:.6f} kg CO2/year\n')
" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## Custom Query 5: "Which namespace is the most power-hungry?"

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
from src.kepler_client import KeplerClient
from collections import defaultdict

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')

pods = client.list_pods()

# Aggregate by namespace
namespace_power = defaultdict(lambda: {'pods': 0, 'total_watts': 0.0})

for pod_info in pods:
    ns = pod_info['namespace']
    metrics = client.get_pod_metrics(pod_info['pod'], ns)
    power = metrics.get('cpu_watts', 0.0)

    namespace_power[ns]['pods'] += 1
    namespace_power[ns]['total_watts'] += power

print(f'\n📦 Power Consumption by Namespace\n')

# Sort by total power
sorted_ns = sorted(namespace_power.items(), key=lambda x: x[1]['total_watts'], reverse=True)

for ns, data in sorted_ns:
    avg_power = data['total_watts'] / data['pods'] if data['pods'] > 0 else 0
    print(f'  {ns}:')
    print(f'    Pods: {data[\"pods\"]} | Total: {data[\"total_watts\"]:.6f} W | Avg: {avg_power:.6f} W/pod')

print()
" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## How to Create Your Own Custom Query

1. **Choose what you want to know** (the "question")
2. **Find the right function** from the table above
3. **Write Python code** to call that function
4. **Format the output** to be demo-friendly

### Template:

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
# Import what you need
from src.kepler_client import KeplerClient

# Connect to Kepler
client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')

# Your custom query here
print('My Custom Analysis')
# ... your code ...

" 2>&1 | grep -v '^\[' | grep -v '^2025'
```

---

## For Demo Script

Add any of these custom queries to `COMPLETE_DEMO_SCRIPT.md` as additional demonstration points. They show different "angles" of asking about power consumption and compliance.

**Recommended for OSS Korea demo:**
- Query 3 (Korean compliance) - Shows regulatory focus
- Query 4 (Carbon footprint) - Visual impact of emissions
- Query 5 (Namespace comparison) - Shows multi-tenant optimization potential
