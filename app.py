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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'natos-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class VehicleSimulator:
    """Simulates realistic vehicle telemetry data"""
    
    # Engine profile definitions
    ENGINE_PROFILES = {
        "2.0t_i4": {
            "name": "2.0L Turbo I4",
            "displacement": 2.0,
            "cylinders": 4,
            "aspiration": "turbocharged",
            "max_boost": 15.0,
            "redline": 7000,
            "base_fuel_pressure": 43.5,
            "idle_rpm": 800,
        },
        "ls2": {
            "name": "GM LS2 6.0L V8",
            "model": "ls2",
            "displacement": 6.0,
            "cylinders": 8,
            "aspiration": "naturally_aspirated",
            "compression_ratio": 10.9,
            "bore": 4.000,
            "stroke": 3.622,
            "max_boost": 0,
            "redline": 6500,
            "base_fuel_pressure": 58.0,
            "idle_rpm": 650,
            "cam_profile": "ls2_stock",
            "fuel_system": "ls2_stock",
            "stock_hp": 400,
            "stock_torque": 400,
            "injector_flow_rate": 28.0,
            "injector_count": 8,
        },
    }
    
    def __init__(self, engine_profile="ls2"):
        self.running = False
        self.engine_on = False
        self.engine_profile_key = engine_profile
        
        # Load engine profile
        profile = self.ENGINE_PROFILES.get(engine_profile, self.ENGINE_PROFILES["ls2"])
        
        # Engine specifications
        self.engine_config = {
            "name": profile.get("name", "Unknown"),
            "model": profile.get("model", ""),
            "displacement": profile["displacement"],
            "cylinders": profile["cylinders"],
            "aspiration": profile["aspiration"],
            "max_boost": profile["max_boost"],
            "redline": profile["redline"],
            "cam_profile": profile.get("cam_profile", ""),
            "fuel_system": profile.get("fuel_system", ""),
            "compression_ratio": profile.get("compression_ratio", 0),
            "bore": profile.get("bore", 0),
            "stroke": profile.get("stroke", 0),
            "stock_hp": profile.get("stock_hp", 0),
            "stock_torque": profile.get("stock_torque", 0),
            "injector_flow_rate": profile.get("injector_flow_rate", 0),
            "injector_count": profile.get("injector_count", 0),
        }
        
        idle_rpm = profile.get("idle_rpm", 800)
        
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
            "fuel_pressure": profile.get("base_fuel_pressure", 43.5),  # PSI
            "lambda": 1.0,
            "ignition_timing": 25 if engine_profile == "ls2" else 15,  # degrees BTDC
            "injector_duty": 20,  # %
            "voltage": 14.2,
        }
        
        # Tuning parameters
        if engine_profile == "ls2":
            self.tune = {
                "mode": "stock",
                "fuel_map_adjustment": 0,
                "timing_adjustment": 0,
                "boost_target": 0,  # NA engine
                "afr_target": 14.7,
                "rev_limit": 6500,
                "cam_profile": "ls2_stock",
                "fuel_system": "ls2_stock",
            }
        else:
            self.tune = {
                "mode": "stock",
                "fuel_map_adjustment": 0,
                "timing_adjustment": 0,
                "boost_target": 0,
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
        self._idle_rpm = idle_rpm
        
    def start(self):
        """Start the engine"""
        self.engine_on = True
        self.telemetry["rpm"] = self._idle_rpm + random.randint(-50, 50)
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
        
        is_ls2 = self.engine_profile_key == "ls2"
        idle_rpm = self._idle_rpm
        redline = self.tune["rev_limit"]
        
        # RPM calculation
        target_rpm = idle_rpm + (self.throttle_input / 100) * (redline - idle_rpm)
        self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.1
        self.telemetry["rpm"] = max(idle_rpm, min(redline, self.telemetry["rpm"]))
        
        # Speed calculation (LS2 uses 6-speed gear ratios)
        if self.telemetry["gear"] > 0:
            if is_ls2:
                # T56 6-speed manual ratios (C6 Corvette)
                gear_ratio = [0, 2.97, 2.07, 1.43, 1.00, 0.84, 0.56][min(self.telemetry["gear"], 6)]
            else:
                gear_ratio = [0, 3.5, 2.1, 1.4, 1.0, 0.8][min(self.telemetry["gear"], 5)]
            self.telemetry["speed"] = (self.telemetry["rpm"] / gear_ratio) * 0.05
        
        # Auto gear shifting
        max_gear = 6 if is_ls2 else 5
        shift_up_rpm = 6000 if is_ls2 else 6000
        shift_down_rpm = 1500 if is_ls2 else 2000
        if self.telemetry["rpm"] > shift_up_rpm and self.telemetry["gear"] < max_gear:
            self.telemetry["gear"] += 1
        elif self.telemetry["rpm"] < shift_down_rpm and self.telemetry["gear"] > 1:
            self.telemetry["gear"] -= 1
            
        # Boost/MAP calculation
        if is_ls2:
            # Naturally aspirated - MAP varies with throttle (vacuum to atmospheric)
            # At idle/closed throttle: ~8 PSI (high vacuum)
            # At WOT: ~14.5-14.7 PSI (near atmospheric)
            map_pressure = 8.0 + (self.throttle_input / 100) * 6.7
            self.telemetry["map"] = map_pressure
            self.telemetry["boost"] = 0  # NA engine, no boost
        else:
            # Turbo engine boost calculation
            if self.throttle_input > 30 and self.telemetry["rpm"] > 2500:
                boost_target = (self.throttle_input / 100) * self.tune.get("boost_target", 12)
                self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.05
            else:
                self.telemetry["boost"] *= 0.9
            self.telemetry["boost"] = max(0, self.telemetry["boost"])
            self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # AFR calculation
        base_afr = self.tune["afr_target"]
        if is_ls2:
            # LS2 NA AFR behavior
            if self.throttle_input > 80:
                target_afr = 12.8  # Rich for power/safety at WOT
            elif self.throttle_input < 15:
                target_afr = 14.7  # Stoichiometric at idle/cruise
            elif self.throttle_input > 50:
                target_afr = 13.5  # Slightly rich at part throttle
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
        
        # Temperature simulations
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / redline)
        
        # Engine coolant temp (LS2 runs slightly warmer)
        base_ect = 195 if is_ls2 else 180
        target_ect = base_ect + (load_factor * 25)
        self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp (V8 generates more heat)
        base_oil = 200 if is_ls2 else 180
        target_oil = base_oil + (load_factor * 45)
        self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp
        if is_ls2:
            # NA engine - IAT affected by under-hood heat soak
            target_iat = 85 + (load_factor * 25)
        else:
            target_iat = 75 + (self.telemetry["boost"] * 8)
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp (LS2 runs higher EGT at load)
        if is_ls2:
            target_egt = 700 + (load_factor * 700)
        else:
            target_egt = 800 + (load_factor * 600) + (self.telemetry["boost"] * 20)
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure (LS2 has higher oil pressure at RPM)
        rpm_factor = self.telemetry["rpm"] / 1000
        if is_ls2:
            self.telemetry["oil_pressure"] = 25 + (rpm_factor * 8)  # LS2 oil pressure curve
        else:
            self.telemetry["oil_pressure"] = 10 + (rpm_factor * 10)
        
        # Fuel pressure (LS2 runs 58 PSI, turbo runs 43.5 PSI)
        base_fuel_pressure = 58.0 if is_ls2 else 43.5
        self.telemetry["fuel_pressure"] = base_fuel_pressure + random.uniform(-0.5, 0.5)
        
        # Knock detection (LS2: more likely with advanced timing on regular fuel)
        knock_probability = 0
        if is_ls2:
            if self.telemetry["afr"] > 14.0 and self.telemetry["rpm"] > 4000:
                knock_probability = 0.01
            if self.tune["timing_adjustment"] > 2:
                knock_probability += 0.015
            if self.telemetry["iat"] > 120:
                knock_probability += 0.005
        else:
            if self.telemetry["afr"] > 13.5 and self.telemetry["boost"] > 10:
                knock_probability = 0.02
            if self.tune["timing_adjustment"] > 3:
                knock_probability += 0.01
            
        if random.random() < knock_probability:
            self.telemetry["knock_count"] += 1
            self.telemetry["ignition_timing"] -= 3 if is_ls2 else 2
            
        # Ignition timing (LS2 runs more aggressive base timing)
        if is_ls2:
            base_timing = 25 + self.tune["timing_adjustment"]
            # Timing varies with RPM for LS2
            if self.telemetry["rpm"] > 5000:
                base_timing -= 2  # Pull timing at high RPM
            elif self.telemetry["rpm"] < 2000:
                base_timing -= 5  # Less timing at low RPM
        else:
            base_timing = 15 + self.tune["timing_adjustment"]
            if self.telemetry["boost"] > 8:
                base_timing -= (self.telemetry["boost"] - 8) * 0.5
        self.telemetry["ignition_timing"] = base_timing
        
        # Injector duty cycle
        if is_ls2:
            # LS2 injector duty based on load and RPM (8 injectors)
            duty = 15 + (load_factor * 65) + (self.tune["fuel_map_adjustment"])
        else:
            duty = 20 + (load_factor * 60) + (self.tune["fuel_map_adjustment"])
        self.telemetry["injector_duty"] = min(95, max(5, duty))
        
        # Add realistic noise
        noise_keys = ["rpm", "afr", "oil_pressure"]
        if not is_ls2:
            noise_keys.append("boost")
        for key in noise_keys:
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

