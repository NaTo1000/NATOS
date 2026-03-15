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
    
    def __init__(self):
        self.running = False
        self.engine_on = False
        
        # Engine specifications (default: 2.0L Turbo I4)
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
            "nitrous_active": False,
            "nitrous_bottle_pressure": 900,  # PSI (full bottle)
            "overboost_active": False,
            "overboost_psi": 0,
            "transbrake_engaged": False,
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
        
        # Nitrous oxide system
        self.nitrous = {
            "armed": False,
            "active": False,
            "type": "wet",         # "wet" (fuel+nos) or "dry" (nos only)
            "shot_size": 100,      # HP equivalent (75, 100, 150, 200)
            "bottle_pressure": 900,  # PSI (full ~900-1050)
            "min_rpm_activate": 3500,  # Don't spray below this RPM
            "max_rpm_activate": 7000,  # Cut above this
            "fuel_enrichment": 15,     # % extra fuel for wet shot
        }
        
        # Overboost system
        self.overboost = {
            "enabled": False,
            "active": False,
            "boost_adder": 6,        # PSI added above base boost target
            "duration": 10.0,        # Seconds allowed
            "cooldown": 30.0,        # Seconds before reuse
            "timer": 0,              # Current active timer
            "cooldown_timer": 0,     # Current cooldown timer
        }
        
        # Transbrake launch mode
        self.transbrake = {
            "armed": False,
            "engaged": False,
            "launch_rpm": 5000,      # RPM to hold during staging
            "boost_build_target": 15,  # PSI to build on the line
            "two_step_rpm": 5000,    # Two-step rev limiter
            "launched": False,       # Has the launch occurred
        }
        
        # Driving simulation
        self.throttle_input = 0
        self.brake_input = 0
        self.target_gear = 1
        
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
        # Reset active systems on shutdown
        self.nitrous["active"] = False
        self.overboost["active"] = False
        self.overboost["timer"] = 0
        self.transbrake["engaged"] = False
        self.transbrake["launched"] = False
        self.telemetry["nitrous_active"] = False
        self.telemetry["overboost_active"] = False
        self.telemetry["transbrake_engaged"] = False
        
    def update(self):
        """Update telemetry based on driving conditions"""
        if not self.engine_on:
            return
            
        # --- Transbrake logic ---
        if self.transbrake["engaged"]:
            # Hold RPM at launch RPM, build boost against the converter
            self.throttle_input = 100
            self.telemetry["throttle_position"] = 100
            target_rpm = self.transbrake["launch_rpm"]
            self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.2
            self.telemetry["rpm"] = max(800, min(self.transbrake["two_step_rpm"] + 100, self.telemetry["rpm"]))
            self.telemetry["speed"] = 0  # Brakes held
            self.telemetry["gear"] = 1
            # Build boost against the stall
            boost_build = self.transbrake["boost_build_target"]
            self.telemetry["boost"] += (boost_build - self.telemetry["boost"]) * 0.08
            self.telemetry["transbrake_engaged"] = True
        else:
            self.telemetry["transbrake_engaged"] = False

            # Simulate throttle input (random driving pattern)
            if random.random() < 0.05:  # 5% chance to change throttle
                self.throttle_input = random.uniform(0, 100)
                
            self.telemetry["throttle_position"] = self.throttle_input
            
            # RPM calculation
            target_rpm = 800 + (self.throttle_input / 100) * 6000
            self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.1
            self.telemetry["rpm"] = max(800, min(self.tune["rev_limit"], self.telemetry["rpm"]))
            
            # Speed calculation
            if self.telemetry["gear"] > 0:
                gear_ratio = [0, 3.5, 2.1, 1.4, 1.0, 0.8][self.telemetry["gear"]]
                self.telemetry["speed"] = (self.telemetry["rpm"] / gear_ratio) * 0.05
            
            # Auto gear shifting
            if self.telemetry["rpm"] > 6000 and self.telemetry["gear"] < 5:
                self.telemetry["gear"] += 1
            elif self.telemetry["rpm"] < 2000 and self.telemetry["gear"] > 1:
                self.telemetry["gear"] -= 1
        
        # --- Boost calculation (turbo) ---
        effective_boost_target = self.tune.get("boost_target", 12)
        
        # Overboost adder
        if self.overboost["active"]:
            self.overboost["timer"] += 0.1  # 100ms per tick
            if self.overboost["timer"] >= self.overboost["duration"]:
                # Overboost expired
                self.overboost["active"] = False
                self.overboost["timer"] = 0
                self.overboost["cooldown_timer"] = self.overboost["cooldown"]
            else:
                effective_boost_target += self.overboost["boost_adder"]
                self.telemetry["overboost_active"] = True
                self.telemetry["overboost_psi"] = self.overboost["boost_adder"]
        else:
            self.telemetry["overboost_active"] = False
            self.telemetry["overboost_psi"] = 0
            # Tick cooldown
            if self.overboost["cooldown_timer"] > 0:
                self.overboost["cooldown_timer"] = max(0, self.overboost["cooldown_timer"] - 0.1)
        
        if not self.transbrake["engaged"]:
            if self.throttle_input > 30 and self.telemetry["rpm"] > 2500:
                boost_target = (self.throttle_input / 100) * effective_boost_target
                self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.05
            else:
                self.telemetry["boost"] *= 0.9  # Boost decay
                
        self.telemetry["boost"] = max(0, self.telemetry["boost"])
        self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # --- Nitrous oxide system ---
        nos_hp_adder = 0
        if (self.nitrous["armed"] and
                self.throttle_input >= 95 and
                self.telemetry["rpm"] >= self.nitrous["min_rpm_activate"] and
                self.telemetry["rpm"] <= self.nitrous["max_rpm_activate"] and
                self.nitrous["bottle_pressure"] > 100):
            self.nitrous["active"] = True
            self.telemetry["nitrous_active"] = True
            nos_hp_adder = self.nitrous["shot_size"]
            # Consume bottle pressure (~1 PSI per tick at 10Hz)
            self.nitrous["bottle_pressure"] = max(0, self.nitrous["bottle_pressure"] - 0.8)
            self.telemetry["nitrous_bottle_pressure"] = self.nitrous["bottle_pressure"]
        else:
            self.nitrous["active"] = False
            self.telemetry["nitrous_active"] = False
        
        # --- AFR calculation (richer under load, accounts for nitrous) ---
        base_afr = self.tune["afr_target"]
        if self.nitrous["active"]:
            # Nitrous demands richer mixtures for safety
            target_afr = 11.0 if self.nitrous["type"] == "wet" else 11.3
        elif self.throttle_input > 70 and self.telemetry["boost"] > 5:
            target_afr = 11.5  # Rich for power/safety
        elif self.throttle_input < 20:
            target_afr = 15.5  # Lean for economy
        else:
            target_afr = base_afr
            
        self.telemetry["afr"] += (target_afr - self.telemetry["afr"]) * 0.1
        self.telemetry["lambda"] = self.telemetry["afr"] / 14.7
        
        # --- Temperature simulations ---
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / 7000)
        
        # Nitrous increases EGT and coolant load
        nos_heat = (nos_hp_adder / 200) * 0.3 if self.nitrous["active"] else 0
        
        # Engine coolant temp
        target_ect = 180 + (load_factor * 30) + (nos_heat * 20)
        self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp
        target_oil = 180 + (load_factor * 50) + (nos_heat * 15)
        self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp (nitrous cools intake charge)
        iat_nos_cooling = -30 if self.nitrous["active"] else 0
        target_iat = 75 + (self.telemetry["boost"] * 8) + iat_nos_cooling
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp (nitrous raises EGT significantly)
        target_egt = 800 + (load_factor * 600) + (self.telemetry["boost"] * 20)
        if self.nitrous["active"]:
            target_egt += nos_hp_adder * 1.5
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure
        rpm_factor = self.telemetry["rpm"] / 1000
        self.telemetry["oil_pressure"] = 10 + (rpm_factor * 10)
        
        # Knock detection (simulated - more likely with aggressive timing/lean AFR/nitrous)
        knock_probability = 0
        if self.telemetry["afr"] > 13.5 and self.telemetry["boost"] > 10:
            knock_probability = 0.02
        if self.tune["timing_adjustment"] > 3:
            knock_probability += 0.01
        if self.nitrous["active"]:
            knock_probability += 0.015  # Nitrous increases knock risk
            
        if random.random() < knock_probability:
            self.telemetry["knock_count"] += 1
            self.telemetry["ignition_timing"] -= 2  # Pull timing on knock
            
        # Ignition timing
        base_timing = 15 + self.tune["timing_adjustment"]
        if self.telemetry["boost"] > 8:
            base_timing -= (self.telemetry["boost"] - 8) * 0.5  # Retard under boost
        if self.nitrous["active"]:
            base_timing -= 4  # Retard timing for nitrous safety
        self.telemetry["ignition_timing"] = base_timing
        
        # Injector duty cycle (nitrous wet system adds fuel)
        duty = 20 + (load_factor * 60) + (self.tune["fuel_map_adjustment"])
        if self.nitrous["active"] and self.nitrous["type"] == "wet":
            duty += self.nitrous["fuel_enrichment"]
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
        
        # Nitrous safety checks
        if self.nitrous["active"]:
            warnings.append(f"NOS ACTIVE: {self.nitrous['shot_size']}hp {self.nitrous['type']} shot")
            if self.nitrous["bottle_pressure"] < 200:
                warnings.append(f"WARNING: NOS bottle low ({self.nitrous['bottle_pressure']:.0f} PSI)")
            if self.telemetry["egt"] > 1400:
                critical.append("CRITICAL: EGT too high with nitrous active!")
        
        # Overboost warnings
        if self.overboost["active"]:
            remaining = self.overboost["duration"] - self.overboost["timer"]
            warnings.append(f"OVERBOOST ACTIVE: +{self.overboost['boost_adder']} PSI ({remaining:.1f}s left)")
        
        # Transbrake warnings
        if self.transbrake["engaged"]:
            warnings.append(f"TRANSBRAKE ENGAGED: Holding {self.transbrake['launch_rpm']} RPM - Building boost")
            
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
                "nitrous": vehicle.nitrous,
                "overboost": vehicle.overboost,
                "transbrake": vehicle.transbrake,
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
    elif mode == 'ls3_big_boost':
        # LS3 6.2L V8 big boost full tune
        vehicle.engine_config.update({
            "displacement": 6.2,
            "cylinders": 8,
            "aspiration": "twin-turbocharged",
            "max_boost": 28.0,
            "redline": 7200,
        })
        vehicle.tune.update({
            "mode": "ls3_big_boost",
            "fuel_map_adjustment": 25,
            "timing_adjustment": 6,
            "boost_target": 24,
            "afr_target": 11.5,
            "rev_limit": 7200,
        })
        # LS3 big boost defaults for overboost & transbrake
        vehicle.overboost["boost_adder"] = 8
        vehicle.overboost["duration"] = 12.0
        vehicle.transbrake["launch_rpm"] = 5500
        vehicle.transbrake["boost_build_target"] = 18
        vehicle.transbrake["two_step_rpm"] = 5500
    
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/tune/custom', methods=['POST'])
def set_custom_tune():
    data = request.json
    vehicle.tune.update(data)
    return jsonify({"status": "success", "tune": vehicle.tune})

