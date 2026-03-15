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
import math
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'natos-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# LS-series engine profiles
LS_ENGINE_PROFILES = {
    "ls1": {
        "name": "LS1 (5.7L V8)",
        "displacement": 5.7,
        "cylinders": 8,
        "aspiration": "supercharged",
        "max_boost": 8.0,
        "redline": 6000,
        "stock_hp": 350,
        "torque": 365,
        "compression_ratio": 10.25,
        "bore_mm": 99.0,
        "stroke_mm": 92.0,
        "final_drive": 3.42,
        "tire_diameter_in": 26.0,
        "gear_ratios": [0, 2.66, 1.78, 1.30, 1.0, 0.74, 0.50],  # index 0=neutral, 1-6=gears
    },
    "ls2": {
        "name": "LS2 (6.0L V8)",
        "displacement": 6.0,
        "cylinders": 8,
        "aspiration": "supercharged",
        "max_boost": 10.0,
        "redline": 6500,
        "stock_hp": 400,
        "torque": 400,
        "compression_ratio": 10.9,
        "bore_mm": 101.6,
        "stroke_mm": 92.0,
        "final_drive": 3.73,
        "tire_diameter_in": 27.0,
        "gear_ratios": [0, 2.66, 1.78, 1.30, 1.0, 0.74, 0.50],
    },
    "ls3": {
        "name": "LS3 (6.2L V8)",
        "displacement": 6.2,
        "cylinders": 8,
        "aspiration": "supercharged",
        "max_boost": 12.0,
        "redline": 6600,
        "stock_hp": 430,
        "torque": 424,
        "compression_ratio": 10.7,
        "bore_mm": 103.25,
        "stroke_mm": 92.0,
        "final_drive": 3.73,
        "tire_diameter_in": 27.0,
        "gear_ratios": [0, 2.97, 2.07, 1.43, 1.0, 0.71, 0.57],
    },
}


