# Complete Demo Script - OSS Korea 2025
## Carbon-Aware Kubernetes with Kepler + MCP + Claude AI

**Presenter**: Marco Gonzalez
**Duration**: 15-20 minutes (10 min setup verification + 5-10 min live demo)
**Audience**: Open Source Summit Korea 2025

---

## Pre-Demo Checklist (Do this 30 minutes before your session)

- [ ] Laptop charged and connected to power
- [ ] Venue WiFi tested (backup: mobile hotspot ready)
- [ ] SSH key file accessible: `oss-korea.pem`
- [ ] AWS CLI configured with profile `mgonzalezo`
- [ ] Claude Desktop installed and configured
- [ ] Terminal window ready (increase font size for audience)
- [ ] Backup screenshots prepared (in case of connectivity issues)

---

## Part 1: Infrastructure Setup & Verification (10 minutes)

### Step 1: Start the AWS EC2 Instance (3 minutes)

**What viewers will see**: Terminal commands starting infrastructure

**Script to say**:
> "Good morning everyone! Today I'll demonstrate how we can use AI to optimize
> Kubernetes workloads for Korean carbon neutrality regulations. Let me start
> by launching our demonstration cluster on AWS."

**Commands**:
```bash
# Navigate to project directory
cd ~/Documents/Marco/talks/Open-Source-Summit-Korea-2025/Open-source-Summit-Korea-2025

# Start the EC2 instance
cd aws-deployment
./scripts/start-instance.sh
```

**What to say while waiting** (instance takes ~60 seconds to start):
> "We're running Kepler on a bare-metal c5.metal instance in AWS us-east-1.
> This gives us access to hardware performance counters needed for accurate
> power measurements using eBPF. The instance runs K3s - a lightweight
> Kubernetes distribution - with Kepler deployed as a DaemonSet."

**Expected output**:
```
Starting instance i-01d31a7c7323ef2f1...
{
    "StartingInstances": [
        {
            "CurrentState": {
                "Code": 0,
                "Name": "pending"
            },
            "InstanceId": "i-01d31a7c7323ef2f1",
            ...
        }
    ]
}

Waiting for instance to start...
Instance started successfully!
Current IP: 52.91.152.207
```

**Point to highlight**:
> "Note the IP address: 52.91.152.207 - this is where our Kepler metrics and
> MCP server are running. The instance preserves all configuration across
> stop/start cycles to save costs - it's about $117 per day running, but only
> $0.33 per day when stopped."

---

### Step 2: Wait for Kubernetes to Initialize (2 minutes)

**Script to say**:
> "K3s starts automatically on boot, but we need to wait about 2 minutes for
> all services to become ready. Let me explain the architecture while we wait."

**Show architecture slide** (or draw on whiteboard):
```
┌─────────────────────────────────────────────────────────────┐
│ AWS EC2 c5.metal Instance (52.91.152.207)                   │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │ K3s Cluster                                  │          │
│  │                                               │          │
│  │  ┌────────────────┐    ┌──────────────────┐ │          │
│  │  │ Kepler         │    │ Carbon-Kepler    │ │          │
│  │  │ DaemonSet      │───▶│ MCP Server       │ │          │
│  │  │                │    │ (8 tools)        │ │          │
│  │  │ • eBPF probes  │    │                  │ │          │
│  │  │ • RAPL counters│    │ Port 8000 (SSE)  │ │          │
│  │  │ • Prometheus   │    └──────────────────┘ │          │
│  │  │   metrics      │                          │          │
│  │  └────────────────┘                          │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ MCP Protocol (SSE over HTTP)
         │ Internet
         │
┌────────┴─────────────────────────────────────────────────────┐
│ Presenter Laptop (Fedora 41)                                 │
│                                                               │
│  ┌──────────────────┐                                        │
│  │ Claude Desktop   │                                        │
│  │                  │                                        │
│  │ Natural language │                                        │
│  │ queries about    │                                        │
│  │ power & carbon   │                                        │
│  └──────────────────┘                                        │
└───────────────────────────────────────────────────────────────┘
```

**What to say**:
> "Kepler - Kubernetes Efficient Power Level Exporter - uses eBPF to monitor
> power consumption at the pod level. It reads hardware performance counters
> and RAPL (Running Average Power Limit) registers to calculate power usage
> with less than 1% overhead.
>
> The MCP server - Model Context Protocol - exposes Kepler metrics and Korean
> compliance assessment tools to AI assistants. This allows Claude to query
> power data using natural language and recommend optimization actions."

---

### Step 3: Verify Kubernetes Cluster Status (1 minute)

**Script to say**:
> "Now let's verify our cluster is healthy. I'll SSH into the instance and
> check all pods are running."