# --- Nitrous Oxide Control ---

@app.route('/api/nitrous/arm', methods=['POST'])
def nitrous_arm():
    data = request.json or {}
    vehicle.nitrous["armed"] = True
    if "type" in data:
        vehicle.nitrous["type"] = data["type"]
    if "shot_size" in data:
        vehicle.nitrous["shot_size"] = int(data["shot_size"])
    return jsonify({"status": "armed", "nitrous": vehicle.nitrous})

@app.route('/api/nitrous/disarm', methods=['POST'])
def nitrous_disarm():
    vehicle.nitrous["armed"] = False
    vehicle.nitrous["active"] = False
    vehicle.telemetry["nitrous_active"] = False
    return jsonify({"status": "disarmed", "nitrous": vehicle.nitrous})

@app.route('/api/nitrous/purge', methods=['POST'])
def nitrous_purge():
    """Purge the nitrous lines (brief activation for pressure equalization)"""
    if vehicle.nitrous["bottle_pressure"] > 50:
        vehicle.nitrous["bottle_pressure"] -= 10
        vehicle.telemetry["nitrous_bottle_pressure"] = vehicle.nitrous["bottle_pressure"]
    return jsonify({"status": "purged", "bottle_pressure": vehicle.nitrous["bottle_pressure"]})

