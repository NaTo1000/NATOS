# 🏎️ NATOS - AI-Powered ECU Tuning System

**N**eural **A**utonomous **T**uning & **O**ptimization **S**ystem

## ⚠️ CRITICAL WARNING

**THIS SOFTWARE IS FOR EDUCATIONAL AND SIMULATION PURPOSES ONLY**

- ❌ **DO NOT** use on actual vehicles without professional validation
- ❌ **DO NOT** deploy without extensive dyno testing
- ❌ **DO NOT** use in regions with strict emissions regulations
- ⚠️ Improper ECU tuning can cause:
  - Catastrophic engine failure
  - Fire hazards
  - Voided warranties
  - Legal liability
  - Insurance invalidation

**Any use of this software is at your own risk.**

---

## 🎯 Features

### Real-Time Telemetry Monitoring
- **Engine Parameters**: RPM, throttle position, gear selection
- **Boost Control**: Real-time boost pressure monitoring
- **Air/Fuel Ratio**: AFR and Lambda monitoring
- **Temperature Monitoring**: Coolant, oil, intake, exhaust temps
- **Pressure Monitoring**: Oil pressure, fuel pressure
- **Ignition System**: Timing advance, knock detection
- **Fuel System**: Injector duty cycle, fuel trim

### AI-Powered Tuning Modes

1. **Stock Mode**
   - Factory-safe parameters
   - Optimal reliability
   - Standard performance
   - Recommended for daily driving

2. **Economy Mode**
   - Fuel efficiency optimization
   - Lean AFR tuning
   - Reduced boost
   - Lower rev limit
   - Best for highway cruising

3. **Performance Mode**
   - Aggressive tuning
   - Higher boost targets
   - Rich AFR for power
   - Advanced timing
   - ⚠️ Requires premium fuel

4. **Modified Mode**
   - Maximum performance
   - For upgraded engines
   - High boost (20+ PSI)
   - Very rich AFR (11.5:1)
   - ⚠️ Requires forged internals

### Autonomous AI Drive Profiles

- **Aggressive AI**: Higher throttle behavior with stronger boost/timing bias
- **Mild AI**: Balanced autonomous control for general driving simulation
- **Eco AI**: Low-load control focused on reduced boost and efficiency

### Safety Systems

- **Knock Detection**: Automatic timing retardation
- **Temperature Protection**: Overheating warnings
- **Pressure Monitoring**: Oil pressure critical alerts
- **AFR Safety**: Rich/lean mixture warnings
- **Over-Boost Protection**: Automatic boost limiting
- **Rev Limiter**: Configurable RPM limits

### AI Capabilities (Framework)

- Engine specification research
- Driving pattern analysis
- Adaptive tune optimization
- Real-time safety monitoring
- Modification recommendations

---

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- pip package manager
- Modern web browser

### Quick Start

```bash
cd natos
chmod +x start.sh
./start.sh
```

Or manually:

```bash
pip install -r requirements.txt
python app.py
```

The dashboard will be available at: **http://localhost:5000**

---

## 📊 Dashboard Guide

### Control Panel

**Engine Control**
- **Start Engine**: Begin simulation
- **Stop Engine**: Stop all telemetry

**Tuning Mode**
- Select from 4 pre-configured modes
- ⚠️ Warning prompts for aggressive modes

**AI Tuning Agent** (Framework)
- Launch AI Tuner: Opens AI configuration
- Research Engine: Internet-based engine research
- Optimize Tune: AI-driven tune optimization

### Telemetry Display

**Primary Gauges**
- Large, color-coded displays
- Real-time updates (10 Hz)
- Warning states (yellow border)
- Critical states (red border, pulsing)

**Historical Charts**
- RPM & Boost History
- Temperature Monitor (coolant, oil, exhaust)
- AFR & Lambda tracking
- Power Parameters (throttle, timing)
- Real-time MAP vs AFR air-curve mapping with throttle-weighted points

**Motion Logging**
- Real-time full motion delta log (RPM, speed, throttle)
- Per-sample AI profile tags for autonomous behavior tracing

### Safety Alerts

- **Green**: No alerts - system nominal
- **Yellow**: Warning - monitor closely
- **Red**: Critical - immediate action required

---

## 🤖 AI Tuning Agent

### Research Engine

Gathers information about:
- Factory specifications
- Safe boost limits
- Recommended AFR ranges
- Common failure points
- Compatible modifications

### Analyze Driving Pattern

Monitors:
- Throttle usage patterns
- RPM range preferences
- Boost utilization
- Driving style classification

