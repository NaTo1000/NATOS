"""
NATOS AI Tuning Agent
Autonomous tuning system with LS-series engine support,
methanol/water injection, nitrous fogging, and wheel speed awareness
"""

import os
import json
from typing import Dict, List, Any

# LS-series engine knowledge base
LS_ENGINE_DATA = {
    "ls1": {
        "engine_type": "LS1 5.7L Pushrod V8",
        "safe_boost_limit": 8,
        "max_boost_modified": 14,
        "stock_hp": 350,
        "stock_torque": 365,
        "afr_recommendations": {
            "idle": 14.7,
            "cruise": 14.7,
            "part_throttle": 13.5,
            "wide_open_throttle": 11.8,
            "max_boost": 11.5
        },
        "timing_guidelines": {
            "base_timing": 25,
            "boost_retard": -0.8,
            "knock_retard": -3
        },
        "common_issues": [
            "Stock pistons limit boost to ~8 PSI safely",
            "LS1 heads flow ~200 CFM stock",
            "Fuel system limits around 450hp on stock injectors",
            "Oil consumption at high RPM with stock rings"
        ],
        "recommended_mods": [
            "LS6 intake manifold (+15hp)",
            "Long-tube headers (+25hp)",
            "Supercharger kit (Magnuson/Vortech)",
            "Upgraded fuel injectors (42lb+)",
        ]
    },
    "ls2": {
        "engine_type": "LS2 6.0L Pushrod V8",
        "safe_boost_limit": 10,
        "max_boost_modified": 16,
        "stock_hp": 400,
        "stock_torque": 400,
        "afr_recommendations": {
            "idle": 14.7,
            "cruise": 14.7,
            "part_throttle": 13.2,
            "wide_open_throttle": 11.8,
            "max_boost": 11.3
        },
        "timing_guidelines": {
            "base_timing": 25,
            "boost_retard": -0.8,
            "knock_retard": -3
        },
        "common_issues": [
            "Cylinder wall thickness limits bore size",
            "Stock fuel pump insufficient above 500hp",
            "Valve springs fatigue above 6500 RPM sustained",
            "Oil pan windage at high RPM"
        ],
        "recommended_mods": [
            "Ported LS3 heads (+40hp)",
            "Supercharger (Whipple/Procharger)",
            "Upgraded valve springs (for higher RPM)",
            "High-flow fuel pump and injectors"
        ]
    },
    "ls3": {
        "engine_type": "LS3 6.2L Pushrod V8",
        "safe_boost_limit": 12,
        "max_boost_modified": 18,
        "stock_hp": 430,
        "stock_torque": 424,
        "afr_recommendations": {
            "idle": 14.7,
            "cruise": 14.7,
            "part_throttle": 13.0,
            "wide_open_throttle": 11.5,
            "max_boost": 11.0
        },
        "timing_guidelines": {
            "base_timing": 25,
            "boost_retard": -0.8,
            "knock_retard": -3
        },
        "common_issues": [
            "Stock bottom end good to ~650hp",
            "Head gaskets may fail above 14 PSI",
            "Fuel system limits at ~550hp stock",
            "Heat soak in supercharged applications"
        ],
        "recommended_mods": [
            "CNC ported LS3 heads (+50hp)",
            "Supercharger (2.3L Whipple = 600+hp)",
            "Forged internals (for 700+hp builds)",
            "Methanol injection for intercooling"
        ]
    }
}


