# Test Workloads for Power Hotspot Detection

**Purpose**: Deploy high-power workloads to demonstrate non-compliant scenarios and trigger preventive actions.

---

## Workloads Included

### 1. **high-power-cpu-burner** (3 replicas)
- **Purpose**: Simulate CPU-intensive workload
- **Power Impact**: HIGH - Uses 4 CPU workers with stress testing
- **Expected**: Triggers "alert" and "rightsizing" preventive actions
- **Demo Use**: Show power hotspots in action

### 2. **memory-intensive-app** (2 replicas)
- **Purpose**: Simulate memory-intensive operations
- **Power Impact**: MEDIUM - Allocates and uses 512MB RAM actively
- **Expected**: May trigger compliance warnings
- **Demo Use**: Show memory-related power consumption

### 3. **inefficient-fibonacci** (2 replicas)
- **Purpose**: Deliberately inefficient code (no memoization)
- **Power Impact**: HIGH - Recursive Fibonacci calculations
- **Expected**: Low efficiency score, triggers "rightsizing" action
- **Demo Use**: Demonstrate code inefficiency detection

### 4. **crypto-miner-simulation** (1 replica)
- **Purpose**: Simulate cryptocurrency mining (CPU-intensive hashing)
- **Power Impact**: EXTREME - Continuous SHA256 hashing
- **Expected**: Highest power consumer, multiple preventive actions
- **Demo Use**: Show extreme power consumption scenario

### 5. **over-provisioned-idle** (2 replicas)
- **Purpose**: Request lots of resources but remain mostly idle
- **Power Impact**: MEDIUM - Wasteful resource allocation
- **Expected**: Triggers "rightsizing" action with high estimated savings
- **Demo Use**: Show resource waste detection

---

## Quick Deploy

```bash
# SSH to your instance
ssh -i oss-korea.pem ubuntu@52.91.152.207

# Deploy all test workloads
sudo kubectl apply -f ~/carbon-kepler-mcp/test-workloads/high-power-app.yaml

# Wait for pods to start (~30 seconds)
sudo kubectl get pods -n demo-workloads -w

# Verify all pods are running
sudo kubectl get pods -n demo-workloads
```

Expected output:
```
NAME                                      READY   STATUS    RESTARTS   AGE
high-power-cpu-burner-xxxxx-xxxxx        1/1     Running   0          30s
high-power-cpu-burner-xxxxx-xxxxx        1/1     Running   0          30s
high-power-cpu-burner-xxxxx-xxxxx        1/1     Running   0          30s
memory-intensive-app-xxxxx-xxxxx         1/1     Running   0          30s
memory-intensive-app-xxxxx-xxxxx         1/1     Running   0          30s
inefficient-fibonacci-xxxxx-xxxxx        1/1     Running   0          30s
inefficient-fibonacci-xxxxx-xxxxx        1/1     Running   0          30s
crypto-miner-simulation-xxxxx-xxxxx      1/1     Running   0          30s
over-provisioned-idle-xxxxx-xxxxx        1/1     Running   0          30s
over-provisioned-idle-xxxxx-xxxxx        1/1     Running   0          30s
```

---

## Wait for Metrics to Accumulate

**IMPORTANT**: Kepler needs time to collect power metrics from running workloads.

```bash
# Wait 2-3 minutes for meaningful power data
echo "Waiting for Kepler to collect power metrics..."
sleep 180

# Check that Kepler is collecting data for these pods
curl -s http://localhost:28282/metrics | grep "demo-workloads" | grep "kepler_pod_cpu_watts" | head -5
```

You should see non-zero power values for the demo workloads.

---

## Test Power Hotspot Detection

### Test 1: Identify All Hotspots