### Generate Optimal Tune

Creates custom tune based on:
- Engine specifications
- Driving patterns
- Installed modifications
- Safety priority level

### Adaptive Learning

Real-time adjustments for:
- Knock events (timing retardation)
- Temperature excursions (enrichment)
- Lean conditions under boost
- Critical safety events

---

## 🔧 Technical Architecture

### Backend (Python/Flask)

**app.py**
- Flask web server
- SocketIO for real-time communication
- Vehicle simulator with realistic physics
- RESTful API endpoints
- Safety monitoring system

**ai_tuner.py**
- AI agent framework
- Online research capabilities
- Pattern analysis algorithms
- Adaptive tuning logic

### Frontend (HTML/JavaScript)

**dashboard.html**
- Real-time telemetry display
- Chart.js for historical graphs
- SocketIO client for live updates
- Responsive design
- Warning/alert system

### Communication Protocol

- **WebSocket**: Real-time telemetry streaming
- **HTTP REST API**: Control commands
- **JSON**: Data serialization
- **10Hz Update Rate**: Smooth real-time monitoring

---

## 📡 API Reference

### Engine Control

**Start Engine**
```http
POST /api/engine/start
Response: {"status": "started", "rpm": 850}
```

**Stop Engine**
```http
POST /api/engine/stop
Response: {"status": "stopped"}
```

### Tuning Control

**Set Tuning Mode**
```http
POST /api/tune/mode
Body: {"mode": "stock|economy|performance|modified"}
Response: {"status": "success", "tune": {...}}
```

**Custom Tune**
```http
POST /api/tune/custom
Body: {
  "fuel_map_adjustment": 10,
  "timing_adjustment": 3,
  "boost_target": 18,
  "afr_target": 12.0,
  "rev_limit": 7200
}
Response: {"status": "success", "tune": {...}}
```

### Status Query

**Get Current Status**
```http
GET /api/status
Response: {
  "engine_on": true,
  "telemetry": {...},
  "tune": {...},
  "engine_config": {...},
  "autonomous_control": {...}
}
```

### Autonomous AI Control

**Get AI Control State**
```http
GET /api/ai/control
Response: {
  "status": "success",
  "autonomous_control": {"enabled": true, "profile": "mild"},
  "profiles": ["aggressive", "mild", "eco"]
}
```

**Set AI Control State**
```http
POST /api/ai/control
Body: {"profile": "aggressive|mild|eco", "enabled": true}
Response: {"status": "success", "autonomous_control": {...}}
```

### WebSocket Events

**Connect**
```javascript
socket.on('connection_response', (data) => {
  // {"status": "connected"}
});
```

**Telemetry Update** (10Hz)
```javascript
socket.on('telemetry_update', (data) => {
  // {
  //   "telemetry": {...},
  //   "tune": {...},
  //   "safety": {"warnings": [], "critical": []},
  //   "timestamp": "2026-02-02T..."
  // }
});
```

---

## 🎨 Customization

### Adding Custom Tune Modes

Edit `app.py`, add to `/api/tune/mode` endpoint:

```python
elif mode == 'custom_mode':
    vehicle.tune.update({
        "mode": "custom_mode",
        "fuel_map_adjustment": X,
        "timing_adjustment": Y,
        "boost_target": Z,
        "afr_target": A,
        "rev_limit": B,
    })
```

### Adjusting Safety Limits

Edit `VehicleSimulator.__init__()` in `app.py`:

```python
self.limits = {
    "max_ect": 230,      # Coolant temp (°F)
    "max_oil_temp": 280, # Oil temp (°F)
    "max_egt": 1600,     # Exhaust temp (°F)
    "max_knock": 5,      # Knock count
    "min_afr": 10.5,     # Minimum AFR
    "max_afr": 16.0,     # Maximum AFR
}
```

### Modifying Telemetry Update Rate

In `app.py`, `telemetry_thread()`:

```python
time.sleep(0.1)  # 10 Hz (change to 0.05 for 20Hz, etc.)
```

---

## 🔬 Simulation Details

### Engine Modeling

**Turbocharger Simulation**
- Spool dynamics based on RPM and throttle
- Heat generation from compression
- Boost decay when off-throttle

**Thermal Modeling**
- Coolant temperature with load-based heating
- Oil temperature with friction heating
- Intercooler heat transfer
- Exhaust gas temperature dynamics

**Fuel System**
- AFR calculation based on load
- Injector duty cycle simulation
- Lambda sensor output

**Ignition System**
- Base timing with boost compensation
- Knock detection probability
- Automatic timing retardation

