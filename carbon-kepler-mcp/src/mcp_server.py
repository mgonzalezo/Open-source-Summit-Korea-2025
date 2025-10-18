"""
Carbon-Aware Kepler MCP Server

FastMCP server providing tools for Korean regulatory compliance assessment
of Kubernetes workloads based on Kepler energy metrics.
"""

import os
from typing import Dict, List, Optional
import structlog
from fastmcp import FastMCP

from .kepler_client import KeplerClient
from .korea_compliance import (
    WorkloadMetrics,
    assess_korea_compliance,
    calculate_reduction_target,
    estimate_cost_savings
)
from .recommendation_engine import generate_recommendation, OptimizationSuggestion
from .compliance_standards import (
    KOREA_CARBON_NEUTRALITY,
    KOREA_PUE_GREEN_DC,
    REGIONAL_CARBON_INTENSITY,
    get_regional_carbon_intensity
)

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize MCP server
mcp = FastMCP("carbon-kepler-mcp")

# Initialize Kepler client
KEPLER_ENDPOINT = os.getenv(
    "KEPLER_ENDPOINT",
    "https://localhost:30443/metrics"
)
KOREA_CARBON_INTENSITY = float(os.getenv(
    "KOREA_CARBON_INTENSITY",
    str(KOREA_CARBON_NEUTRALITY.grid_carbon_intensity_gco2_kwh)
))
KOREA_PUE_TARGET = float(os.getenv(
    "KOREA_PUE_TARGET",
    str(KOREA_PUE_GREEN_DC.target_pue)
))

kepler_client = KeplerClient(endpoint=KEPLER_ENDPOINT)

logger.info(
    "mcp_server_initialized",
    kepler_endpoint=KEPLER_ENDPOINT,
    korea_carbon_intensity=KOREA_CARBON_INTENSITY,
    korea_pue_target=KOREA_PUE_TARGET
)


# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool()
async def assess_workload_compliance(
    workload_name: str,
    namespace: str = "default",
    standard: str = "KR_CARBON_2050",
    region: str = "ap-northeast-2"
) -> Dict:
    """
    Assess compliance of a Kubernetes workload with Korean regulatory standards.

    Evaluates both:
    1. Carbon Neutrality Act (탄소중립 녹색성장 기본법) - 424 gCO2eq/kWh target
    2. Energy Use Rationalization Act (에너지이용 합리화법) - PUE ≤ 1.4 target

    Args:
        workload_name: Pod or deployment name
        namespace: Kubernetes namespace (default: "default")
        standard: Compliance standard code (default: "KR_CARBON_2050")
        region: AWS region (default: "ap-northeast-2" for Seoul)

    Returns:
        Compliance assessment with status (COMPLIANT/NON_COMPLIANT) and recommendations
    """
    logger.info(
        "assessing_workload_compliance",
        workload=workload_name,
        namespace=namespace,
        standard=standard,
        region=region
    )

    try:
        # Fetch workload metrics from Kepler
        pod_metrics = kepler_client.get_pod_metrics(workload_name, namespace)
        node_metrics = kepler_client.get_node_metrics()

        # Create workload metrics object
        workload_metrics = WorkloadMetrics(
            cpu_watts=pod_metrics["cpu_watts"],
            memory_watts=pod_metrics["memory_watts"],
            gpu_watts=pod_metrics["gpu_watts"],
            other_watts=pod_metrics["other_watts"]
        )

        # Get regional carbon intensity
        regional_data = get_regional_carbon_intensity(region)
        if regional_data:
            grid_intensity = regional_data["average_gco2_kwh"]
        else:
            grid_intensity = KOREA_CARBON_INTENSITY

        # Assess compliance
        assessment = assess_korea_compliance(
            workload_name=workload_name,
            namespace=namespace,
            region=region,
            workload_metrics=workload_metrics,
            node_total_power_watts=node_metrics["cpu_watts"] + node_metrics["memory_watts"],
            grid_carbon_intensity_gco2_kwh=grid_intensity
        )

        # Generate recommendations
        recommendation = generate_recommendation(assessment, workload_metrics, region)

        # Build response
        response = {
            "workload": workload_name,
            "namespace": namespace,
            "standard": standard,
            "region": region,

            # Overall status
            "status": (
                "COMPLIANT" if (
                    assessment.carbon.status == "COMPLIANT" and
                    assessment.pue.status == "COMPLIANT"
                ) else "NON_COMPLIANT"
            ),

            # Carbon compliance
            "carbon_status": assessment.carbon.status,
            "current_carbon_intensity_gCO2eq_kWh": assessment.carbon.current_carbon_intensity_gco2_kwh,
            "target_carbon_intensity_gCO2eq_kWh": assessment.carbon.target_carbon_intensity_gco2_kwh,
            "grid_carbon_intensity_gCO2eq_kWh": assessment.carbon.grid_carbon_intensity_gco2_kwh,

            # PUE compliance
            "pue_status": assessment.pue.status,
            "current_pue": assessment.pue.current_pue,
            "target_pue": assessment.pue.target_pue,

            # Power and emissions
            "current_power_watts": assessment.power_watts,
            "hourly_emissions_gCO2eq": assessment.carbon.hourly_emissions_gco2,
            "monthly_emissions_kg": assessment.carbon.monthly_emissions_kg,

            # Recommendations
            "recommendation": recommendation.summary,
            "optimizations": [opt.dict() for opt in recommendation.optimizations],
            "priority_actions": recommendation.priority_actions,

            "timestamp": assessment.timestamp
        }

        logger.info(
            "workload_assessment_complete",
            workload=workload_name,
            status=response["status"],
            carbon_status=response["carbon_status"],
            pue_status=response["pue_status"]
        )

        return response

    except Exception as e:
        logger.error(
            "workload_assessment_failed",
            workload=workload_name,
            error=str(e)
        )
        raise


