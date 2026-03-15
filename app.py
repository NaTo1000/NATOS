"""
NATOS - Autonomous Tuning & Optimization System
AI-Powered ECU Tuning with Real-time Telemetry

WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY
DO NOT USE ON ACTUAL VEHICLES WITHOUT PROFESSIONAL VALIDATION
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import random
import json
from datetime import datetime
from ls1_tuner import LS1AdvancedTuner, LS1_ENGINE_CONFIG, LS1_TUNE_PRESETS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'natos-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class VehicleSimulator:
    """Simulates realistic vehicle telemetry data"""
    
    def __init__(self):
        self.running = False
        self.engine_on = False
        self.engine_profile = "2.0t_i4"  # "2.0t_i4" or "ls1_v8"
        
        # Engine specifications
        self.engine_config = {
            "displacement": 2.0,  # Liters
            "cylinders": 4,
            "aspiration": "turbocharged",
            "max_boost": 15.0,  # PSI
            "redline": 7000,  # RPM
        }
        
        # Current telemetry
        self.telemetry = {
            "rpm": 0,
            "speed": 0,
            "throttle_position": 0,
            "afr": 14.7,  # Air/Fuel Ratio (stoichiometric)
            "map": 14.7,  # Manifold pressure (PSI)
            "boost": 0,
            "iat": 75,  # Intake Air Temp (F)
            "ect": 180,  # Engine Coolant Temp (F)
            "egt": 800,  # Exhaust Gas Temp (F)
            "oil_pressure": 0,  # PSI
            "oil_temp": 180,  # F
            "knock_count": 0,
            "gear": 0,
            "fuel_pressure": 43.5,  # PSI
            "lambda": 1.0,
            "ignition_timing": 15,  # degrees BTDC
            "injector_duty": 20,  # %
            "voltage": 14.2,
        }
        
        # Tuning parameters
        self.tune = {
            "mode": "stock",
            "fuel_map_adjustment": 0,  # % change
            "timing_adjustment": 0,  # degrees
            "boost_target": 0,  # PSI (0 = stock)
            "afr_target": 14.7,
            "rev_limit": 7000,
        }
        
        # Safety limits
        self.limits = {
            "max_ect": 230,  # F
            "max_oil_temp": 280,  # F
            "max_egt": 1600,  # F
            "max_knock": 5,
            "min_afr": 10.5,
            "max_afr": 16.0,
        }
        
        # Driving simulation
        self.throttle_input = 0
        self.brake_input = 0
        self.target_gear = 1
        
    def set_engine_profile(self, profile: str):
        """Switch engine profile between 2.0T I4 and LS1 V8"""
        if profile == "ls1_v8":
            self.engine_profile = "ls1_v8"
            self.engine_config = {
                "displacement": LS1_ENGINE_CONFIG["displacement"],
                "cylinders": LS1_ENGINE_CONFIG["cylinders"],
                "aspiration": LS1_ENGINE_CONFIG["aspiration"],
                "max_boost": LS1_ENGINE_CONFIG["max_boost"],
                "redline": LS1_ENGINE_CONFIG["redline"],
            }
            self.tune.update({
                "mode": "ls1_stock",
                "fuel_map_adjustment": 0,
                "timing_adjustment": 0,
                "boost_target": 0,
                "afr_target": 14.7,
                "rev_limit": 6000,
            })
            self.limits.update({
                "max_ect": 240,
                "max_oil_temp": 280,
                "max_egt": 1500,
            })
        else:
            self.engine_profile = "2.0t_i4"
            self.engine_config = {
                "displacement": 2.0,
                "cylinders": 4,
                "aspiration": "turbocharged",
                "max_boost": 15.0,
                "redline": 7000,
            }
            self.tune.update({
                "mode": "stock",
                "fuel_map_adjustment": 0,
                "timing_adjustment": 0,
                "boost_target": 12,
                "afr_target": 14.7,
                "rev_limit": 7000,
            })
            self.limits.update({
                "max_ect": 230,
                "max_oil_temp": 280,
                "max_egt": 1600,
            })

    def start(self):
        """Start the engine"""
        self.engine_on = True
        self.telemetry["rpm"] = 800 + random.randint(-50, 50)
        self.telemetry["oil_pressure"] = 30 + random.randint(-2, 2)
        
    def stop(self):
        """Stop the engine"""
        self.engine_on = False
        self.telemetry["rpm"] = 0
        self.telemetry["oil_pressure"] = 0
        self.telemetry["boost"] = 0
        
    def update(self):
        """Update telemetry based on driving conditions"""
        if not self.engine_on:
            return
            
        # Simulate throttle input (random driving pattern)
        if random.random() < 0.05:  # 5% chance to change throttle
            self.throttle_input = random.uniform(0, 100)
            
        self.telemetry["throttle_position"] = self.throttle_input
        
        is_ls1 = self.engine_profile == "ls1_v8"
        
        # RPM calculation - LS1 has lower idle and different RPM range
        idle_rpm = 600 if is_ls1 else 800
        rpm_range = 5400 if is_ls1 else 6000
        target_rpm = idle_rpm + (self.throttle_input / 100) * rpm_range
        self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.1
        self.telemetry["rpm"] = max(idle_rpm, min(self.tune["rev_limit"], self.telemetry["rpm"]))
        
        # Speed calculation - LS1 has different gearing (6-speed T56)
        if self.telemetry["gear"] > 0:
            if is_ls1:
                gear_ratios = [0, 2.66, 1.78, 1.30, 1.00, 0.74, 0.50]
                gear_idx = max(0, min(self.telemetry["gear"], len(gear_ratios) - 1))
                gear_ratio = gear_ratios[gear_idx]
            else:
                gear_ratios = [0, 3.5, 2.1, 1.4, 1.0, 0.8]
                gear_idx = max(0, min(self.telemetry["gear"], len(gear_ratios) - 1))
                gear_ratio = gear_ratios[gear_idx]
            self.telemetry["speed"] = (self.telemetry["rpm"] / gear_ratio) * 0.05
        
        # Auto gear shifting
        max_gear = 6 if is_ls1 else 5
        shift_up_rpm = 5500 if is_ls1 else 6000
        shift_down_rpm = 1500 if is_ls1 else 2000
        if self.telemetry["rpm"] > shift_up_rpm and self.telemetry["gear"] < max_gear:
            self.telemetry["gear"] += 1
        elif self.telemetry["rpm"] < shift_down_rpm and self.telemetry["gear"] > 1:
            self.telemetry["gear"] -= 1
            
        # Boost / MAP calculation
        if is_ls1:
            # LS1 is NA - MAP based on throttle position (vacuum to atmospheric)
            # Idle/closed throttle = ~8 PSI MAP (high vacuum)
            # WOT = ~14.7 PSI MAP (atmospheric)
            if self.tune.get("boost_target", 0) > 0:
                # Forced induction LS1
                fi_boost = (self.throttle_input / 100) * self.tune["boost_target"]
                self.telemetry["boost"] += (fi_boost - self.telemetry["boost"]) * 0.08
                self.telemetry["boost"] = max(0, self.telemetry["boost"])
            else:
                self.telemetry["boost"] = 0
            map_value = 8 + (self.throttle_input / 100) * 6.7 + self.telemetry["boost"]
            self.telemetry["map"] = map_value
        else:
            # 2.0T turbo boost model
            if self.throttle_input > 30 and self.telemetry["rpm"] > 2500:
                boost_target = (self.throttle_input / 100) * self.tune.get("boost_target", 12)
                self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.05
            else:
                self.telemetry["boost"] *= 0.9
            self.telemetry["boost"] = max(0, self.telemetry["boost"])
            self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # AFR calculation
        base_afr = self.tune["afr_target"]
        if is_ls1:
            # LS1 NA AFR curve - richer at WOT for power
            if self.throttle_input > 80:
                target_afr = min(base_afr, 12.5)  # WOT enrichment
            elif self.throttle_input > 50:
                target_afr = min(base_afr, 13.5)  # Part throttle
            elif self.throttle_input < 15:
                target_afr = 14.7  # Stoich at idle/cruise
            else:
                target_afr = base_afr
        else:
            if self.throttle_input > 70 and self.telemetry["boost"] > 5:
                target_afr = 11.5
            elif self.throttle_input < 20:
                target_afr = 15.5
            else:
                target_afr = base_afr
            
        self.telemetry["afr"] += (target_afr - self.telemetry["afr"]) * 0.1
        self.telemetry["lambda"] = self.telemetry["afr"] / 14.7
        
        # Temperature simulations - LS1 V8 has different thermal characteristics
        redline = self.engine_config.get("redline", 7000)
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / redline)
        
        # Engine coolant temp - LS1 runs hotter due to larger displacement
        if is_ls1:
            target_ect = 195 + (load_factor * 35)  # LS1 thermostat at 195°F
            self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.008  # Slower response (larger mass)
        else:
            target_ect = 180 + (load_factor * 30)
            self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp - LS1 has larger oil capacity, slower to heat
        if is_ls1:
            target_oil = 195 + (load_factor * 55)
            self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.006
        else:
            target_oil = 180 + (load_factor * 50)
            self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp - LS1 NA has lower IAT than turbo
        if is_ls1:
            target_iat = 80 + (load_factor * 15)  # NA engines have minimal intake heating
            if self.telemetry["boost"] > 0:
                target_iat += self.telemetry["boost"] * 6  # FI heating
        else:
            target_iat = 75 + (self.telemetry["boost"] * 8)  # Heat from compression
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp - LS1 runs different EGT ranges
        if is_ls1:
            target_egt = 700 + (load_factor * 500) + (self.telemetry["boost"] * 25)
        else:
            target_egt = 800 + (load_factor * 600) + (self.telemetry["boost"] * 20)
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure - LS1 has higher oil pressure due to larger pump
        rpm_factor = self.telemetry["rpm"] / 1000
        if is_ls1:
            self.telemetry["oil_pressure"] = 15 + (rpm_factor * 8)
        else:
            self.telemetry["oil_pressure"] = 10 + (rpm_factor * 10)
        
        # Knock detection - LS1 knock behavior differs from turbo
        knock_probability = 0
        if is_ls1:
            # LS1 knock: more likely with aggressive timing or lean condition at high RPM
            if self.telemetry["afr"] > 14.0 and self.telemetry["rpm"] > 4000:
                knock_probability = 0.015
            if self.tune["timing_adjustment"] > 4:
                knock_probability += 0.02
        else:
            if self.telemetry["afr"] > 13.5 and self.telemetry["boost"] > 10:
                knock_probability = 0.02
            if self.tune["timing_adjustment"] > 3:
                knock_probability += 0.01
            
        if random.random() < knock_probability:
            self.telemetry["knock_count"] += 1
            self.telemetry["ignition_timing"] -= 2  # Pull timing on knock
            
        # Ignition timing - LS1 has higher base timing (NA engine)
        if is_ls1:
            base_timing = 24 + self.tune["timing_adjustment"]  # LS1 base timing ~24° BTDC
            if self.telemetry["boost"] > 0:
                base_timing -= self.telemetry["boost"] * 1.0  # Retard under boost (if FI)
        else:
            base_timing = 15 + self.tune["timing_adjustment"]
            if self.telemetry["boost"] > 8:
                base_timing -= (self.telemetry["boost"] - 8) * 0.5  # Retard under boost
        self.telemetry["ignition_timing"] = base_timing
        
        # Injector duty cycle
        duty = 20 + (load_factor * 60) + (self.tune["fuel_map_adjustment"])
        self.telemetry["injector_duty"] = min(95, max(5, duty))
        
        # Add realistic noise
        for key in ["rpm", "afr", "boost", "oil_pressure"]:
            self.telemetry[key] += random.uniform(-0.5, 0.5)
            
    def check_safety(self):
        """Check for dangerous conditions"""
        warnings = []
        critical = []
        
        if self.telemetry["ect"] > self.limits["max_ect"]:
            critical.append(f"CRITICAL: Coolant temp {self.telemetry['ect']:.1f}°F exceeds limit!")
            
        if self.telemetry["oil_temp"] > self.limits["max_oil_temp"]:
            critical.append(f"CRITICAL: Oil temp {self.telemetry['oil_temp']:.1f}°F exceeds limit!")
            
        if self.telemetry["egt"] > self.limits["max_egt"]:
            critical.append(f"CRITICAL: Exhaust temp {self.telemetry['egt']:.1f}°F exceeds limit!")
            
        if self.telemetry["knock_count"] > self.limits["max_knock"]:
            critical.append(f"CRITICAL: Knock count {self.telemetry['knock_count']} detected!")
            
        if self.telemetry["afr"] < self.limits["min_afr"]:
            warnings.append(f"WARNING: AFR {self.telemetry['afr']:.1f} too rich!")
            
        if self.telemetry["oil_pressure"] < 10 and self.telemetry["rpm"] > 2000:
            critical.append("CRITICAL: Low oil pressure!")
            
        return {"warnings": warnings, "critical": critical}

# Global vehicle instance
vehicle = VehicleSimulator()

def telemetry_thread():
    """Background thread for telemetry updates"""
    while True:
        if vehicle.engine_on:
            vehicle.update()
            safety = vehicle.check_safety()
            
            data = {
                "telemetry": vehicle.telemetry,
                "tune": vehicle.tune,
                "safety": safety,
                "engine_profile": vehicle.engine_profile,
                "timestamp": datetime.now().isoformat()
            }
            
            socketio.emit('telemetry_update', data)
        
        time.sleep(0.1)  # 10 Hz update rate

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/engine/start', methods=['POST'])
def start_engine():
    vehicle.start()
    return jsonify({"status": "started", "rpm": vehicle.telemetry["rpm"]})

@app.route('/api/engine/stop', methods=['POST'])
def stop_engine():
    vehicle.stop()
    return jsonify({"status": "stopped"})

@app.route('/api/tune/mode', methods=['POST'])
def set_tune_mode():
    data = request.json
    mode = data.get('mode', 'stock')
    
    # Apply tuning presets
    if mode == 'stock':
        vehicle.tune.update({
            "mode": "stock",
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": 12,
            "afr_target": 14.7,
            "rev_limit": 7000,
        })
    elif mode == 'economy':
        vehicle.tune.update({
            "mode": "economy",
            "fuel_map_adjustment": -5,
            "timing_adjustment": 2,
            "boost_target": 10,
            "afr_target": 15.2,
            "rev_limit": 6500,
        })
    elif mode == 'performance':
        vehicle.tune.update({
            "mode": "performance",
            "fuel_map_adjustment": 10,
            "timing_adjustment": 3,
            "boost_target": 18,
            "afr_target": 12.5,
            "rev_limit": 7500,
        })
    elif mode == 'modified':
        vehicle.tune.update({
            "mode": "modified",
            "fuel_map_adjustment": 15,
            "timing_adjustment": 5,
            "boost_target": 22,
            "afr_target": 11.8,
            "rev_limit": 7800,
        })
    elif mode in LS1_TUNE_PRESETS:
        vehicle.tune.update(LS1_TUNE_PRESETS[mode])
    
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/tune/custom', methods=['POST'])
def set_custom_tune():
    data = request.json
    vehicle.tune.update(data)
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "engine_on": vehicle.engine_on,
        "telemetry": vehicle.telemetry,
        "tune": vehicle.tune,
        "engine_config": vehicle.engine_config,
        "engine_profile": vehicle.engine_profile,
    })

# LS1 Advanced Tuning Module endpoints
ls1_tuner = LS1AdvancedTuner()

@app.route('/api/engine/profile', methods=['POST'])
def set_engine_profile():
    """Switch between engine profiles (2.0T I4 or LS1 V8)"""
    data = request.json
    profile = data.get('profile', '2.0t_i4')
    if profile not in ('2.0t_i4', 'ls1_v8'):
        return jsonify({"status": "error", "message": "Invalid profile. Use '2.0t_i4' or 'ls1_v8'"}), 400
    was_running = vehicle.engine_on
    if was_running:
        vehicle.stop()
    vehicle.set_engine_profile(profile)
    return jsonify({
        "status": "success",
        "engine_profile": vehicle.engine_profile,
        "engine_config": vehicle.engine_config,
        "tune": vehicle.tune,
        "message": f"Switched to {vehicle.engine_config.get('displacement', '')}L engine profile"
    })

@app.route('/api/ls1/research', methods=['GET'])
def ls1_research():
    """Get LS1 engine research data"""
    return jsonify(ls1_tuner.research_engine())

@app.route('/api/ls1/presets', methods=['GET'])
def ls1_presets():
    """Get available LS1 tune presets"""
    return jsonify({"presets": ls1_tuner.get_available_presets()})

@app.route('/api/ls1/generate_tune', methods=['POST'])
def ls1_generate_tune():
    """Generate an optimized LS1 tune"""
    data = request.json or {}
    modifications = data.get('modifications', [])
    driving_style = data.get('driving_style', 'street')
    fuel_octane = data.get('fuel_octane', 93)
    safety_priority = data.get('safety_priority', 'high')
    result = ls1_tuner.generate_tune(
        modifications=modifications,
        driving_style=driving_style,
        fuel_octane=fuel_octane,
        safety_priority=safety_priority,
    )
    return jsonify(result)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Start telemetry thread
    thread = threading.Thread(target=telemetry_thread, daemon=True)
    thread.start()
    
    print("=" * 60)
    print("🏎️  NATOS - Autonomous Tuning & Optimization System")
    print("=" * 60)
    print("⚠️  WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY")
    print("=" * 60)
    print("\n🌐 Starting web server on http://localhost:5000")
    print("\n📊 Dashboard will open automatically...\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