```bash
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 << 'EOF'
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def test():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    print("\n" + "="*80)
    print("POWER HOTSPOT DETECTION - Demo Workloads")
    print("="*80 + "\n")

    # Lower threshold to catch more pods
    hotspots, actions = detector.identify_power_hotspots(
        namespace="demo-workloads",
        power_threshold_watts=0.1,  # Catch any pod using >0.1W
        compliance_check=True
    )

    print(f"Found {len(hotspots)} hotspots in demo-workloads namespace")
    print(f"Generated {len(actions)} preventive actions\n")

    if hotspots:
        print("🔥 POWER HOTSPOTS:\n")
        for h in hotspots:
            status = "✅" if (h.carbon_compliant and h.pue_compliant) else "❌"
            print(f"  {h.rank}. {h.name}")
            print(f"     Power: {h.power_watts:.4f}W")
            print(f"     Efficiency: {h.power_efficiency_score:.1f}/100")
            print(f"     Compliance: {status}")
            print(f"     Monthly Emissions: {h.monthly_emissions_kg:.4f} kg CO2")
            print()

    if actions:
        print("⚠️  PREVENTIVE ACTIONS:\n")
        for i, a in enumerate(actions[:5], 1):
            print(f"  Action {i}: {a.action_type.upper()} [{a.priority}]")
            print(f"    Resource: {a.resource}")
            print(f"    Reason: {a.reason}")
            print(f"    Savings: {a.estimated_savings_watts:.4f}W, {a.estimated_co2_reduction_kg_month:.4f} kg CO2/month")
            print(f"    Steps:")
            for step in a.implementation_steps[:2]:
                print(f"      • {step}")
            print()

asyncio.run(test())
EOF
```

### Test 2: Compare Demo vs System Workloads

```bash
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 << 'EOF'
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def test():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    print("\n" + "="*80)
    print("NAMESPACE COMPARISON")
    print("="*80 + "\n")

    # Compare demo-workloads vs system workloads
    demo_summary = detector.get_power_consumption_summary(namespace='demo-workloads')
    system_summary = detector.get_power_consumption_summary(namespace='kube-system')

    print("Demo Workloads (demo-workloads namespace):")
    print(f"  Total Power: {demo_summary['total_power_watts']:.4f}W")
    print(f"  Average Power: {demo_summary['average_power_watts']:.4f}W")
    print(f"  Compliance Rate: {demo_summary['compliance_rate_percent']:.1f}%")

    print("\nSystem Workloads (kube-system namespace):")
    print(f"  Total Power: {system_summary['total_power_watts']:.4f}W")
    print(f"  Average Power: {system_summary['average_power_watts']:.4f}W")
    print(f"  Compliance Rate: {system_summary['compliance_rate_percent']:.1f}%")

    power_ratio = demo_summary['total_power_watts'] / system_summary['total_power_watts'] if system_summary['total_power_watts'] > 0 else 0
    print(f"\n🔥 Demo workloads use {power_ratio:.1f}x more power than system workloads!")

asyncio.run(test())
EOF
```

### Test 3: Identify Most Inefficient Workload

```bash
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 << 'EOF'
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def test():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    print("\n" + "="*80)
    print("LEAST EFFICIENT WORKLOADS (Candidates for Optimization)")
    print("="*80 + "\n")

    # Sort by efficiency (lowest first)
    consumers = detector.list_top_power_consumers(
        namespace="demo-workloads",
        limit=5,
        sort_by="efficiency"
    )

    for c in consumers:
        print(f"  {c.rank}. {c.name}")
        print(f"     Efficiency Score: {c.power_efficiency_score:.1f}/100 ⚠️")
        print(f"     Power: {c.power_watts:.4f}W")
        print(f"     Monthly Emissions: {c.monthly_emissions_kg:.4f} kg")
        print()

asyncio.run(test())
EOF
```

---

## Expected Results

After deploying high-power workloads and waiting 2-3 minutes:

### Power Consumption
- **crypto-miner-simulation**: Highest power (continuous CPU hashing)
- **high-power-cpu-burner**: High power (stress testing with 4 workers × 3 replicas)
- **inefficient-fibonacci**: Medium-high power (recursive calculations)
- **memory-intensive-app**: Medium power (memory allocation)
- **over-provisioned-idle**: Low actual power BUT triggers rightsizing action