@mcp.tool()
async def compare_optimization_impact(
    workload_name: str,
    namespace: str = "default",
    optimizations: List[str] = ["temporal_shift", "resource_rightsizing"],
    standard: str = "KR_CARBON_2050",
    region: str = "ap-northeast-2"
) -> Dict:
    """
    Compare before/after carbon impact of applying optimizations.

    Args:
        workload_name: Pod or deployment name
        namespace: Kubernetes namespace (default: "default")
        optimizations: List of optimization types to apply
        standard: Compliance standard code (default: "KR_CARBON_2050")
        region: AWS region (default: "ap-northeast-2")

    Returns:
        Before/after comparison with estimated impact
    """
    logger.info(
        "comparing_optimization_impact",
        workload=workload_name,
        optimizations=optimizations
    )

    # Get current assessment
    current = await assess_workload_compliance(workload_name, namespace, standard, region)

    # Calculate optimized scenario
    total_reduction = 0.0
    applied_optimizations = []

    for opt in current.get("optimizations", []):
        if opt["type"] in optimizations:
            total_reduction += opt["estimated_reduction_percent"]
            applied_optimizations.append(opt)

    # Calculate new power and emissions
    current_power = current["current_power_watts"]
    optimized_power = calculate_reduction_target(current_power, total_reduction)

    # Estimate new emissions
    grid_intensity = current["grid_carbon_intensity_gCO2eq_kWh"]
    from .carbon_calculator import calculate_carbon_emissions, calculate_monthly_emissions, gco2_to_kg

    optimized_hourly_emissions = calculate_carbon_emissions(optimized_power, grid_intensity)
    optimized_monthly_emissions = gco2_to_kg(calculate_monthly_emissions(optimized_hourly_emissions))

    # Estimate cost savings
    power_reduction = current_power - optimized_power
    monthly_cost_savings = estimate_cost_savings(power_reduction)

    # Determine new compliance status
    optimized_intensity = grid_intensity  # Simplified
    optimized_status = (
        "COMPLIANT" if optimized_intensity <= current["target_carbon_intensity_gCO2eq_kWh"]
        else "NON_COMPLIANT"
    )

    response = {
        "workload": workload_name,
        "namespace": namespace,

        "current_status": current["status"],
        "current_power_watts": current_power,
        "current_emissions_gCO2eq_hour": current["hourly_emissions_gCO2eq"],
        "current_monthly_emissions_kg": current["monthly_emissions_kg"],

        "optimized_status": optimized_status,
        "optimized_power_watts": optimized_power,
        "optimized_emissions_gCO2eq_hour": optimized_hourly_emissions,
        "optimized_monthly_emissions_kg": optimized_monthly_emissions,

        "reduction_percent": total_reduction,
        "power_reduction_watts": power_reduction,
        "emissions_reduction_kg_month": current["monthly_emissions_kg"] - optimized_monthly_emissions,

        "estimated_cost_savings_usd_month": monthly_cost_savings,

        "applied_optimizations": applied_optimizations,
        "implementation_steps": [
            f"Apply {opt['type']}: {opt['description']}"
            for opt in applied_optimizations
        ]
    }

    return response


