# aws bedrock + anthropic mcp integration plan

project: kepler energy monitoring with aws bedrock intelligence
target audience: aws top engineer presentation
aws solution coverage: 70%+ (from 20% current)
date: 2025-12-29

## executive summary

transform the current fastmcp-based carbon compliance solution into an enterprise-grade aws-powered platform that leverages:

- amazon bedrock for ai-powered compliance analysis
- anthropic's claude via bedrock for natural language processing
- aws lambda for serverless mcp tool execution
- amazon api gateway for secure api access
- aws privatelink for secure connectivity
- korean government apis for real-time carbon intensity data
- aws cloudwatch for observability
- amazon dynamodb for compliance history
- aws step functions for workflow orchestration

## current architecture (20% aws)

```
claude desktop (windows)
         |
         | SSE
         v
aws c5.metal (ap-northeast-1)
  |
  | k3s cluster
  |   |
  |   | fastmcp server (python)
  |   |  - 8 compliance tools
  |   |  - kepler client
  |   |
  |   | kepler v0.11.2
  |   |  - intel rapl (4 zones)
```

aws components: c5.metal instance only
open source: fastmcp, kepler, k3s

## target architecture (70%+ aws)

```
aws cloud services
  |
  | amazon bedrock (us-east-1)
  |   - claude 3.5 sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)
  |   - compliance analysis
  |   - natural language queries
  |   - recommendations generation
  |
  |   - amazon titan embeddings g1 - text
  |   - semantic search for historical compliance data
  |
  |        ^
  |        | aws privatelink
  |        |
  | mcp tool layer (serverless)
  |
  |   aws lambda functions (python 3.12)
  |     - tool 1: assess_workload_compliance_bedrock
  |     - tool 2: query_gov_carbon_intensity
  |     - tool 3: get_compliance_recommendations_ai
  |     - tool 4: analyze_power_trends_bedrock
  |     - tool 5: optimize_workload_placement
  |     - tool 6: predict_carbon_impact
  |     - tool 7: generate_compliance_report
  |     - tool 8: monitor_regulatory_changes
  |
  |   amazon api gateway (regional - ap-northeast-1)
  |     - rest api for mcp protocol
  |     - iam authentication
  |     - request validation
  |     - rate limiting & throttling
  |
  | data & storage layer
  |
  |   amazon dynamodb
  |     - compliance_assessments (historical data)
  |     - workload_metrics (time-series)
  |     - gov_api_cache (rate limit management)
  |     - compliance_trends (analytics)
  |
  |   amazon s3
  |     - compliance reports (pdf/json)
  |     - historical metrics backup
  |     - audit logs
  |
  |   amazon opensearch (optional)
  |     - advanced analytics
  |     - compliance dashboards
  |
  | orchestration & workflow
  |
  |   aws step functions
  |     - multi-workload compliance scan
  |     - government api data collection
  |     - scheduled compliance reporting
  |
  |   amazon eventbridge
  |     - schedule compliance checks
  |     - react to metric threshold violations
  |     - trigger alerts
  |
  | observability & security
  |
  |   amazon cloudwatch
  |     - lambda function metrics
  |     - api gateway logs
  |     - custom compliance metrics
  |     - alarms for non-compliance
  |
  |   aws x-ray
  |     - distributed tracing
  |     - performance bottleneck identification
  |
  |   aws secrets manager
  |     - government api credentials
  |     - bedrock access keys
  |
  |   aws iam
  |     - least privilege access
  |     - service-to-service authentication
  |
  |        ^
  |        | https
  |        |
  | monitoring infrastructure (hybrid)
  |
  |   aws c5.metal bare-metal instance (ap-northeast-1)
  |
  |     k3s kubernetes cluster
  |
  |       kepler v0.11.2 daemonset
  |         - intel rapl power measurement (4 zones)
  |         - real-time metrics export
  |         - http metrics endpoint
  |
  |       amazon cloudwatch agent
  |         - forward kepler metrics to cloudwatch
  |         - custom metric namespaces
  |
  |       metrics exporter service
  |         - rest api for lambda to query metrics
  |         - caching layer for performance
  |
  |     hardware specifications:
  |       - intel xeon platinum 8275cl (cascade lake)
  |       - 96 vcpus (2 sockets x 48 cores)
  |       - 192 gb ram (96 gb per socket)
  |       - 10 gbps network bandwidth
  |       - intel rapl support (bare-metal advantage)
  |       - 4 rapl zones: 2 cpu packages + 2 dram zones
  |
  |        ^
  |        |
  |  claude desktop (mcp client)
```

