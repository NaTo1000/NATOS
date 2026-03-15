"""
NATOS LS1 Advanced Tuning Module
Specialized tuning system for GM LS1 5.7L V8 engines

The LS1 is a naturally aspirated 5.7L (346 ci) aluminum-block V8
found in C5 Corvettes, 4th-gen F-bodies (Camaro/Trans Am), and GTO.
Stock output: 305-350 HP depending on variant and year.

WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY
DO NOT USE ON ACTUAL VEHICLES WITHOUT PROFESSIONAL VALIDATION
"""

import json
from typing import Dict, List, Any


# LS1 Engine Specifications
LS1_ENGINE_CONFIG = {
    "name": "GM LS1 5.7L V8",
    "displacement": 5.7,  # Liters (346 ci)
    "cylinders": 8,
    "configuration": "V8",
    "aspiration": "naturally_aspirated",
    "block_material": "aluminum",
    "head_material": "aluminum",
    "bore": 3.898,  # inches
    "stroke": 3.622,  # inches
    "compression_ratio": 10.25,
    "max_boost": 0.0,  # NA engine - no boost stock
    "redline": 6000,  # RPM (stock - upgradable to 7200 with aftermarket valvetrain)
    "stock_hp": 345,  # HP @ 5600 RPM (LS1 Corvette)
    "stock_torque": 350,  # lb-ft @ 4400 RPM
    "fuel_system": "sequential_multi_port",
    "ignition": "coil_near_plug",
    "firing_order": [1, 8, 7, 2, 6, 5, 4, 3],
    "idle_rpm": 600,
    "max_map": 14.7,  # PSI (atmospheric for NA)
}

# LS1 Tune Presets
LS1_TUNE_PRESETS = {
    "ls1_stock": {
        "mode": "ls1_stock",
        "fuel_map_adjustment": 0,
        "timing_adjustment": 0,
        "boost_target": 0,  # NA - no boost
        "afr_target": 14.7,
        "rev_limit": 6000,
        "description": "Factory stock LS1 calibration",
    },
    "ls1_street": {
        "mode": "ls1_street",
        "fuel_map_adjustment": 3,
        "timing_adjustment": 2,
        "boost_target": 0,
        "afr_target": 14.2,
        "rev_limit": 6200,
        "description": "Mild street tune - improved throttle response and torque",
    },
    "ls1_performance": {
        "mode": "ls1_performance",
        "fuel_map_adjustment": 8,
        "timing_adjustment": 4,
        "boost_target": 0,
        "afr_target": 13.0,
        "rev_limit": 6500,
        "description": "Performance tune - headers, intake, cam-ready",
    },
    "ls1_race": {
        "mode": "ls1_race",
        "fuel_map_adjustment": 15,
        "timing_adjustment": 6,
        "boost_target": 0,
        "afr_target": 12.5,
        "rev_limit": 7000,
        "description": "Race tune - aggressive timing and fueling for modified engines",
    },
}


