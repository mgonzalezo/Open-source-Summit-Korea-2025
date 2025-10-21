# OSS Korea 2025 Demo - Quick Reference Card

**Instance IP**: 57.182.90.243 (Tokyo - ap-northeast-1)
**Instance ID**: i-013b5cd6ee511f107
**SSH Key**: `oss-korea.pem`
**Region**: ap-northeast-1 (Tokyo, Japan - ~10ms to Seoul 🇰🇷)
**Project**: Carbon-Aware Kepler MCP for Korean Regulatory Compliance

---

## Pre-Demo Checklist (30 min before)

```bash
cd /home/margonza/Documents/Marco/talks/Open-Source-Summit-Korea-2025/Open-source-Summit-Korea-2025

# 1. Start instance (if stopped)
cd aws-deployment && ./scripts/start-instance.sh
# ⏱️ Wait 3 minutes for K3s to start

# 2. Verify all systems running
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -A"
# Expected: All pods Running (1/1 or 2/2 READY)

# 3. Check demo workloads deployed
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -n demo-workloads"
# Expected: 10 pods Running (if not, deploy them - see below)

# 4. Quick MCP server health check
ssh -i oss-korea.pem ubuntu@57.182.90.243 "sudo kubectl get pods -n carbon-mcp"
# Expected: carbon-mcp-server pod in Running state (1/1 READY)
```

✅ All systems ready? → Proceed to demo!

---

## First-Time Setup (Tokyo Deployment)

**Only needed if MCP server or demo workloads are NOT deployed yet**:

### Deploy MCP Server (~5 min)

```bash
# 1. Wait for instance to fully boot
sleep 180

# 2. Sync code to Tokyo instance
rsync -avz -e "ssh -i oss-korea.pem -o StrictHostKeyChecking=no" \
  carbon-kepler-mcp/ \
  ubuntu@57.182.90.243:~/carbon-kepler-mcp/

# 3. Build and deploy MCP server
ssh -i oss-korea.pem ubuntu@57.182.90.243 << 'REMOTE'
cd ~/carbon-kepler-mcp
sudo docker build -t carbon-kepler-mcp:latest .
sudo kubectl apply -f k8s/namespace.yaml
sudo kubectl apply -f k8s/deployment.yaml
sudo kubectl apply -f k8s/service.yaml
sudo kubectl wait --for=condition=ready pod -l app=carbon-mcp-server -n carbon-mcp --timeout=300s
echo "✅ MCP server deployed"
REMOTE

# 4. Verify MCP server
curl http://57.182.90.243:8000/health
# Expected: {"status":"healthy","tools":8}
```

### Deploy Demo Workloads (~2 min)

```bash
# Deploy high-power test workloads
ssh -i oss-korea.pem ubuntu@57.182.90.243 \
  "sudo kubectl apply -f ~/carbon-kepler-mcp/test-workloads/high-power-app.yaml"

# Verify (should see 10 pods)
ssh -i oss-korea.pem ubuntu@57.182.90.243 \
  "sudo kubectl get pods -n demo-workloads"
```

### Update Claude Desktop Config (~1 min)

```bash
cat > ~/.config/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "carbon-kepler": {
      "url": "http://57.182.90.243:8000/sse",
      "transport": "sse"
    }
  }
}
EOF

# Restart Claude Desktop
pkill -f Claude
sleep 2
~/Downloads/nest-v0.8.9-linux-x86_64.AppImage &
```

---

## Demo Script (5-7 minutes)

### Slide 1: Context (1 min)
**Korean Regulatory Landscape**
- 🇰🇷 탄소중립 녹색성장 기본법 (Carbon Neutrality Act 2050)
- 🇰🇷 에너지이용 합리화법 (Energy Use Rationalization Act)
- Target: Carbon neutrality by 2050
- Problem: How do K8s operators identify inefficient workloads?

### Slide 2: Live Demo Part 1 - Detection (2 min)

**Run the strict compliance demo** (shows 10/10 violations):

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243 "
  sudo kubectl cp ~/carbon-kepler-mcp/test-workloads/demo-non-compliant.py carbon-mcp/\$(sudo kubectl get pod -n carbon-mcp -l app=carbon-mcp-server -o jsonpath='{.items[0].metadata.name}'):/tmp/demo.py && \
  sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 /tmp/demo.py | head -70
