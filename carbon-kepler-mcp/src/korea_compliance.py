"""
Korea Compliance Calculations

Implements Korean regulatory compliance logic for carbon neutrality and PUE standards.
"""

from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field
import structlog

from .compliance_standards import (
    KOREA_CARBON_NEUTRALITY,
    KOREA_PUE_GREEN_DC,
    CarbonStandard,
    PUEStandard
)
from .carbon_calculator import (
    calculate_carbon_emissions,
    calculate_workload_carbon_intensity,
    estimate_pue_from_node_metrics,
    gco2_to_kg,
    calculate_monthly_emissions
)

logger = structlog.get_logger()


ComplianceStatus = Literal["COMPLIANT", "NON_COMPLIANT"]


class WorkloadMetrics(BaseModel):
    """Workload power and resource metrics"""
    cpu_watts: float = Field(..., description="CPU power consumption in watts")
    memory_watts: float = Field(..., description="Memory power consumption in watts")
    gpu_watts: float = Field(0.0, description="GPU power consumption in watts")
    other_watts: float = Field(0.0, description="Other components power in watts")

    @property
    def total_watts(self) -> float:
        """Total power consumption"""
        return self.cpu_watts + self.memory_watts + self.gpu_watts + self.other_watts


class CarbonComplianceResult(BaseModel):
    """Result of carbon compliance assessment"""
    status: ComplianceStatus
    current_carbon_intensity_gco2_kwh: float
    target_carbon_intensity_gco2_kwh: float
    grid_carbon_intensity_gco2_kwh: float
    gap_percent: float = Field(..., description="Positive = over target, Negative = under target")
    hourly_emissions_gco2: float
    monthly_emissions_kg: float


class PUEComplianceResult(BaseModel):
    """Result of PUE compliance assessment"""
    status: ComplianceStatus
    current_pue: float
    target_pue: float
    gap_percent: float = Field(..., description="Positive = inefficient, Negative = efficient")


class KoreaComplianceAssessment(BaseModel):
    """Complete Korean regulatory compliance assessment"""
    workload_name: str
    namespace: str
    region: str

    # Carbon Neutrality (탄소중립 녹색성장 기본법)
    carbon: CarbonComplianceResult

    # PUE Standard (에너지이용 합리화법)
    pue: PUEComplianceResult

    # Power metrics
    power_watts: float
    timestamp: str


def assess_carbon_compliance(
    workload_power_watts: float,
    grid_carbon_intensity_gco2_kwh: float,
    standard: CarbonStandard = KOREA_CARBON_NEUTRALITY
) -> CarbonComplianceResult:
    """
    Assess compliance with carbon neutrality standard

    Args:
        workload_power_watts: Workload power consumption in watts
        grid_carbon_intensity_gco2_kwh: Grid carbon intensity
        standard: Carbon standard to assess against

    Returns:
        CarbonComplianceResult
    """
    # Calculate workload carbon intensity
    workload_intensity = calculate_workload_carbon_intensity(
        workload_power_watts,
        grid_carbon_intensity_gco2_kwh
    )

    # Check compliance
    is_compliant = standard.is_compliant(workload_intensity)
    gap_percent = standard.compliance_gap_percent(workload_intensity)

    # Calculate emissions
    hourly_emissions = calculate_carbon_emissions(
        workload_power_watts,
        grid_carbon_intensity_gco2_kwh,
        hours=1.0
    )

    monthly_emissions = calculate_monthly_emissions(hourly_emissions)
    monthly_emissions_kg = gco2_to_kg(monthly_emissions)

    logger.debug(
        "carbon_compliance_assessed",
        status="COMPLIANT" if is_compliant else "NON_COMPLIANT",
        workload_intensity=workload_intensity,
        target=standard.target_carbon_intensity_gco2_kwh,
        gap_percent=gap_percent
    )

    return CarbonComplianceResult(
        status="COMPLIANT" if is_compliant else "NON_COMPLIANT",
        current_carbon_intensity_gco2_kwh=workload_intensity,
        target_carbon_intensity_gco2_kwh=standard.target_carbon_intensity_gco2_kwh,
        grid_carbon_intensity_gco2_kwh=grid_carbon_intensity_gco2_kwh,
        gap_percent=gap_percent,
        hourly_emissions_gco2=hourly_emissions,
        monthly_emissions_kg=monthly_emissions_kg
    )


