# Demo Guide - OSS Korea 2025

**Carbon-Aware Kepler MCP Server Demo**

## Pre-Demo Checklist

- [ ] AWS K3s cluster running with Kepler v0.11.2
- [ ] Kepler HTTPS endpoint accessible: `https://<IP>:30443/metrics`
- [ ] Carbon MCP Server deployed and running
- [ ] Demo workloads created (efficient-app + heavy-app)
- [ ] Claude Desktop configured with MCP
- [ ] Fallback screenshots prepared

## Demo Flow (25 minutes)

### 1. Introduction (2 minutes)

**Talking Points:**
- "Korea's Carbon Neutrality Act (탄소중립 녹색성장 기본법) requires net-zero by 2050"
- "Data centers must achieve PUE ≤ 1.4 for Green certification (에너지이용 합리화법)"
- "Korea's grid: 424 gCO2eq/kWh (coal 35%, gas 28%, nuclear 25%)"
- "Challenge: How to monitor and optimize workload carbon footprint in real-time?"

### 2. Architecture Overview (5 minutes)

**Show Diagram:**
```
User → Claude Desktop → MCP Server → Kepler → AWS c5.metal
```

**Key Points:**
- **Kepler:** eBPF-based real metrics (not simulated)
- **Model Server:** ML power estimation (RAPL unavailable on AWS)
- **MCP Server:** Korean compliance intelligence
- **Claude Desktop:** Natural language interface

**Commands to Show:**
```bash
# Show Kepler is running
kubectl get pods -n kepler-system

# Show MCP server is running
kubectl get pods -n carbon-mcp

# Show Kepler metrics
curl -k https://<IP>:30443/metrics | grep kepler_pod_cpu_watts
```

### 3. Live Demo (15 minutes)

#### Demo 1: Compliant Workload (3 min)

**Claude Desktop Query:**
> "Check if efficient-app in namespace demo complies with Korean carbon neutrality standards"

**Expected Response:**
```
 COMPLIANT: efficient-app meets both Korean Carbon Neutrality 2050
(398 gCO2eq/kWh ≤ 424 gCO2eq/kWh) and Green Data Center PUE requirements
(1.3 ≤ 1.4).

Current metrics:
• Power: 8.5W
• Carbon: 398 gCO2eq/kWh
• PUE: 1.3
• Monthly emissions: 2.5 kg CO2eq

Recommendations:
• Continue monitoring for compliance drift
• Document as best practice configuration
```

**Talking Points:**
- "This lightweight workload is compliant"
- "Low power consumption = low carbon footprint"
- "Meets both PUE and carbon targets"

#### Demo 2: Non-Compliant Workload (5 min)

**Claude Desktop Query:**
> "Check if heavy-app in namespace demo complies with Korean standards"

**Expected Response:**
```
️ NON-COMPLIANT: heavy-app exceeds both Korean standards:
• Carbon: 510 gCO2eq/kWh (20% over 424 target)
• PUE: 1.6 (14% over 1.4 target)

Current metrics:
• Power: 65W
• Hourly emissions: 33.2 gCO2eq
• Monthly emissions: 24.1 kg CO2eq

Recommendations:
1. URGENT: Reduce power by 20% to meet carbon target
2. Improve cooling efficiency for PUE ≤ 1.4
3. Reschedule to 2am-6am KST (10% cleaner grid)
4. Right-size CPU from 8 to 6 cores (15% reduction)
```

**Talking Points:**
- "This CPU-intensive workload exceeds both targets"
- "Clear NON-COMPLIANT status with gap percentages"
- "Actionable recommendations provided"

#### Demo 3: Optimization Impact (4 min)

**Claude Desktop Query:**
> "What's the impact of rescheduling heavy-app to 2am and right-sizing CPU?"

**Expected Response:**
```
Optimization Impact Analysis:

Current:
• Power: 65W
• Emissions: 24.1 kg/month
• Status: NON-COMPLIANT

After optimizations (temporal_shift + resource_rightsizing):
• Power: 55.3W (15% reduction)
• Emissions: 20.5 kg/month
• Status: COMPLIANT 

Estimated savings:
• Power reduction: 9.7W
• Emissions reduction: 3.6 kg CO2eq/month
• Cost savings: $5.20/month

Implementation:
1. Create CronJob for 2am-6am KST schedule
2. Update CPU requests from 8 cores to 6 cores
3. Monitor for performance impact
```

**Talking Points:**
- "Combined optimizations achieve compliance"
- "25% total reduction brings workload into compliance"
- "Both environmental and cost benefits"

#### Demo 4: Regional Comparison (3 min)

**Claude Desktop Query:**
> "Compare heavy-app carbon impact across AWS regions"

