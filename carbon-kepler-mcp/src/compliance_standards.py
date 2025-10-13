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
# ============================================================================

REGIONAL_CARBON_INTENSITY = {
    # Asia Pacific
    "ap-northeast-2": {  # Seoul, Korea
        "region_name": "Seoul (Korea)",
        "average_gco2_kwh": 424,
        "grid_mix": {
            "coal": 35,
            "natural_gas": 28,
            "nuclear": 25,
            "renewable": 12
        }
    },
    "ap-northeast-1": {  # Tokyo, Japan
        "region_name": "Tokyo (Japan)",
        "average_gco2_kwh": 480,
        "grid_mix": {
            "coal": 30,
            "natural_gas": 40,
            "nuclear": 15,
            "renewable": 15
        }
    },
    "ap-southeast-1": {  # Singapore
        "region_name": "Singapore",
        "average_gco2_kwh": 650,
        "grid_mix": {
            "coal": 2,
            "natural_gas": 95,
            "renewable": 3
        }
    },

    # North America
    "us-east-1": {  # Virginia, USA
        "region_name": "Virginia (USA)",
        "average_gco2_kwh": 450,
        "grid_mix": {
            "coal": 20,
            "natural_gas": 40,
            "nuclear": 25,
            "renewable": 15
        }
    },
    "us-west-2": {  # Oregon, USA
        "region_name": "Oregon (USA)",
        "average_gco2_kwh": 200,
        "grid_mix": {
            "coal": 5,
            "natural_gas": 15,
            "nuclear": 10,
            "renewable": 70  # Hydroelectric
        }
    },

    # Europe
    "eu-north-1": {  # Stockholm, Sweden
        "region_name": "Stockholm (Sweden)",
        "average_gco2_kwh": 50,
        "grid_mix": {
            "coal": 0,
            "natural_gas": 5,
            "nuclear": 35,
            "renewable": 60  # Hydroelectric + Wind
        }
    },
    "eu-central-1": {  # Frankfurt, Germany
        "region_name": "Frankfurt (Germany)",
        "average_gco2_kwh": 350,
        "grid_mix": {
            "coal": 25,
            "natural_gas": 15,
            "nuclear": 10,
            "renewable": 50  # Wind + Solar
        }
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