@app.route('/api/nitrous/refill', methods=['POST'])
def nitrous_refill():
    """Refill the nitrous bottle"""
    vehicle.nitrous["bottle_pressure"] = 950
    vehicle.telemetry["nitrous_bottle_pressure"] = 950
    return jsonify({"status": "refilled", "bottle_pressure": vehicle.nitrous["bottle_pressure"]})

@app.route('/api/nitrous/status', methods=['GET'])
def nitrous_status():
    return jsonify({"nitrous": vehicle.nitrous})

# --- Overboost Control ---

@app.route('/api/overboost/enable', methods=['POST'])
def overboost_enable():
    data = request.json or {}
    vehicle.overboost["enabled"] = True
    if "boost_adder" in data:
        vehicle.overboost["boost_adder"] = min(12, max(2, float(data["boost_adder"])))
    if "duration" in data:
        vehicle.overboost["duration"] = min(15, max(3, float(data["duration"])))
    return jsonify({"status": "enabled", "overboost": vehicle.overboost})

@app.route('/api/overboost/disable', methods=['POST'])
def overboost_disable():
    vehicle.overboost["enabled"] = False
    vehicle.overboost["active"] = False
    vehicle.overboost["timer"] = 0
    vehicle.telemetry["overboost_active"] = False
    return jsonify({"status": "disabled", "overboost": vehicle.overboost})

