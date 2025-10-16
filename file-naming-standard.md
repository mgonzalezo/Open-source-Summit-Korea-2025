# File Naming Standard

All files in this repository follow lowercase naming conventions with hyphens as word separators.

## Standard Format

- Use lowercase letters only
- Separate words with hyphens (-)
- Use descriptive names
- Avoid special characters except hyphens and underscores

## Examples

### Documentation Files
```
readme.md                  (not README.md)
deployment-guide.md        (not Deployment-Guide.md)
architecture-roles.md      (not ARCHITECTURE_ROLES.md)
demo-guide.md             (not DEMO_GUIDE.md)
implementation-status.md   (not IMPLEMENTATION_STATUS.md)
```

### Configuration Files
```
carbon-intensity.json     (not Carbon-Intensity.json)
regulations.json          (not Regulations.json)
regions.json             (not Regions.json)
```

### Script Files
```
build.sh                 (not Build.sh)
deploy.sh                (not Deploy.sh)
test-local.sh            (not Test-Local.sh)
```

### Python Modules
```
mcp_server.py            (underscores for Python modules)
kepler_client.py
korea_compliance.py
```

## Renamed Files

### Main Directory
- README.md → readme.md
- CLEANUP_SUMMARY.md → cleanup-summary.md

### AWS Deployment
- aws-deployment/docs/CLOUDFORMATION-README.md → cloudformation-readme.md

### Carbon MCP Server
- carbon-kepler-mcp/README.md → readme.md
- carbon-kepler-mcp/ARCHITECTURE_ROLES.md → architecture-roles.md
- carbon-kepler-mcp/DEMO_GUIDE.md → demo-guide.md
- carbon-kepler-mcp/IMPLEMENTATION_STATUS.md → implementation-status.md

## Python Module Convention

Python modules use underscores (_) as per PEP 8 style guide:
- mcp_server.py
- kepler_client.py
- korea_compliance.py
- compliance_standards.py
- recommendation_engine.py
- prometheus_parser.py
- carbon_calculator.py

## Directory Names

All directory names are lowercase with hyphens:
- aws-deployment/
- carbon-kepler-mcp/
- carbon-kepler-mcp/src/
- carbon-kepler-mcp/k8s/
- carbon-kepler-mcp/config/
- carbon-kepler-mcp/scripts/
- carbon-kepler-mcp/tests/

## Future Files

All new files should follow this lowercase convention.