**Commands**:
```bash
# SSH into the instance
ssh -i oss-korea.pem ubuntu@52.91.152.207

# Check all pods across all namespaces
sudo kubectl get pods -A
```

**Expected output**:
```
NAMESPACE       NAME                                      READY   STATUS    RESTARTS   AGE
kube-system     local-path-provisioner-...                1/1     Running   0          15m
kube-system     coredns-...                               1/1     Running   0          15m
kube-system     metrics-server-...                        1/1     Running   0          15m
kepler-system   kepler-exporter-xxxxx                     1/1     Running   0          15m
carbon-mcp      carbon-mcp-server-xxxxx                   1/1     Running   0          15m
demo-workloads  high-power-cpu-burner-...                 1/1     Running   0          45m
demo-workloads  crypto-miner-simulation-...               1/1     Running   0          45m
demo-workloads  memory-intensive-app-...                  1/1     Running   0          45m
[... more demo workload pods ...]
```

**What to say**:
> "Perfect! All pods are in 'Running' state. Notice we have:
> - Kepler running in the 'kepler-system' namespace
> - Our MCP server in 'carbon-mcp' namespace
> - Demo workloads in 'demo-workloads' - these are intentionally power-hungry
>   applications we deployed to simulate real-world inefficient workloads."

**Point out**:
> "These demo workloads have been running for 45+ minutes, which is important
> because Kepler calculates power from the rate of change of energy counters.
> You need at least 10-15 minutes of runtime to get accurate power measurements."

---

### Step 4: Verify Kepler is Collecting Metrics (2 minutes)

**Script to say**:
> "Let's verify Kepler is successfully collecting power metrics from our workloads."

**Commands**:
```bash
# Check Kepler pod logs
sudo kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler --tail=20
```

**Expected output** (point out these key lines):
```
I0121 06:30:45.123456       1 exporter.go:123] Started Kepler in 5.2s
I0121 06:30:45.234567       1 power.go:456] Using RAPL power meter
I0121 06:30:45.345678       1 collector.go:789] Collecting metrics for 15 pods
I0121 06:30:50.456789       1 exporter.go:234] Exported 342 metrics
```

**What to say**:
> "Good! Kepler is using RAPL (Running Average Power Limit) to read hardware
> power counters. It's collecting metrics for all 15 pods in our cluster and
> exporting them via Prometheus format."

**Next, check if pods have power metrics**:
```bash
# Query Kepler metrics directly via NodePort
curl -s http://localhost:30080/metrics | grep kepler_pod_cpu_watts | head -10
```

**Expected output**:
```
kepler_pod_cpu_watts{pod_name="high-power-cpu-burner-789756c966-2rdpt",pod_namespace="demo-workloads"} 0.156234
kepler_pod_cpu_watts{pod_name="crypto-miner-simulation-64b6ffff96-rwrrz",pod_namespace="demo-workloads"} 0.128456
kepler_pod_cpu_watts{pod_name="memory-intensive-app-6fc47df958-2b6vg",pod_namespace="demo-workloads"} 0.085123
[... more metrics ...]
```

**What to say**:
> "Excellent! We can see actual power measurements in watts for each pod.
> For example, the high-power-cpu-burner is consuming about 0.15 watts, the
> crypto-miner simulation about 0.13 watts. These numbers might seem small,
> but remember this is per-pod power. In a real cluster with thousands of
> pods, these add up quickly."

**Note**: If values show 0.000000, say:
> "If we see zeros here, it means the workloads haven't been running long
> enough for Kepler to accumulate energy counter deltas. For this demo, we've
> had them running for 45+ minutes, so we should see real values."

---

### Step 5: Verify MCP Server is Running (1 minute)

**Script to say**:
> "Now let's verify our MCP server is healthy and accessible. This is the bridge
> that allows Claude AI to query Kepler metrics."

**Commands**:
```bash
# Check MCP server pod
sudo kubectl get pods -n carbon-mcp

# Check MCP server logs
sudo kubectl logs -n carbon-mcp deployment/carbon-mcp-server --tail=20
```

**Expected output**:
```
NAME                                 READY   STATUS    RESTARTS   AGE
carbon-mcp-server-xxxxx-xxxxx        1/1     Running   0          15m

[Logs]
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**What to say**:
> "Perfect! The MCP server is running on port 8000 using SSE (Server-Sent Events)
> transport. This is exactly what Claude Desktop expects for the MCP protocol."

**Test the MCP server endpoint**:
```bash
# Check that SSE endpoint is responding (MCP uses Server-Sent Events)
curl -s -m 2 http://localhost:30800/sse 2>&1 | head -1
# If it hangs, that's good - it means SSE is waiting for events
# Press Ctrl+C to exit

