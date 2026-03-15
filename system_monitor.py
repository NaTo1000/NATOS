"""
NATOS System Monitor
Monitors system BIOS settings, CPU/GPU temperature, voltage rails,
fan speeds, and overall system health.
Uses psutil when available, falls back to simulated values.
"""

import random
import platform
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemMonitor:
    """Monitors system BIOS, temperatures, voltages, and hardware health."""

    def __init__(self):
        self.monitoring_active = False
        self.history = []
        self.alerts = []
        self.bios_config = self._read_bios_info()
        self.thresholds = {
            "cpu_temp_warn": 75,
            "cpu_temp_crit": 90,
            "gpu_temp_warn": 80,
            "gpu_temp_crit": 95,
            "voltage_12v_min": 11.4,
            "voltage_12v_max": 12.6,
            "voltage_5v_min": 4.75,
            "voltage_5v_max": 5.25,
            "voltage_3v3_min": 3.13,
            "voltage_3v3_max": 3.47,
            "fan_min_rpm": 500,
        }

    def _read_bios_info(self):
        """Read system BIOS / platform information."""
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Unknown",
            "bios_vendor": "NATOS Virtual BIOS",
            "bios_version": "1.0.0",
            "boot_mode": "UEFI",
            "secure_boot": True,
            "virtualization": True,
        }

    def start(self):
        """Start system monitoring."""
        self.monitoring_active = True
        return {"status": "monitoring", "has_psutil": HAS_PSUTIL}

    def stop(self):
        """Stop system monitoring."""
        self.monitoring_active = False
        return {"status": "stopped"}

    def read_temperatures(self):
        """Read system temperatures."""
        temps = {}
        if HAS_PSUTIL:
            try:
                sensor_temps = psutil.sensors_temperatures()
                if sensor_temps:
                    for name, entries in sensor_temps.items():
                        for i, entry in enumerate(entries):
                            label = entry.label or f"{name}_{i}"
                            temps[label] = {
                                "current": entry.current,
                                "high": entry.high,
                                "critical": entry.critical,
                            }
            except (AttributeError, OSError):
                pass

        if not temps:
            # Simulated temperature readings
            base_cpu = 45 + random.uniform(-3, 3)
            temps = {
                "cpu_package": {"current": round(base_cpu, 1),
                                "high": 85.0, "critical": 100.0},
                "cpu_core_0": {"current": round(base_cpu + random.uniform(-2, 2), 1),
                               "high": 85.0, "critical": 100.0},
                "cpu_core_1": {"current": round(base_cpu + random.uniform(-2, 2), 1),
                               "high": 85.0, "critical": 100.0},
                "gpu": {"current": round(40 + random.uniform(-3, 5), 1),
                        "high": 90.0, "critical": 100.0},
                "motherboard": {"current": round(35 + random.uniform(-2, 2), 1),
                                "high": 60.0, "critical": 75.0},
                "nvme_ssd": {"current": round(38 + random.uniform(-2, 3), 1),
                             "high": 70.0, "critical": 80.0},
            }
        return temps

    def read_voltages(self):
        """Read system voltage rails."""
        # Voltage readings (simulated - real hardware sensors vary)
        return {
            "12v_rail": {"value": round(12.0 + random.uniform(-0.15, 0.15), 2),
                         "nominal": 12.0, "unit": "V"},
            "5v_rail": {"value": round(5.0 + random.uniform(-0.05, 0.05), 2),
                        "nominal": 5.0, "unit": "V"},
            "3.3v_rail": {"value": round(3.3 + random.uniform(-0.03, 0.03), 2),
                          "nominal": 3.3, "unit": "V"},
            "vcore": {"value": round(1.2 + random.uniform(-0.05, 0.05), 3),
                      "nominal": 1.2, "unit": "V"},
            "vdimm": {"value": round(1.35 + random.uniform(-0.02, 0.02), 3),
                      "nominal": 1.35, "unit": "V"},
            "battery": {"value": round(3.0 + random.uniform(-0.1, 0.1), 2),
                        "nominal": 3.0, "unit": "V"},
        }

    def read_fan_speeds(self):
        """Read fan speeds."""
        fans = {}
        if HAS_PSUTIL:
            try:
                sensor_fans = psutil.sensors_fans()
                if sensor_fans:
                    for name, entries in sensor_fans.items():
                        for i, entry in enumerate(entries):
                            label = entry.label or f"{name}_{i}"
                            fans[label] = {"rpm": entry.current}
            except (AttributeError, OSError):
                pass

        if not fans:
            fans = {
                "cpu_fan": {"rpm": 1200 + random.randint(-100, 100)},
                "case_fan_1": {"rpm": 900 + random.randint(-50, 50)},
                "case_fan_2": {"rpm": 850 + random.randint(-50, 50)},
                "gpu_fan": {"rpm": 1000 + random.randint(-80, 80)},
            }
        return fans

    def read_system_resources(self):
        """Read CPU, memory, disk usage."""
        if HAS_PSUTIL:
            cpu_percent = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": mem.percent,
                "memory_total_gb": round(mem.total / (1024**3), 1),
                "memory_used_gb": round(mem.used / (1024**3), 1),
                "disk_percent": disk.percent,
                "disk_total_gb": round(disk.total / (1024**3), 1),
                "disk_used_gb": round(disk.used / (1024**3), 1),
            }
        return {
            "cpu_percent": round(random.uniform(5, 25), 1),
            "memory_percent": round(random.uniform(30, 60), 1),
            "memory_total_gb": 16.0,
            "memory_used_gb": round(random.uniform(4, 10), 1),
            "disk_percent": round(random.uniform(40, 70), 1),
            "disk_total_gb": 500.0,
            "disk_used_gb": round(random.uniform(200, 350), 1),
        }

    def check_alerts(self, temps, voltages, fans):
        """Check for threshold violations."""
        alerts = []
        # Temperature alerts
        for name, t in temps.items():
            current = t.get("current", 0)
            if "cpu" in name.lower() and current > self.thresholds["cpu_temp_crit"]:
                alerts.append({"level": "critical", "source": name,
                               "message": f"CPU temp {current}°C exceeds critical threshold"})
            elif "cpu" in name.lower() and current > self.thresholds["cpu_temp_warn"]:
                alerts.append({"level": "warning", "source": name,
                               "message": f"CPU temp {current}°C above warning threshold"})
            if "gpu" in name.lower() and current > self.thresholds["gpu_temp_crit"]:
                alerts.append({"level": "critical", "source": name,
                               "message": f"GPU temp {current}°C exceeds critical threshold"})
            elif "gpu" in name.lower() and current > self.thresholds["gpu_temp_warn"]:
                alerts.append({"level": "warning", "source": name,
                               "message": f"GPU temp {current}°C above warning threshold"})

        # Voltage alerts
        v12 = voltages.get("12v_rail", {}).get("value", 12.0)
        if v12 < self.thresholds["voltage_12v_min"] or v12 > self.thresholds["voltage_12v_max"]:
            alerts.append({"level": "warning", "source": "12v_rail",
                           "message": f"12V rail at {v12}V outside tolerance"})
        v5 = voltages.get("5v_rail", {}).get("value", 5.0)
        if v5 < self.thresholds["voltage_5v_min"] or v5 > self.thresholds["voltage_5v_max"]:
            alerts.append({"level": "warning", "source": "5v_rail",
                           "message": f"5V rail at {v5}V outside tolerance"})

        # Fan alerts
        for name, f in fans.items():
            if f["rpm"] < self.thresholds["fan_min_rpm"]:
                alerts.append({"level": "warning", "source": name,
                               "message": f"Fan speed {f['rpm']} RPM below minimum"})

        self.alerts = alerts
        return alerts

    def get_full_reading(self):
        """Get a complete system health reading."""
        temps = self.read_temperatures()
        voltages = self.read_voltages()
        fans = self.read_fan_speeds()
        resources = self.read_system_resources()
        alerts = self.check_alerts(temps, voltages, fans)

        reading = {
            "timestamp": datetime.now().isoformat(),
            "temperatures": temps,
            "voltages": voltages,
            "fans": fans,
            "resources": resources,
            "alerts": alerts,
            "bios": self.bios_config,
        }

        self.history.append(reading)
        if len(self.history) > 100:
            self.history = self.history[-100:]

        return reading

    def get_status(self):
        """Get system monitor status summary."""
        reading = self.get_full_reading()
        # Calculate overall health score
        alert_penalty = len([a for a in reading["alerts"] if a["level"] == "critical"]) * 20
        alert_penalty += len([a for a in reading["alerts"] if a["level"] == "warning"]) * 5
        health_score = max(0, 100 - alert_penalty)

        return {
            "monitoring_active": self.monitoring_active,
            "has_psutil": HAS_PSUTIL,
            "health_score": health_score,
            "temperatures": reading["temperatures"],
            "voltages": reading["voltages"],
            "fans": reading["fans"],
            "resources": reading["resources"],
            "alerts": reading["alerts"],
            "bios": reading["bios"],
        }