# Global vehicle instance (default to LS2)
vehicle = VehicleSimulator(engine_profile="ls2")

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
    is_ls2 = vehicle.engine_profile_key == "ls2"
    
    if is_ls2:
        # LS2-specific tuning modes with cam and fuel system awareness
        if mode == 'stock':
            vehicle.tune.update({
                "mode": "stock",
                "fuel_map_adjustment": 0,
                "timing_adjustment": 0,
                "boost_target": 0,
                "afr_target": 14.7,
                "rev_limit": 6500,
                "cam_profile": "ls2_stock",
                "fuel_system": "ls2_stock",
            })
        elif mode == 'economy':
            vehicle.tune.update({
                "mode": "economy",
                "fuel_map_adjustment": -3,
                "timing_adjustment": 1,
                "boost_target": 0,
                "afr_target": 14.7,
                "rev_limit": 5500,
                "cam_profile": "ls2_stock",
                "fuel_system": "ls2_stock",
            })
        elif mode == 'performance':
            vehicle.tune.update({
                "mode": "performance",
                "fuel_map_adjustment": 3,
                "timing_adjustment": 2,
                "boost_target": 0,
                "afr_target": 13.0,
                "rev_limit": 6500,
                "cam_profile": "ls2_street_performance",
                "fuel_system": "ls2_stage1",
            })
        elif mode == 'modified':
            vehicle.tune.update({
                "mode": "modified",
                "fuel_map_adjustment": 5,
                "timing_adjustment": 3,
                "boost_target": 0,
                "afr_target": 12.8,
                "rev_limit": 6800,
                "cam_profile": "ls2_hot_street",
                "fuel_system": "ls2_stage1",
            })
        elif mode == 'ls2_race':
            vehicle.tune.update({
                "mode": "ls2_race",
                "fuel_map_adjustment": 8,
                "timing_adjustment": 4,
                "boost_target": 0,
                "afr_target": 12.5,
                "rev_limit": 7200,
                "cam_profile": "ls2_race",
                "fuel_system": "ls2_stage2",
            })
    else:
        # Default turbo I4 tuning modes
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
    
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/engine/profile', methods=['POST'])
def set_engine_profile():
    """Switch engine profile (e.g., from turbo I4 to LS2)"""
    global vehicle
    data = request.json
    profile = data.get('profile', 'ls2')
    
    if profile not in VehicleSimulator.ENGINE_PROFILES:
        return jsonify({"status": "error", "message": f"Unknown profile: {profile}"}), 400
    
    was_running = vehicle.engine_on
    if was_running:
        vehicle.stop()
    
    vehicle = VehicleSimulator(engine_profile=profile)
    
    if was_running:
        vehicle.start()
    
    return jsonify({
        "status": "success",
        "profile": profile,
        "engine_config": vehicle.engine_config
    })

@app.route('/api/engine/profiles', methods=['GET'])
def get_engine_profiles():
    """List available engine profiles"""
    profiles = {}
    for key, profile in VehicleSimulator.ENGINE_PROFILES.items():
        profiles[key] = {"name": profile["name"], "displacement": profile["displacement"],
                         "cylinders": profile["cylinders"], "aspiration": profile["aspiration"]}
    return jsonify({"profiles": profiles})

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
        "engine_config": vehicle.engine_config
    })

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