## korean government api integration

### target apis

1. 전력거래소 (kpx - korea power exchange)
   - real-time carbon intensity data
   - grid composition (renewable vs fossil fuel mix)
   - regional electricity pricing
   - api: https://openapi.kpx.or.kr/

2. 한국환경공단 (k-eco - korea environment corporation)
   - carbon emission factors
   - greenhouse gas inventory data
   - api: https://www.gir.go.kr/ (greenhouse gas inventory & research center)

3. 한국에너지공단 (kea - korea energy agency)
   - energy efficiency standards
   - data center pue benchmarks
   - api: tbd (requires registration)

4. 기상청 (kma - korea meteorological administration)
   - weather-based renewable energy forecasting
   - regional climate data
   - api: https://www.weather.go.kr/w/index.do

### api integration architecture

```python
# aws lambda function: query_gov_carbon_intensity
import boto3
import requests
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')
cache_table = dynamodb.Table('gov_api_cache')

def lambda_handler(event, context):
    """
    query korean government apis for real-time carbon intensity

    integrations:
    1. kpx api - real-time grid carbon intensity
    2. k-eco api - official emission factors
    3. dynamodb caching - reduce api calls (rate limiting)
    """

    region = event.get('region', 'ap-northeast-2')

    # check cache first (5-minute ttl)
    cached = get_cached_intensity(region)
    if cached:
        return cached

    # query kpx api
    kpx_credentials = get_secret('gov-api/kpx')
    carbon_intensity = query_kpx_api(kpx_credentials, region)

    # query k-eco for official factors
    keco_credentials = get_secret('gov-api/keco')
    emission_factors = query_keco_api(keco_credentials)

    # combine and cache
    result = {
        'region': region,
        'carbon_intensity_gco2_kwh': carbon_intensity,
        'emission_factors': emission_factors,
        'source': 'korean_government_apis',
        'timestamp': datetime.utcnow().isoformat(),
        'data_quality': 'official'
    }

    cache_intensity(region, result)
    return result
```

## implementation phases

### phase 1: aws foundation (week 1)

deliverables:
- aws account setup with proper iam roles
- amazon bedrock model access (claude 3.5 sonnet)
- vpc configuration with privatelink to bedrock
- dynamodb tables creation
- s3 buckets for reports and logs

steps:
1. enable bedrock in us-east-1
2. request access to claude 3.5 sonnet and titan embeddings
3. create vpc with private subnets
4. setup vpc endpoint for bedrock
5. create iam roles for lambda execution
6. deploy dynamodb tables (see schema below)
7. create s3 buckets with lifecycle policies

aws services used: bedrock, vpc, iam, dynamodb, s3

### phase 2: government api integration (week 1-2)

deliverables:
- korean government api registration
- credentials stored in aws secrets manager
- lambda functions for api queries
- dynamodb caching layer
- api gateway endpoints

steps:
1. register for kpx api access
2. register for k-eco api access
3. store credentials in secrets manager
4. implement lambda function: query_gov_carbon_intensity
5. implement lambda function: get_emission_factors
6. setup dynamodb caching with ttl
7. create api gateway rest api
8. configure iam authentication

aws services used: lambda, secrets manager, api gateway, dynamodb

### phase 3: mcp tool migration (week 2)

deliverables:
- 8 lambda functions implementing mcp tools
- bedrock integration for ai-powered analysis
- cloudwatch metrics and alarms
- x-ray tracing enabled

mcp tools as lambda functions:

1. assess_workload_compliance_bedrock
   - fetch kepler metrics from c5.metal
   - query government apis for current standards
   - use claude to analyze compliance
   - generate recommendations via bedrock
   - store results in dynamodb

2. query_gov_carbon_intensity
   - real-time carbon intensity from kpx
   - caching for rate limit compliance
   - regional carbon intensity mapping