class VehicleSimulator:
    """Simulates realistic vehicle telemetry data with LS-series engines,
    methanol/water injection, nitrous fogging, and wheel speed tracking."""
    
    def __init__(self):
        self.running = False
        self.engine_on = False
        
        # Active engine profile (default LS1)
        self.engine_profile = "ls1"
        self.engine_config = dict(LS_ENGINE_PROFILES["ls1"])
        
        # Current telemetry
        self.telemetry = {
            "rpm": 0,
            "speed": 0,
            "throttle_position": 0,
            "afr": 14.7,
            "map": 14.7,
            "boost": 0,
            "iat": 75,
            "ect": 180,
            "egt": 800,
            "oil_pressure": 0,
            "oil_temp": 180,
            "knock_count": 0,
            "gear": 0,
            "fuel_pressure": 58.0,  # LS-series fuel pressure (PSI)
            "lambda": 1.0,
            "ignition_timing": 25,  # LS engines run more timing
            "injector_duty": 15,
            "voltage": 14.2,
            # Wheel speed sensors (MPH per wheel)
            "wheel_speed_fl": 0,
            "wheel_speed_fr": 0,
            "wheel_speed_rl": 0,
            "wheel_speed_rr": 0,
            "wheel_slip": 0.0,  # % slip between engine speed and wheel speed
            "traction_control_active": False,
            # Methanol/water injection
            "meth_flow_rate": 0,  # cc/min
            "meth_pressure": 0,  # PSI
            "meth_tank_level": 100,  # %
            # Nitrous fogging
            "nitrous_flow_rate": 0,  # cc/min
            "nitrous_pressure": 0,  # PSI (bottle)
            "nitrous_bottle_temp": 75,  # F
            "nitrous_bottle_level": 100,  # %
        }
        
        # Tuning parameters
        self.tune = {
            "mode": "stock",
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": self.engine_config["max_boost"] * 0.6,
            "afr_target": 14.7,
            "rev_limit": self.engine_config["redline"],
        }
        
        # Methanol/water injection system
        self.meth_injection = {
            "enabled": False,
            "active": False,  # currently injecting
            "boost_activation_psi": 3.0,  # activate above this boost
            "flow_rate_max": 1000,  # cc/min max
            "mix_ratio": 50,  # % methanol (rest is water)
            "iat_reduction": 40,  # degrees F cooling at full flow
            "octane_boost": 5,  # effective octane increase
        }
        
        # Nitrous fogging system
        self.nitrous = {
            "enabled": False,
            "active": False,  # currently spraying
            "mode": "wet",  # wet or dry
            "shot_size_hp": 100,  # HP equivalent shot
            "activation_rpm": 3000,  # min RPM to activate
            "activation_throttle": 80,  # min throttle % to activate
            "bottle_pressure_full": 900,  # PSI when full at 75F
            "fuel_enrichment": 12,  # % extra fuel for wet shot
        }
        
        # Safety limits
        self.limits = {
            "max_ect": 230,
            "max_oil_temp": 280,
            "max_egt": 1600,
            "max_knock": 5,
            "min_afr": 10.5,
            "max_afr": 16.0,
            "max_slip": 15.0,  # % slip before traction warning
        }
        
        # Driving simulation
        self.throttle_input = 0
        self.brake_input = 0
        self.target_gear = 1
        
    def set_engine_profile(self, profile_name):
        """Switch to a different LS engine profile"""
        if profile_name in LS_ENGINE_PROFILES:
            self.engine_profile = profile_name
            self.engine_config = dict(LS_ENGINE_PROFILES[profile_name])
            # Update rev limit to match engine
            self.tune["rev_limit"] = self.engine_config["redline"]
            return True
        return False
        
    def start(self):
        """Start the engine"""
        self.engine_on = True
        self.telemetry["rpm"] = 800 + random.randint(-50, 50)
        self.telemetry["oil_pressure"] = 30 + random.randint(-2, 2)
        self.telemetry["gear"] = 0
        
    def stop(self):
        """Stop the engine"""
        self.engine_on = False
        self.telemetry["rpm"] = 0
        self.telemetry["oil_pressure"] = 0
        self.telemetry["boost"] = 0
        self.telemetry["speed"] = 0
        self.telemetry["wheel_speed_fl"] = 0
        self.telemetry["wheel_speed_fr"] = 0
        self.telemetry["wheel_speed_rl"] = 0
        self.telemetry["wheel_speed_rr"] = 0
        self.telemetry["wheel_slip"] = 0
        self.telemetry["traction_control_active"] = False
        self.telemetry["meth_flow_rate"] = 0
        self.telemetry["meth_pressure"] = 0
        self.telemetry["nitrous_flow_rate"] = 0
        self.telemetry["nitrous_pressure"] = 0
        self.meth_injection["active"] = False
        self.nitrous["active"] = False
        
    def _calculate_wheel_speed(self):
        """Calculate individual wheel speeds from engine RPM and drivetrain.
        Returns theoretical vehicle speed in MPH from wheel rotation."""
        if self.telemetry["gear"] == 0:
            return 0.0
        gear = self.telemetry["gear"]
        gear_ratios = self.engine_config.get("gear_ratios", [0, 2.66, 1.78, 1.30, 1.0, 0.74, 0.50])
        if gear >= len(gear_ratios):
            gear = len(gear_ratios) - 1
        gear_ratio = gear_ratios[gear]
        final_drive = self.engine_config.get("final_drive", 3.42)
        tire_dia = self.engine_config.get("tire_diameter_in", 26.0)
        tire_circumference_ft = (tire_dia * math.pi) / 12.0
        # driveshaft RPM = engine RPM / gear ratio
        # axle RPM = driveshaft RPM / final drive
        axle_rpm = self.telemetry["rpm"] / (gear_ratio * final_drive)
        # speed = axle_rpm * tire_circumference * 60 / 5280
        speed_mph = (axle_rpm * tire_circumference_ft * 60) / 5280.0
        return max(0.0, speed_mph)
        
    def _update_wheel_speeds(self, theoretical_speed):
        """Update individual wheel speed sensors with realistic variation."""
        if theoretical_speed < 1.0:
            self.telemetry["wheel_speed_fl"] = 0
            self.telemetry["wheel_speed_fr"] = 0
            self.telemetry["wheel_speed_rl"] = 0
            self.telemetry["wheel_speed_rr"] = 0
            self.telemetry["wheel_slip"] = 0
            self.telemetry["traction_control_active"] = False
            return
            
        # Front wheels track actual vehicle speed (driven by road)
        base_front = theoretical_speed
        self.telemetry["wheel_speed_fl"] = base_front + random.uniform(-0.3, 0.3)
        self.telemetry["wheel_speed_fr"] = base_front + random.uniform(-0.3, 0.3)
        
        # Rear wheels (driven) can spin faster under power
        power_factor = (self.throttle_input / 100.0) * (self.telemetry["boost"] / max(self.engine_config["max_boost"], 1))
        # Add nitrous contribution to wheelspin
        if self.nitrous["active"]:
            power_factor += 0.3
        slip_factor = 1.0 + (power_factor * 0.08)
        rear_speed = theoretical_speed * slip_factor
        self.telemetry["wheel_speed_rl"] = rear_speed + random.uniform(-0.5, 0.5)
        self.telemetry["wheel_speed_rr"] = rear_speed + random.uniform(-0.5, 0.5)
        
        # Calculate slip percentage
        avg_front = (self.telemetry["wheel_speed_fl"] + self.telemetry["wheel_speed_fr"]) / 2.0
        avg_rear = (self.telemetry["wheel_speed_rl"] + self.telemetry["wheel_speed_rr"]) / 2.0
        if avg_front > 1.0:
            self.telemetry["wheel_slip"] = max(0, ((avg_rear - avg_front) / avg_front) * 100.0)
        else:
            self.telemetry["wheel_slip"] = 0
        
        self.telemetry["traction_control_active"] = self.telemetry["wheel_slip"] > self.limits["max_slip"]
    
    def _update_meth_injection(self):
        """Update methanol/water injection system state."""
        if not self.meth_injection["enabled"] or self.telemetry["meth_tank_level"] <= 0:
            self.meth_injection["active"] = False
            self.telemetry["meth_flow_rate"] = 0
            self.telemetry["meth_pressure"] = 0
            return
            
        boost = self.telemetry["boost"]
        if boost >= self.meth_injection["boost_activation_psi"]:
            self.meth_injection["active"] = True
            # Flow rate proportional to boost above activation threshold
            boost_range = self.engine_config["max_boost"] - self.meth_injection["boost_activation_psi"]
            if boost_range > 0:
                flow_pct = min(1.0, (boost - self.meth_injection["boost_activation_psi"]) / boost_range)
            else:
                flow_pct = 1.0
            self.telemetry["meth_flow_rate"] = flow_pct * self.meth_injection["flow_rate_max"]
            self.telemetry["meth_pressure"] = 80 + (flow_pct * 40)  # 80-120 PSI
            
            # Reduce IAT based on flow rate (major benefit of meth injection)
            iat_cooling = (flow_pct * self.meth_injection["iat_reduction"])
            self.telemetry["iat"] -= iat_cooling * 0.1  # gradual effect
            
            # Consume tank
            self.telemetry["meth_tank_level"] -= 0.01 * flow_pct
            self.telemetry["meth_tank_level"] = max(0, self.telemetry["meth_tank_level"])
        else:
            self.meth_injection["active"] = False
            self.telemetry["meth_flow_rate"] *= 0.8  # decay
            self.telemetry["meth_pressure"] *= 0.8
    
    def _update_nitrous(self):
        """Update nitrous fogging system state."""
        if not self.nitrous["enabled"] or self.telemetry["nitrous_bottle_level"] <= 0:
            self.nitrous["active"] = False
            self.telemetry["nitrous_flow_rate"] = 0
            self.telemetry["nitrous_pressure"] = 0
            return
            
        rpm = self.telemetry["rpm"]
        throttle = self.throttle_input
        
        # Bottle pressure varies with temperature
        temp = self.telemetry["nitrous_bottle_temp"]
        level = self.telemetry["nitrous_bottle_level"] / 100.0
        self.telemetry["nitrous_pressure"] = self.nitrous["bottle_pressure_full"] * level * (temp / 75.0)
        
        if rpm >= self.nitrous["activation_rpm"] and throttle >= self.nitrous["activation_throttle"]:
            self.nitrous["active"] = True
            # Flow rate based on shot size
            hp_factor = self.nitrous["shot_size_hp"] / 100.0
            self.telemetry["nitrous_flow_rate"] = hp_factor * 500  # cc/min approx
            
            # Nitrous cools intake charge significantly
            self.telemetry["iat"] -= 15 * 0.1  # spray cooling
            
            # Consume bottle
            self.telemetry["nitrous_bottle_level"] -= 0.05 * hp_factor
            self.telemetry["nitrous_bottle_level"] = max(0, self.telemetry["nitrous_bottle_level"])
            
            # Bottle cools as nitrous is used
            self.telemetry["nitrous_bottle_temp"] -= 0.1
        else:
            self.nitrous["active"] = False
            self.telemetry["nitrous_flow_rate"] *= 0.7  # decay
            # Bottle temp slowly returns to ambient
            self.telemetry["nitrous_bottle_temp"] += (75 - self.telemetry["nitrous_bottle_temp"]) * 0.01
        
    def update(self):
        """Update telemetry based on driving conditions"""
        if not self.engine_on:
            return
            
        redline = self.engine_config.get("redline", 6000)
        
        # Simulate throttle input (random driving pattern)
        if random.random() < 0.05:
            self.throttle_input = random.uniform(0, 100)
            
        self.telemetry["throttle_position"] = self.throttle_input
        
        # RPM calculation (scaled to LS V8 characteristics)
        target_rpm = 700 + (self.throttle_input / 100) * (redline - 800)
        self.telemetry["rpm"] += (target_rpm - self.telemetry["rpm"]) * 0.1
        # Nitrous adds RPM acceleration
        if self.nitrous["active"]:
            nos_rpm_boost = self.nitrous["shot_size_hp"] * 0.5
            self.telemetry["rpm"] += nos_rpm_boost * 0.02
        self.telemetry["rpm"] = max(700, min(self.tune["rev_limit"], self.telemetry["rpm"]))
        
        # Calculate theoretical speed from engine RPM through drivetrain
        theoretical_speed = self._calculate_wheel_speed()
        self.telemetry["speed"] = theoretical_speed
        
        # Update individual wheel speeds
        self._update_wheel_speeds(theoretical_speed)
        
        # Auto gear shifting (LS engines with 6-speed)
        gear_ratios = self.engine_config.get("gear_ratios", [0, 2.66, 1.78, 1.30, 1.0, 0.74, 0.50])
        max_gear = len(gear_ratios) - 1
        if self.telemetry["rpm"] > (redline - 500) and self.telemetry["gear"] < max_gear:
            self.telemetry["gear"] += 1
        elif self.telemetry["rpm"] < 1800 and self.telemetry["gear"] > 1:
            self.telemetry["gear"] -= 1
        elif self.telemetry["gear"] == 0 and self.throttle_input > 5:
            self.telemetry["gear"] = 1
            
        # Boost calculation (supercharger - instant response, no spool)
        if self.throttle_input > 15 and self.telemetry["rpm"] > 1500:
            boost_target = (self.throttle_input / 100) * self.tune.get("boost_target", self.engine_config["max_boost"])
            # Supercharger boost is more linear with RPM than turbo
            rpm_factor = min(1.0, self.telemetry["rpm"] / 4000.0)
            boost_target *= rpm_factor
            # Supercharger responds faster than turbo (0.15 vs 0.05)
            self.telemetry["boost"] += (boost_target - self.telemetry["boost"]) * 0.15
        else:
            self.telemetry["boost"] *= 0.85
            
        self.telemetry["boost"] = max(0, self.telemetry["boost"])
        self.telemetry["map"] = 14.7 + self.telemetry["boost"]
        
        # Methanol/water injection update
        self._update_meth_injection()
        
        # Nitrous fogging update
        self._update_nitrous()
        
        # AFR calculation (richer under load, enriched with nitrous)
        base_afr = self.tune["afr_target"]
        if self.throttle_input > 70 and self.telemetry["boost"] > 5:
            target_afr = 11.5
        elif self.throttle_input < 20:
            target_afr = 14.7
        else:
            target_afr = base_afr
            
        # Nitrous wet shot enrichment
        if self.nitrous["active"] and self.nitrous["mode"] == "wet":
            target_afr -= (self.nitrous["fuel_enrichment"] / 100.0) * 3.0
        # Meth injection allows leaner due to octane boost
        if self.meth_injection["active"]:
            target_afr += 0.3
            
        self.telemetry["afr"] += (target_afr - self.telemetry["afr"]) * 0.1
        self.telemetry["lambda"] = self.telemetry["afr"] / 14.7
        
        # Temperature simulations (LS V8 thermal model)
        load_factor = (self.throttle_input / 100) * (self.telemetry["rpm"] / redline)
        
        # Engine coolant temp (LS engines run hot under boost)
        target_ect = 185 + (load_factor * 35)
        if self.nitrous["active"]:
            target_ect += 10  # Extra heat from added power
        self.telemetry["ect"] += (target_ect - self.telemetry["ect"]) * 0.01
        
        # Oil temp
        target_oil = 185 + (load_factor * 55)
        self.telemetry["oil_temp"] += (target_oil - self.telemetry["oil_temp"]) * 0.008
        
        # Intake air temp (meth/water reduces this significantly)
        target_iat = 85 + (self.telemetry["boost"] * 10)
        self.telemetry["iat"] += (target_iat - self.telemetry["iat"]) * 0.05
        
        # Exhaust gas temp (nitrous increases EGT significantly)
        target_egt = 900 + (load_factor * 500) + (self.telemetry["boost"] * 25)
        if self.nitrous["active"]:
            target_egt += self.nitrous["shot_size_hp"] * 1.5
        self.telemetry["egt"] += (target_egt - self.telemetry["egt"]) * 0.05
        
        # Oil pressure (LS engines - higher baseline)
        rpm_factor = self.telemetry["rpm"] / 1000
        self.telemetry["oil_pressure"] = 25 + (rpm_factor * 8)
        
        # Knock detection (more likely with high boost, lean AFR, no meth)
        knock_probability = 0
        if self.telemetry["afr"] > 13.5 and self.telemetry["boost"] > 6:
            knock_probability = 0.02
        if self.tune["timing_adjustment"] > 3:
            knock_probability += 0.01
        # Meth injection reduces knock risk
        if self.meth_injection["active"]:
            knock_probability *= 0.3
        # Nitrous can increase knock if AFR isn't right
        if self.nitrous["active"] and self.telemetry["afr"] > 12.5:
            knock_probability += 0.03
            
        if random.random() < knock_probability:
            self.telemetry["knock_count"] += 1
            self.telemetry["ignition_timing"] -= 2
            
        # Ignition timing (LS engines run more timing than I4)
        base_timing = 25 + self.tune["timing_adjustment"]
        if self.telemetry["boost"] > 5:
            base_timing -= (self.telemetry["boost"] - 5) * 0.8
        # Meth allows more timing
        if self.meth_injection["active"]:
            base_timing += 2
        # Nitrous requires less timing
        if self.nitrous["active"]:
            base_timing -= 4
        self.telemetry["ignition_timing"] = base_timing
        
        # Injector duty cycle (LS engines with larger injectors)
        duty = 15 + (load_factor * 55) + (self.tune["fuel_map_adjustment"])
        if self.nitrous["active"]:
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
        
        # Wheel slip / traction warning
        if self.telemetry["wheel_slip"] > self.limits["max_slip"]:
            warnings.append(f"WARNING: Wheel slip {self.telemetry['wheel_slip']:.1f}% - Traction control active!")
        
        # Meth tank low
        if self.meth_injection["enabled"] and self.telemetry["meth_tank_level"] < 10:
            warnings.append(f"WARNING: Meth/Water tank low ({self.telemetry['meth_tank_level']:.0f}%)!")
        if self.meth_injection["enabled"] and self.telemetry["meth_tank_level"] <= 0:
            critical.append("CRITICAL: Meth/Water tank EMPTY - no injection protection!")
        
        # Nitrous bottle low
        if self.nitrous["enabled"] and self.telemetry["nitrous_bottle_level"] < 15:
            warnings.append(f"WARNING: Nitrous bottle low ({self.telemetry['nitrous_bottle_level']:.0f}%)!")
        if self.nitrous["enabled"] and self.telemetry["nitrous_bottle_level"] <= 0:
            critical.append("CRITICAL: Nitrous bottle EMPTY!")
        
        # Nitrous + lean = danger
        if self.nitrous["active"] and self.telemetry["afr"] > 13.0:
            critical.append(f"CRITICAL: Lean AFR {self.telemetry['afr']:.1f} with nitrous active - detonation risk!")
            
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
                "engine_config": vehicle.engine_config,
                "meth_injection": vehicle.meth_injection,
                "nitrous": vehicle.nitrous,
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

