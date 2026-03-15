"""
NATOS AI Tuning Agent
Autonomous tuning system with internet research capabilities

Now backed by a comprehensive performance database, tuning algorithm
research, and statistical overlay analysis to find optimal starting
points across engine categories.
"""

import os
import json
from typing import Dict, List, Any

from performance_database import PerformanceDatabase
from tuning_algorithms import (
    MapInterpolationTuner,
    PIDFuelTrimTuner,
    IterativeOptimizer,
    GeneticAlgorithmTuner,
    VolumetricEfficiencyModel,
    TuningAlgorithmComparator,
)
from overlay_analyzer import (
    OverlayAnalyzer,
    StartingPointFinder,
    PerformanceScorer,
    AnalysisReport,
)


class AITuningAgent:
    """AI agent that researches and creates optimal ECU tunes.

    Integrates the performance database (15 engine profiles, 60 variants),
    five tuning algorithms, and the overlay analyser to derive data-driven
    starting points.
    """
    
    def __init__(self):
        # AI client would be initialized here in production
        # self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.knowledge_base = {
            "engines": {},
            "modifications": {},
            "tuning_strategies": {}
        }
        
        # Performance database and analysis tools
        self.perf_db = PerformanceDatabase()
        self.overlay = OverlayAnalyzer(self.perf_db)
        self.starting_point_finder = StartingPointFinder(self.perf_db)
        self.scorer = PerformanceScorer(self.perf_db)
        self.report_gen = AnalysisReport(self.perf_db)
        
        # Tuning algorithm suite
        self.map_tuner = MapInterpolationTuner()
        self.pid_tuner = PIDFuelTrimTuner()
        self.iterative_opt = IterativeOptimizer()
        self.genetic_opt = GeneticAlgorithmTuner()
        self.ve_model = VolumetricEfficiencyModel()
        self.algo_comparator = TuningAlgorithmComparator()
        
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

    # ------------------------------------------------------------------
    # Database-backed research & analysis methods
    # ------------------------------------------------------------------

    def research_from_database(self, engine_id: str) -> Dict[str, Any]:
        """Research an engine using the performance database.
        
        Args:
            engine_id: Engine identifier from the database.
            
        Returns:
            Comprehensive research data including dyno curves,
            all tuned variants, and scoring.
        """
        engine = self.perf_db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found in database"}
        
        variants = self.perf_db.get_all_variants(engine_id)
        stock_dyno = self.perf_db.get_dyno_data(engine_id, "stock")
        stock_score = self.scorer.score_tune(engine_id, "stock")
        
        variant_scores = {}
        for v in variants:
            vname = v["variant"]
            variant_scores[vname] = self.scorer.score_tune(engine_id, vname)
        
        return {
            "engine": engine,
            "stock_dyno": stock_dyno,
            "variants": variants,
            "stock_score": stock_score,
            "variant_scores": variant_scores,
        }

    def get_optimal_starting_point(self, category: str = "all") -> Dict[str, Any]:
        """Find the optimal starting point for a given engine category.
        
        This method overlays data from all engines and tuned variants
        in the category, runs iterative and genetic optimisation, and
        returns the consensus tune parameters with confidence scores.
        
        Args:
            category: One of "4cyl_turbo", "6cyl_turbo", "v8_na",
                      "v8_forced", "v6_na", "v6_turbo", "diesel",
                      "rotary", "high_performance", or "all".
                      
        Returns:
            Dict with tune_parameters, confidence, and supporting data.
        """
        return self.starting_point_finder.find_optimal_starting_point(category)

    def get_all_starting_points(self) -> Dict[str, Any]:
        """Find optimal starting points for every engine category.
        
        Returns:
            Dict mapping category name to its starting point analysis.
        """
        return self.starting_point_finder.find_all_starting_points()

    def compare_algorithms_for_engine(self, engine_id: str,
                                       target: str = "power") -> Dict[str, Any]:
        """Compare all tuning algorithms on a single engine.
        
        Args:
            engine_id: Engine to optimise.
            target: Optimisation target ("power", "economy", "balanced").
            
        Returns:
            Comparison results for each algorithm.
        """
        return self.algo_comparator.compare_all(engine_id, target)

    def generate_engine_report(self, engine_id: str) -> str:
        """Generate a full analysis report for an engine.
        
        Args:
            engine_id: Engine identifier.
            
        Returns:
            Formatted report string.
        """
        return self.report_gen.generate_engine_report(engine_id)

    def generate_category_report(self, category: str) -> str:
        """Generate analysis report for an engine category.
        
        Args:
            category: Engine category name.
            
        Returns:
            Formatted report string.
        """
        return self.report_gen.generate_category_report(category)

    def list_database_engines(self) -> List[Dict[str, Any]]:
        """List all engines available in the performance database.
        
        Returns:
            List of engine summary dicts.
        """
        return self.perf_db.list_engines()

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

    # ---- New database-backed features ----

    print("\n" + "=" * 60)
    print("📦 PERFORMANCE DATABASE")
    print("=" * 60)

    engines = agent.list_database_engines()
    print(f"\nEngines in database: {len(engines)}")
    for e in engines:
        print(f"  • {e['engine_id']}: {e['name']} "
              f"({e['stock_power_hp']:.0f} hp)")

    print("\n" + "=" * 60)
    print("🔬 DATABASE-BACKED ENGINE RESEARCH (2.0L Turbo I4)")
    print("=" * 60)
    db_research = agent.research_from_database("20t_i4")
    if "error" not in db_research:
        print(f"\nStock score: {db_research['stock_score']['composite']}/100")
        for vname, vscore in db_research["variant_scores"].items():
            print(f"  {vname}: {vscore['composite']}/100 "
                  f"({vscore['peak_power_hp']:.0f} hp)")

    print("\n" + "=" * 60)
    print("🎯 OPTIMAL STARTING POINT — 4-Cylinder Turbo Category")
    print("=" * 60)
    sp = agent.get_optimal_starting_point("4cyl_turbo")
    print(f"\nCategory: {sp['category_label']}")
    print(f"Engines analysed: {sp['engines_analysed']}")
    print(f"Confidence: {sp['confidence']:.1f}%")
    print("\nRecommended tune parameters:")
    for param, info in sp["tune_parameters"].items():
        print(f"  {param}: {info['recommended']:.2f} "
              f"(±{info.get('stdev', 0):.2f})")

    print("\n" + "=" * 60)
    print("⚡ ALGORITHM COMPARISON (2.0L Turbo I4)")
    print("=" * 60)
    comparison = agent.compare_algorithms_for_engine("20t_i4", "power")
    for algo_name, result in comparison.items():
        if isinstance(result, dict):
            print(f"\n  {algo_name}:")
            for k, v in result.items():
                if not isinstance(v, (dict, list)):
                    print(f"    {k}: {v}")

if __name__ == "__main__":
    example_usage()