3. get_compliance_recommendations_ai
   - use claude to generate tailored recommendations
   - consider workload characteristics
   - reference korean regulations
   - provide implementation steps

4. analyze_power_trends_bedrock
   - time-series analysis of power consumption
   - anomaly detection using bedrock
   - predictive analytics

5. optimize_workload_placement
   - regional carbon intensity comparison
   - cost analysis
   - latency considerations
   - claude-powered decision making

6. predict_carbon_impact
   - what-if scenario analysis
   - future carbon projections
   - bedrock-based forecasting

7. generate_compliance_report
   - pdf report generation
   - stored in s3
   - signed urls for sharing
   - claude-generated executive summary

8. monitor_regulatory_changes
   - web scraping of korean regulatory sites
   - nlp analysis via bedrock
   - alert when regulations change

steps:
1. create lambda layer with dependencies (boto3, requests)
2. implement each tool as separate lambda function
3. configure bedrock invocation permissions
4. setup cloudwatch log groups
5. enable x-ray tracing
6. create custom cloudwatch metrics
7. setup cloudwatch alarms for failures

aws services used: lambda, bedrock, cloudwatch, x-ray

### phase 4: workflow orchestration (week 3)

deliverables:
- step functions workflows
- eventbridge rules for scheduling
- automated compliance scanning
- alerting system

step functions workflows:

1. daily compliance scan
   - start
   - list all workloads (lambda)
   - for each workload:
     - fetch metrics (lambda)
     - query gov apis (lambda)
     - assess compliance (lambda + bedrock)
     - store results (dynamodb)
   - generate summary report (lambda + bedrock)
   - send to s3
   - trigger sns notification
   - end

2. real-time alert workflow
   - eventbridge detects high power consumption
   - fetch workload details (lambda)
   - assess compliance (lambda + bedrock)
   - if non-compliant:
     - generate recommendations (lambda + bedrock)
     - send sns alert
     - create incident ticket

steps:
1. design step functions state machines
2. implement workflow lambda functions
3. create eventbridge rules
4. configure sns topics for alerts
5. test end-to-end workflows
6. setup cloudwatch dashboards

aws services used: step functions, eventbridge, sns, cloudwatch

### phase 5: metrics pipeline (week 3)

deliverables:
- cloudwatch agent on c5.metal
- kepler metrics forwarded to cloudwatch
- custom metric namespaces
- metrics api for lambda consumption

architecture:
```
kepler (k3s) -> cloudwatch agent -> cloudwatch metrics
                                          |
                                          v
                                    lambda queries via cloudwatch api

alternative: kepler -> metrics exporter service -> lambda (http)
```

steps:
1. install cloudwatch agent on c5.metal
2. configure agent to scrape kepler metrics
3. create custom cloudwatch metric namespace: KeplerPowerMetrics
4. implement metrics exporter rest api (optional)
5. update lambda functions to query cloudwatch
6. optimize with caching

aws services used: cloudwatch, ec2 systems manager

### phase 6: client integration (week 4)

deliverables:
- mcp client library for api gateway
- claude desktop configuration
- testing and validation
- documentation

steps:
1. create mcp client for api gateway (http/rest)
2. implement authentication (iam sigv4)
3. update claude desktop config
4. end-to-end testing
5. performance optimization
6. documentation

aws services used: api gateway, iam

### phase 7: enhanced observability (week 4)

deliverables:
- cloudwatch dashboards
- cost tracking
- performance metrics
- compliance kpi dashboards

dashboards:
1. compliance overview
   - current compliance rate
   - trend over time
   - top non-compliant workloads

2. power consumption
   - real-time rapl metrics
   - per-workload breakdown
   - carbon intensity heatmap

3. api performance
   - lambda execution times
   - bedrock invocation latency
   - government api response times
   - error rates

4. cost tracking
   - bedrock token usage
   - lambda invocations
   - dynamodb capacity units
   - total monthly cost

steps:
1. create cloudwatch dashboards
2. configure custom metrics
3. setup cost allocation tags
4. create aws cost explorer reports
5. implement cost alerts

aws services used: cloudwatch, cost explorer, aws budgets

## dynamodb schema

### table: compliance_assessments

partition key: workload_id (string)
sort key: timestamp (number - unix timestamp)