"
```

**Key Talking Points**:
- "Here we simulate a strict Green Cloud Initiative"
- "Target: 300 gCO2/kWh (30% better than grid average 424)"
- "PUE target: 1.2 (Tier-1 data center certification)"
- Point to screen: "All 10 workloads are NON-COMPLIANT ❌"
- "Total emissions: 38.68 kg CO2/month for just 10 workloads"
- "Imagine a cluster with 1,000+ workloads..."

### Slide 3: Live Demo Part 2 - MCP Integration (2 min)

**Option A**: If Claude Desktop is configured, show natural language query:
- Ask: "Which containers are consuming the most power?"
- MCP server responds with hotspot list + preventive actions

**Option B**: If no Claude Desktop, show the tools via CLI:

```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243

# Show demo workloads
sudo kubectl get pods -n demo-workloads

# Run power analysis (WORKING COMMAND - tested!)
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

    print(f'\nPower Analysis Results:')
    print(f'  Hotspots found: {len(hotspots)}')
    print(f'  Remediation actions: {len(actions)}')
    print()

    if hotspots:
        print('Top Power Consumers:')
        for h in hotspots[:5]:
            print(f'  {h.rank}. {h.name}: {h.power_watts:.6f}W')

asyncio.run(test())
"
```

**Key Talking Points**:
- "This is the MCP (Model Context Protocol) integration"
- "AI assistant can query Kepler metrics through natural language"
- "Tools automatically generate preventive actions"

### Slide 4: Preventive Actions (1-2 min)

Show the 4 action types from demo output:

1. **ALERT** [HIGH] - Immediate investigation for extreme power (>10W)
2. **RIGHTSIZING** [MEDIUM] - Optimize resource allocation (30% reduction)
3. **TEMPORAL_SHIFT** [MEDIUM] - Schedule for clean grid hours (2am-6am KST)
4. **REGIONAL_MIGRATION** [LOW] - Move to cleaner regions (Seoul 424 → Stockholm 50 gCO2/kWh)

**Key Talking Point**:
- "Total potential savings: 38W power, 11,768 kg CO2/month"
- "This is just from 10 workloads. Scale to 1,000 workloads = 1,176 tons CO2/month"

### Slide 5: Architecture (1 min)

Show the stack:
```
┌─────────────────────┐
│  Claude Desktop     │  ← AI Assistant
│  (User Interface)   │
└──────────┬──────────┘
           │ MCP Protocol (SSE)
┌──────────▼──────────┐
│  Carbon-Kepler MCP  │  ← 8 Tools (Python/FastMCP)
│  Server (FastMCP)   │
└──────────┬──────────┘
           │ HTTP
┌──────────▼──────────┐
│  Kepler (eBPF)      │  ← Power metrics via Prometheus
│  DaemonSet          │
└──────────┬──────────┘
           │ eBPF
┌──────────▼──────────┐
│  Linux Kernel       │  ← Energy counters (RAPL/perf)
│  (c5.metal)         │
└─────────────────────┘
```

**Key Talking Points**:
- "100% open source: Kepler + MCP + Claude"
- "Kepler uses eBPF for <1% overhead"
- "MCP enables any AI to access power metrics"
- "Works on AWS, on-prem, anywhere with Kubernetes"

### Slide 6: Korean Compliance (1 min)

Show the regulations:

**탄소중립 녹색성장 기본법 (Carbon Neutrality Act)**
- Target: 35% reduction by 2030 (vs 2018 baseline)
- Net zero by 2050
- Grid: 424 gCO2/kWh (coal 35%, gas 28%, nuclear 25%, renewable 12%)

**에너지이용 합리화법 (Energy Rationalization Act)**
- Green Data Center certification
- PUE ≤ 1.4 required
- Energy efficiency reporting mandatory

**Key Talking Point**:
- "Korean orgs need tools NOW to prepare for 2030/2050 targets"
- "This demo shows how to identify inefficient workloads before they violate regulations"

### Slide 7: Conclusion (30 sec)

**What you can do today**:
1. Deploy Kepler on your Kubernetes clusters
2. Connect MCP server for AI-powered insights
3. Start optimizing workloads proactively

**Resources**:
- Kepler: github.com/sustainable-computing-io/kepler
- MCP: github.com/anthropics/fastmcp
- This demo: [your repo URL]

---

## Backup Slides (If Demo Fails)

### Screenshots to have ready:
1. Terminal output of `demo-non-compliant.py` showing 10/10 violations
2. Power hotspot detection output
3. Preventive actions list
4. Architecture diagram
5. `kubectl get pods -A` showing all systems running

### Fallback narrative:
- "Here's what the output looks like when all systems are running..."
- "In testing, we identified 10 non-compliant workloads consuming 126W total"
- "The system generated 20 preventive actions automatically"
- Continue with architecture and Korean compliance slides

---

## Post-Demo

**CRITICAL**: Stop instance immediately to save costs!

```bash
cd aws-deployment && ./scripts/stop-instance.sh
# Saves $117/day
```

Verify stopped:
```bash
aws ec2 describe-instances --profile mgonzalezo --region us-east-1 \
  --instance-ids i-01d31a7c7323ef2f1 \
  --query 'Reservations[0].Instances[0].State.Name'