### Physics Calculations

**RPM Response**
```python
target_rpm = idle + (throttle/100) * (redline - idle)
actual_rpm += (target_rpm - actual_rpm) * damping_factor
```

**Boost Calculation**
```python
if throttle > 30% and rpm > 2500:
    boost_target = (throttle/100) * max_boost
    boost += (boost_target - boost) * spool_rate
```

**Temperature Dynamics**
```python
load_factor = (throttle/100) * (rpm/redline)
target_temp = base_temp + (load_factor * max_delta)
temp += (target_temp - temp) * thermal_inertia
```

---

## 🚨 Safety Features

### Automatic Protection

1. **Knock Protection**
   - Detect knock events
   - Retard timing by 2°
   - Reduce boost by 2 PSI
   - Log event for analysis

2. **Temperature Protection**
   - Monitor coolant temp
   - Enrich mixture for cooling
   - Warn at 220°F
   - Critical at 230°F

3. **Lean Protection**
   - Monitor AFR under boost
   - Add fuel if AFR > 13.5
   - Critical alert if AFR > 15.0

4. **Oil Pressure Protection**
   - Monitor oil pressure
   - Emergency RPM limit if pressure < 10 PSI
   - Critical alert

### Warning Hierarchy

**Level 1: Informational** (Green)
- Normal operation
- No action needed

**Level 2: Warning** (Yellow)
- Monitor situation
- May require adjustment
- Not immediately dangerous

**Level 3: Critical** (Red)
- Immediate attention required
- Potential engine damage
- Reduce load or shut down

---

## 🔮 Future Enhancements

### Phase 2: AI Integration
- [ ] Real internet research via API
- [ ] LLM-powered tuning recommendations
- [ ] Natural language tune configuration
- [ ] Predictive maintenance alerts

### Phase 3: Hardware Integration
- [ ] OBD-II adapter support
- [ ] Direct CAN bus communication
- [ ] Real ECU flashing capability
- [ ] Wideband O2 sensor integration

### Phase 4: Advanced Features
- [ ] Data logging to disk
- [ ] Dyno chart overlay
- [ ] Tune comparison tool
- [ ] Cloud tune library
- [ ] Mobile app interface

### Phase 5: Professional Tools
- [ ] Multi-vehicle support
- [ ] Customer database
- [ ] Billing integration
- [ ] Tune version control
- [ ] Professional reporting

---

## 📚 Resources

### Tuning Fundamentals

**AFR (Air/Fuel Ratio)**
- Stoichiometric: 14.7:1 (gasoline)
- Rich for power: 11.5-12.5:1
- Lean for economy: 15.0-16.0:1
- Dangerously lean: >15.5:1 under boost

**Ignition Timing**
- More advance = more power (up to limit)
- Too much advance = knock/detonation
- Retard under boost for safety
- Typical range: 10-20° BTDC

**Boost Pressure**
- Stock turbos: 10-15 PSI
- Upgraded turbos: 15-25 PSI
- Requires supporting mods above 18 PSI
- 1 PSI ≈ 5-7% power gain

### Common Modifications

**Stage 1** (Stock Engine)
- ECU tune
- Intake/exhaust
- Boost controller
- +15-20% power

**Stage 2** (Mild Upgrades)
- Intercooler upgrade
- Fuel pump
- Injectors
- Exhaust
- +25-35% power

**Stage 3** (Built Engine)
- Forged internals
- Upgraded turbo
- Full fuel system
- Standalone ECU
- +50-100% power

---

## 🤝 Contributing

This is an educational project. Contributions welcome for:
- Improved physics simulation
- Better UI/UX design
- Additional tuning modes
- Safety enhancements
- Documentation improvements

---

## 📄 License

**Educational Use Only**

This software is provided for educational and research purposes. No warranty or guarantee is provided. The authors are not liable for any damages resulting from use of this software.

---

## 🙏 Acknowledgments

- Inspired by professional tuning platforms (HP Tuners, EcuTek, COBB)
- Physics modeling based on engine dynamics research
- Safety protocols from professional tuning guidelines

---

## 📞 Disclaimer

**REPEAT: THIS IS A SIMULATION TOOL FOR EDUCATIONAL PURPOSES**

Real ECU tuning requires:
- Professional tuning knowledge
- Dyno testing equipment
- Emissions compliance testing
- Insurance and liability coverage
- Professional certification

**Always consult with professional tuners before modifying any vehicle.**

---

Built with ❤️ for automotive enthusiasts and engineers

🏎️ **Drive Safe, Tune Smart** 🏎️
