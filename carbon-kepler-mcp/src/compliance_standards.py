"""
Compliance Standards Definitions

Defines carbon intensity and PUE standards for various regions and regulations,
with primary focus on Korean regulatory requirements.
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class CarbonStandard(BaseModel):
    """Carbon intensity compliance standard"""
    code: str = Field(..., description="Unique standard code (e.g., KR_CARBON_2050)")
    name: str = Field(..., description="Official standard name")
    name_local: Optional[str] = Field(None, description="Name in local language")
    target_carbon_intensity_gco2_kwh: float = Field(
        ...,
        description="Target carbon intensity in gCO2eq/kWh"
    )
    grid_carbon_intensity_gco2_kwh: float = Field(
        ...,
        description="Current grid carbon intensity in gCO2eq/kWh"
    )
    enforcement_date: Optional[str] = Field(None, description="Enforcement date (ISO format)")
    description: str = Field(..., description="Standard description")
    reference_url: Optional[str] = Field(None, description="Official documentation URL")

    def is_compliant(self, workload_intensity: float) -> bool:
        """Check if a workload intensity is compliant with this standard"""
        return workload_intensity <= self.target_carbon_intensity_gco2_kwh

    def compliance_gap_percent(self, workload_intensity: float) -> float:
        """Calculate compliance gap as percentage (+/- from target)"""
        return ((workload_intensity - self.target_carbon_intensity_gco2_kwh) /
                self.target_carbon_intensity_gco2_kwh * 100)


class PUEStandard(BaseModel):
    """Power Usage Effectiveness (PUE) standard"""
    code: str = Field(..., description="Unique standard code")
    name: str = Field(..., description="Official standard name")
    name_local: Optional[str] = Field(None, description="Name in local language")
    target_pue: float = Field(..., description="Target PUE ratio", ge=1.0)
    baseline_pue: float = Field(..., description="Baseline/typical PUE for comparison", ge=1.0)
    certification_level: Optional[str] = Field(None, description="Certification level/tier")
    description: str = Field(..., description="Standard description")
    reference_url: Optional[str] = Field(None, description="Official documentation URL")

    def is_compliant(self, measured_pue: float) -> bool:
        """Check if a measured PUE is compliant with this standard"""
        return measured_pue <= self.target_pue

    def efficiency_improvement_percent(self, measured_pue: float) -> float:
        """Calculate efficiency improvement from baseline"""
        return ((self.baseline_pue - measured_pue) / self.baseline_pue * 100)


# ============================================================================
# KOREAN STANDARDS (Primary Focus)
# ============================================================================

KOREA_CARBON_NEUTRALITY = CarbonStandard(
    code="KR_CARBON_2050",
    name="Framework Act on Carbon Neutrality and Green Growth",
    name_local="탄소중립 녹색성장 기본법",
    target_carbon_intensity_gco2_kwh=424,  # Korea grid average (2024)
    grid_carbon_intensity_gco2_kwh=424,
    enforcement_date="2021-09-24",
    description=(
        "South Korea's commitment to achieve carbon neutrality by 2050, "
        "with interim targets of 35% reduction by 2030 (compared to 2018 baseline). "
        "Grid mix: Coal 35%, Natural Gas 28%, Nuclear 25%, Renewable 12%."
    ),
    reference_url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613"
)

KOREA_PUE_GREEN_DC = PUEStandard(
    code="KR_PUE_GREEN_DC",
    name="Energy Use Rationalization Act - Green Data Center",
    name_local="에너지이용 합리화법 - 그린 데이터센터",
    target_pue=1.4,
    baseline_pue=1.8,
    certification_level="Green Data Center Certification",
    description=(
        "Korean Ministry of Trade, Industry and Energy (MOTIE) requires PUE ≤ 1.4 "
        "for Green Data Center certification under the Energy Use Rationalization Act. "
        "This standard encourages energy-efficient data center operations."
    ),
    reference_url="https://www.law.go.kr/법령/에너지이용합리화법"
)


# ============================================================================
# GLOBAL STANDARDS (For Comparison)
# ============================================================================

US_EPA_ENERGY_STAR = CarbonStandard(
    code="US_EPA_ENERGY_STAR",
    name="EPA Energy Star Data Center",
    target_carbon_intensity_gco2_kwh=450,  # US grid average
    grid_carbon_intensity_gco2_kwh=450,
    description=(
        "US Environmental Protection Agency Energy Star certification for data centers. "
        "US grid mix: Natural Gas 40%, Coal 20%, Nuclear 19%, Renewable 21%."
    ),
    reference_url="https://www.energystar.gov/buildings/tools-and-resources/data_center_resources"
)

EU_CODE_OF_CONDUCT = PUEStandard(
    code="EU_COC_DC",
    name="EU Code of Conduct for Data Centres",
    target_pue=1.3,
    baseline_pue=2.0,
    certification_level="Best Practice",
    description=(
        "EU voluntary standard for energy-efficient data centers. "
        "Targets PUE ≤ 1.3 for best practice recognition."
    ),
    reference_url="https://e3p.jrc.ec.europa.eu/communities/data-centres-code-conduct"
)

ASHRAE_THERMAL_90_4 = PUEStandard(
    code="ASHRAE_THERMAL_90_4",
    name="ASHRAE Standard 90.4 - Energy Efficiency for Data Centers",
    target_pue=1.2,
    baseline_pue=2.0,
    description=(
        "American Society of Heating, Refrigerating and Air-Conditioning Engineers (ASHRAE) "
        "standard for high-efficiency data center design."
    ),
    reference_url="https://www.ashrae.org/technical-resources/bookstore/standard-90-4"
)


# ============================================================================
# REGIONAL CARBON INTENSITY DATA
# Source: IEA, EPA, EMA, Ember Climate (2024 data)
# ============================================================================

REGIONAL_CARBON_INTENSITY = {
    # Asia Pacific
    "ap-northeast-2": {  # Seoul, Korea
        "region_name": "Seoul (Korea)",
        "average_gco2_kwh": 436,  # IEA 2024: Korea grid average
        "grid_mix": {
            "coal": 34,
            "natural_gas": 27,
            "nuclear": 29,
            "renewable": 10  # Solar + Wind
        },
        "source": "IEA Electricity 2024, Korea Power Exchange"
    },
    "ap-northeast-1": {  # Tokyo, Japan
        "region_name": "Tokyo (Japan)",
        "average_gco2_kwh": 462,  # IEA 2024: Japan grid average
        "grid_mix": {
            "coal": 31,
            "natural_gas": 37,
            "nuclear": 6,  # Post-Fukushima low nuclear
            "renewable": 22  # Growing solar
        },
        "source": "IEA Electricity 2024, TEPCO data"
    },
    "ap-southeast-1": {  # Singapore
        "region_name": "Singapore",
        "average_gco2_kwh": 392,  # EMA 2024: Natural gas dominated
        "grid_mix": {
            "coal": 0,
            "natural_gas": 95,
            "renewable": 5  # Solar growing rapidly
        },
        "source": "Singapore Energy Market Authority (EMA) 2024"
    },

    # North America
    "us-east-1": {  # Virginia, USA
        "region_name": "Virginia (USA)",
        "average_gco2_kwh": 331,  # EPA eGRID 2024: PJM region
        "grid_mix": {
            "coal": 19,
            "natural_gas": 36,
            "nuclear": 35,  # High nuclear in Virginia
            "renewable": 10
        },
        "source": "EPA eGRID 2024, PJM Interconnection"
    },
    "us-west-2": {  # Oregon, USA
        "region_name": "Oregon (USA)",
        "average_gco2_kwh": 91,  # EPA eGRID 2024: NWPP region
        "grid_mix": {
            "coal": 3,
            "natural_gas": 13,
            "nuclear": 8,
            "renewable": 76  # Hydroelectric dominant
        },
        "source": "EPA eGRID 2024, Northwest Power Pool"
    },

    # Europe
    "eu-north-1": {  # Stockholm, Sweden
        "region_name": "Stockholm (Sweden)",
        "average_gco2_kwh": 13,  # Ember 2024: One of world's cleanest
        "grid_mix": {
            "coal": 0,
            "natural_gas": 1,
            "nuclear": 30,
            "renewable": 69  # Hydroelectric + Wind
        },
        "source": "Ember European Electricity Review 2024"
    },
    "eu-central-1": {  # Frankfurt, Germany
        "region_name": "Frankfurt (Germany)",
        "average_gco2_kwh": 380,  # Ember 2024: Transitioning grid
        "grid_mix": {
            "coal": 26,  # Still significant lignite
            "natural_gas": 13,
            "nuclear": 6,   # Phase-out ongoing
            "renewable": 55  # Wind + Solar
        },
        "source": "Ember European Electricity Review 2024, Bundesnetzagentur"
    }
}


# ============================================================================
# REGIONAL PUE DATA
# Source: AWS Sustainability Reports, Industry Estimates (2024)
# ============================================================================

REGIONAL_PUE_DATA = {
    "ap-northeast-2": {  # Seoul, Korea
        "typical_pue": 1.45,  # Above Korean Green DC target (1.4)
        "data_center_type": "Standard AWS Region",
        "climate_zone": "Temperate (hot summers, cold winters)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "ap-northeast-1": {  # Tokyo, Japan
        "typical_pue": 1.42,
        "data_center_type": "Standard AWS Region",
        "climate_zone": "Temperate (humid subtropical)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "ap-southeast-1": {  # Singapore
        "typical_pue": 1.28,  # Excellent efficiency despite tropical climate
        "data_center_type": "AWS Availability Zones with liquid cooling",
        "climate_zone": "Tropical (equatorial)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "us-east-1": {  # Virginia, USA
        "typical_pue": 1.32,
        "data_center_type": "AWS US East (N. Virginia)",
        "climate_zone": "Temperate (humid subtropical)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "us-west-2": {  # Oregon, USA
        "typical_pue": 1.35,
        "data_center_type": "AWS US West (Oregon)",
        "climate_zone": "Temperate (oceanic)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "eu-north-1": {  # Stockholm, Sweden
        "typical_pue": 1.25,  # Excellent efficiency due to cold climate (free cooling)
        "data_center_type": "AWS EU (Stockholm) - free cooling enabled",
        "climate_zone": "Cold (subarctic)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    },
    "eu-central-1": {  # Frankfurt, Germany
        "typical_pue": 1.38,
        "data_center_type": "AWS EU (Frankfurt)",
        "climate_zone": "Temperate (oceanic)",
        "source": "AWS Sustainability 2024 Regional Report (estimated)"
    }
}


# ============================================================================
# STANDARDS REGISTRY
# ============================================================================

CARBON_STANDARDS: Dict[str, CarbonStandard] = {
    "KR_CARBON_2050": KOREA_CARBON_NEUTRALITY,
    "US_EPA_ENERGY_STAR": US_EPA_ENERGY_STAR,
}

PUE_STANDARDS: Dict[str, PUEStandard] = {
    "KR_PUE_GREEN_DC": KOREA_PUE_GREEN_DC,
    "EU_COC_DC": EU_CODE_OF_CONDUCT,
    "ASHRAE_THERMAL_90_4": ASHRAE_THERMAL_90_4,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_carbon_standard(code: str) -> Optional[CarbonStandard]:
    """Get carbon standard by code"""
    return CARBON_STANDARDS.get(code)


def get_pue_standard(code: str) -> Optional[PUEStandard]:
    """Get PUE standard by code"""
    return PUE_STANDARDS.get(code)


def get_regional_carbon_intensity(region: str) -> Optional[Dict]:
    """Get regional carbon intensity data"""
    return REGIONAL_CARBON_INTENSITY.get(region)


def list_carbon_standards() -> List[str]:
    """List all available carbon standard codes"""
    return list(CARBON_STANDARDS.keys())


def list_pue_standards() -> List[str]:
    """List all available PUE standard codes"""
    return list(PUE_STANDARDS.keys())


def list_regions() -> List[str]:
    """List all available regions"""
    return list(REGIONAL_CARBON_INTENSITY.keys())


def get_regional_pue(region: str) -> Optional[Dict]:
    """Get regional PUE data"""
    return REGIONAL_PUE_DATA.get(region)
