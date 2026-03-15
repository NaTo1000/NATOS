"""
NATOS AI Tuning Agent
Autonomous tuning system with internet research capabilities
"""

import os
import json
import math
from typing import Dict, List, Any

class AITuningAgent:
    """AI agent that researches and creates optimal ECU tunes"""
    
    def __init__(self):
        # AI client would be initialized here in production
        # self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.knowledge_base = {
            "engines": {},
            "modifications": {},
            "tuning_strategies": {}
        }
        
    def research_engine(self, engine_specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research engine online to gather tuning information
        
        Args:
            engine_specs: Dictionary containing engine specifications
            
        Returns:
            Research findings with tuning recommendations
        """
        
        query = f"""
        Research tuning information for this engine:
        - Displacement: {engine_specs.get('displacement', 'Unknown')}L
        - Cylinders: {engine_specs.get('cylinders', 'Unknown')}
        - Aspiration: {engine_specs.get('aspiration', 'Unknown')}
        - Max Boost: {engine_specs.get('max_boost', 'Unknown')} PSI
        
        Find:
        1. Safe boost limits
        2. Recommended AFR ranges for different scenarios
        3. Timing advance/retard guidelines
        4. Common failure points
        5. Performance modifications that work well
        """
        
        # In production, this would make actual web searches
        # For now, we'll return realistic simulated data
        
        displacement = engine_specs.get('displacement', 2.0)
        cylinders = engine_specs.get('cylinders', 4)
        aspiration = engine_specs.get('aspiration', 'turbocharged')
        
        base_safe_boost = 22 - (displacement * 2)
        safe_boost_limit = max(12, min(25, round(base_safe_boost)))
        max_boost_modified = min(30, safe_boost_limit + 5)
        
        safe_power_per_liter = max(80, 150 + (cylinders * 10) - (displacement * 15))
        power_smoothness = min(1.0, round(0.5 + (cylinders * 0.1), 2))
        
        base_timing = max(10, round(18 - displacement * 1.5))
        boost_retard_per_psi = round(-0.3 - (displacement * 0.1), 2)
        
        hp_limit = round(displacement * safe_power_per_liter)
        fuel_pump_limit = round(hp_limit * 1.15)
        
        engine_type = f"{displacement}L {aspiration.title()} Inline-{cylinders}"
        
        return {
            "engine_type": engine_type,
            "safe_boost_limit": safe_boost_limit,
            "max_boost_modified": max_boost_modified,
            "safe_power_per_liter": round(safe_power_per_liter, 1),
            "power_smoothness": power_smoothness,
            "afr_recommendations": {
                "idle": 14.7,
                "cruise": 15.0,
                "part_throttle": 14.0,
                "wide_open_throttle": 11.8,
                "max_boost": 11.5
            },
            "timing_guidelines": {
                "base_timing": base_timing,
                "boost_retard": boost_retard_per_psi,
                "knock_retard": -2
            },
            "common_issues": [
                f"Weak piston rings above {hp_limit}hp",
                f"Stock turbo efficient to ~{safe_boost_limit} PSI",
                f"Fuel pump limits at {fuel_pump_limit}hp",
                f"Stock intercooler heat soaks above {safe_boost_limit - 3} PSI"
            ],
            "recommended_mods": [
                "Upgraded intercooler (reduces IAT by 30-50°F)",
                f"High-flow fuel pump (supports {fuel_pump_limit + 100}hp)",
                f"Forged pistons (safe to {max_boost_modified} PSI)",
                f"Larger turbo (efficient to {max_boost_modified}+ PSI)"
            ]
        }
    
    def analyze_driving_pattern(self, telemetry_history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze driving patterns to optimize tune
        
        Args:
            telemetry_history: List of telemetry snapshots
            
        Returns:
            Driving pattern analysis
        """
        
        if not telemetry_history:
            return {"pattern": "insufficient_data"}
        
        # Analyze throttle usage
        avg_throttle = sum(t['throttle_position'] for t in telemetry_history) / len(telemetry_history)
        max_throttle = max(t['throttle_position'] for t in telemetry_history)
        
        # Analyze RPM range
        avg_rpm = sum(t['rpm'] for t in telemetry_history) / len(telemetry_history)
        max_rpm = max(t['rpm'] for t in telemetry_history)
        
        # Analyze boost usage
        avg_boost = sum(t['boost'] for t in telemetry_history) / len(telemetry_history)
        max_boost = max(t['boost'] for t in telemetry_history)
        
        # Determine driving style
        if avg_throttle < 30 and max_rpm < 4000:
            style = "economy"
            recommendation = "Optimize for fuel efficiency"
        elif avg_throttle < 50 and max_rpm < 5000:
            style = "moderate"
            recommendation = "Balanced tune for daily driving"
        elif avg_throttle <= 60 and max_rpm <= 6000:
            style = "spirited"
            recommendation = "Spirited tune with enhanced throttle response"
        elif avg_throttle > 60 or max_rpm > 6000:
            style = "aggressive"
            recommendation = "Performance-oriented tune"
        else:
            style = "mixed"
            recommendation = "Adaptive tune with multiple modes"
        
        num_samples = len(telemetry_history)
        data_confidence = round(min(1.0, num_samples / 50.0), 2)
        
        return {
            "driving_style": style,
            "recommendation": recommendation,
            "data_confidence": data_confidence,
            "statistics": {
                "avg_throttle": avg_throttle,
                "max_throttle": max_throttle,
                "avg_rpm": avg_rpm,
                "max_rpm": max_rpm,
                "avg_boost": avg_boost,
                "max_boost": max_boost
            }
        }
    
    def generate_tune(self, 
                      engine_specs: Dict[str, Any],
                      driving_pattern: Dict[str, Any],
                      modifications: List[str],
                      safety_priority: str = "high") -> Dict[str, Any]:
        """
        Generate optimized tune based on all available data
        
        Args:
            engine_specs: Engine specifications
            driving_pattern: Analyzed driving pattern
            modifications: List of installed modifications
            safety_priority: "high", "medium", or "low"
            
        Returns:
            Complete tune parameters
        """
        
        research = self.research_engine(engine_specs)
        
        # Base tune on driving pattern
        style = driving_pattern.get("driving_style", "moderate")
        
        # Start with conservative values
        tune = {
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": 12,
            "afr_target": 14.7,
            "rev_limit": 7000,
        }
        
        # Adjust for driving style
        if style == "economy":
            tune.update({
                "fuel_map_adjustment": -5,
                "timing_adjustment": 2,
                "boost_target": 10,
                "afr_target": 15.0,
                "rev_limit": 6500
            })
        elif style == "spirited":
            tune.update({
                "fuel_map_adjustment": 5,
                "timing_adjustment": 2,
                "boost_target": 14,
                "afr_target": 12.8,
                "rev_limit": 7000
            })
        elif style == "aggressive" or style == "performance":
            tune.update({
                "fuel_map_adjustment": 10,
                "timing_adjustment": 3,
                "boost_target": 16,
                "afr_target": 12.0,
                "rev_limit": 7200
            })
        
        # Adjust for modifications
        has_intercooler = any("intercooler" in mod.lower() for mod in modifications)
        has_fuel_pump = any("fuel pump" in mod.lower() for mod in modifications)
        has_internals = any("forged" in mod.lower() or "piston" in mod.lower() for mod in modifications)
        
        if has_intercooler:
            tune["boost_target"] += 2  # Can run more boost with better cooling
            
        if has_fuel_pump:
            tune["fuel_map_adjustment"] += 5  # Can add more fuel
            
        if has_internals:
            tune["boost_target"] = min(22, tune["boost_target"] + 4)  # Stronger internals
            tune["rev_limit"] = min(7800, tune["rev_limit"] + 300)
        
        # Apply safety limits
        if safety_priority == "high":
            tune["boost_target"] = min(15, tune["boost_target"])
            tune["afr_target"] = max(12.0, tune["afr_target"])
            tune["timing_adjustment"] = min(2, tune["timing_adjustment"])
        elif safety_priority == "medium":
            tune["boost_target"] = min(18, tune["boost_target"])
            tune["afr_target"] = max(11.5, tune["afr_target"])
            tune["timing_adjustment"] = min(4, tune["timing_adjustment"])
        
        # Parameter interaction effects
        if tune["boost_target"] > 14 and tune["timing_adjustment"] > 2:
            tune["timing_adjustment"] -= 1
        if tune["afr_target"] < 12.5 and tune["boost_target"] > 14:
            tune["fuel_map_adjustment"] += 3
        
        # Add safety warnings
        warnings = []
        if tune["boost_target"] > 15:
            warnings.append(f"Boost target {tune['boost_target']} PSI requires upgraded components")
        if tune["afr_target"] < 12.0:
            warnings.append(f"Rich AFR {tune['afr_target']} may cause carbon buildup")
        if tune["timing_adjustment"] > 3:
            warnings.append(f"Advanced timing +{tune['timing_adjustment']}° increases knock risk")
        
        boost = tune["boost_target"]
        hp_gain = round(15 + 10 * math.sqrt(boost / 10), 1)
        tq_gain = round(20 + 12 * math.sqrt(boost / 10), 1)
        turbo_lag_estimate = round(0.5 + (boost / 20), 2)
        
        return {
            "tune_parameters": tune,
            "confidence": 0.85,
            "warnings": warnings,
            "recommendations": research["recommended_mods"],
            "turbo_lag_estimate": turbo_lag_estimate,
            "expected_gains": {
                "horsepower": f"+{hp_gain}%",
                "torque": f"+{tq_gain}%",
                "fuel_economy": f"{-10 if style == 'aggressive' else +5}%"
            }
        }
    
    def monitor_and_adapt(self, 
                          current_tune: Dict[str, Any],
                          telemetry: Dict[str, Any],
                          safety_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor telemetry and adapt tune in real-time
        
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
            adjustments["timing_adjustment"] = current_tune["timing_adjustment"] - 1
            reasons.append("High intake temp - retarding timing for safety")
        
        # Check AFR
        if telemetry.get("afr", 14.7) < 10.5:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] - 5
            reasons.append("Dangerously rich - reducing fuel")
        elif telemetry.get("afr", 14.7) > 15.5 and telemetry.get("boost", 0) > 5:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] + 5
            reasons.append("Lean under boost - adding fuel for safety")
        
        # Check oil pressure
        if telemetry.get("oil_pressure", 50) < 10 and telemetry.get("rpm", 0) > 2000:
            adjustments["rev_limit"] = 3000  # Emergency limp mode
            reasons.append("CRITICAL: Low oil pressure - limiting RPM")
        
        # Check EGT
        if telemetry.get("egt", 0) > 1400:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] + 5
            adjustments["boost_target"] = current_tune["boost_target"] - 3
            reasons.append("High EGT - enriching mixture and reducing boost")
        
        # Check injector duty cycle
        if telemetry.get("injector_duty", 0) > 85:
            adjustments["fuel_map_adjustment"] = current_tune["fuel_map_adjustment"] - 3
            reasons.append("WARNING: Injector duty cycle >85% - reducing fuel map to protect injectors")
        
        # Check voltage
        if telemetry.get("voltage", 14.0) < 13.0:
            reasons.append("WARNING: Low voltage - electrical system strain detected")
        
        # Check for over-boost
        if telemetry.get("boost", 0) > current_tune.get("boost_target", 12) + 3:
            adjustments["boost_target"] = 0
            adjustments["timing_adjustment"] = current_tune["timing_adjustment"] - 5
            reasons.append("CRITICAL: Over-boost detected - emergency boost cut and timing retard")
        
        return {
            "adjustments_needed": len(adjustments) > 0,
            "adjustments": adjustments,
            "reasons": reasons,
            "severity": "critical" if "CRITICAL" in str(reasons) else "warning" if reasons else "normal"
        }