```

Expected: `"stopped"`

---

## Troubleshooting During Demo

**Issue**: SSH connection refused
**Fix**: Instance may still be starting, wait 2-3 minutes

**Issue**: Pods not ready
**Quick Check**:
```bash
ssh -i oss-korea.pem ubuntu@52.91.152.207 "sudo kubectl get pods -A | grep -v Running"
```
If anything not Running, switch to backup slides

**Issue**: Demo script fails
**Quick Recovery**:
```bash
# Show the simpler version
ssh -i oss-korea.pem ubuntu@52.91.152.207 "sudo kubectl exec -n carbon-mcp deployment/carbon-mcp-server -- python3 -c 'from src.kepler_client import KeplerClient; c = KeplerClient(\"http://kepler.kepler-system.svc.cluster.local:28282/metrics\"); print(f\"Total pods with metrics: {len(c.list_pods())}\")'"
```
Then switch to backup slides

**Issue**: Can't copy/paste commands
**Have these ready in a local file**:
- Save all demo commands to `/tmp/demo_commands.sh` before presentation
- Can source them quickly if needed

---

## Timing Notes

- Total demo time: 5-7 minutes
- SSH commands take ~5-10 seconds each
- `demo-non-compliant.py` takes ~3 seconds to run
- Power hotspot detection takes ~2 seconds
- Budget 1 extra minute for unexpected delays

---

## Contact Info to Share

**Kepler Project**: sustainable-computing-io@googlegroups.com
**MCP Protocol**: github.com/anthropics/fastmcp/issues
**This Demo**: [Your GitHub/Email]

---

**Good luck with your presentation!** 🚀🇰🇷

Remember: Even if the live demo fails, you have comprehensive backup slides and can show the code/architecture/results.

---

## Quick Command Reference

### Verify Kepler Metrics
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
curl -s http://localhost:30080/metrics | grep kepler_pod_cpu_watts | head -10
```

### Verify MCP Server
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl logs -n carbon-mcp -l app=carbon-mcp-server --tail=20
```

### Test Power Analysis (Verified Working!)
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
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
    print(f'Hotspots: {len(hotspots)}, Actions: {len(actions)}')

asyncio.run(test())
"
```

---

## Troubleshooting

### Instance won't start
```bash
aws ec2 start-instances --instance-ids i-013b5cd6ee511f107 --region ap-northeast-1 --profile mgonzalezo
# Wait 3 minutes
```

### MCP server pod crashed
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl delete pod -n carbon-mcp -l app=carbon-mcp-server
# Wait 30 seconds for auto-restart
```

### Kepler not collecting metrics
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler --tail=50
```

### Demo workloads not deployed
```bash
ssh -i oss-korea.pem ubuntu@57.182.90.243
sudo kubectl apply -f ~/Open-source-Summit-Korea-2025/carbon-kepler-mcp/test-workloads/high-power-app.yaml
```

---

## After Demo - Cleanup

```bash
# Stop instance to save costs (~$4/hour)
cd aws-deployment && ./scripts/stop-instance.sh

# Verify stopped
aws ec2 describe-instances --instance-ids i-013b5cd6ee511f107 --region ap-northeast-1 --profile mgonzalezo --query 'Reservations[0].Instances[0].State.Name'
# Expected: "stopped"
```

---

## Emergency Fallbacks

If **everything** fails during demo:

1. **Show slides only** - All architecture diagrams are self-explanatory
2. **Walk through code** - Show the 8 MCP tools in `src/mcp_server.py`
3. **Show GitHub repo** - Live code is always accessible
4. **Reference documentation** - Point to COMPLETE_DEMO_SCRIPT.md

**Remember**: The concept is solid even if live demo fails. Focus on the **why** (Korean regulations) and the **how** (MCP + Kepler).
