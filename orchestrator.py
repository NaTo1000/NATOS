"""
NATOS Orchestrator - AI-Powered Real-Time Optimization Workflow Engine

Implements a hierarchical orchestration system inspired by WatsonX patterns:

Hierarchy:
  Supervisor  →  oversees the entire pipeline
    ├── BoostController  →  manages BCU via the bcu_module
    ├── TelemetryMonitor →  aggregates and analyzes live sensor data
    ├── AIOptimizer      →  runs on-the-fly tune adjustments
    └── SafetyGuardian   →  enforces hard safety limits

The Orchestrator coordinates these workers in a publish-subscribe
event loop running at the telemetry tick rate (10 Hz default).

WARNING: FOR EDUCATIONAL/SIMULATION PURPOSES ONLY
"""

import time
import threading
import math
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime
from collections import deque

from bcu_module import BoostControllerUnit, BCUState


# ────────────────────────────────────────────────────────────────
# Enums & Constants
# ────────────────────────────────────────────────────────────────

class WorkerRole(Enum):
    SUPERVISOR = "supervisor"
    BOOST_CONTROLLER = "boost_controller"
    TELEMETRY_MONITOR = "telemetry_monitor"
    AI_OPTIMIZER = "ai_optimizer"
    SAFETY_GUARDIAN = "safety_guardian"


class WorkerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class OptimizationGoal(Enum):
    PERFORMANCE = "performance"
    ECONOMY = "economy"
    BALANCED = "balanced"
    SAFETY = "safety"


# Sliding-window sizes
TELEMETRY_WINDOW = 100   # ~10 s at 10 Hz
OPTIMIZATION_INTERVAL = 20  # run optimizer every N ticks (~2 s)


# ────────────────────────────────────────────────────────────────
# Worker base & concrete workers
# ────────────────────────────────────────────────────────────────

class OrchestratorWorker:
    """Base class for all orchestrator workers."""

    def __init__(self, role: WorkerRole):
        self.role = role
        self.state = WorkerState.IDLE
        self.last_run = datetime.now()
        self.run_count = 0
        self.error_count = 0
        self.metrics: Dict[str, Any] = {}

    def tick(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "state": self.state.value,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_run": self.last_run.isoformat(),
            "metrics": self.metrics,
        }


class TelemetryMonitor(OrchestratorWorker):
    """Aggregates live telemetry into rolling statistics."""

    def __init__(self):
        super().__init__(WorkerRole.TELEMETRY_MONITOR)
        self.history: deque = deque(maxlen=TELEMETRY_WINDOW)
        self.trend: Dict[str, float] = {}

    def tick(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.state = WorkerState.RUNNING
        self.last_run = datetime.now()
        self.run_count += 1

        telemetry = context.get("telemetry", {})
        self.history.append(telemetry)

        if len(self.history) >= 5:
            self.trend = self._compute_trends()

        self.metrics = {
            "window_size": len(self.history),
            "trends": self.trend,
        }
        self.state = WorkerState.IDLE
        return {"trends": self.trend, "window_size": len(self.history)}

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.history)

    # ── internals ───────────────────────────────────────────────
    def _compute_trends(self) -> Dict[str, float]:
        """Simple linear-slope trend for key parameters."""
        keys = ["boost", "rpm", "egt", "iat", "knock_count", "afr"]
        trends = {}
        window = list(self.history)
        n = len(window)
        for k in keys:
            vals = [t.get(k, 0) for t in window]
            if n < 2:
                trends[k] = 0.0
                continue
            mean_x = (n - 1) / 2.0
            mean_y = sum(vals) / n
            num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(vals))
            den = sum((i - mean_x) ** 2 for i in range(n))
            trends[k] = round(num / den, 4) if den else 0.0
        return trends