@app.route('/api/engine/profile', methods=['POST'])
def set_engine_profile():
    """Switch LS engine profile (ls1, ls2, ls3)"""
    data = request.json
    profile = data.get('profile', 'ls1')
    if vehicle.set_engine_profile(profile):
        return jsonify({
            "status": "success",
            "profile": profile,
            "engine_config": vehicle.engine_config
        })
    return jsonify({"status": "error", "message": "Unknown profile"}), 400

@app.route('/api/engine/profiles', methods=['GET'])
def get_engine_profiles():
    """List available LS engine profiles"""
    return jsonify({"profiles": LS_ENGINE_PROFILES})

@app.route('/api/meth/toggle', methods=['POST'])
def toggle_meth_injection():
    """Enable or disable methanol/water injection"""
    data = request.get_json(force=True, silent=True) or {}
    vehicle.meth_injection["enabled"] = data.get("enabled", not vehicle.meth_injection["enabled"])
    if not vehicle.meth_injection["enabled"]:
        vehicle.meth_injection["active"] = False
        vehicle.telemetry["meth_flow_rate"] = 0
        vehicle.telemetry["meth_pressure"] = 0
    return jsonify({"status": "success", "meth_injection": vehicle.meth_injection})

@app.route('/api/meth/config', methods=['POST'])
def config_meth_injection():
    """Configure methanol/water injection parameters"""
    data = request.json
    allowed_keys = ["boost_activation_psi", "flow_rate_max", "mix_ratio"]
    for key in allowed_keys:
        if key in data:
            vehicle.meth_injection[key] = data[key]
    return jsonify({"status": "success", "meth_injection": vehicle.meth_injection})