# Better verification - check pod logs for startup confirmation
sudo kubectl logs -n carbon-mcp -l app=carbon-mcp-server --tail=5
```

**Expected output**:

```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**What to say**:
> "Perfect! The MCP server logs show it's running successfully on port 8000 inside
> the container, exposed via NodePort 30800. The SSE transport is ready to accept
> connections from Claude Desktop. The server provides 8 specialized tools for
> analyzing Kepler power metrics and Korean regulatory compliance."

**Exit SSH**:
```bash
exit  # Return to your laptop
```

---

### Step 6: Test External Accessibility (1 minute)

**Script to say**:
> "The MCP server needs to be accessible from the internet so Claude Desktop
> can connect to it. Let's verify port 30800 is open and the SSE endpoint responds."

**Commands** (from your laptop):
```bash
# Test from your laptop (not SSH) - replace with your actual instance IP
curl -v -m 3 http://57.182.90.243:30800/sse
```

**Expected output**:

```text
* Connected to 57.182.90.243 (57.182.90.243) port 30800
> GET /sse HTTP/1.1
> Host: 57.182.90.243:30800
>
< HTTP/1.1 200 OK
< content-type: text/event-stream
< transfer-encoding: chunked
```

(The connection will hang here - press Ctrl+C - this is expected for SSE)

**What to say**:
> "Perfect! We can reach the MCP server from the internet on port 30800. The SSE
> endpoint is responding correctly with 'text/event-stream' content type. If this
> failed, it would mean the AWS security group isn't configured properly, and
> Claude Desktop wouldn't be able to connect."

**If it fails**, troubleshoot:
```bash
# Check security group allows port 8000
aws ec2 describe-security-groups \
  --profile mgonzalezo \
  --region us-east-1 \
  --filters "Name=group-name,Values=*kepler*" \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`8000`]'
```

---

## Part 2: Claude Desktop Demo (5-10 minutes)

### Step 7: Launch Claude Desktop (30 seconds)

**Script to say**:
> "Now for the exciting part - let's use Claude AI to analyze our cluster's
> power consumption using natural language. I'll open Claude Desktop, which
> is configured to connect to our MCP server."

**Commands**:
```bash
# Open Claude Desktop (adjust path if needed)
~/Downloads/nest-v0.8.9-linux-x86_64.AppImage &
```

**What to say while it loads**:
> "Claude Desktop is Anthropic's official desktop application. I've configured
> it to connect to our MCP server by adding a simple JSON config file at
> ~/.config/Claude/claude_desktop_config.json. The configuration just points
> to our server URL: http://52.91.152.207:8000/sse"

**Show the config file** (optional):
```bash
cat ~/.config/Claude/claude_desktop_config.json
```

**What to say**:
> "That's it - just the server URL. No complex integration code needed. The
> MCP protocol handles everything else."

---

### Step 8: Verify MCP Connection in Claude Desktop (30 seconds)

**Script to say**:
> "Once Claude Desktop is open, I can verify the MCP connection. Look for the
> 'Tools' icon in the bottom left corner."

**Actions**:
1. Click the "Tools" or "MCP" icon (usually bottom left or in a sidebar)
2. Look for "carbon-kepler" in the list of connected servers
3. Expand it to show the 8 available tools

**What to say**:
> "Great! You can see Claude has discovered our 'carbon-kepler' server with
> 8 tools available:
>
> 1. assess_workload_compliance - Check if workloads meet Korean regulations
> 2. identify_power_hotspots - Find high-power consumers
> 3. list_top_power_consumers - Ranked list by power usage
> 4. get_power_consumption_summary - Cluster overview
> 5. compare_optimization_impact - Simulate optimization scenarios
> 6. get_regional_carbon_data - Compare regions
> 7. compare_regional_footprint - Multi-region analysis
> 8. get_korea_compliance_standards - Regulatory information
>
> Claude can now call these tools automatically based on my questions."

---

### Step 9: Query 1 - Discover Available Tools (1 minute)

**Script to say**:
> "Let me start with a simple question to show Claude's awareness of the tools."

**Type in Claude Desktop**:
```
What tools do you have available for monitoring Kubernetes power consumption?
```

**Expected response**:
```
I have access to 8 tools from the carbon-kepler MCP server for monitoring
and optimizing Kubernetes power consumption with a focus on Korean regulatory
compliance:

1. **identify_power_hotspots** - Identifies which containers/pods consume the
   most power and recommends preventive actions

2. **list_top_power_consumers** - Lists top power-consuming workloads with
   Korean compliance metrics

3. **get_power_consumption_summary** - Provides cluster-wide power consumption
   overview

[... continues with all 8 tools ...]

Would you like me to analyze your cluster's power consumption?
```