class BoostController(OrchestratorWorker):
    """Wraps the BCU module as an orchestrator worker."""

    def __init__(self, bcu: BoostControllerUnit):
        super().__init__(WorkerRole.BOOST_CONTROLLER)
        self.bcu = bcu

    def tick(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.state = WorkerState.RUNNING
        self.last_run = datetime.now()
        self.run_count += 1

        telemetry = context.get("telemetry", {})
        result = self.bcu.update(telemetry)
        self.metrics = {
            "boost_target": self.bcu.boost_target,
            "wastegate_duty": self.bcu.wastegate_duty,
            "state": self.bcu.state.value,
        }
        self.state = WorkerState.IDLE
        return result


class SafetyGuardian(OrchestratorWorker):
    """Hard safety layer — can override any other worker."""

    CRITICAL_LIMITS = {
        "max_ect": 230,
        "max_oil_temp": 280,
        "max_egt": 1600,
        "max_knock": 5,
        "min_afr": 10.5,
        "min_oil_pressure": 10,
    }

    def __init__(self, bcu: BoostControllerUnit):
        super().__init__(WorkerRole.SAFETY_GUARDIAN)
        self.bcu = bcu
        self.alerts: List[Dict[str, Any]] = []

    def tick(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.state = WorkerState.RUNNING
        self.last_run = datetime.now()
        self.run_count += 1

        telemetry = context.get("telemetry", {})
        new_alerts: List[str] = []
        severity = "normal"

        checks = [
            ("ect", "max_ect", "Coolant temperature"),
            ("oil_temp", "max_oil_temp", "Oil temperature"),
            ("egt", "max_egt", "Exhaust gas temperature"),
        ]
        for param, limit_key, label in checks:
            val = telemetry.get(param, 0)
            if val > self.CRITICAL_LIMITS[limit_key]:
                new_alerts.append(f"CRITICAL: {label} {val:.0f}°F exceeds {self.CRITICAL_LIMITS[limit_key]}°F")
                severity = "critical"

        knock = telemetry.get("knock_count", 0)
        if knock > self.CRITICAL_LIMITS["max_knock"]:
            new_alerts.append(f"CRITICAL: Knock count {knock}")
            severity = "critical"

        afr = telemetry.get("afr", 14.7)
        if afr < self.CRITICAL_LIMITS["min_afr"]:
            new_alerts.append(f"WARNING: AFR {afr:.1f} dangerously rich")
            if severity != "critical":
                severity = "warning"

        oil = telemetry.get("oil_pressure", 50)
        rpm = telemetry.get("rpm", 0)
        if oil < self.CRITICAL_LIMITS["min_oil_pressure"] and rpm > 2000:
            new_alerts.append("CRITICAL: Low oil pressure — LIMP MODE")
            severity = "critical"
            self.bcu.state = BCUState.LIMP_MODE
            self.bcu.boost_target = 0

        if new_alerts:
            record = {
                "timestamp": datetime.now().isoformat(),
                "alerts": new_alerts,
                "severity": severity,
            }
            self.alerts.append(record)
            if len(self.alerts) > 200:
                self.alerts = self.alerts[-200:]

        self.metrics = {"severity": severity, "alert_count": len(self.alerts)}
        self.state = WorkerState.IDLE
        return {"alerts": new_alerts, "severity": severity}


class AIOptimizer(OrchestratorWorker):
    """
    On-the-fly AI optimization worker.

    Consumes telemetry trends and adjusts BCU parameters toward the
    chosen OptimizationGoal using lightweight heuristic rules
    (simulating a WatsonX Coder / LLM orchestration layer).
    """

    def __init__(self, bcu: BoostControllerUnit):
        super().__init__(WorkerRole.AI_OPTIMIZER)
        self.bcu = bcu
        self.goal = OptimizationGoal.BALANCED
        self.recommendations: List[Dict[str, Any]] = []
        self._tick_counter = 0

    def set_goal(self, goal: str) -> Dict[str, Any]:
        try:
            self.goal = OptimizationGoal[goal.upper()]
        except KeyError:
            return {"error": f"Unknown goal '{goal}'. Use: PERFORMANCE, ECONOMY, BALANCED, SAFETY"}
        return {"goal": self.goal.value}

    def tick(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.state = WorkerState.RUNNING
        self.last_run = datetime.now()
        self.run_count += 1
        self._tick_counter += 1

        # Only optimize every OPTIMIZATION_INTERVAL ticks
        if self._tick_counter % OPTIMIZATION_INTERVAL != 0:
            self.state = WorkerState.IDLE
            return {"action": "skip", "next_in": OPTIMIZATION_INTERVAL - (self._tick_counter % OPTIMIZATION_INTERVAL)}

        trends = context.get("trends", {})
        telemetry = context.get("telemetry", {})
        safety_severity = context.get("safety_severity", "normal")

        recommendation = self._optimize(trends, telemetry, safety_severity)
        if recommendation:
            self.recommendations.append(recommendation)
            if len(self.recommendations) > 200:
                self.recommendations = self.recommendations[-200:]

        self.metrics = {
            "goal": self.goal.value,
            "total_recommendations": len(self.recommendations),
        }
        self.state = WorkerState.IDLE
        return recommendation or {"action": "hold"}

    # ── optimisation heuristics ─────────────────────────────────
    def _optimize(self, trends: Dict, telemetry: Dict, safety: str) -> Optional[Dict[str, Any]]:
        """Lightweight heuristic optimizer (simulates WatsonX inference)."""

        # Never optimize during safety events
        if safety == "critical":
            return {"action": "safety_hold", "reason": "Critical safety condition active"}

        boost_trend = trends.get("boost", 0)
        knock_trend = trends.get("knock_count", 0)
        egt_trend = trends.get("egt", 0)
        afr = telemetry.get("afr", 14.7)
        boost = telemetry.get("boost", 0)
        rpm = telemetry.get("rpm", 0)

        actions: List[str] = []

        if self.goal == OptimizationGoal.PERFORMANCE:
            # Push towards higher boost if safe
            if knock_trend <= 0 and egt_trend < 5 and boost < self.bcu.boost_max - 1:
                self.bcu.increase_boost(1)
                actions.append(f"Boost +{self.bcu.boost_increment.value} PSI (performance)")
            if knock_trend <= 0 and self.bcu.timing_offset < 5:
                self.bcu.advance_timing(1)
                actions.append(f"Timing +{self.bcu.timing_increment.value}° (performance)")

        elif self.goal == OptimizationGoal.ECONOMY:
            # Lean toward lower boost, slightly advanced timing
            if boost > 8:
                self.bcu.decrease_boost(1)
                actions.append(f"Boost -{self.bcu.boost_increment.value} PSI (economy)")
            if knock_trend <= 0 and self.bcu.timing_offset < 3:
                self.bcu.advance_timing(1)
                actions.append(f"Timing +{self.bcu.timing_increment.value}° (economy)")

        elif self.goal == OptimizationGoal.BALANCED:
            # Maintain middle ground
            if knock_trend > 0:
                self.bcu.retard_timing(1)
                actions.append("Timing retarded (knock trend)")
            if egt_trend > 3:
                self.bcu.decrease_boost(1)
                actions.append("Boost reduced (rising EGT)")
            if knock_trend <= 0 and egt_trend < 1 and boost < 14:
                self.bcu.increase_boost(1)
                actions.append("Boost increased (conditions stable)")

        elif self.goal == OptimizationGoal.SAFETY:
            # Actively reduce towards conservative values
            if self.bcu.boost_target > 12:
                self.bcu.decrease_boost(1)
                actions.append("Boost reduced (safety goal)")
            if self.bcu.timing_offset > 0:
                self.bcu.retard_timing(1)
                actions.append("Timing retarded (safety goal)")

        if not actions:
            return None

        return {
            "action": "optimize",
            "goal": self.goal.value,
            "adjustments": actions,
            "timestamp": datetime.now().isoformat(),
            "context": {
                "boost_trend": boost_trend,
                "knock_trend": knock_trend,
                "egt_trend": egt_trend,
            },
        }


# ────────────────────────────────────────────────────────────────
# WatsonX Integration Layer (simulated)
# ────────────────────────────────────────────────────────────────

class WatsonXConnector:
    """
    Simulated WatsonX Coder / Orchestrator integration.

    In production this would call the IBM WatsonX API for advanced
    inference; here it wraps the heuristic optimizer with the same
    interface contract so it can be swapped in later.
    """

    def __init__(self):
        self.connected = True
        self.model_id = "watsonx-coder-v1"
        self.call_count = 0
        self.last_response: Optional[Dict[str, Any]] = None

    def infer(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a WatsonX inference call."""
        self.call_count += 1
        action = prompt.get("action", "analyse")
        telemetry = prompt.get("telemetry", {})
        trends = prompt.get("trends", {})

        # Simulated model response
        response = {
            "model": self.model_id,
            "call_id": self.call_count,
            "timestamp": datetime.now().isoformat(),
        }

        if action == "analyse":
            response["analysis"] = {
                "engine_health": "nominal" if telemetry.get("knock_count", 0) < 3 else "degraded",
                "boost_efficiency": min(100, round((telemetry.get("boost", 0) / max(1, prompt.get("boost_target", 12))) * 100, 1)),
                "thermal_headroom": max(0, 1500 - telemetry.get("egt", 800)),
            }
        elif action == "recommend":
            response["recommendation"] = {
                "boost_delta": 0.5 if trends.get("knock_count", 0) <= 0 else -1.0,
                "timing_delta": 0.5 if trends.get("knock_count", 0) <= 0 else -1.0,
                "confidence": 0.85,
            }
        else:
            response["echo"] = prompt

        self.last_response = response
        return response

    def status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "model_id": self.model_id,
            "call_count": self.call_count,
        }


# ────────────────────────────────────────────────────────────────
# Orchestrator — the top-level supervisor
# ────────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Top-level supervisor that coordinates all workers.

    Hierarchy:
        Orchestrator (supervisor)
        ├── TelemetryMonitor
        ├── BoostController (wraps BCU)
        ├── AIOptimizer
        ├── SafetyGuardian
        └── WatsonXConnector (external AI bridge)

    Execution order per tick:
        1. TelemetryMonitor — aggregate sensor data
        2. SafetyGuardian   — enforce hard limits
        3. BoostController  — PID wastegate + BCU logic
        4. AIOptimizer      — on-the-fly tune adjustments
    """

    def __init__(self, bcu: Optional[BoostControllerUnit] = None):
        self.bcu = bcu or BoostControllerUnit()

        # Workers
        self.telemetry_monitor = TelemetryMonitor()
        self.boost_controller = BoostController(self.bcu)
        self.safety_guardian = SafetyGuardian(self.bcu)
        self.ai_optimizer = AIOptimizer(self.bcu)
        self.watsonx = WatsonXConnector()

        self._workers: List[OrchestratorWorker] = [
            self.telemetry_monitor,
            self.safety_guardian,
            self.boost_controller,
            self.ai_optimizer,
        ]

        # Orchestrator state
        self.active = False
        self.tick_count = 0
        self.last_tick_result: Dict[str, Any] = {}
        self.optimization_goal = OptimizationGoal.BALANCED

    # ── lifecycle ───────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        """Activate the orchestrator and BCU."""
        self.active = True
        self.bcu.activate()
        self.ai_optimizer.set_goal(self.optimization_goal.value)
        return self.get_status()

    def stop(self) -> Dict[str, Any]:
        """Deactivate the orchestrator and BCU."""
        self.active = False
        self.bcu.deactivate()
        for w in self._workers:
            w.state = WorkerState.IDLE
        return self.get_status()

    def set_optimization_goal(self, goal: str) -> Dict[str, Any]:
        """Set the AI optimization goal."""
        try:
            self.optimization_goal = OptimizationGoal[goal.upper()]
        except KeyError:
            return {"error": f"Unknown goal '{goal}'"}
        self.ai_optimizer.set_goal(goal)
        return {"goal": self.optimization_goal.value}

    # ── main tick ───────────────────────────────────────────────

    def tick(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute one orchestration cycle.

        Call this at each telemetry update (10 Hz).
        """
        if not self.active:
            return {"active": False}

        self.tick_count += 1
        context: Dict[str, Any] = {"telemetry": telemetry}

        results: Dict[str, Any] = {"tick": self.tick_count}

        # 1. Telemetry aggregation
        tm_result = self.telemetry_monitor.tick(context)
        context["trends"] = tm_result.get("trends", {})
        results["telemetry_monitor"] = tm_result

        # 2. Safety check
        sg_result = self.safety_guardian.tick(context)
        context["safety_severity"] = sg_result.get("severity", "normal")
        results["safety_guardian"] = sg_result

        # 3. Boost controller (BCU)
        bc_result = self.boost_controller.tick(context)
        results["boost_controller"] = bc_result

        # 4. AI optimizer
        ai_result = self.ai_optimizer.tick(context)
        results["ai_optimizer"] = ai_result

        # 5. WatsonX inference (every 50 ticks ≈ 5 s)
        if self.tick_count % 50 == 0:
            wx_result = self.watsonx.infer({
                "action": "analyse",
                "telemetry": telemetry,
                "trends": context.get("trends", {}),
                "boost_target": self.bcu.boost_target,
            })
            results["watsonx"] = wx_result

        self.last_tick_result = results
        return results

    # ── status & monitoring ─────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Full orchestrator status for the monitoring dashboard."""
        return {
            "active": self.active,
            "tick_count": self.tick_count,
            "optimization_goal": self.optimization_goal.value,
            "bcu": self.bcu.get_status(),
            "workers": {w.role.value: w.status() for w in self._workers},
            "watsonx": self.watsonx.status(),
        }

    def get_optimization_history(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Return recent AI optimizer recommendations."""
        return self.ai_optimizer.recommendations[-last_n:]

    def get_safety_alerts(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Return recent safety alerts."""
        return self.safety_guardian.alerts[-last_n:]

    def get_telemetry_trends(self) -> Dict[str, float]:
        """Return current telemetry trend slopes."""
        return self.telemetry_monitor.trend