### Preventive Actions Expected

1. **ALERT** (High Priority)
   - Triggered by: crypto-miner-simulation, high-power-cpu-burner
   - Reason: Power consumption > 5W threshold

2. **RIGHTSIZING** (Medium Priority)
   - Triggered by: over-provisioned-idle, inefficient-fibonacci
   - Reason: Low efficiency score (wasteful resource allocation)
   - Estimated savings: ~30% power reduction

3. **TEMPORAL_SHIFT** (Medium Priority)
   - May trigger if workload becomes non-compliant
   - Reason: Schedule during cleaner grid hours (2am-6am KST)

4. **REGIONAL_MIGRATION** (Low Priority)
   - May trigger if monthly emissions > 10kg
   - Reason: Move to cleaner region (Seoul → Stockholm)

---

## Demo Script (5 minutes)

```bash
# 1. Deploy workloads (30s)
sudo kubectl apply -f ~/carbon-kepler-mcp/test-workloads/high-power-app.yaml

# 2. Wait for metrics (2m)
echo "Waiting for power metrics to accumulate..."
sleep 120

# 3. Run hotspot detection (1m)
sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c "
import asyncio
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

async def test():
    client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
    detector = PowerHotspotDetector(client, 424.0, 1.4)

    hotspots, actions = detector.identify_power_hotspots(
        namespace='demo-workloads',
        power_threshold_watts=0.1,
        compliance_check=True
    )

    print(f'\n🔥 Found {len(hotspots)} power hotspots')
    print(f'⚠️  Generated {len(actions)} preventive actions\n')

    for h in hotspots[:3]:
        print(f'{h.rank}. {h.name}: {h.power_watts:.4f}W (efficiency: {h.power_efficiency_score:.1f}/100)')

    for a in actions[:2]:
        print(f'\n[{a.priority}] {a.action_type}: {a.resource}')

asyncio.run(test())
"

# 4. Explain results and preventive actions (1.5m)
```

---

## Cleanup

```bash
# Remove all demo workloads
sudo kubectl delete namespace demo-workloads

# Verify cleanup
sudo kubectl get pods -n demo-workloads
# Should return: No resources found in demo-workloads namespace.
```

---

## Adjusting Power Consumption

To make workloads consume MORE power:

```bash
# Increase CPU stress workers
# Edit high-power-app.yaml and change:
args:
  - "--cpu"
  - "8"  # Instead of "4"

# Increase replicas
spec:
  replicas: 5  # Instead of 3
```

To make workloads consume LESS power but still trigger alerts:

```bash
# Lower the threshold in detection
power_threshold_watts=0.01  # Instead of 0.1
```

---

## Troubleshooting

### No hotspots detected after deploying workloads

**Cause**: Kepler hasn't collected enough metrics yet
**Solution**: Wait 3-5 minutes, then re-run detection

```bash
# Check if Kepler sees the pods
curl -s http://localhost:28282/metrics | grep demo-workloads | grep cpu_watts
```

### Workloads not starting

**Cause**: Resource limits too high for node
**Solution**: Reduce CPU/memory requests in YAML

```bash
# Check pod status
sudo kubectl describe pod -n demo-workloads <pod-name>

# Check node resources
sudo kubectl top nodes
```

### All workloads show 0W power

**Cause**: Kepler may need restart or pods just started
**Solution**: Wait longer or restart Kepler

```bash
# Restart Kepler
sudo kubectl rollout restart daemonset/kepler -n kepler-system
```

---

## Korean Compliance Context

These workloads will help demonstrate:

- **탄소중립 녹색성장 기본법** (Carbon Neutrality Act)
  - Show workloads exceeding carbon targets
  - Calculate monthly emissions impact

- **에너지이용 합리화법** (Energy Rationalization Act)
  - Demonstrate PUE impact of inefficient workloads
  - Show green data center compliance

---

**Ready to demonstrate power hotspot detection with real workloads!** 🚀
