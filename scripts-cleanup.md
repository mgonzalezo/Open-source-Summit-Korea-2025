# Scripts Cleanup Summary

Simplified script structure to include only essential scripts.

## Scripts Removed

### AWS Deployment Scripts (removed 4 of 6)
- check-stack.sh (removed - can use AWS CLI directly)
- start-stack.sh (removed - can use AWS console or CLI)
- stop-stack.sh (removed - can use AWS console or CLI)
- deploy-stack.sh (removed - replaced by create-stack.sh)

### AWS Deployment Scripts (kept 2)
- create-stack.sh (renamed from deploy-automated-stack.sh)
- delete-stack.sh

### Carbon MCP Scripts (removed 2 of 4)
- test-local.sh (removed - can use Python directly)
- test-mcp.sh (removed - can use curl directly)

### Carbon MCP Scripts (kept 2)
- build.sh
- deploy.sh

## Simplified Structure

### AWS Deployment
```
aws-deployment/scripts/
├── create-stack.sh    # Create and deploy CloudFormation stack
└── delete-stack.sh    # Delete stack and cleanup
```

### Carbon MCP Server
```
carbon-kepler-mcp/scripts/
├── build.sh          # Build Docker image
└── deploy.sh         # Deploy to K8s cluster
```

## Usage

### AWS Stack Management
```bash
# Create stack
cd aws-deployment/scripts
./create-stack.sh

# Delete stack
./delete-stack.sh
```

### AWS Instance Management (Use AWS CLI)
```bash
# Check status
aws cloudformation describe-stacks --stack-name kepler-k3s-stack

# Stop instance
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# Start instance
aws ec2 start-instances --instance-ids <INSTANCE_ID>
```

### Carbon MCP Deployment
```bash
# Build
cd carbon-kepler-mcp/scripts
./build.sh

# Deploy
./deploy.sh
```

### Testing (Use Direct Commands)
```bash
# Test Kepler metrics
curl -k https://<IP>:30443/metrics | grep kepler_node

# Test MCP server
curl -X POST http://<IP>:30800/tools/assess_workload_compliance \
  -H "Content-Type: application/json" \
  -d '{"workload_name": "app", "namespace": "prod"}'

# Run Python locally
python3 -m src.mcp_server
```

## Benefits

1. **Simpler maintenance** - Fewer scripts to update
2. **More flexible** - Use AWS CLI/Console for instance management
3. **Standard tools** - Use curl/Python directly for testing
4. **Clear purpose** - Each script has one clear job

## Migration Guide

### Old vs New

| Old Command | New Command |
|-------------|-------------|
| `./deploy-automated-stack.sh` | `./create-stack.sh` |
| `./deploy-stack.sh` | `./create-stack.sh` |
| `./check-stack.sh` | `aws cloudformation describe-stacks ...` |
| `./start-stack.sh` | `aws ec2 start-instances ...` |
| `./stop-stack.sh` | `aws ec2 stop-instances ...` |
| `./test-local.sh` | `python3 -m src.mcp_server` |
| `./test-mcp.sh` | `curl -X POST http://...` |

## Documentation Updated

All markdown files have been updated to reference the new simplified script structure.
