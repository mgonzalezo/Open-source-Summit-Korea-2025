"""
Recommendation Engine

Generates actionable recommendations based on compliance status and workload characteristics.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import structlog

from .korea_compliance import (
    KoreaComplianceAssessment,
    ComplianceStatus,
    WorkloadMetrics
)
from .compliance_standards import (
    REGIONAL_CARBON_INTENSITY,
    KOREA_PUE_GREEN_DC,
    get_regional_pue
)

logger = structlog.get_logger()


class OptimizationSuggestion(BaseModel):
    """Single optimization suggestion"""
    type: str = Field(..., description="Optimization type")
    description: str = Field(..., description="Human-readable description")
    estimated_reduction_percent: float = Field(
        ...,
        description="Estimated reduction in emissions (%)"
    )
    estimated_new_power_watts: Optional[float] = Field(
        None,
        description="Estimated new power consumption"
    )
    estimated_new_intensity_gco2_kwh: Optional[float] = Field(
        None,
        description="Estimated new carbon intensity"
    )
    implementation_complexity: str = Field(
        "medium",
        description="Implementation complexity (low/medium/high)"
    )


class ComplianceRecommendation(BaseModel):
    """Complete recommendation package"""
    summary: str = Field(..., description="Executive summary")
    status_emoji: str = Field(..., description="Status indicator emoji")
    optimizations: List[OptimizationSuggestion] = Field(
        default_factory=list,
        description="List of optimization suggestions"
    )
    priority_actions: List[str] = Field(
        default_factory=list,
        description="Prioritized action items"
    )


def generate_recommendation(
    assessment: KoreaComplianceAssessment,
    workload_metrics: WorkloadMetrics,
    region: str = "ap-northeast-2"
) -> ComplianceRecommendation:
    """
    Generate comprehensive recommendation based on compliance assessment

    Args:
        assessment: Korea compliance assessment
        workload_metrics: Workload power metrics
        region: AWS region

    Returns:
        ComplianceRecommendation
    """
    carbon_status = assessment.carbon.status
    pue_status = assessment.pue.status

    # Determine overall status
    if carbon_status == "COMPLIANT" and pue_status == "COMPLIANT":
        return _generate_compliant_recommendation(assessment)
    elif carbon_status == "NON_COMPLIANT" and pue_status == "NON_COMPLIANT":
        return _generate_double_non_compliant_recommendation(
            assessment, workload_metrics, region
        )
    elif carbon_status == "NON_COMPLIANT":
        return _generate_carbon_non_compliant_recommendation(
            assessment, workload_metrics, region
        )
    else:  # pue_status == "NON_COMPLIANT"
        return _generate_pue_non_compliant_recommendation(
            assessment, workload_metrics
        )


def _generate_compliant_recommendation(
    assessment: KoreaComplianceAssessment
) -> ComplianceRecommendation:
    """Generate recommendation for fully compliant workload"""
    summary = (
        f"✅ COMPLIANT: {assessment.workload_name} meets both Korean Carbon Neutrality 2050 "
        f"({assessment.carbon.current_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh ≤ "
        f"{assessment.carbon.target_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh) and "
        f"Green Data Center PUE requirements "
        f"({assessment.pue.current_pue} ≤ {assessment.pue.target_pue}). "
        "Continue monitoring and consider further optimizations to maintain compliance."
    )

    optimizations = [
        OptimizationSuggestion(
            type="continuous_monitoring",
            description="Set up automated compliance monitoring",
            estimated_reduction_percent=0,
            implementation_complexity="low"
        ),
        OptimizationSuggestion(
            type="best_practices",
            description="Document current configuration as best practice",
            estimated_reduction_percent=0,
            implementation_complexity="low"
        )
    ]

    priority_actions = [
        "Monitor workload for compliance drift",
        "Document current resource allocation as reference",
        "Consider sharing best practices with team"
    ]

    return ComplianceRecommendation(
        summary=summary,
        status_emoji="✅",
        optimizations=optimizations,
        priority_actions=priority_actions
    )


def _generate_double_non_compliant_recommendation(
    assessment: KoreaComplianceAssessment,
    workload_metrics: WorkloadMetrics,
    region: str
) -> ComplianceRecommendation:
    """Generate recommendation for workload failing both carbon and PUE compliance"""
    carbon_gap = abs(assessment.carbon.gap_percent)
    pue_gap = abs(assessment.pue.gap_percent)

    summary = (
        f"⚠️ NON-COMPLIANT: {assessment.workload_name} exceeds both Korean standards:\n"
        f"• Carbon: {assessment.carbon.current_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh "
        f"({carbon_gap:.1f}% over {assessment.carbon.target_carbon_intensity_gco2_kwh:.0f} target)\n"
        f"• PUE: {assessment.pue.current_pue} "
        f"({pue_gap:.1f}% over {assessment.pue.target_pue} target)\n\n"
        "Immediate action required to meet Korean regulatory compliance."
    )

    optimizations = []

    # Temporal shift optimization
    temporal_opt = _calculate_temporal_shift_optimization(
        assessment.power_watts,
        region,
        assessment.carbon.grid_carbon_intensity_gco2_kwh
    )
    if temporal_opt:
        optimizations.append(temporal_opt)

    # Resource right-sizing
    resource_opt = _calculate_resource_optimization(
        workload_metrics,
        target_reduction=carbon_gap
    )
    if resource_opt:
        optimizations.append(resource_opt)

    # Regional migration
    regional_opt = _calculate_regional_optimization(region, assessment.power_watts)
    if regional_opt:
        optimizations.append(regional_opt)

    # PUE optimization
    pue_opt = _calculate_pue_optimization(assessment.pue.current_pue, pue_gap)
    if pue_opt:
        optimizations.append(pue_opt)

    priority_actions = [
        f"1. URGENT: Reduce power consumption by {carbon_gap:.0f}% to meet carbon target",
        f"2. Improve cooling efficiency to achieve PUE ≤ {assessment.pue.target_pue}",
        "3. Consider temporal workload shifting to cleaner grid hours (2am-6am KST)",
        "4. Evaluate resource allocation (CPU/memory right-sizing)",
        "5. Assess feasibility of regional migration for batch workloads"
    ]

    return ComplianceRecommendation(
        summary=summary,
        status_emoji="⚠️",
        optimizations=optimizations,
        priority_actions=priority_actions
    )


def _generate_carbon_non_compliant_recommendation(
    assessment: KoreaComplianceAssessment,
    workload_metrics: WorkloadMetrics,
    region: str
) -> ComplianceRecommendation:
    """Generate recommendation for workload failing carbon compliance only"""
    carbon_gap = abs(assessment.carbon.gap_percent)

    summary = (
        f"⚠️ NON-COMPLIANT (Carbon): {assessment.workload_name} exceeds Korean Carbon "
        f"Neutrality 2050 target by {carbon_gap:.1f}%:\n"
        f"• Current: {assessment.carbon.current_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh\n"
        f"• Target: {assessment.carbon.target_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh\n"
        f"✅ PUE: {assessment.pue.current_pue} (compliant)"
    )

    optimizations = []

    # Temporal shift
    temporal_opt = _calculate_temporal_shift_optimization(
        assessment.power_watts,
        region,
        assessment.carbon.grid_carbon_intensity_gco2_kwh
    )
    if temporal_opt:
        optimizations.append(temporal_opt)

    # Resource optimization
    resource_opt = _calculate_resource_optimization(
        workload_metrics,
        target_reduction=carbon_gap
    )
    if resource_opt:
        optimizations.append(resource_opt)

    # Regional migration
    regional_opt = _calculate_regional_optimization(region, assessment.power_watts)
    if regional_opt:
        optimizations.append(regional_opt)

    priority_actions = [
        f"1. Reduce power consumption by ~{carbon_gap:.0f}% to meet carbon target",
        "2. Schedule workload during cleaner grid hours (2am-6am KST)",
        "3. Right-size CPU and memory allocation",
        "4. Consider batch workload migration to cleaner regions"
    ]

    return ComplianceRecommendation(
        summary=summary,
        status_emoji="⚠️",
        optimizations=optimizations,
        priority_actions=priority_actions
    )


def _generate_pue_non_compliant_recommendation(
    assessment: KoreaComplianceAssessment,
    workload_metrics: WorkloadMetrics
) -> ComplianceRecommendation:
    """Generate recommendation for workload failing PUE compliance only"""
    pue_gap = abs(assessment.pue.gap_percent)

    summary = (
        f"⚠️ NON-COMPLIANT (PUE): {assessment.workload_name} exceeds Korean Green Data Center "
        f"PUE requirement by {pue_gap:.1f}%:\n"
        f"• Current PUE: {assessment.pue.current_pue}\n"
        f"• Target PUE: ≤ {assessment.pue.target_pue}\n"
        f"✅ Carbon: {assessment.carbon.current_carbon_intensity_gco2_kwh:.0f} gCO2eq/kWh (compliant)"
    )

    optimizations = []

    # PUE optimization
    pue_opt = _calculate_pue_optimization(assessment.pue.current_pue, pue_gap)
    if pue_opt:
        optimizations.append(pue_opt)

    priority_actions = [
        f"1. Improve data center cooling efficiency (target PUE ≤ {assessment.pue.target_pue})",
        "2. Review facility overhead (HVAC, lighting, UPS losses)",
        "3. Optimize server utilization to improve IT equipment efficiency",
        "4. Consider hot/cold aisle containment for better cooling"
    ]

    return ComplianceRecommendation(
        summary=summary,
        status_emoji="⚠️",
        optimizations=optimizations,
        priority_actions=priority_actions
    )


# ============================================================================
# OPTIMIZATION CALCULATORS
# ============================================================================

def _calculate_temporal_shift_optimization(
    power_watts: float,
    region: str,
    current_intensity: float
) -> Optional[OptimizationSuggestion]:
    """Calculate temporal shift optimization (2am-6am cleaner grid)"""
    # Estimate 10% cleaner grid during off-peak hours (2am-6am)
    off_peak_intensity = current_intensity * 0.90
    reduction_percent = 10.0

    return OptimizationSuggestion(
        type="temporal_shift",
        description="Reschedule workload to 2am-6am KST (cleaner grid hours)",
        estimated_reduction_percent=reduction_percent,
        estimated_new_intensity_gco2_kwh=off_peak_intensity,
        implementation_complexity="medium"
    )


def _calculate_resource_optimization(
    metrics: WorkloadMetrics,
    target_reduction: float
) -> Optional[OptimizationSuggestion]:
    """Calculate resource right-sizing optimization"""
    # Assume we can achieve ~15% reduction through CPU right-sizing
    reduction_percent = min(15.0, target_reduction)
    new_cpu_watts = metrics.cpu_watts * (1 - reduction_percent / 100)
    new_total = new_cpu_watts + metrics.memory_watts + metrics.gpu_watts

    return OptimizationSuggestion(
        type="resource_rightsizing",
        description=f"Right-size CPU allocation (reduce from {metrics.cpu_watts:.1f}W)",
        estimated_reduction_percent=reduction_percent,
        estimated_new_power_watts=new_total,
        implementation_complexity="low"
    )


def _calculate_regional_optimization(
    current_region: str,
    power_watts: float
) -> Optional[OptimizationSuggestion]:
    """
    Calculate regional migration optimization.

    Finds the best region based on:
    1. Carbon intensity (primary - lowest gCO2/kWh)
    2. PUE efficiency (secondary - lowest PUE for tied carbon savings)
    3. Korean Green DC compliance (PUE ≤ 1.4)
    """
    current_data = REGIONAL_CARBON_INTENSITY.get(current_region)
    if not current_data:
        return None

    current_intensity = current_data["average_gco2_kwh"]

    # Find best region by comparing ALL available regions
    best_region = None
    best_intensity = float('inf')
    best_pue = float('inf')

    for region_code, region_data in REGIONAL_CARBON_INTENSITY.items():
        if region_code == current_region:
            continue  # Skip current region

        intensity = region_data["average_gco2_kwh"]

        # Get PUE data if available
        pue_data = get_regional_pue(region_code)
        pue = pue_data.get("typical_pue", 999) if pue_data else 999

        # Find region with lowest carbon (primary), then lowest PUE (secondary)
        if intensity < best_intensity or (intensity == best_intensity and pue < best_pue):
            best_region = region_code
            best_intensity = intensity
            best_pue = pue

    if not best_region:
        return None

    best_data = REGIONAL_CARBON_INTENSITY[best_region]
    reduction_percent = ((current_intensity - best_intensity) / current_intensity * 100)

    if reduction_percent <= 0:
        return None

    # Build description with PUE awareness
    description = f"Migrate to {best_data['region_name']} (cleaner grid"

    # Add PUE info if available and meets Korean target
    if best_pue < 999:
        meets_pue = best_pue <= KOREA_PUE_GREEN_DC.target_pue
        if meets_pue:
            description += f", PUE {best_pue} ✅"
        else:
            description += f", PUE {best_pue}"

    description += ")"

    return OptimizationSuggestion(
        type="regional_migration",
        description=description,
        estimated_reduction_percent=reduction_percent,
        estimated_new_intensity_gco2_kwh=best_intensity,
        implementation_complexity="high"
    )


def _calculate_pue_optimization(
    current_pue: float,
    gap_percent: float
) -> Optional[OptimizationSuggestion]:
    """Calculate PUE improvement optimization"""
    target_improvement = min(gap_percent, 20.0)  # Cap at 20% improvement
    new_pue = current_pue * (1 - target_improvement / 100)

    return OptimizationSuggestion(
        type="pue_improvement",
        description=f"Improve cooling efficiency (target PUE: {new_pue:.2f})",
        estimated_reduction_percent=target_improvement,
        implementation_complexity="high"
    )