@mcp.tool()
async def list_workloads_by_compliance(
    namespace: str = "default",
    standard: str = "KR_CARBON_2050",
    status_filter: Optional[str] = None,
    region: str = "ap-northeast-2"
) -> Dict:
    """
    List all workloads in a namespace by compliance status.

    Args:
        namespace: Kubernetes namespace (default: "default")
        standard: Compliance standard code (default: "KR_CARBON_2050")
        status_filter: Filter by status ("COMPLIANT" or "NON_COMPLIANT")
        region: AWS region (default: "ap-northeast-2")

    Returns:
        Inventory of workloads with compliance summary
    """
    logger.info("listing_workloads", namespace=namespace)

    # Get all pods in namespace
    pods = kepler_client.list_pods(namespace)

    workloads = []
    compliant_count = 0
    non_compliant_count = 0

    for pod_info in pods:
        pod_name = pod_info["pod"]

        try:
            assessment = await assess_workload_compliance(
                pod_name,
                namespace,
                standard,
                region
            )

            if status_filter and assessment["status"] != status_filter:
                continue

            workloads.append({
                "workload": pod_name,
                "status": assessment["status"],
                "carbon_status": assessment["carbon_status"],
                "pue_status": assessment["pue_status"],
                "power_watts": assessment["current_power_watts"],
                "emissions_kg_month": assessment["monthly_emissions_kg"]
            })

            if assessment["status"] == "COMPLIANT":
                compliant_count += 1
            else:
                non_compliant_count += 1

        except Exception as e:
            logger.warning("workload_assessment_skipped", pod=pod_name, error=str(e))

    return {
        "namespace": namespace,
        "standard": standard,
        "total_workloads": len(workloads),
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "workloads": workloads
    }


@mcp.tool()
async def get_regional_comparison(
    workload_name: str,
    namespace: str = "default",
    current_region: str = "ap-northeast-2",
    comparison_regions: List[str] = ["us-east-1", "eu-north-1", "ap-northeast-1"]
) -> Dict:
    """
    Compare carbon impact of workload across AWS regions.

    Args:
        workload_name: Pod or deployment name
        namespace: Kubernetes namespace (default: "default")
        current_region: Current AWS region (default: "ap-northeast-2")
        comparison_regions: Regions to compare (default: us-east-1, eu-north-1, ap-northeast-1)

    Returns:
        Regional comparison with best region recommendation
    """
    logger.info("comparing_regions", workload=workload_name, regions=comparison_regions)

    # Get workload metrics
    pod_metrics = kepler_client.get_pod_metrics(workload_name, namespace)
    power_watts = (
        pod_metrics["cpu_watts"] +
        pod_metrics["memory_watts"] +
        pod_metrics["gpu_watts"]
    )

    from .carbon_calculator import calculate_carbon_emissions

    comparisons = []
    best_region = None
    best_intensity = float('inf')

    for region in [current_region] + comparison_regions:
        regional_data = get_regional_carbon_intensity(region)

        if not regional_data:
            continue

        intensity = regional_data["average_gco2_kwh"]
        emissions = calculate_carbon_emissions(power_watts, intensity)

        is_current = (region == current_region)
        is_compliant = intensity <= KOREA_CARBON_NEUTRALITY.target_carbon_intensity_gco2_kwh

        comparisons.append({
            "region": region,
            "region_name": regional_data["region_name"],
            "carbon_intensity_gCO2eq_kWh": intensity,
            "hourly_emissions_gCO2eq": emissions,
            "status": "COMPLIANT" if is_compliant else "NON_COMPLIANT",
            "is_current": is_current
        })

        if intensity < best_intensity:
            best_intensity = intensity
            best_region = regional_data["region_name"]

    # Sort by carbon intensity
    comparisons.sort(key=lambda x: x["carbon_intensity_gCO2eq_kWh"])

    current_intensity = get_regional_carbon_intensity(current_region)["average_gco2_kwh"]
    best_region_intensity = comparisons[0]["carbon_intensity_gCO2eq_kWh"]
    savings_percent = ((current_intensity - best_region_intensity) / current_intensity * 100)

    return {
        "workload": workload_name,
        "namespace": namespace,
        "power_watts": power_watts,
        "comparisons": comparisons,
        "best_region": comparisons[0]["region_name"],
        "best_region_savings_percent": savings_percent,
        "migration_recommendation": (
            f"Migrating to {comparisons[0]['region_name']} would reduce carbon emissions by "
            f"{savings_percent:.1f}%. Consider for batch workloads or latency-insensitive applications."
            if savings_percent > 10 else
            "Current region is already relatively clean. Migration not recommended."
        )
    }