**What to say**:
> "Notice Claude understands the context - it knows these are Kubernetes power
> monitoring tools and can explain what each does. This is the power of MCP -
> the tools are self-describing with rich metadata."

---

### Step 10: Query 2 - Identify Power Hotspots (2 minutes)

**Script to say**:
> "Now let's ask the key question - which workloads are consuming the most power?"

**Type in Claude Desktop**:
```
Which containers in my Kubernetes cluster are consuming the most power?
I'm particularly interested in the demo-workloads namespace and any
recommendations for Korean regulatory compliance.
```

**What happens** (explain to audience):
> "Watch what happens - Claude will automatically call the identify_power_hotspots
> tool with the appropriate parameters. You'll see a 'thinking' indicator or
> 'calling tools' message."

**Expected response**:
```
I'll analyze your cluster's power consumption focusing on the demo-workloads
namespace.

[Calls identify_power_hotspots with namespace="demo-workloads"]

I found 10 power hotspots in your cluster. Here are the top consumers:

**Top 5 Power Hotspots:**

1. **high-power-cpu-burner-1** (demo-workloads)
   • Power: 0.156W (ranked #1)
   • Monthly emissions: 0.048 kg CO2
   • Efficiency score: 45/100 ⚠️
   • Status: Alert - elevated power consumption

2. **crypto-miner-simulation** (demo-workloads)
   • Power: 0.128W (ranked #2)
   • Monthly emissions: 0.039 kg CO2
   • Efficiency score: 52/100

3. **memory-intensive-app-1** (demo-workloads)
   • Power: 0.085W (ranked #3)
   • Monthly emissions: 0.026 kg CO2
   • Efficiency score: 61/100

[... continues with more workloads ...]

**Korean Regulatory Compliance:**

According to 탄소중립 녹색성장 기본법 (Carbon Neutrality Act 2050), the
target is 424 gCO2eq/kWh for the Seoul grid. These workloads are currently
compliant, but I've identified several optimization opportunities.

**Recommended Preventive Actions:**

1. **ALERT (High Priority)** - high-power-cpu-burner workloads
   → Investigate for resource leaks or runaway processes

2. **RIGHTSIZING (Medium Priority)** - Multiple workloads
   → Reduce CPU allocation by 30%
   → Potential savings: 0.12W, 0.037 kg CO2/month

3. **TEMPORAL_SHIFT (Medium Priority)** - Batch workloads
   → Schedule for 2am-6am KST when grid is cleaner
   → Reduces carbon intensity by ~15%

4. **REGIONAL_MIGRATION (Low Priority)** - High emitters
   → Consider eu-north-1 (Stockholm: 50 gCO2/kWh vs Seoul: 424)
   → Potential 88% carbon reduction

Would you like me to analyze any specific workload in more detail?
```

**What to say** (while Claude is responding):
> "This is incredible! Claude just:
> 1. Called the MCP tool with the right parameters
> 2. Parsed the JSON response from Kepler
> 3. Ranked workloads by power consumption
> 4. Assessed Korean regulatory compliance
> 5. Generated 4 types of preventive actions
> 6. Estimated potential savings
>
> All from a single natural language question! No kubectl commands, no manual
> metric queries, no spreadsheet calculations. The AI understands the context
> and provides actionable recommendations."

---

### Step 11: Query 3 - Deep Dive on Specific Workload (1 minute)

**Script to say**:
> "Let's dig deeper into one of the high-power workloads."

**Type in Claude Desktop**:
```
Tell me more about the crypto-miner-simulation workload. Should I be concerned?
What specific actions should I take?
```

**Expected response**:
```
Let me analyze the crypto-miner-simulation workload in detail.

[May call list_top_power_consumers or already has data from previous query]

**crypto-miner-simulation Analysis:**

Current State:
• Power consumption: 0.128W
• Rank: #2 out of 10 workloads
• Monthly emissions: 0.039 kg CO2
• Efficiency score: 52/100 (below average)

**Should you be concerned?**

⚠️ **Moderate concern** - While this workload is technically compliant with
Korean regulations (424 gCO2eq/kWh target), it's consuming 2x more power than
the median pod in your cluster. The name suggests it might be a cryptocurrency
mining simulation, which is typically very CPU-intensive.

**Recommended Actions:**

1. **Immediate (Next 24 hours):**
   - Review if this workload is necessary for production
   - Check CPU utilization: `kubectl top pod crypto-miner-simulation-xxx -n demo-workloads`
   - Examine if this is actually a demo/test workload that can be removed

2. **Short-term (This week):**
   - If required: Implement resource limits
     ```yaml
     resources:
       limits:
         cpu: 500m  # Restrict to 0.5 CPU cores
     ```
   - Schedule it for off-peak hours (2am-6am KST) using CronJob
   - This reduces carbon footprint by ~15% due to cleaner grid mix

3. **Long-term (This month):**
   - Consider if this workload could run in a cleaner region
   - Seoul (ap-northeast-2): 424 gCO2/kWh
   - Stockholm (eu-north-1): 50 gCO2/kWh
   - Potential: 88% carbon reduction

**Estimated Savings if optimized:**
- Power reduction: 0.038W (30% of current)
- CO2 reduction: 0.012 kg/month
- Cost savings: ~$0.003/month

For a fleet of 100 similar workloads: 1.2 kg CO2/month, $0.30/month saved.

Would you like me to show you how to implement any of these recommendations?
```

