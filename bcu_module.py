"""
NATOS BCU Module - Boost Controller Unit
Manages boost pressure and ignition timing with preset increment adjustments.

Provides:
- Preset timing increments (0.5°, 1.0°, 2.0°, 5.0° BTDC)
- Boost pressure control with configurable step sizes
- Wastegate duty cycle management
- Safety interlocks with automatic fallback
- Real-time PID-style feedback control

WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY
"""

import time
import math
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class TimingIncrement(Enum):
    """Preset timing adjustment increments in degrees BTDC."""
    FINE = 0.5
    STANDARD = 1.0
    COARSE = 2.0
    AGGRESSIVE = 5.0


class BoostIncrement(Enum):
    """Preset boost adjustment increments in PSI."""
    FINE = 0.5
    STANDARD = 1.0
    COARSE = 2.0
    AGGRESSIVE = 5.0


class BCUState(Enum):
    """BCU operational states."""
    IDLE = "idle"
    ACTIVE = "active"
    HOLDING = "holding"
    RAMP_UP = "ramp_up"
    RAMP_DOWN = "ramp_down"
    SAFETY_CUTBACK = "safety_cutback"
    LIMP_MODE = "limp_mode"


class BoostControllerUnit:
    """
    Boost Controller Unit with preset timing and boost adjustments.

    The BCU manages wastegate duty cycle, boost targets, and ignition timing
    through discrete preset increments. It includes PID-style feedback
    control and safety interlocks.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # BCU state
        self.state = BCUState.IDLE
        self.active = False
        self.last_update = datetime.now()

        # Timing control
        self.timing_base = config.get("timing_base", 15.0)      # degrees BTDC
        self.timing_offset = 0.0                                  # current offset
        self.timing_increment = TimingIncrement.STANDARD
        self.timing_min = config.get("timing_min", -5.0)
        self.timing_max = config.get("timing_max", 25.0)

        # Boost control
        self.boost_target = config.get("boost_target", 12.0)     # PSI
        self.boost_current = 0.0
        self.boost_increment = BoostIncrement.STANDARD
        self.boost_min = config.get("boost_min", 0.0)
        self.boost_max = config.get("boost_max", 25.0)

        # Wastegate control
        self.wastegate_duty = 0.0                                 # 0-100%
        self.wastegate_base_duty = config.get("wastegate_base", 30.0)

        # PID controller gains for boost
        self.pid_kp = config.get("pid_kp", 2.0)
        self.pid_ki = config.get("pid_ki", 0.5)
        self.pid_kd = config.get("pid_kd", 0.1)
        self._pid_integral = 0.0
        self._pid_last_error = 0.0

        # Safety interlocks
        self.safety_active = True
        self.safety_limits = {
            "max_boost": config.get("safety_max_boost", 22.0),
            "max_egt": config.get("safety_max_egt", 1500),
            "max_iat": config.get("safety_max_iat", 160),
            "max_knock_count": config.get("safety_max_knock", 3),
            "min_afr_boost": config.get("safety_min_afr", 10.8),
            "min_oil_pressure": config.get("safety_min_oil", 15),
        }

        # Adjustment history for audit trail
        self.adjustment_history: List[Dict[str, Any]] = []

        # Ramp control
        self.ramp_rate = config.get("ramp_rate", 1.0)  # PSI per second

    def activate(self) -> Dict[str, Any]:
        """Activate the BCU and enter active control mode."""
        self.active = True
        self.state = BCUState.ACTIVE
        self.last_update = datetime.now()
        self._log_adjustment("bcu_activate", {
            "timing_base": self.timing_base,
            "boost_target": self.boost_target,
        })
        return self.get_status()

    def deactivate(self) -> Dict[str, Any]:
        """Deactivate BCU and return to idle."""
        self.active = False
        self.state = BCUState.IDLE
        self.timing_offset = 0.0
        self.wastegate_duty = 0.0
        self._pid_integral = 0.0
        self._pid_last_error = 0.0
        self._log_adjustment("bcu_deactivate", {})
        return self.get_status()

    # ── Timing Control ──────────────────────────────────────────────

    def set_timing_increment(self, increment: str) -> Dict[str, Any]:
        """Set the timing adjustment preset increment."""
        try:
            self.timing_increment = TimingIncrement[increment.upper()]
        except KeyError:
            return {"error": f"Invalid increment: {increment}. Use: FINE, STANDARD, COARSE, AGGRESSIVE"}
        return {"timing_increment": self.timing_increment.value}

    def advance_timing(self, steps: int = 1) -> Dict[str, Any]:
        """Advance ignition timing by the preset increment × steps."""
        delta = self.timing_increment.value * steps
        new_offset = self.timing_offset + delta
        effective = self.timing_base + new_offset

        if effective > self.timing_max:
            return {"error": f"Cannot advance beyond {self.timing_max}° BTDC",
                    "current": effective - delta}

        self.timing_offset = new_offset
        self._log_adjustment("timing_advance", {
            "delta": delta, "new_offset": self.timing_offset,
            "effective_timing": self.timing_base + self.timing_offset,
        })
        return self._timing_status()

    def retard_timing(self, steps: int = 1) -> Dict[str, Any]:
        """Retard ignition timing by the preset increment × steps."""
        delta = self.timing_increment.value * steps
        new_offset = self.timing_offset - delta
        effective = self.timing_base + new_offset

        if effective < self.timing_min:
            return {"error": f"Cannot retard below {self.timing_min}° BTDC",
                    "current": effective + delta}

        self.timing_offset = new_offset
        self._log_adjustment("timing_retard", {
            "delta": -delta, "new_offset": self.timing_offset,
            "effective_timing": self.timing_base + self.timing_offset,
        })
        return self._timing_status()

    def set_timing_offset(self, offset: float) -> Dict[str, Any]:
        """Directly set the timing offset (degrees)."""
        effective = self.timing_base + offset
        if not (self.timing_min <= effective <= self.timing_max):
            return {"error": f"Timing {effective}° outside range [{self.timing_min}, {self.timing_max}]"}
        self.timing_offset = offset
        self._log_adjustment("timing_set", {"offset": offset, "effective": effective})
        return self._timing_status()

    # ── Boost Control ───────────────────────────────────────────────

    def set_boost_increment(self, increment: str) -> Dict[str, Any]:
        """Set the boost adjustment preset increment."""
        try:
            self.boost_increment = BoostIncrement[increment.upper()]
        except KeyError:
            return {"error": f"Invalid increment: {increment}. Use: FINE, STANDARD, COARSE, AGGRESSIVE"}
        return {"boost_increment": self.boost_increment.value}

    def increase_boost(self, steps: int = 1) -> Dict[str, Any]:
        """Increase boost target by preset increment × steps."""
        delta = self.boost_increment.value * steps
        new_target = self.boost_target + delta

        if new_target > self.boost_max:
            return {"error": f"Cannot exceed max boost {self.boost_max} PSI",
                    "current": self.boost_target}

        if self.safety_active and new_target > self.safety_limits["max_boost"]:
            return {"error": f"Safety limit: max boost {self.safety_limits['max_boost']} PSI",
                    "current": self.boost_target}

        self.boost_target = new_target
        self.state = BCUState.RAMP_UP
        self._log_adjustment("boost_increase", {
            "delta": delta, "new_target": self.boost_target,
        })
        return self._boost_status()

    def decrease_boost(self, steps: int = 1) -> Dict[str, Any]:
        """Decrease boost target by preset increment × steps."""
        delta = self.boost_increment.value * steps
        new_target = self.boost_target - delta

        if new_target < self.boost_min:
            new_target = self.boost_min

        self.boost_target = new_target
        self.state = BCUState.RAMP_DOWN
        self._log_adjustment("boost_decrease", {
            "delta": -delta, "new_target": self.boost_target,
        })
        return self._boost_status()

    def set_boost_target(self, target: float) -> Dict[str, Any]:
        """Directly set boost target (PSI)."""
        if not (self.boost_min <= target <= self.boost_max):
            return {"error": f"Boost {target} outside range [{self.boost_min}, {self.boost_max}]"}
        if self.safety_active and target > self.safety_limits["max_boost"]:
            return {"error": f"Safety limit: max boost {self.safety_limits['max_boost']} PSI"}
        self.boost_target = target
        self._log_adjustment("boost_set", {"target": target})
        return self._boost_status()

    # ── Wastegate / PID ─────────────────────────────────────────────

    def compute_wastegate_duty(self, actual_boost: float, dt: float = 0.1) -> float:
        """
        PID controller for wastegate duty cycle.

        Args:
            actual_boost: Current measured boost pressure (PSI)
            dt: Time step in seconds

        Returns:
            Wastegate duty cycle 0-100 %
        """
        error = self.boost_target - actual_boost
        self._pid_integral += error * dt
        self._pid_integral = max(-20, min(20, self._pid_integral))  # anti-windup
        derivative = (error - self._pid_last_error) / dt if dt > 0 else 0
        self._pid_last_error = error

        output = (self.wastegate_base_duty
                  + self.pid_kp * error
                  + self.pid_ki * self._pid_integral
                  + self.pid_kd * derivative)

        self.wastegate_duty = max(0.0, min(100.0, output))
        self.boost_current = actual_boost
        return self.wastegate_duty

    # ── Safety Interlocks ───────────────────────────────────────────

    def check_safety(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate telemetry against safety interlocks.

        Returns actions taken and remaining state.
        """
        actions: List[str] = []
        severity = "normal"

        if not self.safety_active:
            return {"actions": [], "severity": "normal", "state": self.state.value}

        # Over-boost protection
        boost = telemetry.get("boost", 0)
        if boost > self.safety_limits["max_boost"]:
            self.wastegate_duty = 100.0  # fully open wastegate
            self.state = BCUState.SAFETY_CUTBACK
            actions.append(f"Over-boost {boost:.1f} PSI → wastegate 100%")
            severity = "critical"

        # Knock protection
        knock = telemetry.get("knock_count", 0)
        if knock > self.safety_limits["max_knock_count"]:
            self.timing_offset = max(self.timing_min - self.timing_base,
                                     self.timing_offset - 2.0)
            self.boost_target = max(self.boost_min, self.boost_target - 2.0)
            actions.append(f"Knock {knock} → retard timing, reduce boost")
            severity = "critical"

        # EGT protection
        egt = telemetry.get("egt", 0)
        if egt > self.safety_limits["max_egt"]:
            self.boost_target = max(self.boost_min, self.boost_target - 1.0)
            actions.append(f"High EGT {egt}°F → reducing boost")
            severity = max(severity, "warning", key=lambda s: ["normal", "warning", "critical"].index(s))

        # IAT protection
        iat = telemetry.get("iat", 0)
        if iat > self.safety_limits["max_iat"]:
            self.timing_offset = max(self.timing_min - self.timing_base,
                                     self.timing_offset - 1.0)
            actions.append(f"High IAT {iat}°F → retard timing")
            severity = max(severity, "warning", key=lambda s: ["normal", "warning", "critical"].index(s))

        # Oil pressure protection
        oil = telemetry.get("oil_pressure", 50)
        rpm = telemetry.get("rpm", 0)
        if oil < self.safety_limits["min_oil_pressure"] and rpm > 2000:
            self.state = BCUState.LIMP_MODE
            self.boost_target = 0
            actions.append("Low oil pressure → LIMP MODE")
            severity = "critical"

        # AFR protection under boost
        afr = telemetry.get("afr", 14.7)
        if afr < self.safety_limits["min_afr_boost"] and boost > 5:
            self.boost_target = max(self.boost_min, self.boost_target - 1.0)
            actions.append(f"Dangerous AFR {afr:.1f} under boost → reducing")
            severity = max(severity, "warning", key=lambda s: ["normal", "warning", "critical"].index(s))

        if actions:
            self._log_adjustment("safety_interlock", {
                "actions": actions, "severity": severity,
            })

        return {"actions": actions, "severity": severity, "state": self.state.value}

    # ── Update Cycle ────────────────────────────────────────────────

    def update(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main BCU update cycle — call at each telemetry tick.

        Returns the complete BCU output including wastegate duty,
        effective timing, and any safety actions.
        """
        now = datetime.now()
        dt = (now - self.last_update).total_seconds()
        self.last_update = now

        if not self.active:
            return self.get_status()

        # 1. Safety check first
        safety = self.check_safety(telemetry)

        # 2. PID wastegate control
        actual_boost = telemetry.get("boost", 0)
        self.compute_wastegate_duty(actual_boost, dt if dt > 0 else 0.1)

        # 3. Update state
        if self.state not in (BCUState.SAFETY_CUTBACK, BCUState.LIMP_MODE):
            error = abs(self.boost_target - actual_boost)
            if error < 0.5:
                self.state = BCUState.HOLDING
            elif actual_boost < self.boost_target:
                self.state = BCUState.RAMP_UP
            else:
                self.state = BCUState.RAMP_DOWN

        status = self.get_status()
        status["safety"] = safety
        return status

    # ── Status / Helpers ────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return complete BCU status."""
        return {
            "active": self.active,
            "state": self.state.value,
            "timing": self._timing_status(),
            "boost": self._boost_status(),
            "wastegate_duty": round(self.wastegate_duty, 1),
            "safety_active": self.safety_active,
            "history_length": len(self.adjustment_history),
        }

    def get_adjustment_history(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Return the last N adjustment records."""
        return self.adjustment_history[-last_n:]

    def apply_tune_params(self, tune: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a complete tune dictionary from the AI tuner or orchestrator."""
        if "boost_target" in tune:
            self.set_boost_target(tune["boost_target"])
        if "timing_adjustment" in tune:
            self.set_timing_offset(tune["timing_adjustment"])
        if "timing_base" in tune:
            self.timing_base = tune["timing_base"]
        self._log_adjustment("tune_applied", tune)
        return self.get_status()

    def _timing_status(self) -> Dict[str, Any]:
        return {
            "base": self.timing_base,
            "offset": round(self.timing_offset, 1),
            "effective": round(self.timing_base + self.timing_offset, 1),
            "increment": self.timing_increment.value,
            "range": [self.timing_min, self.timing_max],
        }

    def _boost_status(self) -> Dict[str, Any]:
        return {
            "target": round(self.boost_target, 1),
            "current": round(self.boost_current, 1),
            "increment": self.boost_increment.value,
            "range": [self.boost_min, self.boost_max],
        }

    def _log_adjustment(self, action: str, details: Dict[str, Any]):
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        }
        self.adjustment_history.append(record)
        # Keep history bounded
        if len(self.adjustment_history) > 500:
            self.adjustment_history = self.adjustment_history[-500:]