**Expected Response:**
```
Regional Comparison:

Current (ap-northeast-2, Seoul):
• 510 gCO2eq/kWh - NON-COMPLIANT

Alternatives:
• us-east-1 (Virginia): 540 gCO2eq/kWh - NON-COMPLIANT (6% worse)
• us-west-2 (Oregon): 240 gCO2eq/kWh - COMPLIANT  (53% better)
• eu-north-1 (Stockholm): 60 gCO2eq/kWh - COMPLIANT  (88% better)

Best region: Stockholm, Sweden (88% reduction)

Migration recommendation:
Migrating to eu-north-1 would reduce carbon emissions by 88%.
Consider for batch workloads or latency-insensitive applications.
```

**Talking Points:**
- "Regional carbon intensity varies dramatically"
- "Sweden (eu-north-1) 88% cleaner due to hydro/nuclear"
- "Migration valuable for batch workloads"

### 4. Technical Highlights (3 minutes)

**Key Technical Points:**

1. **Real eBPF Metrics**
   ```bash
   # Show Kepler is collecting real CPU cycles, not estimates
   kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler | grep "eBPF"
   ```

2. **ML-based Power Estimation**
   ```bash
   # Show Model Server loaded ec2-0.7.11 and specpower models
   kubectl logs -n kepler-model-server kepler-model-server-xxx | grep "pipeline is loaded"
   ```

3. **Korean Regulatory Standards**
   - PUE 1.4 from 에너지이용 합리화법
   - 424 gCO2/kWh from 탄소중립 녹색성장 기본법

4. **MCP Protocol**
   - Standardized AI integration
   - Works with Claude Desktop natively
   - 5 tools + 3 resources

### 5. Q&A (5 minutes)

**Anticipated Questions:**

**Q: Does this work without RAPL?**
A: Yes! Model Server provides ML-based power estimation for AWS where RAPL is unavailable.

**Q: How accurate are the power estimates?**
A: Model Server uses ec2-0.7.11 trained on AWS EC2 instances. Accuracy ~85-90% vs hardware counters.

**Q: Can this integrate with Carbon Aware SDK?**
A: Absolutely! Current version uses static hourly profiles, but we can integrate Carbon Aware SDK for real-time grid data.

**Q: What about other clouds (GCP, Azure)?**
A: Architecture supports multi-cloud. Need to add region-specific carbon intensity data and train models.

**Q: Is this production-ready?**
A: Core functionality is production-ready. For production, recommend:
- Carbon Aware SDK integration
- Prometheus/Grafana dashboards
- Automated compliance alerting

## Fallback Commands (If Claude Desktop Fails)

Use direct HTTP calls:

```bash
# Check compliance
curl -X POST http://<IP>:30800/tools/assess_workload_compliance \
  -H "Content-Type: application/json" \
  -d '{
    "workload_name": "heavy-app",
    "namespace": "demo",
    "standard": "KR_CARBON_2050",
    "region": "ap-northeast-2"
  }' | jq '.recommendation'

# Compare optimization
curl -X POST http://<IP>:30800/tools/compare_optimization_impact \
  -H "Content-Type: application/json" \
  -d '{
    "workload_name": "heavy-app",
    "namespace": "demo",
    "optimizations": ["temporal_shift", "resource_rightsizing"]
  }' | jq '.'

# Regional comparison
curl -X POST http://<IP>:30800/tools/get_regional_comparison \
  -H "Content-Type: application/json" \
  -d '{
    "workload_name": "heavy-app",
    "namespace": "demo",
    "current_region": "ap-northeast-2",
    "comparison_regions": ["us-east-1", "eu-north-1"]
  }' | jq '.best_region'
```

## Demo Workload Creation

```bash
# Create demo namespace
kubectl create namespace demo

# Compliant workload
kubectl run efficient-app -n demo \
  --image=nginx:alpine \
  --requests='cpu=100m,memory=128Mi'

# Non-compliant workload (requires stress-ng image)
kubectl run heavy-app -n demo \
  --image=polinux/stress \
  --requests='cpu=8,memory=16Gi' \
  -- stress --cpu 8 --timeout 3600s
```

## Post-Demo Cleanup

```bash
# Delete demo workloads
kubectl delete namespace demo

# Keep MCP server running for Q&A exploration
```

## Backup Plan

If live demo fails:
1. Have screenshots of successful runs
2. Show architecture diagrams
3. Walk through code highlights
4. Show recorded video demo

## Success Metrics

-  Demonstrate real Kepler metrics collection
-  Show Korean regulatory compliance assessment
-  Provide clear COMPLIANT/NON-COMPLIANT status
-  Generate actionable recommendations
-  Demonstrate regional carbon comparison
-  Show natural language interface with Claude

---

**Time Allocation:**
- Introduction: 2 min
- Architecture: 5 min
- Demo 1 (Compliant): 3 min
- Demo 2 (Non-compliant): 5 min
- Demo 3 (Optimization): 4 min
- Demo 4 (Regional): 3 min
- Q&A: 5 min
**Total: 25 min**
