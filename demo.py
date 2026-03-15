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
    print_header("🔍 DEMO: VW Golf R EA113 Engine Research")
    
    print("Engine Specifications:")
    print("  • Vehicle: VW Golf R")
    print("  • Engine Code: EA113")
    print("  • Displacement: 2.0L (1984cc)")
    print("  • Cylinders: 4 (inline)")
    print("  • Aspiration: Turbocharged (K04-064)")
    print("  • Stock Power: 256 HP / 243 lb-ft")
    print("  • Stock Boost: ~14 PSI")
    
    print_section("Researching EA113 specifications and limitations...")
    time.sleep(1)
    
    agent = AITuningAgent()
    research = agent.research_engine({
        "vehicle": "VW Golf R",
        "engine_code": "EA113",
        "displacement": 2.0,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "turbo": "K04-064",
        "max_boost": 17.4
    })
    
    print("✅ Research Complete!\n")
    print(f"Engine Type: {research['engine_type']}")
    print(f"Safe Boost Limit: {research['safe_boost_limit']} PSI")
    print(f"Modified Engine Max: {research['max_boost_modified']} PSI")
    
    print("\n📊 AFR Recommendations:")
    for scenario, afr in research['afr_recommendations'].items():
        print(f"  • {scenario.replace('_', ' ').title()}: {afr}:1")
    
    print("\n⚠️ Common Issues:")
    for issue in research['common_issues']:
        print(f"  • {issue}")
    
    print("\n🔧 Recommended Modifications:")
    for mod in research['recommended_mods']:
        print(f"  • {mod}")
    
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
    """Demonstrate AI tune generation"""
    print_header("⚙️ DEMO: AI Tune Generation (VW Golf R EA113)")
    
    print("Vehicle Configuration:")
    print("  • Engine: VW Golf R EA113 2.0T K04")
    print("  • Modifications:")
    print("    - Front-mount intercooler")
    print("    - High-pressure fuel pump upgrade")
    print("    - Upgraded diverter valve")
    print("  • Safety Priority: HIGH")
    
    print_section("Generating optimized EA113 tune...")
    time.sleep(1.5)
    
    agent = AITuningAgent()
    
    # Simulate mixed driving pattern
    pattern = {
        "driving_style": "performance",
        "recommendation": "Performance-oriented tune",
        "statistics": {
            "avg_throttle": 65.0,
            "max_throttle": 95.0,
            "avg_rpm": 4500,
            "max_rpm": 6800,
            "avg_boost": 12.0,
            "max_boost": 16.0
        }
    }
    
    tune = agent.generate_tune(
        {"vehicle": "VW Golf R", "engine_code": "EA113", "displacement": 2.0,
         "cylinders": 4, "aspiration": "turbocharged", "turbo": "K04-064", "max_boost": 17.4},
        pattern,
        ["Front-mount intercooler", "High-pressure fuel pump", "Upgraded diverter valve"],
        safety_priority="high"
    )
    
    print("✅ Tune Generated!\n")
    
    params = tune['tune_parameters']
    print("📋 Tune Parameters:")
    print(f"  • Fuel Map Adjustment: {params['fuel_map_adjustment']:+d}%")
    print(f"  • Timing Adjustment: {params['timing_adjustment']:+d}°")
    print(f"  • Boost Target: {params['boost_target']} PSI")
    print(f"  • AFR Target: {params['afr_target']}")
    print(f"  • Rev Limit: {params['rev_limit']} RPM")
    
    print(f"\n🎯 Confidence Level: {tune['confidence']*100:.0f}%")
    
    print("\n📈 Expected Performance Gains:")
    for metric, gain in tune['expected_gains'].items():
        print(f"  • {metric.title()}: {gain}")
    
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
    
    print_header("🏎️ NATOS - VW Golf R EA113 Tuning System Demo")
    
    simulate_typing("Welcome to the NATOS Interactive Demo!", 0.03)
    print("\nThis demo showcases the AI tuning capabilities for the")
    print("VW Golf R EA113 2.0T — from ECO to Shooting Flames.\n")
    
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
