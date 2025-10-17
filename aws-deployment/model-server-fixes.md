# Model Server Deployment Fixes

## Issue Summary

When deploying Kepler with the automated CloudFormation template, the Model Server was failing to start and couldn't connect to Kepler. This document explains what went wrong and how it was fixed.

## Problems Identified

### 1. Missing Container Command (Critical)

**Problem**: The Model Server container was using the default entrypoint from the Docker image, which requires a command argument but none was provided.

**Error**:
```
usage: kepler-model [-h] ... command
kepler-model: error: the following arguments are required: command
```

**Root Cause**: The `quay.io/sustainable_computing_io/kepler_model_server:latest` image changed its entrypoint to require explicit command specification.

**Fix**: Added the correct command to start the model server:
```yaml
command:
- python3
- -u
- /kepler_model/src/kepler_model/server/model_server.py
```

### 2. Service Selector Mismatch (Critical)

**Problem**: The Kubernetes Service selector didn't match the pod labels, causing zero endpoints and preventing Kepler from connecting.

**Symptoms**:
```bash
$ kubectl get endpoints -n kepler-model-server
NAME                  ENDPOINTS   AGE
kepler-model-server   <none>      62m
```

**Root Cause**:
- **Service selector** was looking for: `app.kubernetes.io/component=model-server` AND `app.kubernetes.io/name=kepler-model-server`
- **Pod labels** only had: `app.kubernetes.io/component=model-server` AND `app.kubernetes.io/name=kepler-model-server`
- But after deployment recreation, pods only had: `app=kepler-model-server`

**Fix**: Simplified to use consistent `app=kepler-model-server` label across both:
```yaml
# Deployment
selector:
  matchLabels:
    app: kepler-model-server
template:
  metadata:
    labels:
      app: kepler-model-server

# Service
selector:
  app: kepler-model-server
```

### 3. Incorrect targetPort in Service

**Problem**: Service was using named port `targetPort: http` but this requires the container port to also be named.

**Fix**: Changed to explicit port number:
```yaml
ports:
  - name: http
    port: 8100
    targetPort: 8100  # Was: targetPort: http
    protocol: TCP
```

## Changes Made to CloudFormation Template

File: `aws-deployment/templates/kepler-k3s-automated-stack.yaml`

### Lines 377-386: Simplified Labels
**Before**:
```yaml
labels:
  app.kubernetes.io/component: model-server
  app.kubernetes.io/name: kepler-model-server
selector:
  matchLabels:
    app.kubernetes.io/component: model-server
    app.kubernetes.io/name: kepler-model-server
```

**After**:
```yaml
labels:
  app: kepler-model-server
selector:
  matchLabels:
    app: kepler-model-server
```

### Lines 392-395: Added Container Command
**Before**:
```yaml
containers:
- name: server-api
  image: quay.io/sustainable_computing_io/kepler_model_server:latest
  imagePullPolicy: Always
  ports:
```

**After**:
```yaml
containers:
- name: server-api
  image: quay.io/sustainable_computing_io/kepler_model_server:latest
  imagePullPolicy: Always
  command:
  - python3
  - -u
  - /kepler_model/src/kepler_model/server/model_server.py
  ports:
```

### Lines 429-437: Fixed Service Selector and Port
**Before**:
```yaml
labels:
  app.kubernetes.io/component: model-server
  app.kubernetes.io/name: kepler-model-server
spec:
  selector:
    app.kubernetes.io/component: model-server
    app.kubernetes.io/name: kepler-model-server
  ports:
    - name: http
      port: 8100
      targetPort: http
```

**After**:
```yaml
labels:
  app: kepler-model-server
spec:
  selector:
    app: kepler-model-server
  ports:
    - name: http
      port: 8100
      targetPort: 8100
```

### Line 445: Fixed Wait Command Label
**Before**:
```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kepler-model-server -n kepler-model-server --timeout=300s
```

**After**:
```bash
kubectl wait --for=condition=ready pod -l app=kepler-model-server -n kepler-model-server --timeout=300s
```

## Verification

After fixing, verify Model Server is working:

```bash
# Check pod is running
kubectl get pods -n kepler-model-server
# Should show: kepler-model-server-xxx   1/1     Running

# Check service has endpoints
kubectl get endpoints -n kepler-model-server
# Should show: kepler-model-server   10.42.0.x:8100

# Test Model Server API
kubectl exec -n kepler-system <kepler-pod> -- curl -s http://kepler-model-server.kepler-model-server.svc.cluster.local:8100/best-models
# Should return JSON with model information

# Check Model Server logs
kubectl logs -n kepler-model-server -l app=kepler-model-server
# Should show: "initial pipeline is loaded to /mnt/models/ec2-0.7.11"
#              "initial pipeline is loaded to /mnt/models/specpower-0.7.11"
#              "Running on http://0.0.0.0:8100"
```

## Why This Happened

1. **Image Evolution**: The Model Server image maintainers changed the entrypoint between versions, requiring explicit command specification.

2. **Label Complexity**: Using multiple Kubernetes-style labels (`app.kubernetes.io/*`) created complexity and potential for mismatch. Simpler labels (`app=name`) are more reliable.

3. **Port Naming**: Named ports add a layer of indirection that can fail if not configured on both sides.

## Prevention for Future Deployments

The updated CloudFormation template now includes:

1.  Explicit container command for Model Server
2.  Simple, consistent labels across all resources
3.  Explicit port numbers instead of named port references
4.  Correct label selectors in wait commands

**Result**: Future deployments using `scripts/create-stack.sh` will work without manual intervention.

## ML Models Loaded

When working correctly, the Model Server loads:

- **ec2-0.7.11**: Trained on AWS EC2 instances for RAPL-based power estimation
- **specpower-0.7.11**: Trained on SPECpower data for ACPI-based estimation

These models provide ML-based power consumption estimates based on real eBPF metrics (CPU cycles, instructions, cache misses, etc.) collected by Kepler.

## Related Files

- CloudFormation template: [kepler-k3s-automated-stack.yaml](templates/kepler-k3s-automated-stack.yaml)
- Deployment script: [create-stack.sh](scripts/create-stack.sh)
- Technical guide: [kepler-deployment-summary.md](kepler-deployment-summary.md)