@app.route('/api/meth/refill', methods=['POST'])
def refill_meth_tank():
    """Refill the methanol/water tank"""
    vehicle.telemetry["meth_tank_level"] = 100
    return jsonify({"status": "success", "meth_tank_level": 100})

@app.route('/api/nitrous/toggle', methods=['POST'])
def toggle_nitrous():
    """Enable or disable nitrous fogging system"""
    data = request.get_json(force=True, silent=True) or {}
    vehicle.nitrous["enabled"] = data.get("enabled", not vehicle.nitrous["enabled"])
    if not vehicle.nitrous["enabled"]:
        vehicle.nitrous["active"] = False
        vehicle.telemetry["nitrous_flow_rate"] = 0
    return jsonify({"status": "success", "nitrous": vehicle.nitrous})

@app.route('/api/nitrous/config', methods=['POST'])
def config_nitrous():
    """Configure nitrous fogging parameters"""
    data = request.json
    allowed_keys = ["mode", "shot_size_hp", "activation_rpm", "activation_throttle", "fuel_enrichment"]
    for key in allowed_keys:
        if key in data:
            vehicle.nitrous[key] = data[key]
    return jsonify({"status": "success", "nitrous": vehicle.nitrous})

@app.route('/api/nitrous/refill', methods=['POST'])
def refill_nitrous():
    """Refill the nitrous bottle"""
    vehicle.telemetry["nitrous_bottle_level"] = 100
    vehicle.telemetry["nitrous_bottle_temp"] = 75
    return jsonify({"status": "success", "nitrous_bottle_level": 100})