attributes:
- workload_name (string)
- namespace (string)
- region (string)
- compliance_status (string) - "compliant" | "non_compliant"
- carbon_status (string)
- pue_status (string)
- power_watts (number)
- carbon_intensity_gco2_kwh (number)
- monthly_emissions_kg (number)
- recommendations (list)
- ai_analysis (string) - claude's assessment
- gov_api_data (map) - raw government api response
- ttl (number) - 90 days retention

### table: workload_metrics

partition key: workload_id (string)
sort key: timestamp (number)

attributes:
- cpu_watts (number)
- dram_watts (number)
- total_watts (number)
- rapl_package_0_joules (number)
- rapl_package_1_joules (number)
- rapl_dram_0_joules (number)
- rapl_dram_1_joules (number)
- ttl (number) - 30 days retention

### table: gov_api_cache

partition key: api_endpoint (string)
sort key: region (string)

attributes:
- response_data (map)
- cached_at (number - unix timestamp)
- ttl (number) - 5 minutes for real-time data

### table: compliance_trends

partition key: date (string - yyyy-mm-dd)
sort key: metric_type (string)

attributes:
- total_workloads (number)
- compliant_count (number)
- non_compliant_count (number)
- average_power_watts (number)
- total_carbon_kg (number)
- top_consumers (list)

## cost estimation

### monthly costs (estimated)

| aws service | usage | cost |
|-------------|-------|------|
| amazon bedrock | 1m tokens/day x 30 days | $90-180 |
| aws lambda | 10k invocations/day x 30 days | $5-10 |
| amazon dynamodb | 1gb storage, 10k rcu/wcu | $15-25 |
| amazon s3 | 100gb storage, 1k requests | $5 |
| api gateway | 1m requests/month | $3.50 |
| cloudwatch | custom metrics, logs | $20-30 |
| vpc privatelink | 720 hours | $7.20 |
| c5.metal | 720 hours @ $4.08/hr | $2,937.60 |
| data transfer | 100gb out | $9 |
| step functions | 10k state transitions | $0.25 |
| secrets manager | 5 secrets | $2.50 |
| x-ray | 1m traces | $5 |
| total (without c5.metal) | | $162-278 |
| total (with c5.metal) | | $3,100-3,215 |

cost optimization:
- use spot instances for non-critical workloads
- implement aggressive caching
- use dynamodb on-demand pricing
- compress cloudwatch logs
- use s3 intelligent-tiering

## security considerations

### iam policies

1. lambda execution role
   - bedrock: invokemodel permission
   - dynamodb: read/write to specific tables
   - secrets manager: getsecretvalue
   - cloudwatch: putmetricdata, createloggroup
   - x-ray: puttracesegments

2. api gateway
   - iam authentication required
   - resource policies to restrict access
   - request throttling

3. vpc endpoint
   - private subnet only
   - security group restricts access to lambda

### data protection

- encryption at rest (dynamodb, s3)
- encryption in transit (tls 1.2+)
- secrets rotation via secrets manager
- no pii in logs
- compliance data retention policies

## testing strategy

### unit tests
- each lambda function
- government api mocking
- bedrock response mocking

### integration tests
- end-to-end mcp tool execution
- government api integration
- bedrock integration
- dynamodb operations

### performance tests
- concurrent lambda executions
- api gateway load testing
- bedrock rate limiting
- cloudwatch metric ingestion

### compliance tests
- verify korean regulation calculations
- validate government api data accuracy
- test alert thresholds

## migration path

### parallel deployment (recommended)

1. deploy aws bedrock architecture alongside existing fastmcp
2. route 10% of traffic to new architecture
3. compare results for accuracy
4. gradually increase traffic to 100%
5. deprecate fastmcp

### cutover strategy

- feature flag in kepler metrics exporter
- dual-write to both systems during transition
- rollback plan if issues detected

## success metrics

1. aws solution coverage: >70% (measured by service count and criticality)
2. latency: <2s for compliance assessment
3. accuracy: 100% match with government api data
4. cost: <$300/month (excluding c5.metal)
5. uptime: 99.9% availability
6. compliance: real-time korean regulation updates

## next steps