@mcp.tool()
async def calculate_optimal_schedule(
    workload_name: str,
    namespace: str = "default",
    duration_hours: int = 4,
    region: str = "ap-northeast-2"
) -> Dict:
    """
    Find optimal time window for carbon-efficient workload scheduling.

    Note: This is a simplified version using static hourly profiles.
    Production version should integrate with Carbon Aware SDK for real-time data.

    Args:
        workload_name: Pod or deployment name
        namespace: Kubernetes namespace (default: "default")
        duration_hours: Required duration in hours (default: 4)
        region: AWS region (default: "ap-northeast-2")

    Returns:
        Optimal schedule recommendation
    """
    logger.info("calculating_optimal_schedule", workload=workload_name, duration=duration_hours)

    # Get workload power
    pod_metrics = kepler_client.get_pod_metrics(workload_name, namespace)
    power_watts = (
        pod_metrics["cpu_watts"] +
        pod_metrics["memory_watts"] +
        pod_metrics["gpu_watts"]
    )

    # Simplified hourly carbon intensity profile for Korea (ap-northeast-2)
    # In production, this should come from Carbon Aware SDK
    hourly_profile = {
        0: 380, 1: 375, 2: 370, 3: 365, 4: 370, 5: 380,  # Night (cleanest)
        6: 390, 7: 410, 8: 430, 9: 445, 10: 455, 11: 460,  # Morning ramp-up
        12: 465, 13: 470, 14: 475, 15: 470, 16: 465, 17: 460,  # Peak
        18: 450, 19: 440, 20: 425, 21: 410, 22: 400, 23: 390  # Evening decline
    }

    # Find cleanest window
    best_start_hour = 2  # 2am-6am is typically cleanest
    best_avg_intensity = sum(hourly_profile[h] for h in range(2, 6)) / 4

    current_hour = 14  # Assume current time is 2pm (peak)
    current_intensity = hourly_profile[current_hour]

    from .carbon_calculator import calculate_carbon_emissions

    current_emissions = calculate_carbon_emissions(power_watts, current_intensity, duration_hours)
    optimal_emissions = calculate_carbon_emissions(power_watts, best_avg_intensity, duration_hours)
    reduction = ((current_emissions - optimal_emissions) / current_emissions * 100)

    return {
        "workload": workload_name,
        "namespace": namespace,
        "duration_hours": duration_hours,

        "current_schedule": f"Running now (peak hours)",
        "current_carbon_intensity": current_intensity,
        "current_emissions_gCO2eq": current_emissions,

        "optimal_schedule": f"2am-{2+duration_hours}am KST (off-peak, cleanest grid)",
        "optimal_carbon_intensity": best_avg_intensity,
        "optimal_emissions_gCO2eq": optimal_emissions,

        "reduction_percent": reduction,

        "recommendation": (
            f"Rescheduling this {duration_hours}-hour workload to 2am-{2+duration_hours}am KST "
            f"would reduce carbon emissions by {reduction:.1f}%. "
            "Consider using Kubernetes CronJob for automated scheduling."
        )
    }


# ============================================================================
# MCP RESOURCES
# ============================================================================

@mcp.resource("compliance-standards://korea/{standard_code}")
async def get_korea_standard(standard_code: str) -> str:
    """
    Get Korean compliance standard details.

    URI: compliance-standards://korea/KR_CARBON_2050
    """
    if standard_code == "KR_CARBON_2050":
        return KOREA_CARBON_NEUTRALITY.json(indent=2)
    elif standard_code == "KR_PUE_GREEN_DC":
        return KOREA_PUE_GREEN_DC.json(indent=2)
    else:
        return f"Unknown standard: {standard_code}"


@mcp.resource("carbon-intensity://{region}")
async def get_carbon_intensity_data(region: str) -> str:
    """
    Get regional carbon intensity data.

    URI: carbon-intensity://ap-northeast-2
    """
    import json

    data = get_regional_carbon_intensity(region)
    if data:
        return json.dumps(data, indent=2)
    else:
        return f"No data available for region: {region}"


@mcp.resource("workload-metrics://{namespace}/{pod_name}")
async def get_workload_metrics_resource(namespace: str, pod_name: str) -> str:
    """
    Get Kepler metrics for a specific workload.

    URI: workload-metrics://default/my-app
    """
    import json

    try:
        metrics = kepler_client.get_pod_metrics(pod_name, namespace)
        total_watts = (
            metrics["cpu_watts"] +
            metrics["memory_watts"] +
            metrics["gpu_watts"] +
            metrics["other_watts"]
        )

        result = {
            "namespace": namespace,
            "pod": pod_name,
            "metrics": {
                "cpu_watts": metrics["cpu_watts"],
                "memory_watts": metrics["memory_watts"],
                "gpu_watts": metrics["gpu_watts"],
                "other_watts": metrics["other_watts"],
                "total_watts": total_watts,
                "joules_total": metrics["joules_total"]
            },
            "collection_method": "ebpf"
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return f"Error fetching metrics: {str(e)}"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Run MCP server with SSE transport for Kubernetes deployment
    logger.info("starting_carbon_kepler_mcp_server")

    # Get transport type from environment (default to SSE for K8s)
    transport = os.getenv("MCP_TRANSPORT", "sse")

    if transport == "sse":
        # Run with SSE transport on port 8000 for Kubernetes
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        logger.info("starting_sse_server", port=port)
        mcp.run(transport="sse")
    else:
        # Run with STDIO for local development
        mcp.run()
