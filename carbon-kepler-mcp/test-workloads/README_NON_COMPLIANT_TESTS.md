# Testing Non-Compliant Power Scenarios

This directory contains scripts to test and demonstrate power compliance violations for Open Source Summit Korea 2025.

## Quick Test (Run This First!)

**Verify workloads are running and check their power consumption:**

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c \"
from src.kepler_client import KeplerClient

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
pods = client.list_pods(namespace='demo-workloads')

print(f'Found {len(pods)} pods in demo-workloads namespace\\n')
print('Pod Power Consumption:')
print('-' * 60)

pod_power = []
for pod_info in pods:
    pod_name = pod_info['pod']
    namespace = pod_info['namespace']
    metrics = client.get_pod_metrics(pod_name, namespace)
    cpu_watts = metrics.get('cpu_watts', 0.0)
    pod_power.append((namespace, pod_name, cpu_watts))

for namespace, pod_name, cpu_watts in sorted(pod_power, key=lambda x: x[2], reverse=True):
    print(f'{namespace}/{pod_name}: {cpu_watts:.9f} W')
\" 2>&1 | grep -v '^\[' | grep -v '^2025'"
```

**Expected Output:**

```text
Found 10 pods in demo-workloads namespace

Pod Power Consumption:
------------------------------------------------------------
demo-workloads/high-power-cpu-burner-789756c966-fvnzr: 0.000000621 W
demo-workloads/high-power-cpu-burner-789756c966-x7rnr: 0.000000616 W
demo-workloads/high-power-cpu-burner-789756c966-982lg: 0.000000614 W
... (10 pods total)
```

---

## Quick Reference

### 1. Real Workload Deployment (Requires 15+ minutes for metrics)

Deploy actual high-power Kubernetes workloads:

```bash
# Deploy workloads
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl apply -f ~/carbon-kepler-mcp/test-workloads/high-power-app.yaml"

# Verify deployment
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -n demo-workloads -n production"

# Check CPU consumption (should show >10 CPUs total)
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl top pods -n demo-workloads -n production"

# WAIT 15 minutes for Kepler to accumulate energy metrics
# Then check power metrics
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c \"
from src.kepler_client import KeplerClient

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
pods = client.list_pods(namespace='demo-workloads')

print(f'Found {len(pods)} pods in demo-workloads namespace\\n')
print('Pod Power Consumption:')
print('-' * 60)

# Collect power data for sorting
pod_power = []
for pod_info in pods:
    pod_name = pod_info['pod']
    namespace = pod_info['namespace']
    metrics = client.get_pod_metrics(pod_name, namespace)
    cpu_watts = metrics.get('cpu_watts', 0.0)
    pod_power.append((namespace, pod_name, cpu_watts))

# Sort by power (highest first) and display
for namespace, pod_name, cpu_watts in sorted(pod_power, key=lambda x: x[2], reverse=True):
    print(f'{namespace}/{pod_name}: {cpu_watts:.9f} W')
\" 2>&1 | grep -v '^\[' | grep -v '^2025'"
```

**Limitation**: Kepler calculates power from energy counter deltas, so new workloads show 0W initially.

---

### 2. Simulated Non-Compliant Scenarios (Immediate Results)

Use mock high-power values to demonstrate compliance violations immediately.

#### Option A: Standard Grid Compliance (All Compliant with Current Standards)

This shows that workloads consuming 15-22W are technically COMPLIANT with current Korean grid standards (424 gCO2/kWh), but still trigger preventive action alerts due to high power consumption.

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243 "
  sudo kubectl cp ~/carbon-kepler-mcp/test-workloads/simulate-non-compliant.py carbon-mcp/\$(sudo kubectl get pod -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].metadata.name}'):/tmp/simulate.py && \
  sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 /tmp/simulate.py
"
```

**Expected Output**:
```
Compliant Workloads:     10/10 ✅
Non-Compliant Workloads: 0/10 ❌
Compliance Rate:         100.0%

PREVENTIVE ACTIONS RECOMMENDED
Generated 20 preventive actions

Action 1: ALERT [HIGH PRIORITY]
  Resource: production/ml-training-job
  Reason: Extreme power consumption: 22.4W
```

**Key Insight**: Even "compliant" workloads trigger alerts when they consume >10W because they indicate potential inefficiency.

---

#### Option B: Strict Green Cloud Standards (All Non-Compliant)

This demonstrates a stricter compliance regime where cloud providers must achieve 30% better efficiency than grid average (300 gCO2/kWh target instead of 424).

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243 "
  sudo kubectl cp ~/carbon-kepler-mcp/test-workloads/demo-non-compliant.py carbon-mcp/\$(sudo kubectl get pod -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].metadata.name}'):/tmp/demo.py && \
  sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 /tmp/demo.py
