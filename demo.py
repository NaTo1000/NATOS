#!/usr/bin/env python3
"""
NATOS Interactive Demo Script
Demonstrates AI tuning capabilities without running the web server
"""

import sys
import time
import random
from ai_tuner import AITuningAgent

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_section(text):
    print(f"\n>>> {text}\n")

def simulate_typing(text, delay=0.02):
    """Print text with typing effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def demo_engine_research():
    """Demonstrate engine research capabilities"""
    print_header("🔍 DEMO: LS2 6.0L V8 Engine Research")
    
    print("Engine Specifications:")
    print("  • Engine: GM LS2 (Gen IV Small Block)")
    print("  • Displacement: 6.0L (364 ci)")
    print("  • Configuration: V8, OHV")
    print("  • Aspiration: Naturally Aspirated")
    print("  • Compression Ratio: 10.9:1")
    print("  • Stock Power: 400 HP / 400 lb-ft")
    
    print_section("Researching LS2 engine specifications, cam specs, and fuel system...")
    time.sleep(1)
    
    agent = AITuningAgent()
    research = agent.research_engine({
        "model": "ls2",
        "displacement": 6.0,
        "cylinders": 8,
        "aspiration": "naturally_aspirated",
        "cam_profile": "ls2_stock",
        "fuel_system": "ls2_stock"
    })
    
    print("✅ Research Complete!\n")
    print(f"Engine Type: {research['engine_type']}")
    print(f"Bore × Stroke: {research['bore_stroke']}")
    print(f"Compression Ratio: {research['compression_ratio']}:1")
    print(f"Stock HP: {research['stock_hp']} HP")
    print(f"Estimated HP (current config): {research['estimated_hp']} HP")
    
    print("\n🔩 Cam Specifications (Stock):")
    cam = research['cam_spec']['current_profile']
    print(f"  • Name: {cam['name']}")
    print(f"  • Intake Duration @ 0.050\": {cam['intake_duration_at_050']}°")
    print(f"  • Exhaust Duration @ 0.050\": {cam['exhaust_duration_at_050']}°")
    print(f"  • Intake Lift: {cam['intake_lift']}\"")
    print(f"  • Exhaust Lift: {cam['exhaust_lift']}\"")
    print(f"  • Lobe Separation Angle: {cam['lobe_separation_angle']}°")
    print(f"  • Grind Type: {cam['grind_type']}")
    print(f"  • Optimal RPM Range: {cam['rpm_range'][0]} - {cam['rpm_range'][1]}")
    
    print("\n⛽ Fuel System (Stock):")
    fuel = research['fuel_system']['current_setup']
    print(f"  • Injector Flow Rate: {fuel['injector_flow_rate']} lb/hr")
    print(f"  • Fuel Rail Pressure: {fuel['fuel_rail_pressure']} PSI")
    print(f"  • Fuel Pump Flow: {fuel['fuel_pump_flow']} GPH")
    print(f"  • System Type: {fuel['fuel_system_type']}")
    print(f"  • Max Supported HP: {fuel['max_supported_hp']} HP")
    print(f"  • Injector Duty @ Peak: {research['fuel_system']['injector_duty_at_peak']}%")
    
    print("\n📊 AFR Recommendations:")
    for scenario, afr in research['afr_recommendations'].items():
        print(f"  • {scenario.replace('_', ' ').title()}: {afr}:1")
    
    print("\n🔧 Timing Guidelines:")
    for param, value in research['timing_guidelines'].items():
        print(f"  • {param.replace('_', ' ').title()}: {value}°")
    
    print("\n⚠️ Common Issues:")
    for issue in research['common_issues']:
        print(f"  • {issue}")
    
    print("\n🔧 Recommended Modifications:")
    for mod in research['recommended_mods']:
        print(f"  • {mod}")
    
    # Show cam upgrade options
    print("\n📋 Available Cam Profiles:")
    for key in research['cam_spec']['available_profiles']:
        cam_info = agent.cam_profiles[key]
        print(f"  • {cam_info['name']}: {cam_info['intake_duration_at_050']}°/{cam_info['exhaust_duration_at_050']}° dur, "
              f"{cam_info['intake_lift']}\"/{cam_info['exhaust_lift']}\" lift, "
              f"+{cam_info['estimated_hp_gain']}hp")
    
    input("\nPress Enter to continue...")

def demo_driving_analysis():
    """Demonstrate driving pattern analysis"""
    print_header("📊 DEMO: Driving Pattern Analysis")
    
    print("Simulating 30 seconds of driving telemetry...")
    
    # Simulate realistic driving
    telemetry_history = []
    for i in range(30):
        if i < 10:  # Moderate acceleration
            throttle = random.uniform(40, 60)
            rpm = 2000 + (i * 300)
        elif i < 20:  # Aggressive driving
            throttle = random.uniform(70, 95)
            rpm = 4000 + random.uniform(-500, 1000)
        else:  # Cruise
            throttle = random.uniform(20, 35)
            rpm = 2500 + random.uniform(-200, 200)
        
        boost = (throttle / 100) * 14 if rpm > 2500 else 0
        
        telemetry_history.append({
            "throttle_position": throttle,
            "rpm": rpm,
            "boost": boost
        })
        
        if i % 5 == 0:
            print(f"  {i}s: Throttle={throttle:.0f}%, RPM={rpm:.0f}, Boost={boost:.1f} PSI")
    
    print_section("Analyzing driving pattern...")
    time.sleep(1)
    
    agent = AITuningAgent()
    analysis = agent.analyze_driving_pattern(telemetry_history)
    
    print("✅ Analysis Complete!\n")
    print(f"Driving Style: {analysis['driving_style'].upper()}")
    print(f"Recommendation: {analysis['recommendation']}")
    
    print("\n📈 Statistics:")
    stats = analysis['statistics']
    print(f"  • Average Throttle: {stats['avg_throttle']:.1f}%")
    print(f"  • Max Throttle: {stats['max_throttle']:.1f}%")
    print(f"  • Average RPM: {stats['avg_rpm']:.0f}")
    print(f"  • Max RPM: {stats['max_rpm']:.0f}")
    print(f"  • Average Boost: {stats['avg_boost']:.1f} PSI")
    print(f"  • Max Boost: {stats['max_boost']:.1f} PSI")
    
    input("\nPress Enter to continue...")

def demo_tune_generation():
    """Demonstrate AI tune generation for LS2"""
    print_header("⚙️ DEMO: LS2 AI Tune Generation")
    
    print("Vehicle Configuration:")
    print("  • Engine: GM LS2 6.0L V8")
    print("  • Cam: Street Performance (218°/228° duration)")
    print("  • Fuel System: Stage 1 (36 lb/hr injectors)")
    print("  • Modifications:")
    print("    - Long-tube headers")
    print("    - Cold air intake")
    print("    - High-flow exhaust")
    print("  • Safety Priority: MEDIUM")
    
    print_section("Generating optimized LS2 tune...")
    time.sleep(1.5)
    
    agent = AITuningAgent()
    
    # Simulate performance driving pattern
    pattern = {
        "driving_style": "performance",
        "recommendation": "Performance-oriented tune",
        "statistics": {
            "avg_throttle": 65.0,
            "max_throttle": 95.0,
            "avg_rpm": 4500,
            "max_rpm": 6200,
            "avg_boost": 0,
            "max_boost": 0
        }
    }
    
    tune = agent.generate_tune(
        {
            "model": "ls2",
            "displacement": 6.0,
            "cylinders": 8,
            "aspiration": "naturally_aspirated",
            "cam_profile": "ls2_street_performance",
            "fuel_system": "ls2_stage1"
        },
        pattern,
        ["Long-tube headers", "Cold air intake", "High-flow exhaust"],
        safety_priority="medium"
    )
    
    print("✅ Tune Generated!\n")
    
    params = tune['tune_parameters']
    print("📋 Tune Parameters:")
    print(f"  • Fuel Map Adjustment: {params['fuel_map_adjustment']:+d}%")
    print(f"  • Timing Adjustment: {params['timing_adjustment']:+d}°")
    print(f"  • AFR Target: {params['afr_target']}")
    print(f"  • Rev Limit: {params['rev_limit']} RPM")
    print(f"  • Cam Profile: {params.get('cam_profile', 'N/A')}")
    print(f"  • Fuel System: {params.get('fuel_system', 'N/A')}")
    
    print(f"\n🎯 Confidence Level: {tune['confidence']*100:.0f}%")
    
    print("\n📈 Expected Performance Gains:")
    for metric, gain in tune['expected_gains'].items():
        print(f"  • {metric.replace('_', ' ').title()}: {gain}")
    
    print("\n🔩 Cam Analysis:")
    cam = tune.get('cam_analysis', {})
    print(f"  • Profile: {cam.get('profile', 'N/A')}")
    print(f"  • RPM Range: {cam.get('rpm_range', 'N/A')}")
    print(f"  • HP Gain: +{cam.get('estimated_hp_gain', 0)}hp")
    print(f"  • Idle Quality: {cam.get('idle_quality', 'N/A')}")
    
    print("\n⛽ Fuel System Analysis:")
    fuel = tune.get('fuel_system_analysis', {})
    print(f"  • Setup: {fuel.get('setup', 'N/A')}")
    print(f"  • Injector Duty @ Peak: {fuel.get('injector_duty_at_peak', 0)}%")
    print(f"  • HP Headroom: {fuel.get('headroom_hp', 0)}hp")
    print(f"  • Adequate: {'✅ Yes' if fuel.get('adequate', False) else '❌ No - upgrade needed'}")
    
    if tune['warnings']:
        print("\n⚠️ Warnings:")
        for warning in tune['warnings']:
            print(f"  • {warning}")
    
    print("\n💡 Additional Recommendations:")
    for rec in tune['recommendations'][:3]:
        print(f"  • {rec}")
    
    input("\nPress Enter to continue...")

def demo_adaptive_tuning():
    """Demonstrate real-time adaptive tuning"""
    print_header("🔄 DEMO: Real-Time Adaptive Tuning")
    
    agent = AITuningAgent()
    
    current_tune = {
        "fuel_map_adjustment": 10,
        "timing_adjustment": 3,
        "boost_target": 16,
        "afr_target": 12.5,
        "rev_limit": 7200
    }
    
    print("Current Tune:")
    print(f"  • Boost Target: {current_tune['boost_target']} PSI")
    print(f"  • Timing: {current_tune['timing_adjustment']:+d}°")
    print(f"  • AFR Target: {current_tune['afr_target']}")
    
    scenarios = [
        {
            "name": "Normal Operation",
            "telemetry": {
                "knock_count": 0,
                "ect": 195,
                "iat": 100,
                "afr": 12.3,
                "oil_pressure": 50
            }
        },
        {
            "name": "Knock Detection",
            "telemetry": {
                "knock_count": 5,
                "ect": 195,
                "iat": 110,
                "afr": 13.0,
                "oil_pressure": 50
            }
        },
        {
            "name": "High Temperature",
            "telemetry": {
                "knock_count": 1,
                "ect": 225,
                "iat": 150,
                "afr": 12.8,
                "oil_pressure": 45
            }
        },
        {
            "name": "Lean Condition Under Boost",
            "telemetry": {
                "knock_count": 0,
                "ect": 200,
                "iat": 120,
                "afr": 14.5,
                "boost": 14.0,
                "oil_pressure": 50
            }
        }
    ]
    
    for scenario in scenarios:
        print_section(f"Scenario: {scenario['name']}")
        
        telem = scenario['telemetry']
        print("Telemetry:")
        for key, value in telem.items():
            unit = {"knock_count": "", "ect": "°F", "iat": "°F", "afr": ":1", "oil_pressure": " PSI", "boost": " PSI"}.get(key, "")
            print(f"  • {key.replace('_', ' ').title()}: {value}{unit}")
        
        print("\nAnalyzing...")
        time.sleep(0.5)
        
        adaptation = agent.monitor_and_adapt(current_tune, telem, {})
        
        if adaptation['adjustments_needed']:
            print(f"\n⚠️ Adjustments Required ({adaptation['severity'].upper()})")
            print("\nChanges:")
            for param, value in adaptation['adjustments'].items():
                print(f"  • {param.replace('_', ' ').title()}: {value}")
            print("\nReasons:")
            for reason in adaptation['reasons']:
                print(f"  • {reason}")
        else:
            print("\n✅ No adjustments needed - system operating normally")
        
        print()
        time.sleep(1)
    
    input("\nPress Enter to continue...")

def demo_safety_systems():
    """Demonstrate safety monitoring"""
    print_header("🚨 DEMO: Safety Monitoring Systems")
    
    print("NATOS includes multiple safety systems:\n")
    
    systems = [
        {
            "name": "Knock Detection & Protection",
            "description": "Monitors for engine knock/detonation",
            "actions": [
                "Retards ignition timing by 2°",
                "Reduces boost pressure by 2 PSI",
                "Enriches fuel mixture",
                "Logs event for analysis"
            ]
        },
        {
            "name": "Temperature Protection",
            "description": "Monitors all critical temperatures",
            "actions": [
                "Enriches mixture to cool engine",
                "Reduces boost if IAT too high",
                "Critical alert at dangerous temps",
                "Suggests cooldown period"
            ]
        },
        {
            "name": "AFR Safety",
            "description": "Prevents dangerously lean conditions",
            "actions": [
                "Adds fuel if AFR > 13.5 under boost",
                "Critical alert if AFR > 15.0",
                "Automatic enrichment under load",
                "Monitors oxygen sensor health"
            ]
        },
        {
            "name": "Oil Pressure Monitor",
            "description": "Protects against oil starvation",
            "actions": [
                "Critical alert if pressure < 10 PSI",
                "Emergency RPM limit activation",
                "Recommends immediate shutdown",
                "Logs pressure history"
            ]
        },
        {
            "name": "Over-Boost Protection",
            "description": "Prevents exceeding safe boost limits",
            "actions": [
                "Limits boost to configured maximum",
                "Warns if approaching limits",
                "Considers ambient conditions",
                "Protects engine internals"
            ]
        }
    ]
    
    for i, system in enumerate(systems, 1):
        print(f"{i}. {system['name']}")
        print(f"   {system['description']}")
        print(f"   Actions:")
        for action in system['actions']:
            print(f"     • {action}")
        print()
    
    print("All safety systems operate in real-time at 10 Hz update rate.")
    print("Critical alerts trigger immediate protective actions.")
    
    input("\nPress Enter to continue...")

def main():
    """Main demo menu"""
    
    print_header("🏎️ NATOS - AI ECU Tuning System Demo")
    
    simulate_typing("Welcome to the NATOS Interactive Demo!", 0.03)
    print("\nThis demo showcases the AI tuning capabilities without")
    print("requiring the full web interface.\n")
    
    time.sleep(1)
    
    while True:
        print("\n" + "-" * 60)
        print("DEMO MENU")
        print("-" * 60)
        print("1. Engine Research Demo")
        print("2. Driving Pattern Analysis Demo")
        print("3. AI Tune Generation Demo")
        print("4. Real-Time Adaptive Tuning Demo")
        print("5. Safety Systems Overview")
        print("6. Run All Demos")
        print("0. Exit")
        print("-" * 60)
        
        choice = input("\nSelect demo (0-6): ").strip()
        
        if choice == '1':
            demo_engine_research()
        elif choice == '2':
            demo_driving_analysis()
        elif choice == '3':
            demo_tune_generation()
        elif choice == '4':
            demo_adaptive_tuning()
        elif choice == '5':
            demo_safety_systems()
        elif choice == '6':
            demo_engine_research()
            demo_driving_analysis()
            demo_tune_generation()
            demo_adaptive_tuning()
            demo_safety_systems()
            print_header("✅ All Demos Complete!")
            print("\nThank you for exploring NATOS capabilities!")
            break
        elif choice == '0':
            print("\n👋 Thank you for trying NATOS!")
            print("For the full experience, run: ./start.sh")
            break
        else:
            print("\n❌ Invalid choice. Please select 0-6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
        sys.exit(0)