@app.route('/api/overboost/activate', methods=['POST'])
def overboost_activate():
    """Activate overboost (if enabled and off cooldown)"""
    if not vehicle.overboost["enabled"]:
        return jsonify({"status": "error", "message": "Overboost not enabled"}), 400
    if vehicle.overboost["active"]:
        return jsonify({"status": "error", "message": "Overboost already active"}), 400
    if vehicle.overboost["cooldown_timer"] > 0:
        return jsonify({
            "status": "error",
            "message": f"Overboost cooling down ({vehicle.overboost['cooldown_timer']:.1f}s remaining)"
        }), 400
    vehicle.overboost["active"] = True
    vehicle.overboost["timer"] = 0
    return jsonify({"status": "activated", "overboost": vehicle.overboost})

@app.route('/api/overboost/status', methods=['GET'])
def overboost_status():
    return jsonify({"overboost": vehicle.overboost})

# --- Transbrake Launch Mode ---

@app.route('/api/transbrake/arm', methods=['POST'])
def transbrake_arm():
    data = request.json or {}
    vehicle.transbrake["armed"] = True
    if "launch_rpm" in data:
        vehicle.transbrake["launch_rpm"] = min(7000, max(3000, int(data["launch_rpm"])))
        vehicle.transbrake["two_step_rpm"] = vehicle.transbrake["launch_rpm"]
    if "boost_build_target" in data:
        vehicle.transbrake["boost_build_target"] = min(25, max(5, float(data["boost_build_target"])))
    vehicle.transbrake["launched"] = False
    return jsonify({"status": "armed", "transbrake": vehicle.transbrake})

@app.route('/api/transbrake/engage', methods=['POST'])
def transbrake_engage():
    """Engage transbrake - hold car on the line, build boost"""
    if not vehicle.transbrake["armed"]:
        return jsonify({"status": "error", "message": "Transbrake not armed"}), 400
    if not vehicle.engine_on:
        return jsonify({"status": "error", "message": "Engine not running"}), 400
    vehicle.transbrake["engaged"] = True
    vehicle.transbrake["launched"] = False
    vehicle.telemetry["gear"] = 1
    return jsonify({"status": "engaged", "transbrake": vehicle.transbrake})

@app.route('/api/transbrake/launch', methods=['POST'])
def transbrake_launch():
    """Release transbrake - LAUNCH!"""
    if not vehicle.transbrake["engaged"]:
        return jsonify({"status": "error", "message": "Transbrake not engaged"}), 400
    vehicle.transbrake["engaged"] = False
    vehicle.transbrake["launched"] = True
    vehicle.transbrake["armed"] = False
    vehicle.telemetry["transbrake_engaged"] = False
    return jsonify({"status": "launched", "transbrake": vehicle.transbrake})

@app.route('/api/transbrake/disarm', methods=['POST'])
def transbrake_disarm():
    vehicle.transbrake["armed"] = False
    vehicle.transbrake["engaged"] = False
    vehicle.transbrake["launched"] = False
    vehicle.telemetry["transbrake_engaged"] = False
    return jsonify({"status": "disarmed", "transbrake": vehicle.transbrake})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "engine_on": vehicle.engine_on,
        "telemetry": vehicle.telemetry,
        "tune": vehicle.tune,
        "engine_config": vehicle.engine_config,
        "nitrous": vehicle.nitrous,
        "overboost": vehicle.overboost,
        "transbrake": vehicle.transbrake,
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