**What to say**:
> "Notice how Claude provides context-aware recommendations. It:
> - Understands the workload name suggests crypto mining
> - Provides immediate, short-term, and long-term actions
> - Gives specific kubectl commands and YAML configurations
> - Calculates savings at scale (100 workloads)
> - Cites Korean regulations appropriately
>
> This is the kind of intelligent assistance that makes carbon optimization
> accessible to every Kubernetes operator, not just sustainability experts."

---

### Step 12: Query 4 - Korean Regulatory Context (1 minute)

**Script to say**:
> "Let's ask Claude about the Korean regulatory landscape. This is especially
> relevant for organizations operating data centers in Korea."

**Type in Claude Desktop**:
```
What are the Korean regulatory requirements for data center carbon emissions
and energy efficiency? How do my workloads compare?
```

**Expected response**:
```
Let me get the Korean regulatory standards for you.

[Calls get_korea_compliance_standards]

**Korean Data Center Regulations:**

**1. 탄소중립 녹색성장 기본법 (Carbon Neutrality and Green Growth Act 2050)**

- **Enacted**: September 24, 2021
- **Target**: Achieve carbon neutrality by 2050
- **Interim goal**: 35% emissions reduction by 2030 (vs 2018 baseline)
- **Current grid intensity**: 424 gCO2eq/kWh
  - Coal: 35%
  - Natural Gas: 28%
  - Nuclear: 25%
  - Renewables: 12%

**Compliance for your workloads:**
✅ All workloads are currently within the 424 gCO2eq/kWh target
⚠️ However, with planned grid decarbonization, targets will become stricter

**2. 에너지이용 합리화법 (Energy Use Rationalization Act)**

- **Green Data Center Certification**
- **PUE Requirement**: ≤ 1.4 (Power Usage Effectiveness)
- **Energy reporting**: Mandatory for data centers >1000㎡
- **Efficiency improvements**: 5% annual reduction target

**Your cluster's estimated PUE:**
Based on your workload power (0.82W total) and infrastructure overhead:
- Estimated PUE: ~1.35
- Status: ✅ Compliant (below 1.4 threshold)
- Room for improvement: ~7% to reach best practice (PUE 1.2)

**Recommendations for continued compliance:**

1. **Monitor power trends**: Set up alerts for workloads >0.15W
2. **Implement temporal scheduling**: Use cleaner grid hours (2am-6am)
3. **Rightsizing**: Current analysis shows 30% over-provisioning
4. **Documentation**: Maintain compliance reports for regulatory audits

**Future Considerations:**

Korea is expected to tighten carbon intensity targets:
- 2025: ~380 gCO2/kWh (10% stricter)
- 2030: ~270 gCO2/kWh (35% reduction target)

Proactive optimization now will help meet future requirements.

Would you like help generating a compliance report for your organization?
```

**What to say**:
> "This is powerful! Claude just:
> - Explained both Korean laws in their local names (Korean characters)
> - Provided specific targets and dates
> - Assessed our cluster against current AND future requirements
> - Gave actionable recommendations
> - Even offered to generate compliance reports
>
> This level of regulatory intelligence makes it easy for Korean organizations
> to stay compliant while optimizing their infrastructure. The AI acts as both
> a technical consultant and a regulatory expert."

---

### Step 13: Query 5 - Simulation and What-If Analysis (1-2 minutes)

**Script to say**:
> "Finally, let's use Claude to simulate optimization scenarios. What if we
> optimized all our high-power workloads?"

**Type in Claude Desktop**:
```
If I implement the rightsizing recommendations for all workloads consuming
more than 0.1W, what would be the total impact on power and carbon emissions?
Show me before and after comparison.
```

