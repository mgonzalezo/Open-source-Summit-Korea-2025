"""
Carbon Calculator

Generic carbon footprint and PUE calculation utilities.
"""

from typing import Dict, Optional


def watts_to_kwh(watts: float, hours: float = 1.0) -> float:
    """
    Convert watts to kilowatt-hours (kWh)

    Args:
        watts: Power in watts
        hours: Time period in hours (default: 1.0)

    Returns:
        Energy in kWh
    """
    return (watts * hours) / 1000.0


def calculate_carbon_emissions(
    power_watts: float,
    grid_carbon_intensity_gco2_kwh: float,
    hours: float = 1.0
) -> float:
    """
    Calculate carbon emissions in gCO2eq

    Args:
        power_watts: Power consumption in watts
        grid_carbon_intensity_gco2_kwh: Grid carbon intensity in gCO2eq/kWh
        hours: Time period in hours (default: 1.0)

    Returns:
        Carbon emissions in gCO2eq
    """
    energy_kwh = watts_to_kwh(power_watts, hours)
    return energy_kwh * grid_carbon_intensity_gco2_kwh


def calculate_workload_carbon_intensity(
    power_watts: float,
    grid_carbon_intensity_gco2_kwh: float
) -> float:
    """
    Calculate workload-specific carbon intensity

    Args:
        power_watts: Workload power consumption in watts
        grid_carbon_intensity_gco2_kwh: Grid carbon intensity in gCO2eq/kWh

    Returns:
        Workload carbon intensity in gCO2eq/kWh
    """
    # Edge case: idle/zero-power workloads have 0 carbon intensity
    if power_watts <= 0:
        return 0.0

    # For a workload, the carbon intensity is essentially the grid intensity
    # scaled by the workload's power efficiency
    # In simplified model: workload intensity ≈ grid intensity
    # (More sophisticated models would factor in PUE, cooling, overhead)
    return grid_carbon_intensity_gco2_kwh


def calculate_pue(
    total_facility_power_watts: float,
    it_equipment_power_watts: float
) -> float:
    """
    Calculate Power Usage Effectiveness (PUE)

    PUE = Total Facility Power / IT Equipment Power

    Args:
        total_facility_power_watts: Total data center power (IT + cooling + overhead)
        it_equipment_power_watts: IT equipment power only

    Returns:
        PUE ratio (≥ 1.0, where 1.0 is perfect efficiency)
    """
    if it_equipment_power_watts <= 0:
        raise ValueError("IT equipment power must be > 0")

    pue = total_facility_power_watts / it_equipment_power_watts
    return max(1.0, pue)  # PUE can never be < 1.0


def estimate_pue_from_node_metrics(
    node_total_power_watts: float,
    workload_power_watts: float,
    assumed_overhead_ratio: float = 0.4
) -> float:
    """
    Estimate PUE from node-level metrics

    In cloud environments, we estimate PUE by assuming overhead for cooling,
    networking, and facility infrastructure.

    Args:
        node_total_power_watts: Total node power consumption
        workload_power_watts: Specific workload power consumption
        assumed_overhead_ratio: Assumed overhead ratio (default: 0.4 = 40% overhead)

    Returns:
        Estimated PUE
    """
    # Estimate total facility power by adding assumed overhead
    estimated_facility_power = node_total_power_watts * (1 + assumed_overhead_ratio)

    # Calculate PUE
    return calculate_pue(estimated_facility_power, node_total_power_watts)


def gco2_to_kg(gco2: float) -> float:
    """Convert grams CO2 to kilograms"""
    return gco2 / 1000.0


def gco2_to_tons(gco2: float) -> float:
    """Convert grams CO2 to metric tons"""
    return gco2 / 1_000_000.0


def calculate_monthly_emissions(
    hourly_emissions_gco2: float,
    hours_per_day: float = 24.0,
    days_per_month: float = 30.0
) -> float:
    """
    Calculate monthly emissions from hourly rate

    Args:
        hourly_emissions_gco2: Emissions per hour in gCO2eq
        hours_per_day: Hours per day (default: 24)
        days_per_month: Days per month (default: 30)

    Returns:
        Monthly emissions in gCO2eq
    """
    return hourly_emissions_gco2 * hours_per_day * days_per_month


def calculate_cost_from_power(
    power_watts: float,
    electricity_cost_usd_kwh: float = 0.10,
    hours: float = 1.0
) -> float:
    """
    Calculate electricity cost from power consumption

    Args:
        power_watts: Power consumption in watts
        electricity_cost_usd_kwh: Cost per kWh in USD (default: $0.10/kWh)
        hours: Time period in hours (default: 1.0)

    Returns:
        Cost in USD
    """
    energy_kwh = watts_to_kwh(power_watts, hours)
    return energy_kwh * electricity_cost_usd_kwh
