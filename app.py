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
from ai_tuner import AITuningAgent

app = Flask(__name__)
app.config['SECRET_KEY'] = 'natos-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

TUNE_LIMITS = {
    "fuel_map_adjustment": (-20, 20),
    "timing_adjustment": (-10, 10),
    "boost_target": (0, 30),
    "afr_target": (10.0, 16.0),
    "rev_limit": (5000, 8000),
}


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def normalize_tune_updates(updates):
    """Clamp and sanitize runtime tune updates."""
    normalized = {}
    for key, value in updates.items():
        if key == "mode":
            normalized[key] = str(value)[:32]
            continue

        if key not in TUNE_LIMITS:
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue

        min_value, max_value = TUNE_LIMITS[key]
        numeric_value = clamp(numeric_value, min_value, max_value)
        normalized[key] = int(numeric_value) if key == "rev_limit" else round(numeric_value, 1)

    return normalized


class TwinBrainUpdater:
    """Dual-lane adaptive monitor for live tune analysis and safety changes."""

    def __init__(self):
        self.agent = AITuningAgent()
        self.cooldown_seconds = 1.0
        self.last_adjustment_at = 0
        self.state = self._build_state()

    def _build_state(self, **overrides):
        state = {
            "status": "standby",
            "safety_brain": "Monitoring for live corrections",
            "analysis_brain": "TWINBRAIN analysis idle until engine start",
            "rampack_module": "Mini PCI Rampack standing by",
            "last_adjustment": "No live adjustments applied yet",
            "adjustments": {},
            "reasons": [],
        }
        state.update(overrides)
        return state

    def reset(self):
        self.last_adjustment_at = 0
        self.state = self._build_state()

    def process(self, vehicle, safety_status):
        telemetry = vehicle.telemetry
        tune = vehicle.tune
        adaptation = self.agent.monitor_and_adapt(tune, telemetry, safety_status)

        analysis_brain = self._analyze_headroom(telemetry, tune, safety_status)
        safety_brain = "Safety lane stable"
        status = "tracking"
        applied_adjustments = {}
        reasons = adaptation["reasons"]

        if safety_status["critical"]:
            status = "critical"
            safety_brain = "Safety lane in critical response mode"
        elif adaptation["adjustments_needed"]:
            status = "adapting"
            safety_brain = "Safety lane preparing live parameter correction"

        if adaptation["adjustments_needed"] and time.time() - self.last_adjustment_at >= self.cooldown_seconds:
            normalized_updates = normalize_tune_updates(adaptation["adjustments"])
            applied_adjustments = {
                key: value
                for key, value in normalized_updates.items()
                if tune.get(key) != value
            }
            if applied_adjustments:
                vehicle.tune.update(applied_adjustments)
                self.last_adjustment_at = time.time()
                status = "adapting"
                safety_brain = "Safety lane applied live adjustment"

        last_adjustment = "No update required"
        if applied_adjustments:
            adjustment_text = ", ".join(f"{key}={value}" for key, value in applied_adjustments.items())
            last_adjustment = f"Mini PCI Rampack applied: {adjustment_text}"
        elif adaptation["adjustments_needed"]:
            last_adjustment = "TwinBrain queued a change and is respecting cooldown"

        self.state = self._build_state(
            status=status,
            safety_brain=safety_brain,
            analysis_brain=analysis_brain,
            rampack_module="Mini PCI Rampack linked for on-the-fly parameter updates",
            last_adjustment=last_adjustment,
            adjustments=applied_adjustments,
            reasons=reasons,
        )
        return self.state

    def _analyze_headroom(self, telemetry, tune, safety_status):
        if safety_status["critical"]:
            return "Analysis lane locked to protection-first monitoring"

        throttle = telemetry.get("throttle_position", 0)
        boost = telemetry.get("boost", 0)
        target_boost = tune.get("boost_target", 0)
        iat = telemetry.get("iat", 0)
        knock_count = telemetry.get("knock_count", 0)

        if throttle > 70 and boost < target_boost - 2 and iat < 130 and knock_count == 0:
            return "Analysis lane sees thermal headroom for quicker boost response"
        if throttle < 20 and telemetry.get("afr", 14.7) < tune.get("afr_target", 14.7):
            return "Analysis lane recommends leaner light-load trims for faster transient response"
        return "Analysis lane sees stable operating window for live tuning"

class VehicleSimulator:
    """Simulates realistic vehicle telemetry data"""
    
    def __init__(self):
        self.running = False
        self.engine_on = False
        
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
            
        # Boost calculation (turbo)
        if self.throttle_input > 30 and self.telemetry["rpm"] > 2500:
            boost_target = (self.throttle_input / 100) * self.tune.get("boost_target", 12)
            self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.05
        else:
            self.telemetry["boost"] *= 0.9  # Boost decay
            
        self.telemetry["boost"] = max(0, self.telemetry["boost"])
        self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # AFR calculation (richer under load)
        base_afr = self.tune["afr_target"]
        if self.throttle_input > 70 and self.telemetry["boost"] > 5:
            target_afr = 11.5  # Rich for power/safety
        elif self.throttle_input < 20:
            target_afr = 15.5  # Lean for economy
        else:
            target_afr = base_afr
            
        self.telemetry["afr"] += (target_afr - self.telemetry["afr"]) * 0.1
        self.telemetry["lambda"] = self.telemetry["afr"] / 14.7
        
        # Temperature simulations
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / 7000)
        
        # Engine coolant temp
        target_ect = 180 + (load_factor * 30)
        self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp
        target_oil = 180 + (load_factor * 50)
        self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp
        target_iat = 75 + (self.telemetry["boost"] * 8)  # Heat from compression
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp
        target_egt = 800 + (load_factor * 600) + (self.telemetry["boost"] * 20)
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure
        rpm_factor = self.telemetry["rpm"] / 1000
        self.telemetry["oil_pressure"] = 10 + (rpm_factor * 10)
        
        # Knock detection (simulated - more likely with aggressive timing/lean AFR)
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
twinbrain = TwinBrainUpdater()

def telemetry_thread():
    """Background thread for telemetry updates"""
    while True:
        if vehicle.engine_on:
            vehicle.update()
            safety = vehicle.check_safety()
            twinbrain_state = twinbrain.process(vehicle, safety)
            
            data = {
                "telemetry": vehicle.telemetry,
                "tune": vehicle.tune,
                "safety": safety,
                "twinbrain": twinbrain_state,
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
    twinbrain.reset()
    return jsonify({"status": "started", "rpm": vehicle.telemetry["rpm"]})

@app.route('/api/engine/stop', methods=['POST'])
def stop_engine():
    vehicle.stop()
    twinbrain.reset()
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
    
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/tune/custom', methods=['POST'])
def set_custom_tune():
    data = request.json or {}
    normalized_updates = normalize_tune_updates(data)
    if "mode" in data:
        normalized_updates["mode"] = str(data["mode"])[:32]
    vehicle.tune.update(normalized_updates)
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "engine_on": vehicle.engine_on,
        "telemetry": vehicle.telemetry,
        "tune": vehicle.tune,
        "engine_config": vehicle.engine_config,
        "twinbrain": twinbrain.state
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
