"""
Carbon-Aware Kepler MCP Server

FastMCP server providing tools for Korean regulatory compliance assessment
of Kubernetes workloads based on Kepler energy metrics.
"""

import os
import math
from typing import Dict, List, Optional, Any
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
    REGIONAL_PUE_DATA,
    get_regional_carbon_intensity,
    get_regional_pue
)
from .power_hotspot_tools import PowerHotspotDetector, PowerConsumer, PreventiveAction

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def sanitize_float(value: float) -> float:
    """Sanitize float values to ensure JSON compatibility"""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return value


def sanitize_dict(data: Any) -> Any:
    """Recursively sanitize dictionary to ensure all floats are JSON-safe"""
    if isinstance(data, dict):
        return {k: sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    elif isinstance(data, float):
        return sanitize_float(data)
    return data


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

# Initialize power hotspot detector (inspired by Kepler PR #2250)
hotspot_detector = PowerHotspotDetector(
    kepler_client=kepler_client,
    carbon_intensity_gco2_kwh=KOREA_CARBON_INTENSITY,
    pue_target=KOREA_PUE_TARGET
)

logger.info(
    "mcp_server_initialized",
    kepler_endpoint=KEPLER_ENDPOINT,
    korea_carbon_intensity=KOREA_CARBON_INTENSITY,
    korea_pue_target=KOREA_PUE_TARGET
)


# Helper function: Convert RAPL joules to watts
# IMPORTANT: RAPL metrics are cumulative energy counters in joules.
# To get power (watts), you need two measurements over time:
# watts = (joules_t2 - joules_t1) / (time_t2 - time_t1)
#
# For simplicity in this MCP server, we approximate watts by assuming
# a 5-second collection interval (Kepler default) and using the total_joules
# as a proxy. This is a SIMPLIFICATION - ideally you'd track deltas over time.
#
# Formula used: estimated_watts ≈ total_joules / assumed_uptime_seconds
# Better approach: Use Prometheus rate() function or track metrics over time
def estimate_watts_from_joules(joules_metrics: Dict[str, float], interval_seconds: float = 5.0) -> float:
    """
    Estimate current power (watts) from RAPL joules metrics.

    Args:
        joules_metrics: Dict with keys like 'total_joules', 'cpu_joules_total', etc.
        interval_seconds: Kepler collection interval (default: 5 seconds)

    Returns:
        Estimated power in watts

    Note: This is a ROUGH ESTIMATE. For accurate watts, you need:
          1. Two joules measurements (t1 and t2)
          2. Calculate: watts = (joules_t2 - joules_t1) / (t2 - t1)
    """
    total_joules = joules_metrics.get("total_joules", 0.0)

    if total_joules == 0:
        return 0.0

    # Rough estimate: assume metrics represent recent interval
    # This is NOT accurate for absolute values but gives relative comparison
    estimated_watts = total_joules / interval_seconds

    logger.debug(
        "watts_estimated_from_joules",
        total_joules=total_joules,
        interval_seconds=interval_seconds,
        estimated_watts=estimated_watts
    )

    return estimated_watts


# ============================================================================
# MCP TOOLS
# ============================================================================

# Helper function for compliance assessment (shared by multiple tools)
def _perform_workload_compliance_assessment(
    workload_name: str,
    namespace: str,
    standard: str,
    region: str
) -> Dict:
    """
    Internal helper to perform compliance assessment.

    This function contains the core logic extracted from assess_workload_compliance
    so it can be reused by list_workloads_by_compliance without circular tool calls.
    """
    # Fetch workload power metrics from Kepler (calculates watts from joule deltas)
    pod_power = kepler_client.get_pod_power_watts(workload_name, namespace)
    node_metrics = kepler_client.get_node_metrics()

    # Create workload metrics object
    # Note: Kepler v0.11.2 on AWS c5.metal only exposes CPU metrics at pod level
    workload_metrics = WorkloadMetrics(
        cpu_watts=pod_power.get("total_watts", 0.0),  # Use total_watts (CPU + DRAM)
        memory_watts=0.0,  # Not available in Kepler v0.11.2 at pod level
        gpu_watts=0.0,     # Not available in Kepler v0.11.2 at pod level
        other_watts=0.0    # Not available in Kepler v0.11.2 at pod level
    )

    # Get regional carbon intensity
    regional_data = get_regional_carbon_intensity(region)
    if regional_data:
        grid_intensity = regional_data["average_gco2_kwh"]
    else:
        grid_intensity = KOREA_CARBON_INTENSITY

    # Assess compliance
    # Note: Using CPU watts only since memory/GPU not available at pod level in Kepler v0.11.2
    assessment = assess_korea_compliance(
        workload_name=workload_name,
        namespace=namespace,
        region=region,
        workload_metrics=workload_metrics,
        node_total_power_watts=node_metrics.get("cpu_watts_total", 0.0),
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

    return response


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
        response = _perform_workload_compliance_assessment(
            workload_name, namespace, standard, region
        )

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

    # OPTIMIZATION: Fetch all shared data once for all pods (not per pod in loop)
    regional_data = get_regional_carbon_intensity(region)
    grid_intensity = regional_data["average_gco2_kwh"] if regional_data else KOREA_CARBON_INTENSITY

    # Pre-fetch regional PUE once (not per pod)
    regional_pue_data = get_regional_pue(region)
    regional_pue = regional_pue_data.get("typical_pue") if regional_pue_data else 1.4

    from .korea_compliance import assess_carbon_compliance, PUEComplianceResult

    workloads = []
    compliant_count = 0
    non_compliant_count = 0

    for pod_info in pods:
        pod_name = pod_info["pod"]

        try:
            # Fetch pod power (uses cache after first call)
            pod_power = kepler_client.get_pod_power_watts(pod_name, namespace)
            power_watts = pod_power.get("total_watts", 0.0)

            # Quick carbon compliance check
            carbon_result = assess_carbon_compliance(
                power_watts,
                grid_intensity
            )

            # Quick PUE compliance check (using pre-fetched regional PUE)
            pue_result = PUEComplianceResult(
                status="COMPLIANT" if regional_pue <= KOREA_PUE_TARGET else "NON_COMPLIANT",
                current_pue=regional_pue,
                target_pue=KOREA_PUE_TARGET,
                gap_percent=((regional_pue - KOREA_PUE_TARGET) / KOREA_PUE_TARGET * 100)
            )

            overall_status = (
                "COMPLIANT" if (
                    carbon_result.status == "COMPLIANT" and
                    pue_result.status == "COMPLIANT"
                ) else "NON_COMPLIANT"
            )

            if status_filter and overall_status != status_filter:
                continue

            workloads.append({
                "workload": pod_name,
                "status": overall_status,
                "carbon_status": carbon_result.status,
                "pue_status": pue_result.status,
                "power_watts": power_watts,
                "emissions_kg_month": carbon_result.monthly_emissions_kg
            })

            if overall_status == "COMPLIANT":
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
async def get_migration_recommendations(
    workload_name: str,
    namespace: str = "default",
    current_region: str = "ap-northeast-2",
    threshold_gco2_kwh: float = 424.0
) -> Dict:
    """
    Get recommended regions for workload migration based on carbon compliance.

    Automatically recommends cleaner regions when workload approaches or exceeds
    the Korean carbon target (424 gCO2eq/kWh). Considers BOTH Korean regulatory
    requirements:
    - Carbon Intensity ≤ 424 gCO2eq/kWh (탄소중립법)
    - PUE ≤ 1.4 (에너지합리화법 - Green DC certification)

    Args:
        workload_name: Pod or deployment name
        namespace: Kubernetes namespace (default: "default")
        current_region: Current AWS region (default: "ap-northeast-2" Seoul)
        threshold_gco2_kwh: Carbon threshold to trigger recommendations (default: 424)

    Returns:
        Migration recommendations ranked by carbon savings (primary) and PUE (secondary)
    """
    logger.info("get_migration_recommendations",
                workload=workload_name,
                threshold=threshold_gco2_kwh)

    # Get workload power
    pod_power = kepler_client.get_pod_power_watts(workload_name, namespace)
    power_watts = pod_power.get("total_watts", 0.0)

    from .carbon_calculator import calculate_carbon_emissions

    # Get current region data
    current_data = get_regional_carbon_intensity(current_region)
    if not current_data:
        return {"error": f"Unknown region: {current_region}"}

    current_intensity = current_data["average_gco2_kwh"]
    current_emissions = calculate_carbon_emissions(power_watts, current_intensity)

    # Get current region PUE
    current_pue_data = get_regional_pue(current_region)
    current_pue = current_pue_data.get("typical_pue") if current_pue_data else None

    # Check if we're approaching/exceeding threshold
    threshold_percent = (current_intensity / threshold_gco2_kwh) * 100
    needs_migration = current_intensity >= (threshold_gco2_kwh * 0.9)  # 90% threshold

    # Compare ALL available regions
    all_regions = REGIONAL_CARBON_INTENSITY.keys()
    recommendations = []

    for region in all_regions:
        if region == current_region:
            continue  # Skip current region

        regional_data = get_regional_carbon_intensity(region)
        intensity = regional_data["average_gco2_kwh"]
        emissions = calculate_carbon_emissions(power_watts, intensity)

        savings_gco2 = current_emissions - emissions
        savings_percent = ((current_intensity - intensity) / current_intensity * 100)

        # Get PUE data for this region
        pue_data = get_regional_pue(region)
        typical_pue = pue_data.get("typical_pue") if pue_data else None
        meets_pue_target = (typical_pue <= KOREA_PUE_GREEN_DC.target_pue) if typical_pue else None

        # Only recommend regions that are cleaner
        if savings_percent > 0:
            recommendation = {
                "region_code": region,
                "region_name": regional_data["region_name"],
                "carbon_intensity_gco2_kwh": intensity,
                "estimated_emissions_gco2_hour": emissions,
                "savings_gco2_hour": savings_gco2,
                "savings_percent": savings_percent,
                "grid_mix": regional_data.get("grid_mix", {}),
                "meets_korean_target": intensity <= threshold_gco2_kwh,
                "source": regional_data.get("source", "")
            }

            # Add PUE data if available
            if typical_pue is not None:
                recommendation["typical_pue"] = typical_pue
                recommendation["meets_pue_target"] = meets_pue_target
                if pue_data:
                    recommendation["pue_data_center_type"] = pue_data.get("data_center_type", "")

            recommendations.append(recommendation)

    # Sort by savings percent (primary), then by PUE (secondary - lower is better)
    recommendations.sort(key=lambda x: (-x["savings_percent"], x.get("typical_pue", 999)))

    # Create status message
    if current_intensity >= threshold_gco2_kwh:
        status = "⚠️ EXCEEDS THRESHOLD"
        urgency = "HIGH"
        message = (f"Current region ({current_data['region_name']}) exceeds Korean carbon target "
                  f"by {threshold_percent - 100:.1f}%. Migration RECOMMENDED.")
    elif needs_migration:
        status = "⚠️ APPROACHING THRESHOLD"
        urgency = "MEDIUM"
        message = (f"Current region at {threshold_percent:.1f}% of Korean target. "
                  f"Consider migration to maintain compliance buffer.")
    else:
        status = "✅ BELOW THRESHOLD"
        urgency = "LOW"
        message = (f"Current region at {threshold_percent:.1f}% of threshold. "
                  f"Migration optional for further optimization.")

    # Build current region info
    current_region_info = {
        "code": current_region,
        "name": current_data["region_name"],
        "carbon_intensity_gco2_kwh": current_intensity,
        "current_emissions_gco2_hour": current_emissions,
        "threshold_gco2_kwh": threshold_gco2_kwh,
        "threshold_percent": threshold_percent
    }

    # Add PUE info if available
    if current_pue is not None:
        current_region_info["typical_pue"] = current_pue
        current_region_info["meets_pue_target"] = current_pue <= KOREA_PUE_GREEN_DC.target_pue
        current_region_info["pue_target"] = KOREA_PUE_GREEN_DC.target_pue

    return {
        "workload": workload_name,
        "namespace": namespace,
        "power_watts": power_watts,
        "current_region": current_region_info,
        "status": status,
        "urgency": urgency,
        "message": message,
        "recommended_regions": recommendations[:5],  # Top 5 best options
        "total_regions_analyzed": len(all_regions),
        "migration_note": (
            "Consider latency requirements, data residency regulations, "
            "and application architecture before migration. "
            "Recommendations ranked by carbon savings (primary) and PUE efficiency (secondary)."
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

    # Get workload power (calculates watts from joule deltas)
    pod_power = kepler_client.get_pod_power_watts(workload_name, namespace)
    # Note: Kepler v0.11.2 only provides CPU watts at pod level
    power_watts = pod_power.get("total_watts", 0.0)

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
# POWER HOTSPOT DETECTION TOOLS (Inspired by Kepler PR #2250)
# ============================================================================

@mcp.tool()
async def identify_power_hotspots(
    namespace: Optional[str] = None,
    power_threshold_watts: float = 1.0,
    include_compliance_check: bool = True
) -> Dict:
    """
    Identify which containers/pods are consuming the most power and recommend preventive actions.

    This tool answers: "Which nodes or containers are consuming the most power and
    what preventive actions should we take?"

    Inspired by Kepler PR #2250's list_top_consumers, enhanced with Korean compliance
    standards and carbon-aware preventive action recommendations.

    Args:
        namespace: Kubernetes namespace to analyze (None for all namespaces)
        power_threshold_watts: Minimum power consumption to be considered a hotspot
        include_compliance_check: Flag non-compliant workloads as hotspots

    Returns:
        Dictionary containing:
        - hotspots: List of high power consumers
        - preventive_actions: Recommended actions sorted by priority
        - summary: Overall statistics
    """
    logger.info(
        "identifying_power_hotspots",
        namespace=namespace,
        threshold=power_threshold_watts
    )

    try:
        # Identify hotspots and generate actions
        hotspots, actions = hotspot_detector.identify_power_hotspots(
            namespace=namespace,
            power_threshold_watts=power_threshold_watts,
            compliance_check=include_compliance_check
        )

        # Convert to serializable format
        hotspot_list = [
            {
                "rank": h.rank,
                "name": h.name,
                "namespace": h.namespace,
                "power_watts": h.power_watts,
                "carbon_compliant": h.carbon_compliant,
                "pue_compliant": h.pue_compliant,
                "monthly_emissions_kg": h.monthly_emissions_kg,
                "efficiency_score": h.power_efficiency_score
            }
            for h in hotspots
        ]

        action_list = [
            {
                "action_type": a.action_type,
                "priority": a.priority,
                "resource": a.resource,
                "reason": a.reason,
                "estimated_savings_watts": a.estimated_savings_watts,
                "estimated_co2_reduction_kg_month": a.estimated_co2_reduction_kg_month,
                "implementation_steps": a.implementation_steps
            }
            for a in actions
        ]

        # Calculate summary statistics
        total_power = sum(h.power_watts for h in hotspots)
        total_potential_savings = sum(a.estimated_savings_watts for a in actions)
        total_co2_reduction = sum(a.estimated_co2_reduction_kg_month for a in actions)

        response = {
            "namespace": namespace or "all",
            "threshold_watts": power_threshold_watts,
            "summary": {
                "total_hotspots": len(hotspots),
                "total_power_watts": total_power,
                "total_preventive_actions": len(actions),
                "high_priority_actions": len([a for a in actions if a.priority == "high"]),
                "potential_power_savings_watts": total_potential_savings,
                "potential_co2_reduction_kg_month": total_co2_reduction
            },
            "hotspots": hotspot_list,
            "preventive_actions": action_list[:10],  # Top 10 actions
            "recommendation": _generate_hotspot_recommendation(hotspots, actions)
        }

        logger.info(
            "power_hotspots_identified",
            total_hotspots=len(hotspots),
            total_actions=len(actions)
        )

        return response

    except Exception as e:
        logger.error("hotspot_identification_failed", error=str(e))
        raise


def _generate_hotspot_recommendation(hotspots, actions):
    """Generate human-readable recommendation"""
    if not hotspots:
        return "✅ No power hotspots detected. All workloads are within acceptable limits."

    high_priority = len([a for a in actions if a.priority == "high"])

    if high_priority > 0:
        return (
            f"⚠️  URGENT: {len(hotspots)} power hotspot(s) detected with {high_priority} "
            f"high-priority action(s) required. Immediate attention recommended to prevent "
            f"compliance violations and reduce carbon emissions."
        )
    else:
        return (
            f"⚡ {len(hotspots)} power hotspot(s) detected. Consider implementing the "
            f"recommended preventive actions to improve efficiency and reduce emissions."
        )


@mcp.tool()
async def list_top_power_consumers(
    namespace: Optional[str] = None,
    limit: int = 10,
    sort_by: str = "power"
) -> Dict:
    """
    List top power-consuming workloads in the cluster.

    Similar to Kepler PR #2250's list_top_consumers tool, enhanced with
    Korean compliance metrics.

    Args:
        namespace: Filter by namespace (None for all)
        limit: Maximum number of results (default: 10)
        sort_by: Sort by "power" (highest first) or "efficiency" (lowest efficiency first)

    Returns:
        Ranked list of power consumers with compliance status
    """
    logger.info("listing_top_power_consumers", namespace=namespace, limit=limit)

    try:
        consumers = hotspot_detector.list_top_power_consumers(
            namespace=namespace,
            limit=limit,
            sort_by=sort_by
        )

        consumer_list = [
            {
                "rank": c.rank,
                "name": c.name,
                "namespace": c.namespace,
                "power_watts": c.power_watts,
                "status": "COMPLIANT" if (c.carbon_compliant and c.pue_compliant) else "NON_COMPLIANT",
                "carbon_compliant": c.carbon_compliant,
                "pue_compliant": c.pue_compliant,
                "monthly_emissions_kg": c.monthly_emissions_kg,
                "efficiency_score": c.power_efficiency_score
            }
            for c in consumers
        ]

        # Get summary
        summary = hotspot_detector.get_power_consumption_summary(namespace)

        result = {
            "namespace": namespace or "all",
            "sort_by": sort_by,
            "limit": limit,
            "summary": summary,
            "consumers": consumer_list
        }

        # Sanitize all float values to prevent NaN/Infinity in JSON
        return sanitize_dict(result)

    except Exception as e:
        logger.error("failed_to_list_consumers", error=str(e))
        raise


@mcp.tool()
async def get_power_consumption_summary(
    namespace: Optional[str] = None
) -> Dict:
    """
    Get overall power consumption summary for a namespace or entire cluster.

    Provides a quick overview of power usage, compliance, and top consumers.

    Args:
        namespace: Target namespace (None for cluster-wide)

    Returns:
        Summary statistics including total power, top consumers, compliance rate
    """
    logger.info("getting_power_summary", namespace=namespace)

    try:
        summary = hotspot_detector.get_power_consumption_summary(namespace)
        return sanitize_dict(summary)

    except Exception as e:
        logger.error("failed_to_get_summary", error=str(e))
        raise


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
        # Get native watts metrics from Kepler
        power_metrics = kepler_client.get_pod_power_watts(pod_name, namespace)

        # Extract watts metrics
        total_watts = power_metrics.get("total_watts", 0.0)
        cpu_watts = power_metrics.get("cpu_watts", 0.0)
        dram_watts = power_metrics.get("dram_watts", 0.0)

        result = {
            "namespace": namespace,
            "pod": pod_name,
            "metrics": {
                "cpu_watts": cpu_watts,
                "dram_watts": dram_watts,
                "total_watts": total_watts,
                "measurement_status": power_metrics.get("measurement_status", "active"),
                "note": "Native Kepler watts metrics (CPU package + DRAM)"
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
        host = os.getenv("HOST", "0.0.0.0")  # Bind to all interfaces for K8s
        logger.info("starting_sse_server", host=host, port=port)
        mcp.run(transport="sse", host=host, port=port)
    else:
        # Run with STDIO for local development
        mcp.run()