@app.route('/api/tune/mode', methods=['POST'])
def set_tune_mode():
    data = request.json
    mode = data.get('mode', 'stock')
    redline = vehicle.engine_config.get("redline", 6000)
    max_boost = vehicle.engine_config.get("max_boost", 8)
    
    if mode == 'stock':
        vehicle.tune.update({
            "mode": "stock",
            "fuel_map_adjustment": 0,
            "timing_adjustment": 0,
            "boost_target": max_boost * 0.6,
            "afr_target": 14.7,
            "rev_limit": redline,
        })
    elif mode == 'economy':
        vehicle.tune.update({
            "mode": "economy",
            "fuel_map_adjustment": -5,
            "timing_adjustment": 2,
            "boost_target": max_boost * 0.4,
            "afr_target": 15.2,
            "rev_limit": redline - 500,
        })
    elif mode == 'performance':
        vehicle.tune.update({
            "mode": "performance",
            "fuel_map_adjustment": 10,
            "timing_adjustment": 3,
            "boost_target": max_boost * 0.85,
            "afr_target": 12.5,
            "rev_limit": redline + 200,
        })
    elif mode == 'modified':
        vehicle.tune.update({
            "mode": "modified",
            "fuel_map_adjustment": 15,
            "timing_adjustment": 5,
            "boost_target": max_boost,
            "afr_target": 11.8,
            "rev_limit": redline + 500,
        })
    
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/tune/custom', methods=['POST'])
def set_custom_tune():
    data = request.json
    redline = vehicle.engine_config.get("redline", 6000)
    max_boost = vehicle.engine_config.get("max_boost", 12)
    # Validate and clamp values to safe ranges
    bounds = {
        "fuel_map_adjustment": (-20, 25),
        "timing_adjustment": (-10, 10),
        "boost_target": (0, max_boost * 1.5),
        "afr_target": (10.0, 16.0),
        "rev_limit": (3000, redline + 1000),
    }
    for key, (lo, hi) in bounds.items():
        if key in data:
            vehicle.tune[key] = max(lo, min(hi, float(data[key])))
    if "mode" in data and isinstance(data["mode"], str):
        vehicle.tune["mode"] = data["mode"][:20]
    return jsonify({"status": "success", "tune": vehicle.tune})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "engine_on": vehicle.engine_on,
        "engine_profile": vehicle.engine_profile,
        "telemetry": vehicle.telemetry,
        "tune": vehicle.tune,
        "engine_config": vehicle.engine_config,
        "meth_injection": vehicle.meth_injection,
        "nitrous": vehicle.nitrous
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
    print("🏁 Engine Profiles: LS1 (5.7L) | LS2 (6.0L) | LS3 (6.2L)")
    print("💉 Systems: Boost Control | Meth/Water Injection | Nitrous Fogging")
    print("🔄 Real-time: Wheel Speed → Engine Speed Correlation")
    print("=" * 60)
    print("\n🌐 Starting web server on http://localhost:5000")
    print("\n📊 Dashboard will open automatically...\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
