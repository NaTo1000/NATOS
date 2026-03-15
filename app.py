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
        
        # Engine specifications - VW Golf R EA113 2.0T
        self.engine_config = {
            "vehicle": "VW Golf R",
            "engine_code": "EA113",
            "displacement": 2.0,  # Liters (1984cc)
            "cylinders": 4,
            "layout": "inline",
            "aspiration": "turbocharged",
            "turbo": "K04-064",
            "stock_hp": 256,  # HP
            "stock_torque": 243,  # lb-ft
            "max_boost": 17.4,  # PSI (stock K04)
            "redline": 6800,  # RPM
            "transmission": "6-speed manual",
            "fuel": "premium 91+ AKI",
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
            "boost_target": 14,  # PSI (EA113 stock ~14 PSI cruise)
            "afr_target": 14.7,
            "rev_limit": 6800,
            "overrun_fuel_cut": True,  # Normal: cut fuel on decel
            "anti_lag": False,
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
        self.decelerating = False  # Track decel for flames mode
        self.prev_throttle = 0  # Previous cycle throttle for decel detection
        
    def start(self):
        """Start the engine"""
        self.engine_on = True
        self.telemetry["rpm"] = 850 + random.randint(-50, 50)
        self.telemetry["oil_pressure"] = 30 + random.randint(-2, 2)
        self.telemetry["gear"] = 1
        
    def stop(self):
        """Stop the engine"""
        self.engine_on = False
        self.telemetry["rpm"] = 0
        self.telemetry["oil_pressure"] = 0
        self.telemetry["boost"] = 0
        
    def update(self):
        """Update telemetry based on driving conditions (EA113 physics)"""
        if not self.engine_on:
            return
            
        # Simulate throttle input (random driving pattern)
        if random.random() < 0.05:  # 5% chance to change throttle
            self.throttle_input = random.uniform(0, 100)
        
        # Track deceleration for shooting flames / anti-lag
        self.decelerating = (self.throttle_input < 15 and
                             self.telemetry["rpm"] > 2500 and
                             self.prev_throttle > 30)
        self.prev_throttle = self.throttle_input
            
        self.telemetry["throttle_position"] = self.throttle_input
        
        # RPM calculation (EA113 idle ~850)
        target_rpm = 850 + (self.throttle_input / 100) * 5950
        self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.1
        self.telemetry["rpm"] = max(850, min(self.tune["rev_limit"], self.telemetry["rpm"]))
        
        # Speed calculation (Golf R 6-speed gear ratios)
        if self.telemetry["gear"] > 0:
            gear_ratios = [0, 3.36, 1.95, 1.37, 1.03, 0.84, 0.68]
            gear_idx = min(self.telemetry["gear"], len(gear_ratios) - 1)
            gear_ratio = gear_ratios[gear_idx]
            self.telemetry["speed"] = (self.telemetry["rpm"] / gear_ratio) * 0.05
        
        # Auto gear shifting (6-speed)
        if self.telemetry["rpm"] > 6200 and self.telemetry["gear"] < 6:
            self.telemetry["gear"] += 1
        elif self.telemetry["rpm"] < 1800 and self.telemetry["gear"] > 1:
            self.telemetry["gear"] -= 1
            
        # Boost calculation (K04 turbo spool)
        if self.throttle_input > 30 and self.telemetry["rpm"] > 2500:
            boost_target = (self.throttle_input / 100) * self.tune.get("boost_target", 14)
            self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.05
        elif self.tune.get("anti_lag") and self.decelerating:
            # Anti-lag keeps turbo spooled during decel
            self.telemetry["boost"] *= 0.97  # Slower decay with anti-lag
        else:
            self.telemetry["boost"] *= 0.9  # Boost decay
            
        self.telemetry["boost"] = max(0, self.telemetry["boost"])
        self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # AFR calculation (richer under load)
        base_afr = self.tune["afr_target"]
        if (not self.tune.get("overrun_fuel_cut", True) and
                self.decelerating and self.telemetry["rpm"] > 3000):
            # Shooting flames: dump fuel on overrun for pops & bangs
            target_afr = 10.5  # Very rich on overrun
        elif self.throttle_input > 70 and self.telemetry["boost"] > 5:
            target_afr = 11.5  # Rich for power/safety
        elif self.throttle_input < 20:
            target_afr = 15.5  # Lean for economy
        else:
            target_afr = base_afr
            
        self.telemetry["afr"] += (target_afr - self.telemetry["afr"]) * 0.1
        self.telemetry["lambda"] = self.telemetry["afr"] / 14.7
        
        # Temperature simulations
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / 6800)
        
        # Engine coolant temp
        target_ect = 185 + (load_factor * 30)
        self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp
        target_oil = 200 + (load_factor * 50)
        self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp (K04 compressor heat)
        target_iat = 75 + (self.telemetry["boost"] * 8)
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp
        base_egt = 800 + (load_factor * 600) + (self.telemetry["boost"] * 20)
        if self.tune.get("anti_lag") and self.decelerating:
            # Anti-lag / shooting flames dumps unburnt fuel → extreme EGT
            base_egt += 400
        target_egt = base_egt
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure
        rpm_factor = self.telemetry["rpm"] / 1000
        self.telemetry["oil_pressure"] = 10 + (rpm_factor * 10)
        
        # Knock detection (more likely with aggressive timing/lean AFR)
        knock_probability = 0
        if self.telemetry["afr"] > 13.5 and self.telemetry["boost"] > 10:
            knock_probability = 0.02
        if self.tune["timing_adjustment"] > 3:
            knock_probability += 0.01
            
        if random.random() < knock_probability:
            self.telemetry["knock_count"] += 1
            self.telemetry["ignition_timing"] -= 2  # Pull timing on knock
            
        # Ignition timing
        base_timing = 15 + self.tune["timing_adjustment"]
        if self.telemetry["boost"] > 8:
            base_timing -= (self.telemetry["boost"] - 8) * 0.5
        if self.tune.get("anti_lag") and self.decelerating:
            base_timing -= 10  # Heavily retard timing for anti-lag combustion
        self.telemetry["ignition_timing"] = base_timing
        
        # Injector duty cycle
        duty = 20 + (load_factor * 60) + (self.tune["fuel_map_adjustment"])
        if not self.tune.get("overrun_fuel_cut", True) and self.decelerating:
            duty += 20  # Extra fuel on overrun for flames
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
    
    # VW Golf R EA113 tuning presets — ECO to Shooting Flames
    if mode == 'eco':
        vehicle.tune.update({
            "mode": "eco",
            "fuel_map_adjustment": -5,
            "timing_adjustment": 2,
            "boost_target": 8,
            "afr_target": 15.2,
            "rev_limit": 5500,
            "overrun_fuel_cut": True,
            "anti_lag": False,
        })
    elif mode == 'stock':
        vehicle.tune.update({
            "mode": "stock",
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": 14,
            "afr_target": 14.7,
            "rev_limit": 6800,
            "overrun_fuel_cut": True,
            "anti_lag": False,
        })
    elif mode == 'sport':
        vehicle.tune.update({
            "mode": "sport",
            "fuel_map_adjustment": 5,
            "timing_adjustment": 2,
            "boost_target": 17,
            "afr_target": 13.5,
            "rev_limit": 7000,
            "overrun_fuel_cut": True,
            "anti_lag": False,
        })
    elif mode == 'performance':
        vehicle.tune.update({
            "mode": "performance",
            "fuel_map_adjustment": 10,
            "timing_adjustment": 3,
            "boost_target": 20,
            "afr_target": 12.5,
            "rev_limit": 7200,
            "overrun_fuel_cut": True,
            "anti_lag": False,
        })
    elif mode == 'race':
        vehicle.tune.update({
            "mode": "race",
            "fuel_map_adjustment": 15,
            "timing_adjustment": 5,
            "boost_target": 23,
            "afr_target": 11.8,
            "rev_limit": 7500,
            "overrun_fuel_cut": True,
            "anti_lag": False,
        })
    elif mode == 'flames':
        vehicle.tune.update({
            "mode": "flames",
            "fuel_map_adjustment": 18,
            "timing_adjustment": 5,
            "boost_target": 24,
            "afr_target": 11.5,
            "rev_limit": 7800,
            "overrun_fuel_cut": False,   # Fuel stays on during decel → pops & bangs
            "anti_lag": True,            # Anti-lag keeps turbo spooled
        })
    
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
    print("🏎️  NATOS - VW Golf R EA113 Tuning System")
    print("=" * 60)
    print("⚠️  WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY")
    print("   Modes: ECO → Stock → Sport → Performance → Race → Flames")
    print("=" * 60)
    print("\n🌐 Starting web server on http://localhost:5000")
    print("\n📊 Dashboard will open automatically...\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