**Expected response**:
```
Let me analyze the impact of rightsizing all workloads above 0.1W.

[Calls compare_optimization_impact or calculates from previous data]

**Rightsizing Impact Analysis**

**Current State (Before Optimization):**
- Total cluster power: 0.82W
- Monthly emissions: 0.25 kg CO2
- High-power workloads (>0.1W): 4 pods
  - high-power-cpu-burner-1: 0.156W
  - high-power-cpu-burner-2: 0.152W
  - high-power-cpu-burner-3: 0.150W
  - crypto-miner-simulation: 0.128W
- Total high-power consumption: 0.586W (71% of cluster)

**Optimization Scenario (30% CPU reduction):**
- Reduce CPU requests by 30% for 4 workloads
- Apply vertical pod autoscaling (VPA)
- Implement resource limits

**After Optimization:**
- Optimized workload power: 0.410W (30% reduction)
- Other workloads: 0.234W (unchanged)
- **New total cluster power: 0.644W**

**Impact Summary:**

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Power (W) | 0.820 | 0.644 | -0.176W (-21%) |
| Monthly kWh | 0.599 | 0.470 | -0.129 kWh |
| Monthly CO2 (kg) | 0.254 | 0.199 | -0.055 kg (-22%) |
| Monthly cost ($0.12/kWh) | $0.072 | $0.056 | -$0.016 |

**At Scale (100 workloads):**
- Power savings: 17.6W
- CO2 reduction: 5.5 kg/month (66 kg/year)
- Cost savings: $1.60/month ($19.20/year)

**At Scale (10,000 workloads - typical large cluster):**
- Power savings: 1,760W (1.76 kW)
- CO2 reduction: 550 kg/month (6.6 metric tons/year)
- Cost savings: $160/month ($1,920/year)

**Korean Regulatory Impact:**
✅ Improves PUE from 1.35 → 1.27 (6% improvement)
✅ Increases compliance margin for future stricter targets
✅ Demonstrates 5% annual efficiency improvement (required by law)

**Implementation Steps:**

1. Install Vertical Pod Autoscaler (VPA):
   ```bash
   kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v0.14.0.yaml
   ```

2. Apply VPA to high-power workloads:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: high-power-cpu-burner-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: high-power-cpu-burner
     updatePolicy:
       updateMode: "Auto"
   ```

3. Monitor results after 1 week
4. Iterate on other workloads

**Risk Assessment:**
- Low risk: VPA starts with recommendations only
- Gradual rollout: Apply to 1-2 workloads first
- Rollback: Simple revert to original resource requests

