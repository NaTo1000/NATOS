#!/usr/bin/env python3
"""
NATOS Interactive Demo Script
Demonstrates AI tuning capabilities for LS-series engines
with methanol/water injection, nitrous fogging, and wheel speed monitoring
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
    """Demonstrate LS-series engine research capabilities"""
    print_header("🔍 DEMO: LS-Series Engine Research")
    
    engines = {
        "ls1": {"displacement": 5.7, "cylinders": 8, "aspiration": "supercharged", "max_boost": 8.0, "redline": 6000},
        "ls2": {"displacement": 6.0, "cylinders": 8, "aspiration": "supercharged", "max_boost": 10.0, "redline": 6500},
        "ls3": {"displacement": 6.2, "cylinders": 8, "aspiration": "supercharged", "max_boost": 12.0, "redline": 6600},
    }
    
    agent = AITuningAgent()
    
    for name, specs in engines.items():
        print(f"\n{'─' * 50}")
        print(f"  {name.upper()} - {specs['displacement']}L V8")
        print(f"{'─' * 50}")
        
        research = agent.research_engine(specs)
        
        print(f"  Engine Type: {research['engine_type']}")
        print(f"  Stock HP: {research.get('stock_hp', 'N/A')}")
        print(f"  Safe Boost: {research['safe_boost_limit']} PSI")
        print(f"  Max Boost (Modified): {research['max_boost_modified']} PSI")
        
        print("\n  📊 AFR Recommendations:")
        for scenario, afr in research['afr_recommendations'].items():
            print(f"    • {scenario.replace('_', ' ').title()}: {afr}:1")
        
        print("\n  💉 Meth/Water Injection Benefits:")
        for key, val in research['meth_injection_benefits'].items():
            print(f"    • {key.replace('_', ' ').title()}: {val}")
        
        print("\n  🔵 Nitrous Guidelines:")
        for key, val in research['nitrous_guidelines'].items():
            print(f"    • {key.replace('_', ' ').title()}: {val}")
    
    input("\nPress Enter to continue...")

def demo_driving_analysis():
    """Demonstrate driving pattern analysis with wheel speed data"""
    print_header("📊 DEMO: Driving Pattern Analysis (with Wheel Speed)")
    
    print("Simulating 30 seconds of driving telemetry with wheel speed data...")
    
    telemetry_history = []
    for i in range(30):
        if i < 10:  # Moderate acceleration
            throttle = random.uniform(40, 60)
            rpm = 2000 + (i * 300)
            slip = random.uniform(1, 4)
        elif i < 20:  # Aggressive driving
            throttle = random.uniform(70, 95)
            rpm = 4000 + random.uniform(-500, 1000)
            slip = random.uniform(5, 15)
        else:  # Cruise
            throttle = random.uniform(20, 35)
            rpm = 2500 + random.uniform(-200, 200)
            slip = random.uniform(0, 2)
        
        boost = (throttle / 100) * 10 if rpm > 2000 else 0
        
        telemetry_history.append({
            "throttle_position": throttle,
            "rpm": rpm,
            "boost": boost,
            "wheel_slip": slip
        })
        
        if i % 5 == 0:
            print(f"  {i}s: Throttle={throttle:.0f}%, RPM={rpm:.0f}, Boost={boost:.1f} PSI, Slip={slip:.1f}%")
    
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
    print(f"  • Average Wheel Slip: {stats['avg_wheel_slip']:.1f}%")
    print(f"  • Max Wheel Slip: {stats['max_wheel_slip']:.1f}%")
    
    input("\nPress Enter to continue...")

def demo_tune_generation():
    """Demonstrate AI tune generation for LS3 with meth and nitrous"""
    print_header("⚙️ DEMO: AI Tune Generation (LS3 + Meth + Nitrous)")
    
    print("Vehicle Configuration:")
    print("  • Engine: LS3 6.2L Supercharged V8")
    print("  • Modifications:")
    print("    - Supercharger kit (Whipple 2.3L)")
    print("    - Upgraded fuel pump & injectors")
    print("    - Methanol injection system")
    print("    - Nitrous fogger kit")
    print("  • Safety Priority: HIGH")
    
    print_section("Generating optimized tune...")
    time.sleep(1.5)
    
    agent = AITuningAgent()
    
    pattern = {
        "driving_style": "performance",
        "recommendation": "Performance-oriented tune with traction management",
        "statistics": {
            "avg_throttle": 65.0,
            "max_throttle": 95.0,
            "avg_rpm": 4500,
            "max_rpm": 6400,
            "avg_boost": 8.0,
            "max_boost": 12.0,
            "avg_wheel_slip": 5.0,
            "max_wheel_slip": 12.0
        }
    }
    
    tune = agent.generate_tune(
        {"displacement": 6.2, "cylinders": 8, "aspiration": "supercharged", "max_boost": 12.0, "redline": 6600},
        pattern,
        ["Supercharger kit", "Upgraded fuel pump", "Methanol injection", "Nitrous kit"],
        safety_priority="high"
    )
    
    print("✅ Tune Generated!\n")
    
    params = tune['tune_parameters']
    print("📋 Tune Parameters:")
    print(f"  • Fuel Map Adjustment: {params['fuel_map_adjustment']:+d}%")
    print(f"  • Timing Adjustment: {params['timing_adjustment']:+d}°")
    print(f"  • Boost Target: {params['boost_target']:.0f} PSI")
    print(f"  • AFR Target: {params['afr_target']}")
    print(f"  • Rev Limit: {params['rev_limit']} RPM")
    
    print(f"\n💉 Methanol/Water Injection Config:")
    meth = tune['meth_injection_config']
    print(f"  • Recommended: {'YES' if meth['recommended'] else 'NO'}")
    print(f"  • Activation: {meth['boost_activation_psi']} PSI boost")
    print(f"  • Mix Ratio: {meth['mix_ratio']}% methanol")
    
    print(f"\n🔵 Nitrous Config:")
    nos = tune['nitrous_config']
    print(f"  • Recommended: {'YES' if nos['recommended'] else 'NO'}")
    print(f"  • Shot Size: {nos['shot_size_hp']} HP")
    print(f"  • Mode: {nos['mode'].upper()}")
    
    print(f"\n🎯 Confidence Level: {tune['confidence']*100:.0f}%")
    
    print("\n📈 Expected Performance Gains:")
    for metric, gain in tune['expected_gains'].items():
        print(f"  • {metric.title()}: {gain}")
    
    if tune['warnings']:
        print("\n⚠️ Warnings:")
        for warning in tune['warnings']:
            print(f"  • {warning}")
    
    input("\nPress Enter to continue...")

def demo_adaptive_tuning():
    """Demonstrate real-time adaptive tuning with all systems"""
    print_header("🔄 DEMO: Real-Time Adaptive Tuning (Full System)")
    
    agent = AITuningAgent()
    
    current_tune = {
        "fuel_map_adjustment": 10,
        "timing_adjustment": 3,
        "boost_target": 10,
        "afr_target": 12.0,
        "rev_limit": 6600
    }
    
    print("Current Tune (LS3 Performance):")
    print(f"  • Boost Target: {current_tune['boost_target']} PSI")
    print(f"  • Timing: {current_tune['timing_adjustment']:+d}°")
    print(f"  • AFR Target: {current_tune['afr_target']}")
    
    scenarios = [
        {
            "name": "Normal Operation",
            "telemetry": {
                "knock_count": 0, "ect": 195, "iat": 100, "afr": 12.3,
                "oil_pressure": 50, "wheel_slip": 3.0,
                "meth_tank_level": 80, "nitrous_flow_rate": 0
            }
        },
        {
            "name": "Knock Detection Under Boost",
            "telemetry": {
                "knock_count": 5, "ect": 210, "iat": 135, "afr": 13.0,
                "oil_pressure": 50, "boost": 10, "wheel_slip": 5.0,
                "meth_tank_level": 60, "nitrous_flow_rate": 0
            }
        },
        {
            "name": "Excessive Wheel Spin (Launch)",
            "telemetry": {
                "knock_count": 0, "ect": 200, "iat": 110, "afr": 11.8,
                "oil_pressure": 55, "boost": 8, "wheel_slip": 22.0,
                "meth_tank_level": 70, "nitrous_flow_rate": 0
            }
        },
        {
            "name": "Lean Condition with Nitrous Active",
            "telemetry": {
                "knock_count": 0, "ect": 205, "iat": 95, "afr": 13.2,
                "oil_pressure": 50, "boost": 6, "wheel_slip": 4.0,
                "meth_tank_level": 50, "nitrous_flow_rate": 350
            }
        },
        {
            "name": "Meth Tank Empty Under Boost",
            "telemetry": {
                "knock_count": 2, "ect": 215, "iat": 150, "afr": 12.8,
                "oil_pressure": 48, "boost": 9, "wheel_slip": 3.0,
                "meth_tank_level": 5, "nitrous_flow_rate": 0
            }
        }
    ]
    
    for scenario in scenarios:
        print_section(f"Scenario: {scenario['name']}")
        
        telem = scenario['telemetry']
        print("Telemetry:")
        for key, value in telem.items():
            unit = {
                "knock_count": "", "ect": "°F", "iat": "°F", "afr": ":1",
                "oil_pressure": " PSI", "boost": " PSI", "wheel_slip": "%",
                "meth_tank_level": "%", "nitrous_flow_rate": " cc/min"
            }.get(key, "")
            label = key.replace('_', ' ').title()
            print(f"  • {label}: {value}{unit}")
        
        print("\nAnalyzing...")
        time.sleep(0.5)
        
        adaptation = agent.monitor_and_adapt(current_tune, telem, {})
        
        if adaptation['adjustments_needed']:
            print(f"\n⚠️ Adjustments Required ({adaptation['severity'].upper()})")
            print("\nChanges:")
            for param, value in adaptation['adjustments'].items():
                label = param.replace('_', ' ').title()
                print(f"  • {label}: {value}")
            print("\nReasons:")
            for reason in adaptation['reasons']:
                print(f"  • {reason}")
        else:
            print("\n✅ No adjustments needed - system operating normally")
        
        print()
        time.sleep(1)
    
    input("\nPress Enter to continue...")

def demo_safety_systems():
    """Demonstrate safety monitoring including new systems"""
    print_header("🚨 DEMO: Safety Monitoring Systems")
    
    print("NATOS includes comprehensive safety systems for LS builds:\n")
    
    systems = [
        {
            "name": "Knock Detection & Protection",
            "description": "Monitors for engine knock/detonation on LS V8",
            "actions": [
                "Retards ignition timing by 3° (LS-specific)",
                "Reduces boost pressure by 2 PSI",
                "Enriches fuel mixture",
                "Activates meth injection if available"
            ]
        },
        {
            "name": "Temperature Protection",
            "description": "Monitors all critical LS engine temperatures",
            "actions": [
                "Enriches mixture to cool engine",
                "Activates meth/water injection for charge cooling",
                "Reduces boost if IAT too high",
                "Critical alert at dangerous temps"
            ]
        },
        {
            "name": "AFR Safety",
            "description": "Prevents dangerously lean conditions, especially with nitrous",
            "actions": [
                "Adds fuel if AFR > 12.5 with nitrous active",
                "Critical alert if lean under boost",
                "Automatic enrichment under load",
                "Nitrous auto-disable on lean condition"
            ]
        },
        {
            "name": "Wheel Speed & Traction Control",
            "description": "Real-time wheel speed monitoring from engine to wheels",
            "actions": [
                "Monitors all 4 wheel speeds independently",
                "Calculates real-time slip percentage",
                "Reduces boost on excessive wheel spin",
                "Traction control activation warning"
            ]
        },
        {
            "name": "Methanol/Water Injection Monitor",
            "description": "Monitors meth/water system health and tank level",
            "actions": [
                "Low tank warning at 10%",
                "Reduces boost when tank empty",
                "Retards timing without meth protection",
                "Monitors injection pressure"
            ]
        },
        {
            "name": "Nitrous Fogging Safety",
            "description": "Full nitrous system monitoring and protection",
            "actions": [
                "Bottle pressure and temperature monitoring",
                "Auto-disable on lean AFR condition",
                "RPM and throttle activation gates",
                "Fuel enrichment verification"
            ]
        },
        {
            "name": "Oil Pressure & Over-Boost Protection",
            "description": "Protects LS engine internals",
            "actions": [
                "Critical alert if pressure < 10 PSI",
                "Emergency RPM limit activation",
                "Over-boost wastegate protection",
                "Supercharger bypass monitoring"
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
    print("Wheel speed correlation: Engine RPM → Gear Ratio → Final Drive → Tire → MPH")
    
    input("\nPress Enter to continue...")

def main():
    """Main demo menu"""
    
    print_header("🏎️ NATOS - AI ECU Tuning System Demo")
    
    simulate_typing("Welcome to the NATOS Interactive Demo!", 0.03)
    print("\nLS1/LS2/LS3 Engine Support with Boost Control")
    print("Methanol/Water Injection | Nitrous Fogging | Wheel Speed Monitoring\n")
    
    time.sleep(1)
    
    while True:
        print("\n" + "-" * 60)
        print("DEMO MENU")
        print("-" * 60)
        print("1. LS-Series Engine Research Demo")
        print("2. Driving Pattern Analysis (with Wheel Speed)")
        print("3. AI Tune Generation (LS3 + Meth + Nitrous)")
        print("4. Real-Time Adaptive Tuning (Full System)")
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