def assess_pue_compliance(
    workload_power_watts: float,
    node_total_power_watts: float,
    standard: PUEStandard = KOREA_PUE_GREEN_DC,
    overhead_ratio: float = 0.4
) -> PUEComplianceResult:
    """
    Assess compliance with PUE standard

    Args:
        workload_power_watts: Workload power consumption
        node_total_power_watts: Total node power consumption
        standard: PUE standard to assess against
        overhead_ratio: Assumed facility overhead ratio (default: 0.4 = 40%)

    Returns:
        PUEComplianceResult
    """
    # Estimate PUE from node metrics
    estimated_pue = estimate_pue_from_node_metrics(
        node_total_power_watts,
        workload_power_watts,
        overhead_ratio
    )

    # Check compliance
    is_compliant = standard.is_compliant(estimated_pue)

    # Calculate gap
    gap_percent = ((estimated_pue - standard.target_pue) / standard.target_pue * 100)

    logger.debug(
        "pue_compliance_assessed",
        status="COMPLIANT" if is_compliant else "NON_COMPLIANT",
        estimated_pue=estimated_pue,
        target_pue=standard.target_pue,
        gap_percent=gap_percent
    )

    return PUEComplianceResult(
        status="COMPLIANT" if is_compliant else "NON_COMPLIANT",
        current_pue=round(estimated_pue, 2),
        target_pue=standard.target_pue,
        gap_percent=gap_percent
    )


def assess_korea_compliance(
    workload_name: str,
    namespace: str,
    region: str,
    workload_metrics: WorkloadMetrics,
    node_total_power_watts: float,
    grid_carbon_intensity_gco2_kwh: float = KOREA_CARBON_NEUTRALITY.grid_carbon_intensity_gco2_kwh,
    timestamp: Optional[str] = None
) -> KoreaComplianceAssessment:
    """
    Comprehensive Korean regulatory compliance assessment

    Assesses both:
    1. Carbon Neutrality Act (탄소중립 녹색성장 기본법)
    2. Energy Use Rationalization Act PUE requirement (에너지이용 합리화법)

    Args:
        workload_name: Workload identifier
        namespace: Kubernetes namespace
        region: AWS region
        workload_metrics: Workload power metrics
        node_total_power_watts: Total node power
        grid_carbon_intensity_gco2_kwh: Grid carbon intensity
        timestamp: Assessment timestamp (ISO format)

    Returns:
        KoreaComplianceAssessment
    """
    from datetime import datetime

    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"

    # Assess carbon compliance
    carbon_result = assess_carbon_compliance(
        workload_metrics.total_watts,
        grid_carbon_intensity_gco2_kwh
    )

    # Assess PUE compliance
    pue_result = assess_pue_compliance(
        workload_metrics.total_watts,
        node_total_power_watts
    )

    logger.info(
        "korea_compliance_assessed",
        workload=workload_name,
        namespace=namespace,
        carbon_status=carbon_result.status,
        pue_status=pue_result.status
    )

    return KoreaComplianceAssessment(
        workload_name=workload_name,
        namespace=namespace,
        region=region,
        carbon=carbon_result,
        pue=pue_result,
        power_watts=workload_metrics.total_watts,
        timestamp=timestamp
    )


def calculate_reduction_target(
    current_power_watts: float,
    target_reduction_percent: float
) -> float:
    """
    Calculate target power after reduction

    Args:
        current_power_watts: Current power consumption
        target_reduction_percent: Target reduction percentage (e.g., 20 for 20%)

    Returns:
        Target power in watts
    """
    reduction_factor = 1.0 - (target_reduction_percent / 100.0)
    return current_power_watts * reduction_factor


def estimate_cost_savings(
    power_reduction_watts: float,
    electricity_cost_usd_kwh: float = 0.10,
    hours_per_month: float = 730.0
) -> float:
    """
    Estimate monthly cost savings from power reduction

    Args:
        power_reduction_watts: Power reduction in watts
        electricity_cost_usd_kwh: Electricity cost per kWh (default: $0.10)
        hours_per_month: Hours per month (default: 730)

    Returns:
        Monthly savings in USD
    """
    from .carbon_calculator import watts_to_kwh

    energy_saved_kwh_month = watts_to_kwh(power_reduction_watts, hours_per_month)
    return energy_saved_kwh_month * electricity_cost_usd_kwh
