# 🏎️ NATOS Quick Start Guide

## ⚠️ CRITICAL SAFETY WARNING

**THIS IS A SIMULATION TOOL FOR EDUCATIONAL PURPOSES ONLY**

DO NOT use on actual vehicles without:
- Professional tuning certification
- Dyno testing equipment  
- Comprehensive insurance
- Legal compliance verification

---

## 🚀 Getting Started

### Method 1: Web Dashboard (Recommended)

```bash
cd natos-system
./start.sh
```

Then open your browser to: **http://localhost:5000**

### Method 2: Interactive Demo

```bash
cd natos-system
python demo.py
```

Select from the menu to explore individual features.

---

## 🎮 Using the Web Dashboard

### 1. Start the Engine

Click **"Start Engine"** in the Engine Control panel.

You'll see:
- RPM jump to idle (~850)
- Oil pressure increase
- All telemetry activate

### 2. Select a Tuning Mode

**STOCK Mode** (Default)
- Safe for all conditions
- Factory parameters
- No risk

**ECONOMY Mode**
- Best fuel efficiency
- Reduced performance
- Ideal for daily driving

**PERFORMANCE Mode**
- ⚠️ Requires premium fuel
- Higher boost (18 PSI)
- Aggressive timing
- Rich AFR for power

**MODIFIED Mode**  
- ⚠️⚠️ WARNING: Extreme risk without upgrades
- Requires forged internals
- Very high boost (22 PSI)
- Track use only

### 3. Monitor Telemetry

**Green Cards** = Normal operation
**Yellow Border** = Warning condition
**Red Border (Pulsing)** = Critical - take action!

Key parameters to watch:
- **Coolant Temp**: Should stay < 220°F
- **Oil Pressure**: Should be 10+ PSI at RPM
- **Knock Count**: Should stay at 0
- **AFR**: Should be 11.5-15.0 depending on load

### 4. Watch the Charts

**RPM & Boost History**
- Green line = RPM
- Orange line = Boost pressure

**Temperature Monitor**
- Blue = Coolant
- Yellow = Oil  
- Red = Exhaust

**AFR & Lambda**
- Shows fuel mixture over time

**Power Parameters**
- Throttle position
- Ignition timing

### 5. Safety Alerts

The alert panel shows:
- ✅ Green = All systems normal
- ⚠️ Yellow warnings = Monitor situation
- 🚨 Red critical alerts = Immediate action required

---

## 🤖 AI Tuning Features

### Research Engine (Button)

The AI would research:
- Your specific engine specs
- Known modifications that work
- Common failure points
- Professional tuning data

### Optimize Tune (Button)

AI analyzes:
- Your driving patterns
- Temperature trends
- Knock events
- Performance metrics

Then suggests optimal tune adjustments.

---

## 📊 Understanding the Numbers

### RPM (Revolutions Per Minute)
- Idle: ~850
- Normal driving: 2000-4000
- Performance: 4000-6500
- Redline: 7000+ (varies by tune)

### Boost Pressure (PSI)
- Vacuum (off throttle): 0 PSI
- Part throttle: 3-8 PSI
- Full throttle: 12-22 PSI (depends on mode)

### AFR (Air/Fuel Ratio)
- Stoichiometric: 14.7:1 (chemically perfect)
- Economy: 15.0-15.5:1 (lean)
- Normal: 13.5-14.5:1
- Power: 11.5-12.5:1 (rich)
- Too rich: <11.0:1 (carbon buildup)
- Too lean: >15.0:1 under boost (engine damage!)

### Temperatures
- Coolant: 180-210°F normal, >220°F warning
- Oil: 180-240°F normal, >260°F warning  
- Intake: 70-120°F normal, >140°F warning
- Exhaust: 800-1400°F normal, >1600°F critical

### Ignition Timing
- More advance = more power (until knock)
- Typical: 10-20° BTDC (Before Top Dead Center)
- Retarded under boost for safety

---

## 🔧 Common Scenarios

### Scenario: Knock Detected

**Symptoms:**
- Knock count increases
- Timing automatically retards

**AI Response:**
- Reduces ignition timing (-2°)
- Lowers boost target (-2 PSI)
- Enrichens fuel mixture

**User Action:**
- Use higher octane fuel
- Check for carbon buildup
- Reduce boost if continuing

### Scenario: High Temperatures