def example_usage():
    """Example of how to use the AI Tuning Agent"""
    
    agent = AITuningAgent()
    
    # Engine specs
    engine = {
        "displacement": 2.0,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "max_boost": 15.0
    }
    
    # Research engine
    print("🔍 Researching engine...")
    research = agent.research_engine(engine)
    print(json.dumps(research, indent=2))
    
    # Simulate driving pattern
    telemetry_history = [
        {"throttle_position": 45, "rpm": 3000, "boost": 8},
        {"throttle_position": 80, "rpm": 5500, "boost": 14},
        {"throttle_position": 30, "rpm": 2500, "boost": 3},
    ]
    
    print("\n📊 Analyzing driving pattern...")
    pattern = agent.analyze_driving_pattern(telemetry_history)
    print(json.dumps(pattern, indent=2))
    
    # Generate tune
    print("\n⚙️ Generating optimized tune...")
    modifications = ["Upgraded intercooler", "High-flow fuel pump"]
    tune = agent.generate_tune(engine, pattern, modifications, safety_priority="high")
    print(json.dumps(tune, indent=2))
    
    # Monitor and adapt
    print("\n🔄 Monitoring for adaptive adjustments...")
    current_telemetry = {
        "knock_count": 4,
        "ect": 195,
        "iat": 110,
        "afr": 13.5,
        "oil_pressure": 45
    }
    
    adaptation = agent.monitor_and_adapt(
        tune["tune_parameters"],
        current_telemetry,
        {}
    )
    print(json.dumps(adaptation, indent=2))

if __name__ == "__main__":
    example_usage()