class LS1AdvancedTuner:
    """Advanced tuning module specialized for GM LS1 5.7L V8 engines"""

    def __init__(self):
        self.engine_config = LS1_ENGINE_CONFIG.copy()
        self.knowledge_base = self._load_ls1_knowledge()

    def _load_ls1_knowledge(self) -> Dict[str, Any]:
        """Load LS1-specific tuning knowledge base"""
        return {
            "safe_limits": {
                "max_timing_stock_internals": 28,  # degrees total
                "max_timing_forged": 32,
                "max_rpm_stock": 6200,
                "max_rpm_aftermarket_valvetrain": 7200,
                "min_afr_wot": 12.0,
                "max_afr_cruise": 15.5,
                "max_ect": 240,  # F
                "max_oil_temp": 280,  # F
                "max_egt": 1500,  # F (per cylinder)
                "min_oil_pressure_idle": 15,  # PSI
                "min_oil_pressure_cruise": 30,  # PSI
            },
            "afr_targets": {
                "idle": 14.7,
                "light_cruise": 15.0,
                "cruise": 14.7,
                "part_throttle": 13.5,
                "heavy_load": 12.8,
                "wot": 12.5,
                "wot_aggressive": 12.0,
            },
            "timing_map": {
                "idle": 18,  # degrees BTDC
                "light_cruise": 32,
                "cruise": 28,
                "part_throttle": 26,
                "heavy_load": 22,
                "wot": 24,
                "wot_high_rpm": 26,
            },
            "common_modifications": [
                {
                    "name": "Cold Air Intake",
                    "hp_gain": "8-15",
                    "requires_tune": True,
                    "affects": ["maf_scaling", "iat_compensation"],
                },
                {
                    "name": "Long Tube Headers",
                    "hp_gain": "20-30",
                    "requires_tune": True,
                    "affects": ["timing", "afr", "o2_sensor_location"],
                },
                {
                    "name": "Cam Swap (Stage 2)",
                    "hp_gain": "40-60",
                    "requires_tune": True,
                    "affects": [
                        "idle_quality",
                        "timing",
                        "afr",
                        "rev_limit",
                        "ve_table",
                    ],
                },
                {
                    "name": "Ported Heads",
                    "hp_gain": "30-50",
                    "requires_tune": True,
                    "affects": ["ve_table", "timing", "afr"],
                },
                {
                    "name": "Nitrous (75 shot)",
                    "hp_gain": "75",
                    "requires_tune": True,
                    "affects": ["afr", "timing_retard", "fuel_enrichment"],
                },
                {
                    "name": "Forced Induction (Supercharger)",
                    "hp_gain": "100-200",
                    "requires_tune": True,
                    "affects": [
                        "boost_control",
                        "afr",
                        "timing",
                        "injector_sizing",
                        "fuel_system",
                    ],
                },
            ],
        }

    def research_engine(self) -> Dict[str, Any]:
        """
        Research LS1-specific tuning data

        Returns:
            Comprehensive LS1 research findings
        """
        return {
            "engine_type": "GM LS1 5.7L V8 (Gen III Small Block)",
            "platform": "C5 Corvette / F-Body / GTO",
            "stock_power": f"{self.engine_config['stock_hp']} HP @ 5600 RPM",
            "stock_torque": f"{self.engine_config['stock_torque']} lb-ft @ 4400 RPM",
            "safe_limits": self.knowledge_base["safe_limits"],
            "afr_recommendations": self.knowledge_base["afr_targets"],
            "timing_guidelines": self.knowledge_base["timing_map"],
            "common_issues": [
                "Oil consumption from PCV system at high RPM",
                "Valve spring float above 6200 RPM (stock springs)",
                "Piston ring land failure with excessive timing advance",
                "MAF sensor contamination with oiled air filters",
                "Knock sensor sensitivity to exhaust leaks",
            ],
            "recommended_mods": [
                "Cold air intake with tune (+10-15 HP)",
                "Long tube headers + tune (+25-30 HP)",
                "Cam swap with supporting mods (+50-80 HP)",
                "Ported LS6 intake manifold (+10-15 HP)",
                "Full exhaust with high-flow cats (+10-20 HP)",
            ],
            "tuning_notes": [
                "LS1 responds well to timing advance - safe to 26° at WOT with 93 octane",
                "VE table accuracy is critical for NA power gains",
                "MAF scaling must match any intake modifications",
                "Long tube headers require O2 sensor extension harnesses",
                "Cam swaps require idle airflow and spark table rework",
            ],
        }

    def generate_tune(
        self,
        modifications: List[str],
        driving_style: str = "street",
        fuel_octane: int = 93,
        safety_priority: str = "high",
    ) -> Dict[str, Any]:
        """
        Generate an optimized LS1 tune based on modifications and use case

        Args:
            modifications: List of installed modifications
            driving_style: "daily", "street", "track", "drag"
            fuel_octane: Fuel octane rating (87, 91, 93, 100)
            safety_priority: "high", "medium", "low"

        Returns:
            Complete LS1 tune parameters with recommendations
        """
        # Start from appropriate base preset
        if driving_style == "daily":
            tune = LS1_TUNE_PRESETS["ls1_street"].copy()
        elif driving_style == "track":
            tune = LS1_TUNE_PRESETS["ls1_performance"].copy()
        elif driving_style == "drag":
            tune = LS1_TUNE_PRESETS["ls1_race"].copy()
        else:  # street
            tune = LS1_TUNE_PRESETS["ls1_street"].copy()

        # Detect modifications
        has_intake = any("intake" in m.lower() for m in modifications)
        has_headers = any("header" in m.lower() for m in modifications)
        has_cam = any("cam" in m.lower() for m in modifications)
        has_heads = any("head" in m.lower() or "port" in m.lower() for m in modifications)
        has_nitrous = any("nitrous" in m.lower() or "nos" in m.lower() for m in modifications)
        has_forced_induction = any(
            "supercharger" in m.lower()
            or "turbo" in m.lower()
            or "blower" in m.lower()
            for m in modifications
        )

        # Apply modification adjustments
        if has_intake:
            tune["fuel_map_adjustment"] += 2
            tune["timing_adjustment"] += 1

        if has_headers:
            tune["fuel_map_adjustment"] += 3
            tune["timing_adjustment"] += 2

        if has_cam:
            tune["fuel_map_adjustment"] += 5
            tune["timing_adjustment"] += 3
            tune["rev_limit"] = min(7200, tune["rev_limit"] + 500)
            tune["afr_target"] = min(tune["afr_target"], 13.0)

        if has_heads:
            tune["fuel_map_adjustment"] += 3
            tune["timing_adjustment"] += 1
            tune["rev_limit"] = min(7200, tune["rev_limit"] + 200)

        if has_nitrous:
            tune["fuel_map_adjustment"] += 10
            tune["timing_adjustment"] -= 4  # Retard for nitrous safety
            tune["afr_target"] = 11.8

        if has_forced_induction:
            tune["boost_target"] = 8  # Mild supercharger setup
            tune["fuel_map_adjustment"] += 12
            tune["timing_adjustment"] -= 2  # Retard under boost
            tune["afr_target"] = 11.5

        # Octane-based timing limits
        if fuel_octane <= 87:
            tune["timing_adjustment"] = min(tune["timing_adjustment"], 0)
        elif fuel_octane <= 91:
            tune["timing_adjustment"] = min(tune["timing_adjustment"], 3)
        # 93+ allows full timing

        # Safety caps
        limits = self.knowledge_base["safe_limits"]
        if safety_priority == "high":
            tune["timing_adjustment"] = min(tune["timing_adjustment"], 3)
            tune["afr_target"] = max(tune["afr_target"], 12.5)
            tune["rev_limit"] = min(tune["rev_limit"], 6200)
        elif safety_priority == "medium":
            tune["timing_adjustment"] = min(tune["timing_adjustment"], 5)
            tune["afr_target"] = max(tune["afr_target"], 12.0)
            tune["rev_limit"] = min(tune["rev_limit"], 6800)

        # Generate warnings
        warnings = []
        if tune["timing_adjustment"] > 4:
            warnings.append(
                f"Timing advance +{tune['timing_adjustment']}° requires premium fuel and knock monitoring"
            )
        if tune["rev_limit"] > 6200:
            warnings.append(
                f"Rev limit {tune['rev_limit']} RPM requires upgraded valve springs"
            )
        if has_nitrous:
            warnings.append("Nitrous requires precise fuel system calibration - verify injector sizing")
        if has_forced_induction:
            warnings.append(
                "Forced induction on LS1 requires forged internals for sustained use"
            )

        # Estimate gains
        estimated_hp_gain = 0
        if has_intake:
            estimated_hp_gain += 12
        if has_headers:
            estimated_hp_gain += 25
        if has_cam:
            estimated_hp_gain += 55
        if has_heads:
            estimated_hp_gain += 40
        if has_nitrous:
            estimated_hp_gain += 75
        if has_forced_induction:
            estimated_hp_gain += 150

        return {
            "tune_parameters": tune,
            "base_engine": self.engine_config["name"],
            "estimated_hp": self.engine_config["stock_hp"] + estimated_hp_gain,
            "estimated_gains": f"+{estimated_hp_gain} HP over stock",
            "confidence": 0.85 if safety_priority == "high" else 0.70,
            "warnings": warnings,
            "fuel_requirement": f"{fuel_octane} octane",
            "modifications_detected": {
                "intake": has_intake,
                "headers": has_headers,
                "cam": has_cam,
                "heads": has_heads,
                "nitrous": has_nitrous,
                "forced_induction": has_forced_induction,
            },
        }

    def monitor_and_adapt(
        self, current_tune: Dict[str, Any], telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        LS1-specific real-time monitoring and adaptive adjustments

        Args:
            current_tune: Current tune parameters
            telemetry: Real-time telemetry data

        Returns:
            Recommended adjustments
        """
        adjustments = {}
        reasons = []
        limits = self.knowledge_base["safe_limits"]

        # Knock detection - LS1 is sensitive to detonation
        knock_count = telemetry.get("knock_count", 0)
        if knock_count > 2:
            adjustments["timing_adjustment"] = current_tune.get("timing_adjustment", 0) - 3
            reasons.append(
                f"Knock detected ({knock_count} events) - retarding timing 3°"
            )

        if knock_count > 4:
            adjustments["fuel_map_adjustment"] = (
                current_tune.get("fuel_map_adjustment", 0) + 5
            )
            reasons.append("Excessive knock - enriching fuel for safety")

        # Temperature monitoring - LS1 aluminum block is heat sensitive
        ect = telemetry.get("ect", 180)
        if ect > 225:
            adjustments["timing_adjustment"] = min(
                adjustments.get(
                    "timing_adjustment", current_tune.get("timing_adjustment", 0)
                ),
                current_tune.get("timing_adjustment", 0) - 2,
            )
            reasons.append(f"Elevated coolant temp ({ect:.0f}°F) - reducing timing")

        if ect > 240:
            adjustments["rev_limit"] = 4000
            reasons.append("CRITICAL: Overheating - limp mode engaged")

        # Oil pressure - critical for LS1 rod bearings
        oil_pressure = telemetry.get("oil_pressure", 40)
        rpm = telemetry.get("rpm", 0)
        if oil_pressure < 15 and rpm > 1000:
            adjustments["rev_limit"] = 2500
            reasons.append(
                f"CRITICAL: Low oil pressure ({oil_pressure:.0f} PSI) - emergency RPM limit"
            )
        elif oil_pressure < 25 and rpm > 3000:
            adjustments["rev_limit"] = min(
                adjustments.get("rev_limit", 9999), 4000
            )
            reasons.append(
                f"Low oil pressure ({oil_pressure:.0f} PSI) at high RPM - limiting RPM"
            )

        # AFR monitoring
        afr = telemetry.get("afr", 14.7)
        if afr < 10.5:
            adjustments["fuel_map_adjustment"] = (
                current_tune.get("fuel_map_adjustment", 0) - 5
            )
            reasons.append(f"Dangerously rich ({afr:.1f}) - reducing fuel")
        elif afr > 15.5 and rpm > 3000:
            adjustments["fuel_map_adjustment"] = (
                current_tune.get("fuel_map_adjustment", 0) + 5
            )
            reasons.append(f"Lean condition ({afr:.1f}) under load - adding fuel")

        # Exhaust temp monitoring
        egt = telemetry.get("egt", 800)
        if egt > 1400:
            adjustments["timing_adjustment"] = min(
                adjustments.get(
                    "timing_adjustment", current_tune.get("timing_adjustment", 0)
                ),
                current_tune.get("timing_adjustment", 0) - 2,
            )
            reasons.append(f"High exhaust temps ({egt:.0f}°F) - pulling timing")

        if egt > limits["max_egt"]:
            adjustments["fuel_map_adjustment"] = (
                current_tune.get("fuel_map_adjustment", 0) + 8
            )
            reasons.append("CRITICAL: EGT limit exceeded - maximum fuel enrichment")

        severity = "normal"
        if any("CRITICAL" in r for r in reasons):
            severity = "critical"
        elif reasons:
            severity = "warning"

        return {
            "adjustments_needed": len(adjustments) > 0,
            "adjustments": adjustments,
            "reasons": reasons,
            "severity": severity,
        }

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """
        Get an LS1 tune preset by name

        Args:
            preset_name: One of ls1_stock, ls1_street, ls1_performance, ls1_race

        Returns:
            Tune preset parameters
        """
        if preset_name in LS1_TUNE_PRESETS:
            return LS1_TUNE_PRESETS[preset_name].copy()
        return None

    def get_available_presets(self) -> List[Dict[str, Any]]:
        """
        Get all available LS1 tune presets

        Returns:
            List of preset info dicts
        """
        return [
            {"name": k, "description": v["description"]}
            for k, v in LS1_TUNE_PRESETS.items()
        ]


def example_usage():
    """Example of how to use the LS1 Advanced Tuner"""

    tuner = LS1AdvancedTuner()

    # Research the LS1
    print("🔍 LS1 Engine Research")
    print("=" * 50)
    research = tuner.research_engine()
    print(json.dumps(research, indent=2))

    # Generate a tune for a mildly modified LS1
    print("\n⚙️ Generating Tune - Headers + Intake + Cam")
    print("=" * 50)
    mods = ["Cold Air Intake", "Long Tube Headers", "BTR Stage 2 Cam"]
    tune = tuner.generate_tune(
        modifications=mods,
        driving_style="street",
        fuel_octane=93,
        safety_priority="medium",
    )
    print(json.dumps(tune, indent=2))

    # List available presets
    print("\n📋 Available Presets")
    print("=" * 50)
    for preset in tuner.get_available_presets():
        print(f"  {preset['name']}: {preset['description']}")

    # Monitor with simulated telemetry
    print("\n🔄 Adaptive Monitoring")
    print("=" * 50)
    telemetry = {
        "knock_count": 3,
        "ect": 210,
        "oil_pressure": 35,
        "afr": 13.2,
        "rpm": 4500,
        "egt": 1100,
    }
    adaptation = tuner.monitor_and_adapt(tune["tune_parameters"], telemetry)
    print(json.dumps(adaptation, indent=2))


if __name__ == "__main__":
    example_usage()