**Symptoms:**
- Coolant >220°F
- Oil >260°F

**AI Response:**
- Enrichens mixture (adds fuel for cooling)
- May reduce boost
- Issues warning

**User Action:**
- Reduce load (less throttle)
- Check coolant level
- Ensure radiator airflow
- Let engine cool

### Scenario: Lean AFR Under Boost

**Symptoms:**
- AFR >13.5 with high boost
- Extremely dangerous!

**AI Response:**
- IMMEDIATE fuel addition
- Critical alert
- May reduce boost

**User Action:**
- Reduce throttle immediately
- Check fuel system
- This can destroy engines!

---

## 🎯 Tuning Tips

### For Daily Driving
- Use STOCK or ECONOMY mode
- Watch temperatures in traffic
- Regular oil changes crucial
- Use manufacturer recommended fuel

### For Performance
- PERFORMANCE mode only with premium fuel
- Monitor knock count religiously  
- Keep intake temps low
- Watch oil temperature on track

### For Modified Engines
- MODIFIED mode requires upgrades:
  - Forged pistons & rods
  - Upgraded turbo
  - Better intercooler
  - High-flow fuel system
- Always dyno tune first
- Monitor everything closely

---

## 🛠️ Technical Details

### Update Rate
- Telemetry: 10 Hz (every 100ms)
- Charts: Real-time
- AI monitoring: Continuous

### Simulated Physics
- Realistic turbo spool dynamics
- Thermal modeling with inertia
- Load-based AFR calculation
- Knock probability modeling

### Safety Systems
- Knock detection
- Over-boost protection
- Temperature monitoring
- AFR safety bounds
- Oil pressure critical alerts

---

## 📱 File Structure

```
natos-system/
├── app.py              # Main Flask server
├── ai_tuner.py         # AI tuning engine
├── demo.py             # Interactive demo script
├── requirements.txt    # Python dependencies
├── start.sh            # Quick start script
├── README.md           # Full documentation
└── templates/
    └── dashboard.html  # Web interface
```

---

## 🐛 Troubleshooting

### Server won't start
```bash
pip install -r requirements.txt
python app.py
```

### Dashboard not loading
- Check server is running: `ps aux | grep app.py`
- Try http://127.0.0.1:5000
- Check firewall settings

### Charts not updating
- Refresh browser (Ctrl+F5)
- Check browser console for errors
- Ensure JavaScript enabled

---

## 📚 Learning Resources

### Tuning Fundamentals
- AFR basics and stoichiometry
- Ignition timing theory
- Turbo dynamics
- Engine thermal management

### Advanced Topics
- Volumetric efficiency
- Detonation mechanics  
- Fuel octane requirements
- Boost control strategies

### Safety
- Knock detection methods
- Temperature limits
- Failure mode analysis
- Emergency procedures

---

## 🎓 Next Steps

1. **Explore the demo**: Run `python demo.py`
2. **Start the dashboard**: Run `./start.sh`
3. **Read the README**: Complete technical documentation
4. **Experiment safely**: Try different modes in simulation
5. **Learn the theory**: Understand what each parameter does

---

## ⚡ Pro Tips

- Start with STOCK mode and observe normal behavior
- Watch how boost builds with throttle and RPM
- Notice AFR changes with load
- See timing retard with boost increase
- Monitor temperature trends during hard driving
- Pay attention to knock events
- Understand safety alert triggers

---

## 🎬 Demo Scenarios

The `demo.py` script includes:

1. **Engine Research** - How AI finds engine specs
2. **Driving Analysis** - Pattern recognition
3. **Tune Generation** - AI creates custom tune
4. **Adaptive Tuning** - Real-time adjustments
5. **Safety Systems** - Protection mechanisms

Run each one to understand NATOS capabilities!

---

## 📞 Support

This is an educational prototype. For real ECU tuning:

- Consult professional tuners
- Use dyno testing facilities
- Follow emissions regulations
- Get proper insurance
- Document all changes

---

**Remember: Simulation ≠ Reality**

Real engines have:
- Manufacturing tolerances
- Wear and tear
- Fuel quality variations
- Environmental factors
- Unexpected failure modes

**Always prioritize safety!** 🏎️💨

---

*NATOS - Neural Autonomous Tuning & Optimization System*
*Built for education, learning, and automotive engineering exploration*