class AITuningAgent:
    """AI agent that researches and creates optimal ECU tunes
    with LS-engine awareness, meth/water, and nitrous support"""
    
    def __init__(self):
        self.knowledge_base = {
            "engines": LS_ENGINE_DATA,
            "modifications": {},
            "tuning_strategies": {}
        }
        
    def research_engine(self, engine_specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research engine tuning information for LS-series engines.
        
        Args:
            engine_specs: Dictionary containing engine specifications
            
        Returns:
            Research findings with tuning recommendations
        """
        
        # Identify LS engine from displacement
        displacement = engine_specs.get('displacement', 5.7)
        profile = "ls1"
        if displacement >= 6.1:
            profile = "ls3"
        elif displacement >= 5.9:
            profile = "ls2"
        
        engine_data = LS_ENGINE_DATA.get(profile, LS_ENGINE_DATA["ls1"])
        
        result = dict(engine_data)
        result["meth_injection_benefits"] = {
            "iat_reduction": "30-50°F under boost",
            "effective_octane_increase": "+5 points",
            "safe_timing_advance": "+2-4° with meth active",
            "recommended_mix": "50/50 methanol/water",
            "activation_point": "3+ PSI boost"
        }
        result["nitrous_guidelines"] = {
            "safe_shot_na": "75-100hp on stock internals",
            "safe_shot_boosted": "50-75hp with supercharger",
            "required_afr": "11.5-12.0 under spray",
            "timing_retard": "-2° per 50hp shot",
            "fuel_enrichment": "10-15% additional fuel",
            "wet_vs_dry": "Wet recommended for larger shots"
        }
        result["wheel_speed_notes"] = {
            "traction_management": "Monitor rear wheel slip vs front",
            "launch_control": "Limit RPM until wheel speed matches",
            "safe_slip_pct": "5-10% optimal for traction"
        }
        
        return result
    
    def analyze_driving_pattern(self, telemetry_history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze driving patterns including wheel speed data.
        
        Args:
            telemetry_history: List of telemetry snapshots
            
        Returns:
            Driving pattern analysis
        """
        
        if not telemetry_history:
            return {"pattern": "insufficient_data"}
        
        avg_throttle = sum(t['throttle_position'] for t in telemetry_history) / len(telemetry_history)
        max_throttle = max(t['throttle_position'] for t in telemetry_history)
        
        avg_rpm = sum(t['rpm'] for t in telemetry_history) / len(telemetry_history)
        max_rpm = max(t['rpm'] for t in telemetry_history)
        
        avg_boost = sum(t['boost'] for t in telemetry_history) / len(telemetry_history)
        max_boost = max(t['boost'] for t in telemetry_history)
        
        # Analyze wheel slip if available
        avg_slip = 0
        max_slip = 0
        if 'wheel_slip' in telemetry_history[0]:
            avg_slip = sum(t.get('wheel_slip', 0) for t in telemetry_history) / len(telemetry_history)
            max_slip = max(t.get('wheel_slip', 0) for t in telemetry_history)
        
        if avg_throttle < 30 and max_rpm < 4000:
            style = "economy"
            recommendation = "Optimize for fuel efficiency"
        elif avg_throttle < 50 and max_rpm < 5000:
            style = "moderate"
            recommendation = "Balanced tune for daily driving"
        elif avg_throttle > 60 or max_rpm > 6000:
            style = "aggressive"
            recommendation = "Performance-oriented tune with traction management"
        else:
            style = "mixed"
            recommendation = "Adaptive tune with multiple modes"
        
        return {
            "driving_style": style,
            "recommendation": recommendation,
            "statistics": {
                "avg_throttle": avg_throttle,
                "max_throttle": max_throttle,
                "avg_rpm": avg_rpm,
                "max_rpm": max_rpm,
                "avg_boost": avg_boost,
                "max_boost": max_boost,
                "avg_wheel_slip": avg_slip,
                "max_wheel_slip": max_slip,
            }
        }
    
    def generate_tune(self, 
                      engine_specs: Dict[str, Any],
                      driving_pattern: Dict[str, Any],
                      modifications: List[str],
                      safety_priority: str = "high") -> Dict[str, Any]:
        """
        Generate optimized tune with meth/water and nitrous awareness.
        
        Args:
            engine_specs: Engine specifications
            driving_pattern: Analyzed driving pattern
            modifications: List of installed modifications
            safety_priority: "high", "medium", or "low"
            
        Returns:
            Complete tune parameters
        """
        
        research = self.research_engine(engine_specs)
        style = driving_pattern.get("driving_style", "moderate")
        
        # Start with conservative LS values
        tune = {
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": research.get("safe_boost_limit", 8),
            "afr_target": 14.7,
            "rev_limit": engine_specs.get("redline", 6000),
        }
        
        # Meth/water injection recommendations
        meth_config = {
            "recommended": False,
            "boost_activation_psi": 3.0,
            "mix_ratio": 50,
        }
        
        # Nitrous recommendations
        nitrous_config = {
            "recommended": False,
            "shot_size_hp": 0,
            "mode": "wet",
        }
        
        if style == "economy":
            tune.update({
                "fuel_map_adjustment": -3,
                "timing_adjustment": 2,
                "boost_target": research.get("safe_boost_limit", 8) * 0.5,
                "afr_target": 14.7,
                "rev_limit": engine_specs.get("redline", 6000) - 500
            })
        elif style in ("aggressive", "performance"):
            tune.update({
                "fuel_map_adjustment": 10,
                "timing_adjustment": 3,
                "boost_target": research.get("safe_boost_limit", 8) * 0.85,
                "afr_target": 12.0,
                "rev_limit": engine_specs.get("redline", 6000) + 200
            })
            meth_config["recommended"] = True
            nitrous_config["recommended"] = True
            nitrous_config["shot_size_hp"] = 75
        
        # Adjust for modifications
        has_intercooler = any("intercooler" in mod.lower() for mod in modifications)
        has_fuel_pump = any("fuel pump" in mod.lower() for mod in modifications)
        has_internals = any("forged" in mod.lower() or "piston" in mod.lower() for mod in modifications)
        has_meth = any("meth" in mod.lower() or "water injection" in mod.lower() for mod in modifications)
        has_nitrous = any("nitrous" in mod.lower() or "nos" in mod.lower() for mod in modifications)
        has_supercharger = any("supercharger" in mod.lower() or "blower" in mod.lower() for mod in modifications)
        
        if has_intercooler:
            tune["boost_target"] += 2
        if has_fuel_pump:
            tune["fuel_map_adjustment"] += 5
        if has_internals:
            tune["boost_target"] = min(research.get("max_boost_modified", 14), tune["boost_target"] + 4)
            tune["rev_limit"] = min(engine_specs.get("redline", 6000) + 800, tune["rev_limit"] + 300)
        if has_meth:
            tune["timing_adjustment"] += 2
            meth_config["recommended"] = True
        if has_nitrous:
            nitrous_config["recommended"] = True
            nitrous_config["shot_size_hp"] = 100
        if has_supercharger:
            tune["boost_target"] = min(research.get("max_boost_modified", 14), tune["boost_target"] + 3)
        
        # Apply safety limits
        if safety_priority == "high":
            tune["boost_target"] = min(research.get("safe_boost_limit", 8), tune["boost_target"])
            tune["afr_target"] = max(12.0, tune["afr_target"])
            tune["timing_adjustment"] = min(2, tune["timing_adjustment"])
            nitrous_config["shot_size_hp"] = min(75, nitrous_config["shot_size_hp"])
        elif safety_priority == "medium":
            tune["boost_target"] = min(research.get("safe_boost_limit", 8) + 4, tune["boost_target"])
            tune["afr_target"] = max(11.5, tune["afr_target"])
            tune["timing_adjustment"] = min(4, tune["timing_adjustment"])
        
        warnings = []
        if tune["boost_target"] > research.get("safe_boost_limit", 8):
            warnings.append(f"Boost target {tune['boost_target']:.0f} PSI exceeds stock safe limit")
        if tune["afr_target"] < 12.0:
            warnings.append(f"Rich AFR {tune['afr_target']} may cause carbon buildup")
        if tune["timing_adjustment"] > 3:
            warnings.append(f"Advanced timing +{tune['timing_adjustment']}° increases knock risk")
        if nitrous_config["recommended"] and not has_fuel_pump:
            warnings.append("Nitrous use recommended only with upgraded fuel system")
        
        return {
            "tune_parameters": tune,
            "meth_injection_config": meth_config,
            "nitrous_config": nitrous_config,
            "confidence": 0.85,
            "warnings": warnings,
            "recommendations": research.get("recommended_mods", []),
            "expected_gains": {
                "horsepower": f"+{15 + int(tune['boost_target'])}%",
                "torque": f"+{20 + int(tune['boost_target'])}%",
                "fuel_economy": f"{-10 if style == 'aggressive' else +5}%"
            }
        }
    
    def monitor_and_adapt(self, 
                          current_tune: Dict[str, Any],
                          telemetry: Dict[str, Any],
                          safety_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor telemetry and adapt tune in real-time.
        Includes wheel speed, meth/water, and nitrous awareness.
        
        Args:
            current_tune: Current tune parameters
            telemetry: Real-time telemetry data
            safety_status: Current safety warnings/alerts
            
        Returns:
            Tune adjustments (if needed)
        """
        
        adjustments = {}
        reasons = []
        
        # Check for knock
        if telemetry.get("knock_count", 0) > 3:
            adjustments["timing_adjustment"] = current_tune["timing_adjustment"] - 2
            adjustments["boost_target"] = current_tune["boost_target"] - 2
            reasons.append("Knock detected - retarding timing and reducing boost")
        
        # Check temperatures
        if telemetry.get("ect", 0) > 220:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] + 5
            reasons.append("High coolant temp - enriching mixture for cooling")
        
        if telemetry.get("iat", 0) > 140:
            adjustments["timing_adjustment"] = current_tune.get("timing_adjustment", 0) - 1
            reasons.append("High intake temp - retarding timing (enable meth injection!)")
        
        # Check AFR
        if telemetry.get("afr", 14.7) < 10.5:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] - 5
            reasons.append("Dangerously rich - reducing fuel")
        elif telemetry.get("afr", 14.7) > 15.5 and telemetry.get("boost", 0) > 5:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] + 5
            reasons.append("Lean under boost - adding fuel for safety")
        
        # Check oil pressure
        if telemetry.get("oil_pressure", 50) < 10 and telemetry.get("rpm", 0) > 2000:
            adjustments["rev_limit"] = 3000
            reasons.append("CRITICAL: Low oil pressure - limiting RPM")
        
        # Wheel slip monitoring
        wheel_slip = telemetry.get("wheel_slip", 0)
        if wheel_slip > 15:
            adjustments["boost_target"] = current_tune.get("boost_target", 8) - 3
            reasons.append(f"Excessive wheel slip {wheel_slip:.1f}% - reducing boost for traction")
        
        # Meth tank monitoring
        meth_tank = telemetry.get("meth_tank_level", 100)
        if meth_tank < 10 and telemetry.get("boost", 0) > 5:
            adjustments["boost_target"] = current_tune.get("boost_target", 8) - 2
            adjustments["timing_adjustment"] = current_tune.get("timing_adjustment", 0) - 2
            reasons.append("CRITICAL: Meth tank nearly empty - reducing boost and timing")
        
        # Nitrous safety check
        nitrous_active = telemetry.get("nitrous_flow_rate", 0) > 0
        if nitrous_active and telemetry.get("afr", 14.7) > 12.5:
            adjustments["fuel_map_adjustment"] = current_tune.get("fuel_map_adjustment", 0) + 10
            reasons.append("CRITICAL: Lean condition with nitrous active - adding fuel immediately")
        
        return {
            "adjustments_needed": len(adjustments) > 0,
            "adjustments": adjustments,
            "reasons": reasons,
            "severity": "critical" if "CRITICAL" in str(reasons) else "warning" if reasons else "normal"
        }


def example_usage():
    """Example of how to use the AI Tuning Agent with LS engines"""
    
    agent = AITuningAgent()
    
    # LS3 engine specs
    engine = {
        "displacement": 6.2,
        "cylinders": 8,
        "aspiration": "supercharged",
        "max_boost": 12.0,
        "redline": 6600
    }
    
    # Research engine
    print("🔍 Researching LS3 engine...")
    research = agent.research_engine(engine)
    print(json.dumps(research, indent=2))
    
    # Simulate driving pattern with wheel speed data
    telemetry_history = [
        {"throttle_position": 45, "rpm": 3000, "boost": 6, "wheel_slip": 2.0},
        {"throttle_position": 80, "rpm": 5500, "boost": 10, "wheel_slip": 8.0},
        {"throttle_position": 30, "rpm": 2500, "boost": 3, "wheel_slip": 1.0},
    ]
    
    print("\n📊 Analyzing driving pattern...")
    pattern = agent.analyze_driving_pattern(telemetry_history)
    print(json.dumps(pattern, indent=2))
    
    # Generate tune
    print("\n⚙️ Generating optimized tune...")
    modifications = ["Supercharger kit", "Upgraded fuel pump", "Methanol injection"]
    tune = agent.generate_tune(engine, pattern, modifications, safety_priority="high")
    print(json.dumps(tune, indent=2))
    
    # Monitor and adapt
    print("\n🔄 Monitoring for adaptive adjustments...")
    current_telemetry = {
        "knock_count": 4,
        "ect": 195,
        "iat": 110,
        "afr": 13.5,
        "oil_pressure": 45,
        "wheel_slip": 12.0,
        "meth_tank_level": 80,
        "nitrous_flow_rate": 0
    }
    
    adaptation = agent.monitor_and_adapt(
        tune["tune_parameters"],
        current_telemetry,
        {}
    )
    print(json.dumps(adaptation, indent=2))

if __name__ == "__main__":
    example_usage()