"
```

**Expected Output**:
```
Standard: 한국 그린 클라우드 이니셔티브
Carbon Target: 300.0 gCO2eq/kWh (30% better than grid average: 424.0)
PUE Target: ≤ 1.2 (Tier-1 certification)

Compliant Workloads:     0/10 ✅
Non-Compliant Workloads: 10/10 ❌
Compliance Rate:         0.0%

CARBON INTENSITY VIOLATIONS (10 workloads)
  ❌ production/ml-training-job
     Current: 636 gCO2/kWh
     Exceeds target by: 112.0%
     Monthly emissions: 10,381.37 kg CO2

PUE VIOLATIONS (10 workloads)
  ❌ production/ml-training-job
     Estimated PUE: 1.42
     Exceeds target by: 18.3%
```

**Key Insight**: This demonstrates what happens when stricter regulations are enforced (e.g., EU Green Deal, corporate carbon targets).

---

## Files Overview

### Real Workloads
- **`high-power-app.yaml`**: Kubernetes deployment with 5 types of high-power applications (10 pods total)
  - CPU burners (stress test)
  - Memory intensive apps
  - Inefficient recursive code (Fibonacci)
  - Crypto mining simulation
  - Over-provisioned idle pods

### Simulation Scripts
- **`simulate-non-compliant.py`**: Uses standard Korean compliance targets (424 gCO2/kWh, PUE 1.4)
  - All workloads show as COMPLIANT with current grid standards
  - Generates 20 preventive actions based on power thresholds
  - Demonstrates 4 action types: ALERT, RIGHTSIZING, TEMPORAL_SHIFT, REGIONAL_MIGRATION

- **`demo-non-compliant.py`**: Uses STRICT green cloud targets (300 gCO2/kWh, PUE 1.2)
  - All workloads show as NON-COMPLIANT
  - Models inefficiency: high-power workloads (>10W) have 50% carbon overhead
  - Demonstrates regulatory pressure for cloud providers to optimize

---

## Demo Flow Recommendations

### For OSS Korea 2025 Presentation:

**Option 1: Focus on Preventive Actions** (Use `simulate-non-compliant.py`)
1. Show that even "compliant" workloads can be inefficient
2. Demonstrate MCP tools identifying top power consumers
3. Show 4 types of preventive actions generated automatically
4. Emphasize proactive optimization vs reactive compliance

**Option 2: Focus on Regulatory Compliance** (Use `demo-non-compliant.py`)
1. Explain Korean regulatory landscape (탄소중립 녹색성장 기본법 + 에너지이용 합리화법)
2. Show current standards vs future stricter targets
3. Demonstrate how 10/10 workloads would fail stricter standards
4. Emphasize need for tools to prepare for future regulations

**Option 3: Real Metrics** (Use `high-power-app.yaml` + wait time)
1. Deploy real workloads 30 minutes before demo
2. Show actual Kepler power metrics during presentation
3. Use MCP tools to query live data
4. Most realistic but requires timing

---

## Understanding the Numbers

### Why are the simulated values realistic?

**CPU Power (15-22W per pod)**:
- A modern server CPU socket draws 100-300W under load
- A Kubernetes pod consuming 2-4 CPUs on a 48-core server = ~10-20W
- Our simulated values (15.5W, 22.4W) represent inefficient, high-CPU workloads

**Carbon Intensity**:
- Seoul grid: 424 gCO2eq/kWh (coal + natural gas heavy)
- Inefficient workloads: 636 gCO2eq/kWh (simulates 50% overhead from poor optimization)
- Green cloud target: 300 gCO2eq/kWh (30% better via renewables + efficiency)

**PUE (Power Usage Effectiveness)**:
- Typical data center: PUE 1.8
- Green certified DC: PUE 1.4 (Korean standard)
- Tier-1 efficient DC: PUE 1.2 (strict target)
- High-power workloads increase cooling requirements → higher PUE

### Monthly Emissions Calculation:
```
Power (W) × Grid Intensity (gCO2/kWh) × Hours/month (730) ÷ 1000 = kg CO2/month

Example: 22.4W workload
22.4W × 636 gCO2/kWh × 730h ÷ 1000 = 10,381 kg CO2/month
```

For a fleet of 100 such workloads: **1,038 metric tons CO2/month**

---

## Cleanup

```bash
# Delete demo workloads
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl delete -f ~/carbon-kepler-mcp/test-workloads/high-power-app.yaml"

# Verify deletion
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -n demo-workloads -n production"
```

---

## Troubleshooting

**Issue**: Simulation scripts show import errors
**Fix**: Ensure scripts use `sys.path.insert(0, '/app')` before importing from `src`

**Issue**: Real workloads show 0W in Kepler
**Fix**: Wait 15+ minutes for energy counters to accumulate, then query again

**Issue**: No pods found in demo-workloads namespace
**Fix**: Check if namespace exists and workloads are deployed:
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get ns"
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -A | grep demo"
```

---

**Last Updated**: October 2025 for Open Source Summit Korea 2025