1. review and approve this plan
2. begin phase 1: aws foundation
3. register for korean government apis
4. implement lambda functions
5. test and validate
6. prepare presentation materials

## appendix: bare-metal server details

### aws c5.metal specifications

instance type: c5.metal
region: ap-northeast-1 (tokyo)
pricing: ~$4.08/hour on-demand

#### hardware configuration

processor:
- model: intel xeon platinum 8275cl (cascade lake)
- architecture: x86_64
- base frequency: 3.0 ghz
- turbo frequency: 3.6 ghz
- sockets: 2
- cores per socket: 48
- total vcpus: 96
- hyper-threading: enabled (192 threads)
- cache: l1: 3 mb, l2: 48 mb, l3: 35.75 mb per socket
- instruction sets: avx-512, aes-ni

memory:
- total ram: 192 gb (ddr4)
- configuration: 96 gb per socket
- memory channels: 6 per socket
- speed: 2933 mt/s
- ecc: enabled

storage:
- ebs-optimized: yes
- max ebs bandwidth: 19 gbps
- max iops: 80,000
- storage type: gp3 ssd recommended

network:
- network performance: 25 gbps
- enhanced networking: enabled (ena)
- network interface cards: 4 x 25 gbps
- ipv6 support: yes
- placement groups: supported

power measurement:
- rapl support: native hardware support
- rapl zones: 4 active zones
  - package-0: cpu socket 0
  - package-1: cpu socket 1
  - dram-0: memory socket 0
  - dram-1: memory socket 1
- measurement precision: microjoule (μJ)
- update frequency: ~1ms hardware, 5s kepler aggregation
- power range: 0-200w per package

#### why bare-metal for this use case?

1. native rapl access
   - virtualized instances don't expose rapl counters
   - bare-metal provides direct hardware energy measurement
   - required for accurate power attribution

2. no hypervisor overhead
   - direct kernel access to msr (model-specific registers)
   - full control over power management
   - deterministic performance

3. compliance requirements
   - korean regulations require accurate power measurement
   - hardware-level precision meets audit standards
   - traceable to physical energy consumption

4. performance
   - 96 dedicated vcpus
   - no noisy neighbor issues
   - consistent baseline performance

#### rapl architecture on c5.metal

```
hardware layer:
  cpu package 0 (48 cores)
    msr 0x611 (pkg_energy_status)
    msr 0x619 (dram_energy_status)
  cpu package 1 (48 cores)
    msr 0x611 (pkg_energy_status)
    msr 0x619 (dram_energy_status)

kernel modules:
  msr (model-specific register access)
  intel_rapl_common (rapl framework)
  intel_rapl_msr (msr-based rapl interface)

sysfs interface:
  /sys/class/powercap/intel-rapl:0/ (package-0)
    energy_uj (cumulative microjoules)
    max_energy_range_uj (rollover threshold)
    name
  /sys/class/powercap/intel-rapl:1/ (package-1)
  /sys/class/powercap/intel-rapl:0:0/ (dram-0)
  /sys/class/powercap/intel-rapl:1:0/ (dram-1)

kepler access:
  reads energy_uj every 5 seconds
  calculates: power (w) = delta_energy (j) / delta_time (s)
```

#### instance lifecycle management

start/stop for cost savings:
- stopped: only pay for ebs storage (~$20/month)
- running: full instance cost ($4.08/hr)
- recommendation: stop when not presenting

deployment time:
- cloudformation stack: ~15 minutes
- includes: k3s, kepler, rapl modules, test workloads
- fully automated via userdata script

cost-saving strategy:
```bash
# stop instance after demo
aws ec2 stop-instances --instance-ids i-xxxxx

# start before next presentation
aws ec2 start-instances --instance-ids i-xxxxx

# savings: ~$3,000/month when stopped
```

## references

- amazon bedrock documentation: https://docs.aws.amazon.com/bedrock/
- anthropic claude models: https://www.anthropic.com/claude
- korean government open data portal: https://www.data.go.kr/
- kpx api documentation: https://openapi.kpx.or.kr/
- intel rapl documentation: https://www.kernel.org/doc/html/latest/power/powercap/powercap.html
- aws lambda best practices: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- model context protocol specification: https://spec.modelcontextprotocol.io/