Would you like me to generate the full VPA configuration files?
```

**What to say**:
> "This is the culmination of AI-powered carbon optimization! Claude just:
> - Analyzed our entire cluster
> - Simulated a 30% reduction scenario
> - Calculated before/after metrics
> - Scaled the analysis to 10,000 workloads
> - Assessed regulatory impact
> - Provided complete implementation steps with YAML
> - Evaluated risks and rollback procedures
>
> This kind of analysis would typically require:
> - A sustainability consultant ($5,000+ engagement)
> - Manual data collection and spreadsheets
> - Multiple meetings and iterations
> - Weeks of time
>
> Claude did it in 10 seconds from a natural language question!"

---

## Part 3: Wrap-Up and Q&A (5 minutes)

### Step 14: Summarize the Demo (2 minutes)

**Script to say**:
> "Let me summarize what we've demonstrated today:
>
> **Technology Stack (All Open Source):**
> 1. ✅ Kepler - eBPF-based power monitoring for Kubernetes
> 2. ✅ MCP (Model Context Protocol) - Standard for AI tool integration
> 3. ✅ Claude AI - Natural language interface
> 4. ✅ Korean compliance assessment - Custom tools for 탄소중립법 & 에너지법
>
> **Key Capabilities Demonstrated:**
> 1. ✅ Real-time power monitoring at pod level
> 2. ✅ AI-powered hotspot detection
> 3. ✅ Korean regulatory compliance assessment
> 4. ✅ Automated preventive action recommendations
> 5. ✅ What-if scenario analysis
> 6. ✅ Natural language queries (no kubectl/scripting needed)
>
> **Business Impact:**
> - Democratizes carbon optimization (any operator can do this)
> - Reduces consultant costs ($5,000+ → $0.30 in AI calls)
> - Accelerates time to insight (weeks → seconds)
> - Ensures regulatory compliance (Korean laws built-in)
> - Scales to any cluster size (10 pods or 10,000)
>
> **Why This Matters for Korea:**
> - 2030: 35% emission reduction target
> - 2050: Carbon neutrality goal
> - Data centers are 1-2% of national energy consumption
> - Every watt saved helps meet national climate goals
>
> This is not a research project - it's production-ready today. Kepler is a
> CNCF sandbox project with dozens of contributors. MCP is Anthropic's open
> standard. The code is on GitHub."

---

### Step 15: Show the Code (Optional - 1 minute)

**Script to say**:
> "Let me quickly show you how simple the MCP server code is."

**Commands**:
```bash
# Show the main MCP tool definition
cat carbon-kepler-mcp/src/mcp_server.py | grep -A 20 "@mcp.tool()" | head -25
```

**What to say**:
> "This is the actual code for one of the MCP tools. It's just Python with
> FastMCP decorators. The @mcp.tool() decorator automatically:
> - Generates JSON schema for the tool
> - Handles input validation
> - Exposes it via SSE transport
> - Makes it discoverable by Claude
>
> That's the power of MCP - you focus on business logic, the protocol handles
> everything else."

---

### Step 16: Resources and Next Steps (1 minute)

**Script to say**:
> "If you want to try this yourself, here are the resources:
>
> **GitHub Repositories:**
> - Kepler: github.com/sustainable-computing-io/kepler
> - MCP Protocol: github.com/modelcontextprotocol
> - FastMCP: github.com/anthropics/fastmcp
> - This demo: [show your GitHub repo URL]
>
> **Getting Started:**
> 1. Deploy Kepler to your K8s cluster (5 minutes with Helm)
> 2. Deploy the MCP server (10 minutes)
> 3. Configure Claude Desktop (5 minutes)
> 4. Start optimizing!
>
> **Community:**
> - CNCF Slack: #kepler channel
> - Kepler community meetings: Every Thursday
> - MCP Discord: [Anthropic's community]
>
> **For Korean Organizations:**
> - All compliance assessments are built-in
> - Works with Korean grid carbon intensity data
> - Supports 한글 output (if requested)
>
> The complete setup guide is in the GitHub repo with step-by-step instructions."

---

### Step 17: Clean Up (1 minute)

**Script to say**:
> "Before I take questions, let me show you one more thing - cost management.
> This demo runs on a $117/day instance. When not in use, I stop it to save costs."

**Commands**:
```bash
# Stop the instance (run this AFTER the demo)
cd aws-deployment
./scripts/stop-instance.sh
```

**What to say**:
> "This stops the EC2 instance but preserves all configuration. Next time I
> need it, one command starts everything back up. Stopped cost: $0.33/day
> (just EBS storage). This is important for demo environments - don't pay for
> compute when you're not using it!
>
> In production, you'd run this 24/7 on your existing Kubernetes cluster -
> no separate infrastructure needed."

---

### Step 18: Q&A (remaining time)

**Common questions you might get:**

**Q: Does this only work with AWS?**
> "No! Kepler works on any Kubernetes cluster - AWS, GCP, Azure, on-premises,
> bare metal. The only requirement is Linux kernel 4.18+ for eBPF support and
> access to hardware performance counters. I used AWS for this demo because
> c5.metal instances have full RAPL access, but I've tested it on on-prem
> hardware too."

**Q: What's the overhead of Kepler?**
> "Kepler uses eBPF which is extremely efficient - less than 1% CPU overhead
> in our testing. It's designed to run in production without impacting workloads.
> The DaemonSet pod itself uses about 50-100MB RAM per node."

**Q: Can I use local LLMs instead of Claude?**
> "Yes! The MCP protocol is open and model-agnostic. I demonstrated with Claude
> because it has native MCP support, but you could build a bridge to LM Studio,
> Ollama, or any other LLM. The server-side code doesn't change - just the
> client integration. There are examples in the MCP repository."

**Q: How accurate are the power measurements?**
> "Kepler uses RAPL (Running Average Power Limit) on Intel/AMD CPUs, which is
> the same interface used by Intel PowerTOP and other tools. Academic studies
> show RAPL is accurate within 5-10% of actual power draw measured with hardware
> meters. For GPU workloads, Kepler can use NVIDIA DCGM. The key is it's
> *relative* accuracy - you can reliably compare workloads and track trends."

**Q: What about Korean language support?**
> "The compliance standards include Korean names (탄소중립 녹색성장 기본법,
> 에너지이용 합리화법). Claude understands Korean naturally, so you can ask
> questions in 한글 and it will respond appropriately. The MCP server returns
> English by default, but we could add localization if needed."

**Q: Is this expensive to run?**
> "The demo infrastructure (c5.metal) is expensive, but that's for bare-metal
> access. In production on your existing cluster:
> - Kepler: Free, open source, negligible resource usage
> - MCP Server: Runs in 1 pod, ~200MB RAM, free
> - Claude API: ~$0.02 per query, or use local LLMs for free
>
> Total incremental cost: essentially zero. The ROI is in reduced power costs
> from optimization - even a few watts saved pays for API calls quickly."

**Q: How do I get started?**
> "Three paths:
> 1. **Quick test** (1 hour): Use my GitHub repo, deploy to a test cluster
> 2. **Production pilot** (1 day): Deploy Kepler to one namespace, monitor
> 3. **Full rollout** (1 week): Cluster-wide deployment + MCP integration
>
> I recommend starting with path 1 on a dev cluster to see it working, then
> expanding to production once you're comfortable."

**Q: Can this help us meet Korean carbon reporting requirements?**
> "Absolutely! The MCP server can generate compliance reports showing:
> - Current vs target carbon intensity (424 gCO2/kWh)
> - PUE measurements (required ≤1.4 for green certification)
> - Trend analysis (5% annual improvement requirement)
> - Per-workload emissions for carbon accounting
>
> You could extend the MCP tools to export this data in whatever format your
> regulators require - Excel, PDF reports, etc."

---

## Post-Demo Checklist

After your presentation:

- [ ] Stop the EC2 instance (`./scripts/stop-instance.sh`)
- [ ] Verify instance stopped (check AWS console)
- [ ] Share GitHub repo URL with attendees
- [ ] Upload slides to conference platform
- [ ] Follow up with people who asked for details
- [ ] Write blog post about the demo (optional)
- [ ] Submit talk recording if conference allows

---

## Backup Plans (If Something Breaks)

### If Claude Desktop can't connect to MCP server:

**Fallback 1**: Use CLI to show MCP tools
```bash
ssh -i oss-korea.pem ubuntu@52.91.152.207 "
  sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 << 'EOF'
