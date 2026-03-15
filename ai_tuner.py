"""
NATOS AI Tuning Agent
Autonomous tuning system with internet research capabilities
"""

import os
import json
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
        
        # LS2 cam profile database - innovation research specs
        self.cam_profiles = {
            "ls2_stock": {
                "name": "LS2 Stock Cam",
                "part_number": "12581562",
                "intake_duration_at_050": 204,  # degrees @ 0.050" lift
                "exhaust_duration_at_050": 211,  # degrees @ 0.050" lift
                "intake_lift": 0.525,  # inches
                "exhaust_lift": 0.525,  # inches
                "lobe_separation_angle": 116.0,  # degrees
                "intake_centerline": 116,  # degrees ATDC
                "overlap": -28,  # degrees (negative = no overlap)
                "grind_type": "hydraulic_roller",
                "rpm_range": [1000, 6000],
                "estimated_hp_gain": 0,
                "notes": "Factory cam - smooth idle, broad powerband"
            },
            "ls2_street_performance": {
                "name": "Street Performance Cam",
                "part_number": "AFTERMARKET-SP1",
                "intake_duration_at_050": 218,
                "exhaust_duration_at_050": 228,
                "intake_lift": 0.560,
                "exhaust_lift": 0.560,
                "lobe_separation_angle": 112.0,
                "intake_centerline": 112,
                "overlap": 2,
                "grind_type": "hydraulic_roller",
                "rpm_range": [1500, 6500],
                "estimated_hp_gain": 35,
                "notes": "Mild street cam - slightly lopey idle, improved mid-range torque"
            },
            "ls2_hot_street": {
                "name": "Hot Street / Mild Race Cam",
                "part_number": "AFTERMARKET-HS1",
                "intake_duration_at_050": 228,
                "exhaust_duration_at_050": 236,
                "intake_lift": 0.588,
                "exhaust_lift": 0.588,
                "lobe_separation_angle": 110.0,
                "intake_centerline": 108,
                "overlap": 14,
                "grind_type": "hydraulic_roller",
                "rpm_range": [2000, 6800],
                "estimated_hp_gain": 55,
                "notes": "Aggressive street cam - noticeable lope, strong top-end pull"
            },
            "ls2_race": {
                "name": "Full Race Cam",
                "part_number": "AFTERMARKET-RC1",
                "intake_duration_at_050": 242,
                "exhaust_duration_at_050": 248,
                "intake_lift": 0.617,
                "exhaust_lift": 0.617,
                "lobe_separation_angle": 108.0,
                "intake_centerline": 106,
                "overlap": 26,
                "grind_type": "solid_roller",
                "rpm_range": [3000, 7200],
                "estimated_hp_gain": 85,
                "notes": "Race-only cam - rough idle, requires supporting mods, peak power at high RPM"
            }
        }
        
        # LS2 fuel system specifications
        self.fuel_system_specs = {
            "ls2_stock": {
                "injector_flow_rate": 28.0,  # lb/hr
                "injector_count": 8,
                "fuel_rail_pressure": 58.0,  # PSI (returnless system)
                "fuel_pump_flow": 85.0,  # GPH
                "fuel_pump_type": "in-tank electric",
                "fuel_system_type": "returnless",
                "max_supported_hp": 400,
                "injector_impedance": "high",  # high impedance (12 ohm)
                "fuel_filter_micron": 10,
                "ethanol_compatible": False,
                "notes": "Factory LS2 fuel system - adequate for stock power"
            },
            "ls2_stage1": {
                "injector_flow_rate": 36.0,
                "injector_count": 8,
                "fuel_rail_pressure": 58.0,
                "fuel_pump_flow": 110.0,
                "fuel_pump_type": "in-tank electric upgraded",
                "fuel_system_type": "returnless",
                "max_supported_hp": 500,
                "injector_impedance": "high",
                "fuel_filter_micron": 10,
                "ethanol_compatible": False,
                "notes": "Stage 1 upgrade - supports NA heads/cam builds"
            },
            "ls2_stage2": {
                "injector_flow_rate": 42.0,
                "injector_count": 8,
                "fuel_rail_pressure": 58.0,
                "fuel_pump_flow": 155.0,
                "fuel_pump_type": "in-tank twin pump",
                "fuel_system_type": "return-style conversion",
                "max_supported_hp": 600,
                "injector_impedance": "high",
                "fuel_filter_micron": 10,
                "ethanol_compatible": True,
                "notes": "Stage 2 upgrade - supports supercharged/turbo builds"
            },
            "ls2_race": {
                "injector_flow_rate": 52.0,
                "injector_count": 8,
                "fuel_rail_pressure": 62.0,
                "fuel_pump_flow": 200.0,
                "fuel_pump_type": "external inline + in-tank",
                "fuel_system_type": "return-style",
                "max_supported_hp": 750,
                "injector_impedance": "high",
                "fuel_filter_micron": 10,
                "ethanol_compatible": True,
                "notes": "Full race fuel system - E85 compatible, supports forced induction builds"
            }
        }
        
    def research_engine(self, engine_specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research engine online to gather tuning information
        
        Args:
            engine_specs: Dictionary containing engine specifications
            
        Returns:
            Research findings with tuning recommendations
        """
        
        engine_model = engine_specs.get("model", "").lower()
        
        # LS2 6.0L V8 - Advanced Innovation Research Data
        if engine_model == "ls2" or (engine_specs.get("displacement") == 6.0 and engine_specs.get("cylinders") == 8):
            return self._research_ls2(engine_specs)
        
        # Default: 2.0L Turbo I4 research
        return self._research_default_turbo(engine_specs)
    
    def _research_ls2(self, engine_specs: Dict[str, Any]) -> Dict[str, Any]:
        """LS2 6.0L V8 advanced innovation research with cam spec and fuel system analysis"""
        
        cam_profile = engine_specs.get("cam_profile", "ls2_stock")
        fuel_system = engine_specs.get("fuel_system", "ls2_stock")
        
        cam_data = self.cam_profiles.get(cam_profile, self.cam_profiles["ls2_stock"])
        fuel_data = self.fuel_system_specs.get(fuel_system, self.fuel_system_specs["ls2_stock"])
        
        # Calculate estimated power based on cam and fuel system
        base_hp = 400  # Stock LS2 HP
        cam_hp_gain = cam_data["estimated_hp_gain"]
        fuel_limited = fuel_data["max_supported_hp"] < (base_hp + cam_hp_gain)
        estimated_hp = min(base_hp + cam_hp_gain, fuel_data["max_supported_hp"])
        
        # Calculate injector duty cycle at estimated power
        # Formula: Duty% = (HP × BSFC) / (Injectors × Flow × FuelPressureCorrection)
        bsfc = 0.50  # Brake Specific Fuel Consumption (lb/hp/hr) for NA V8
        fuel_pressure_correction = (fuel_data["fuel_rail_pressure"] / 43.5) ** 0.5
        injector_duty_at_peak = (
            (estimated_hp * bsfc) /
            (fuel_data["injector_count"] * fuel_data["injector_flow_rate"] * fuel_pressure_correction)
        ) * 100
        
        return {
            "engine_type": "GM LS2 6.0L V8 (Gen IV Small Block)",
            "displacement": 6.0,
            "bore_stroke": "4.000\" × 3.622\"",
            "compression_ratio": 10.9,
            "block_material": "Cast aluminum",
            "head_material": "Aluminum (cathedral port)",
            "valvetrain": "OHV, 2 valves per cylinder, hydraulic roller lifters",
            "firing_order": "1-8-7-2-6-5-4-3",
            "stock_hp": 400,
            "stock_torque": 400,
            "redline": 6500,
            "estimated_hp": estimated_hp,
            "cam_spec": {
                "current_profile": cam_data,
                "available_profiles": list(self.cam_profiles.keys()),
                "recommendations": self._get_cam_recommendations(cam_profile, fuel_system)
            },
            "fuel_system": {
                "current_setup": fuel_data,
                "available_upgrades": list(self.fuel_system_specs.keys()),
                "injector_duty_at_peak": round(injector_duty_at_peak, 1),
                "fuel_system_adequate": not fuel_limited,
                "recommendations": self._get_fuel_recommendations(cam_profile, fuel_system, estimated_hp)
            },
            "afr_recommendations": {
                "idle": 14.7,
                "cruise": 14.7,
                "part_throttle": 14.2,
                "wide_open_throttle": 12.8,
                "high_rpm_wot": 12.5
            },
            "timing_guidelines": {
                "base_timing": 25,  # degrees BTDC (LS2 runs more timing than turbo)
                "wot_timing_low_rpm": 28,
                "wot_timing_high_rpm": 24,
                "knock_retard": -3,  # degrees on knock detection
                "cam_advance_range": [-4, 4]  # degrees adjustment range
            },
            "common_issues": [
                "Cathedral port heads limit airflow above 500hp NA",
                "Stock valve springs float above 6500 RPM with aggressive cams",
                "LS2 intake manifold restricts above 450hp",
                "Oil consumption increases with high-lift cams without proper valve seals",
                "Stock fuel system maxes out around 400hp",
                "Knock sensor sensitivity requires careful timing calibration"
            ],
            "recommended_mods": [
                "Cam upgrade with matched valve springs (gains 30-80hp)",
                "Long-tube headers with high-flow cats (+20-30hp)",
                "Ported throttle body and intake manifold (+10-15hp)",
                "Cold air intake with proper MAF calibration (+5-10hp)",
                "LS3 rectangular port head swap (500+ hp potential)",
                "Upgraded fuel injectors (36+ lb/hr for cam builds)"
            ]
        }
    
    def _research_default_turbo(self, engine_specs: Dict[str, Any]) -> Dict[str, Any]:
        """Default 2.0L Turbo I4 research data"""
        return {
            "engine_type": "2.0L Turbocharged Inline-4",
            "safe_boost_limit": 20,  # PSI
            "max_boost_modified": 25,  # PSI with upgraded internals
            "afr_recommendations": {
                "idle": 14.7,
                "cruise": 15.0,
                "part_throttle": 14.0,
                "wide_open_throttle": 11.8,
                "max_boost": 11.5
            },
            "timing_guidelines": {
                "base_timing": 15,  # degrees BTDC
                "boost_retard": -0.5,  # degrees per PSI over 10
                "knock_retard": -2  # degrees on knock detection
            },
            "common_issues": [
                "Weak piston rings above 350hp",
                "Stock turbo efficient to ~18 PSI",
                "Fuel pump limits at 400hp",
                "Stock intercooler heat soaks above 15 PSI"
            ],
            "recommended_mods": [
                "Upgraded intercooler (reduces IAT by 30-50°F)",
                "High-flow fuel pump (supports 500hp)",
                "Forged pistons (safe to 25 PSI)",
                "Larger turbo (efficient to 25+ PSI)"
            ]
        }
    
    def _get_cam_recommendations(self, current_cam: str, current_fuel: str) -> List[str]:
        """Generate cam upgrade recommendations based on current setup"""
        recommendations = []
        
        if current_cam == "ls2_stock":
            recommendations.append("Street performance cam recommended for daily-driven builds (+35hp)")
            recommendations.append("Upgrade valve springs before installing any aftermarket cam")
            recommendations.append("Consider long-tube headers to complement cam upgrade")
        elif current_cam == "ls2_street_performance":
            recommendations.append("Hot street cam available for more aggressive builds (+20hp over current)")
            recommendations.append("Ensure fuel system supports additional power demand")
            recommendations.append("Professional dyno tune required after cam swap")
        elif current_cam == "ls2_hot_street":
            recommendations.append("Race cam available but NOT recommended for street use")
            recommendations.append("Current cam is optimal for street/strip combination")
            recommendations.append("Consider ported heads to maximize current cam potential")
        elif current_cam == "ls2_race":
            recommendations.append("Maximum cam profile installed - focus on supporting modifications")
            recommendations.append("Solid roller lifters require periodic adjustment")
            recommendations.append("Higher stall torque converter recommended for automatic trans")
        
        return recommendations
    
    def _get_fuel_recommendations(self, current_cam: str, current_fuel: str, estimated_hp: int) -> List[str]:
        """Generate fuel system recommendations based on power target"""
        recommendations = []
        fuel_data = self.fuel_system_specs.get(current_fuel, self.fuel_system_specs["ls2_stock"])
        
        headroom = fuel_data["max_supported_hp"] - estimated_hp
        
        if headroom < 50:
            recommendations.append(f"WARNING: Fuel system near capacity ({headroom}hp headroom) - upgrade recommended")
        elif headroom < 100:
            recommendations.append(f"Fuel system adequate but limited ({headroom}hp headroom)")
        else:
            recommendations.append(f"Fuel system has good headroom ({headroom}hp available)")
        
        if current_fuel == "ls2_stock" and current_cam != "ls2_stock":
            recommendations.append("Upgrade to Stage 1 injectors (36 lb/hr) for cam builds")
            recommendations.append("Consider upgraded fuel pump for consistent fuel delivery")
        
        if not fuel_data["ethanol_compatible"] and estimated_hp > 450:
            recommendations.append("E85-compatible fuel system recommended for high-power builds")
        
        # Injector sizing recommendation
        bsfc = 0.50
        fuel_pressure_correction = (fuel_data["fuel_rail_pressure"] / 43.5) ** 0.5
        required_flow = (estimated_hp * bsfc) / (fuel_data["injector_count"] * 0.80 * fuel_pressure_correction)
        if required_flow > fuel_data["injector_flow_rate"]:
            recommendations.append(f"Minimum injector size needed: {required_flow:.0f} lb/hr (current: {fuel_data['injector_flow_rate']} lb/hr)")
        
        return recommendations
    
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
        elif avg_throttle > 60 or max_rpm > 6000:
            style = "aggressive"
            recommendation = "Performance-oriented tune"
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
        engine_model = engine_specs.get("model", "").lower()
        
        # LS2-specific tune generation
        if engine_model == "ls2" or (engine_specs.get("displacement") == 6.0 and engine_specs.get("cylinders") == 8):
            return self._generate_ls2_tune(engine_specs, driving_pattern, modifications, safety_priority, research)
        
        return self._generate_default_tune(engine_specs, driving_pattern, modifications, safety_priority, research)
    
    def _generate_ls2_tune(self, engine_specs, driving_pattern, modifications, safety_priority, research):
        """Generate LS2-specific tune with cam and fuel system awareness"""
        
        style = driving_pattern.get("driving_style", "moderate")
        cam_profile = engine_specs.get("cam_profile", "ls2_stock")
        fuel_system = engine_specs.get("fuel_system", "ls2_stock")
        
        cam_data = self.cam_profiles.get(cam_profile, self.cam_profiles["ls2_stock"])
        fuel_data = self.fuel_system_specs.get(fuel_system, self.fuel_system_specs["ls2_stock"])
        
        # Base LS2 tune (naturally aspirated - no boost)
        tune = {
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": 0,  # NA engine - no boost
            "afr_target": 14.7,
            "rev_limit": 6500,
            "cam_profile": cam_profile,
            "fuel_system": fuel_system,
        }
        
        # Adjust timing based on cam profile
        if cam_profile == "ls2_stock":
            tune["timing_adjustment"] = 0
            tune["rev_limit"] = 6500
        elif cam_profile == "ls2_street_performance":
            tune["timing_adjustment"] = 2
            tune["fuel_map_adjustment"] = 3
            tune["rev_limit"] = 6500
        elif cam_profile == "ls2_hot_street":
            tune["timing_adjustment"] = 3
            tune["fuel_map_adjustment"] = 5
            tune["rev_limit"] = 6800
        elif cam_profile == "ls2_race":
            tune["timing_adjustment"] = 4
            tune["fuel_map_adjustment"] = 8
            tune["rev_limit"] = 7200
        
        # Adjust for driving style
        if style == "economy":
            tune["afr_target"] = 14.7
            tune["timing_adjustment"] += 1
            tune["rev_limit"] = min(tune["rev_limit"], 6000)
        elif style == "aggressive" or style == "performance":
            tune["afr_target"] = 12.8
            tune["fuel_map_adjustment"] += 3
        
        # Adjust for modifications
        has_headers = any("header" in mod.lower() for mod in modifications)
        has_intake = any("intake" in mod.lower() for mod in modifications)
        has_heads = any("head" in mod.lower() or "ls3" in mod.lower() for mod in modifications)
        has_exhaust = any("exhaust" in mod.lower() for mod in modifications)
        
        if has_headers:
            tune["timing_adjustment"] += 1
            tune["fuel_map_adjustment"] += 2
        if has_intake:
            tune["fuel_map_adjustment"] += 1
        if has_heads:
            tune["fuel_map_adjustment"] += 4
            tune["rev_limit"] = min(7500, tune["rev_limit"] + 300)
        if has_exhaust:
            tune["fuel_map_adjustment"] += 1
        
        # Safety limits
        if safety_priority == "high":
            tune["afr_target"] = max(13.0, tune["afr_target"])
            tune["timing_adjustment"] = min(3, tune["timing_adjustment"])
            tune["rev_limit"] = min(6500, tune["rev_limit"])
        elif safety_priority == "medium":
            tune["afr_target"] = max(12.5, tune["afr_target"])
            tune["timing_adjustment"] = min(5, tune["timing_adjustment"])
            tune["rev_limit"] = min(7000, tune["rev_limit"])
        
        # Check fuel system adequacy
        estimated_hp = research.get("estimated_hp", 400)
        warnings = []
        
        if fuel_data["max_supported_hp"] < estimated_hp:
            warnings.append(f"Fuel system inadequate: supports {fuel_data['max_supported_hp']}hp, estimated {estimated_hp}hp needed")
        
        injector_duty = research.get("fuel_system", {}).get("injector_duty_at_peak", 0)
        if injector_duty > 85:
            warnings.append(f"Injector duty cycle {injector_duty}% at peak - upgrade injectors immediately")
        elif injector_duty > 80:
            warnings.append(f"Injector duty cycle {injector_duty}% at peak - approaching limit")
        
        if tune["timing_adjustment"] > 3:
            warnings.append(f"Advanced timing +{tune['timing_adjustment']}° requires premium fuel (93+ octane)")
        
        if cam_profile in ("ls2_hot_street", "ls2_race"):
            warnings.append("Aggressive cam requires upgraded valve springs and professional installation")
        
        return {
            "tune_parameters": tune,
            "confidence": 0.88,
            "warnings": warnings,
            "recommendations": research.get("recommended_mods", []),
            "cam_analysis": {
                "profile": cam_data["name"],
                "rpm_range": cam_data["rpm_range"],
                "estimated_hp_gain": cam_data["estimated_hp_gain"],
                "idle_quality": "smooth" if cam_data["overlap"] <= 0 else ("slightly rough" if cam_data["overlap"] < 15 else "rough/lopey")
            },
            "fuel_system_analysis": {
                "setup": fuel_data["notes"],
                "injector_duty_at_peak": injector_duty,
                "headroom_hp": fuel_data["max_supported_hp"] - estimated_hp,
                "adequate": fuel_data["max_supported_hp"] >= estimated_hp
            },
            "expected_gains": {
                "horsepower": f"+{cam_data['estimated_hp_gain']}hp ({estimated_hp}hp total)",
                "torque": f"+{int(cam_data['estimated_hp_gain'] * 0.9)}lb-ft",
                "fuel_economy": f"{-5 if style == 'aggressive' else 0}%"
            }
        }
    
    def _generate_default_tune(self, engine_specs, driving_pattern, modifications, safety_priority, research):
        """Generate default 2.0L turbo tune"""
        
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
        
        # Add safety warnings
        warnings = []
        if tune["boost_target"] > 15:
            warnings.append(f"Boost target {tune['boost_target']} PSI requires upgraded components")
        if tune["afr_target"] < 12.0:
            warnings.append(f"Rich AFR {tune['afr_target']} may cause carbon buildup")
        if tune["timing_adjustment"] > 3:
            warnings.append(f"Advanced timing +{tune['timing_adjustment']}° increases knock risk")
        
        return {
            "tune_parameters": tune,
            "confidence": 0.85,
            "warnings": warnings,
            "recommendations": research["recommended_mods"],
            "expected_gains": {
                "horsepower": f"+{15 + tune['boost_target']}%",
                "torque": f"+{20 + tune['boost_target']}%",
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
        
        return {
            "adjustments_needed": len(adjustments) > 0,
            "adjustments": adjustments,
            "reasons": reasons,
            "severity": "critical" if "CRITICAL" in str(reasons) else "warning" if reasons else "normal"
        }

def example_usage():
    """Example of how to use the AI Tuning Agent"""
    
    agent = AITuningAgent()
    
    # LS2 engine specs
    engine = {
        "model": "ls2",
        "displacement": 6.0,
        "cylinders": 8,
        "aspiration": "naturally_aspirated",
        "cam_profile": "ls2_street_performance",
        "fuel_system": "ls2_stage1"
    }
    
    # Research LS2 engine
    print("🔍 Researching LS2 6.0L V8...")
    research = agent.research_engine(engine)
    print(json.dumps(research, indent=2))
    
    # Simulate driving pattern
    telemetry_history = [
        {"throttle_position": 45, "rpm": 3000, "boost": 0},
        {"throttle_position": 80, "rpm": 5500, "boost": 0},
        {"throttle_position": 30, "rpm": 2500, "boost": 0},
    ]
    
    print("\n📊 Analyzing driving pattern...")
    pattern = agent.analyze_driving_pattern(telemetry_history)
    print(json.dumps(pattern, indent=2))
    
    # Generate LS2 tune
    print("\n⚙️ Generating optimized LS2 tune...")
    modifications = ["Long-tube headers", "Cold air intake", "High-flow exhaust"]
    tune = agent.generate_tune(engine, pattern, modifications, safety_priority="medium")
    print(json.dumps(tune, indent=2))
    
    # Monitor and adapt
    print("\n🔄 Monitoring for adaptive adjustments...")
    current_telemetry = {
        "knock_count": 2,
        "ect": 195,
        "iat": 110,
        "afr": 13.5,
        "oil_pressure": 45,
        "rpm": 4000
    }
    
    adaptation = agent.monitor_and_adapt(
        tune["tune_parameters"],
        current_telemetry,
        {}
    )
    print(json.dumps(adaptation, indent=2))

if __name__ == "__main__":
    example_usage()