from src.power_hotspot_tools import PowerHotspotDetector
from src.kepler_client import KeplerClient

client = KeplerClient('http://kepler.kepler-system.svc.cluster.local:28282/metrics')
detector = PowerHotspotDetector(client, 424.0, 1.4)

hotspots, actions = detector.identify_power_hotspots(namespace='demo-workloads')
print(f'Found {len(hotspots)} hotspots, {len(actions)} actions')
for h in hotspots[:3]:
    print(f'{h.rank}. {h.name}: {h.power_watts}W')
EOF
"
```

**Fallback 2**: Use simulation script
```bash
ssh -i oss-korea.pem ubuntu@52.91.152.207 "
  sudo kubectl cp ~/carbon-kepler-mcp/test-workloads/demo-non-compliant.py carbon-mcp/\$(sudo kubectl get pod -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].metadata.name}'):/tmp/demo.py && \
  sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 /tmp/demo.py
"
```

**Fallback 3**: Show pre-recorded screenshots

### If EC2 instance won't start:

**Fallback**: Use pre-recorded video of the demo + show code

### If internet is down:

**Fallback**: Tether to mobile hotspot, show slides with screenshots

---

## Timing Breakdown

| Section | Duration | Cumulative |
|---------|----------|------------|
| Introduction | 1 min | 1 min |
| Start instance | 3 min | 4 min |
| Verify K8s | 2 min | 6 min |
| Verify Kepler | 2 min | 8 min |
| Verify MCP | 2 min | 10 min |
| Launch Claude | 1 min | 11 min |
| Query 1 (tools) | 1 min | 12 min |
| Query 2 (hotspots) | 2 min | 14 min |
| Query 3 (deep dive) | 1 min | 15 min |
| Query 4 (regulations) | 1 min | 16 min |
| Query 5 (simulation) | 2 min | 18 min |
| Wrap-up | 2 min | 20 min |
| Q&A | 5-10 min | 25-30 min |

**Total**: 20-30 minutes (perfect for a standard conference slot)

---

## Final Checklist Before Going On Stage

30 minutes before:
- [ ] Laptop charged (100%)
- [ ] Connected to power
- [ ] Venue WiFi working (test: `ping google.com`)
- [ ] Mobile hotspot ready as backup
- [ ] SSH key accessible: `ls -la oss-korea.pem`
- [ ] Terminal font size increased (Ctrl+Shift++) for visibility
- [ ] Claude Desktop tested
- [ ] Backup screenshots ready
- [ ] Water bottle filled
- [ ] Notes printed (this script)

5 minutes before:
- [ ] Start EC2 instance
- [ ] Verify all pods Running
- [ ] Test MCP health endpoint
- [ ] Open Claude Desktop
- [ ] Close unnecessary applications
- [ ] Silence phone
- [ ] Deep breath 😊

---

**You're ready! Good luck with your presentation at Open Source Summit Korea 2025!** 🚀🇰🇷

**Remember**: Even if something breaks, you have an amazing story to tell about
AI-powered carbon optimization. The technology is real, the code is on GitHub,
and the impact is measurable. Focus on the vision and the audience will be inspired!
