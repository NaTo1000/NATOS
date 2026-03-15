"""
tuning_algorithms.py - Comprehensive Tuning Algorithms for the NATOS ECU Tuning System

Implements multiple optimization strategies used in real-world automotive ECU calibration:
  • MapInterpolationTuner     – 2D/3D lookup-table interpolation for fuel / timing maps
  • PIDFuelTrimTuner          – Closed-loop PID fuel-trim controller with anti-windup
  • IterativeOptimizer        – Hill-climbing / gradient-descent parameter optimizer
  • GeneticAlgorithmTuner     – Evolutionary search over tune parameter space
  • VolumetricEfficiencyModel – Speed-density VE-based fuel calculation
  • TuningAlgorithmComparator – Head-to-head comparison of every algorithm

All data is sourced from the local PerformanceDatabase; no external packages required.
"""

from __future__ import annotations

import copy
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from performance_database import PerformanceDatabase

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STOICH_GASOLINE = 14.7
STOICH_DIESEL = 14.5
STOICH_E85 = 9.8
GAS_CONSTANT_AIR = 287.05          # J/(kg·K)
AIR_DENSITY_STP = 1.225            # kg/m³ at 15 °C / 101.325 kPa
KPA_PER_PSI = 6.89476
ATMOSPHERIC_KPA = 101.325


def _sorted_keys(d: Dict[int, Any]) -> List[int]:
    """Return the integer keys of *d* in ascending order."""
    return sorted(d.keys())


# ===================================================================
# 1. MapInterpolationTuner – 2D/3D lookup-table interpolation
# ===================================================================
class MapInterpolationTuner:
    """Bilinear interpolation over 2-D ECU maps (RPM × Load → value).

    ECU calibration tables are stored as sparse grids.  This class provides
    smooth inter-cell interpolation as well as helpers for generating
    complete fuel and timing maps from a target profile.
    """

    def __init__(self) -> None:
        self.db = PerformanceDatabase()

    # ---- core interpolation ------------------------------------------
    @staticmethod
    def interpolate_2d(
        rpm: float,
        load: float,
        map_data: Dict[int, Dict[int, float]],
    ) -> float:
        """Bilinear interpolation of a 2-D map keyed by RPM then Load%.

        Args:
            rpm:      Engine speed (RPM).
            load:     Engine load (0-100 %).
            map_data: Nested dict  RPM -> Load% -> value.

        Returns:
            Interpolated value at the requested (rpm, load) point.
        """
        rpm_keys = _sorted_keys(map_data)
        if not rpm_keys:
            return 0.0

        # Clamp to map bounds
        rpm = max(rpm_keys[0], min(rpm, rpm_keys[-1]))

        # Find surrounding RPM rows
        rpm_lo = rpm_keys[0]
        rpm_hi = rpm_keys[-1]
        for i, rk in enumerate(rpm_keys):
            if rk >= rpm:
                rpm_hi = rk
                rpm_lo = rpm_keys[max(i - 1, 0)]
                break

        def _interp_load(row: Dict[int, float], ld: float) -> float:
            load_keys = _sorted_keys(row)
            if not load_keys:
                return 0.0
            ld = max(load_keys[0], min(ld, load_keys[-1]))
            ld_lo = load_keys[0]
            ld_hi = load_keys[-1]
            for j, lk in enumerate(load_keys):
                if lk >= ld:
                    ld_hi = lk
                    ld_lo = load_keys[max(j - 1, 0)]
                    break
            if ld_hi == ld_lo:
                return row[ld_lo]
            frac = (ld - ld_lo) / (ld_hi - ld_lo)
            return row[ld_lo] + frac * (row[ld_hi] - row[ld_lo])

        val_lo = _interp_load(map_data[rpm_lo], load)
        val_hi = _interp_load(map_data[rpm_hi], load)

        if rpm_hi == rpm_lo:
            return val_lo
        frac = (rpm - rpm_lo) / (rpm_hi - rpm_lo)
        return val_lo + frac * (val_hi - val_lo)

    # ---- convenience accessors ---------------------------------------
    def interpolate_afr(self, engine_id: str, variant: str,
                        rpm: float, load: float) -> float:
        """Return interpolated AFR at the given operating point."""
        afr_map = self.db.get_afr_map(engine_id, variant)
        if afr_map is None:
            return STOICH_GASOLINE
        return self.interpolate_2d(rpm, load, afr_map)

    def interpolate_timing(self, engine_id: str, variant: str,
                           rpm: float, load: float) -> float:
        """Return interpolated ignition timing (°BTDC)."""
        timing_map = self.db.get_timing_map(engine_id, variant)
        if timing_map is None:
            return 10.0
        return self.interpolate_2d(rpm, load, timing_map)

    # ---- map generation ----------------------------------------------
    def generate_fuel_map(
        self,
        engine_id: str,
        target_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Generate an optimised AFR map for *engine_id*.

        Args:
            engine_id:      Engine identifier in the database.
            target_profile: One of ``"power"``, ``"economy"``, ``"balanced"``.

        Returns:
            Dict with ``afr_map``, ``description``, and ``profile`` keys.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        stock_afr = self.db.get_afr_map(engine_id, "stock")
        if stock_afr is None:
            return {"error": "No AFR map available"}

        fuel_type = engine.get("fuel_type", "gasoline")
        stoich = STOICH_DIESEL if fuel_type == "diesel" else STOICH_GASOLINE

        # Profile-specific enrichment / leaning
        offsets = {
            "power":    {"idle": 0.0, "cruise": 0.0, "wot": -0.8},
            "economy":  {"idle": 0.1, "cruise": 0.3, "wot": 0.2},
            "balanced": {"idle": 0.0, "cruise": 0.15, "wot": -0.3},
        }
        profile = offsets.get(target_profile, offsets["balanced"])

        new_map: Dict[int, Dict[int, float]] = {}
        for rpm_key in _sorted_keys(stock_afr):
            new_map[rpm_key] = {}
            for load_key in _sorted_keys(stock_afr[rpm_key]):
                base = stock_afr[rpm_key][load_key]
                if load_key <= 20:
                    adj = profile["idle"]
                elif load_key <= 60:
                    adj = profile["cruise"]
                else:
                    adj = profile["wot"]
                # Never go leaner than stoich under heavy load
                value = base + adj
                if load_key >= 80:
                    value = min(value, stoich)
                new_map[rpm_key][load_key] = round(value, 2)

        return {
            "afr_map": new_map,
            "description": f"Optimised AFR map ({target_profile}) for {engine.get('name', engine_id)}",
            "profile": target_profile,
        }

    def generate_timing_map(
        self,
        engine_id: str,
        target_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Generate an optimised ignition-timing map.

        Args:
            engine_id:      Engine identifier.
            target_profile: ``"power"`` | ``"economy"`` | ``"balanced"``.

        Returns:
            Dict with ``timing_map``, ``description``, and ``profile``.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        stock_timing = self.db.get_timing_map(engine_id, "stock")
        if stock_timing is None:
            return {"error": "No timing map available"}

        is_turbo = engine.get("aspiration", "") in (
            "turbocharged", "supercharged", "twin-turbocharged",
        )

        offsets = {
            "power":    {"low_load": 1.0, "mid_load": 1.5, "high_load": 2.0 if not is_turbo else 0.5},
            "economy":  {"low_load": 2.0, "mid_load": 1.5, "high_load": 0.0},
            "balanced": {"low_load": 1.5, "mid_load": 1.0, "high_load": 1.0 if not is_turbo else 0.0},
        }
        profile = offsets.get(target_profile, offsets["balanced"])

        new_map: Dict[int, Dict[int, float]] = {}
        for rpm_key in _sorted_keys(stock_timing):
            new_map[rpm_key] = {}
            for load_key in _sorted_keys(stock_timing[rpm_key]):
                base = stock_timing[rpm_key][load_key]
                if load_key <= 30:
                    adj = profile["low_load"]
                elif load_key <= 70:
                    adj = profile["mid_load"]
                else:
                    adj = profile["high_load"]
                # Safety cap – never exceed 45° BTDC
                value = min(base + adj, 45.0)
                # Ensure we don't go negative
                value = max(value, 0.0)
                new_map[rpm_key][load_key] = round(value, 1)

        return {
            "timing_map": new_map,
            "description": f"Optimised timing map ({target_profile}) for {engine.get('name', engine_id)}",
            "profile": target_profile,
        }


# ===================================================================
# 2. PIDFuelTrimTuner – Closed-loop PID fuel-trim controller
# ===================================================================
class PIDFuelTrimTuner:
    """PID controller for closed-loop AFR fuel-trim adjustment.

    Mimics the behaviour of a wideband O₂ feedback loop maintaining a
    target AFR.  Includes integral anti-windup clamping.

    Args:
        kp: Proportional gain (default 2.5).
        ki: Integral gain     (default 0.8).
        kd: Derivative gain   (default 0.15).
        windup_limit: Max absolute integral accumulator value (default 25.0 %).
    """

    def __init__(
        self,
        kp: float = 2.5,
        ki: float = 0.8,
        kd: float = 0.15,
        windup_limit: float = 25.0,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.windup_limit = windup_limit

        self._integral: float = 0.0
        self._prev_error: float = 0.0
        self._initialised: bool = False

    def reset(self) -> None:
        """Reset internal state (integral accumulator, previous error)."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialised = False

    def compute(self, target_afr: float, actual_afr: float, dt: float) -> float:
        """Compute the fuel-trim correction needed.

        Args:
            target_afr: Desired air/fuel ratio.
            actual_afr: Measured air/fuel ratio from the wideband sensor.
            dt:         Time-step in seconds since last call.

        Returns:
            Fuel trim percentage (positive = add fuel, negative = remove fuel).
        """
        if dt <= 0.0:
            return 0.0

        # Error: positive means mixture is too lean → need more fuel
        error = actual_afr - target_afr

        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup
        self._integral += error * dt
        self._integral = max(-self.windup_limit, min(self.windup_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative (skip on first call to avoid spike)
        if self._initialised:
            d_term = self.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0
            self._initialised = True

        self._prev_error = error

        trim = p_term + i_term + d_term

        # Clamp total correction to ±30 %
        trim = max(-30.0, min(30.0, trim))
        return round(trim, 2)

    def simulate(
        self,
        target_afr: float,
        disturbance_sequence: List[float],
        dt: float = 0.05,
    ) -> Dict[str, Any]:
        """Run the controller over a simulated disturbance sequence.

        Args:
            target_afr:           Desired AFR.
            disturbance_sequence: List of measured AFR samples.
            dt:                   Time-step between samples.

        Returns:
            Dict with ``trims``, ``errors``, ``settled`` flag, and stats.
        """
        self.reset()
        trims: List[float] = []
        errors: List[float] = []
        for actual in disturbance_sequence:
            trim = self.compute(target_afr, actual, dt)
            trims.append(trim)
            errors.append(round(actual - target_afr, 3))

        settled = all(abs(e) < 0.3 for e in errors[-10:]) if len(errors) >= 10 else False
        return {
            "trims": trims,
            "errors": errors,
            "settled": settled,
            "max_error": max(abs(e) for e in errors) if errors else 0.0,
            "final_trim": trims[-1] if trims else 0.0,
            "samples": len(trims),
        }


# ===================================================================
# 3. IterativeOptimizer – Hill-climbing / gradient-descent
# ===================================================================
class IterativeOptimizer:
    """Iterative parameter optimizer using gradient-approximation hill climbing.

    Explores the neighbourhood of each tune parameter, estimating the
    gradient via finite differences, then steps in the improving direction.
    A simple fitness function balances power, economy, and safety.
    """

    # Defaults per-parameter: (min, max, initial_step)
    PARAM_BOUNDS: Dict[str, Tuple[float, float, float]] = {
        "boost_psi":        (0.0, 30.0, 0.5),
        "afr_wot":          (10.5, 15.0, 0.1),
        "timing_advance":   (0.0, 45.0, 0.5),
        "rev_limit":        (5000, 9500, 100),
        "fuel_trim_pct":    (-15.0, 15.0, 0.5),
    }

    def __init__(self) -> None:
        self.db = PerformanceDatabase()

    # ---- fitness evaluation -----------------------------------------
    def _fitness(
        self,
        params: Dict[str, float],
        engine: Dict[str, Any],
        target: str,
    ) -> float:
        """Score a set of tune parameters (higher = better).

        The score blends:
          • estimated power change  (from boost & timing delta)
          • fuel-economy indicator  (lean cruise AFR)
          • safety penalty          (knock risk, over-boost, lean WOT)
        """
        stock_hp = engine.get("stock_power_hp", 200)
        aspiration = engine.get("aspiration", "naturally_aspirated")
        fuel_type = engine.get("fuel_type", "gasoline")
        stoich = STOICH_DIESEL if fuel_type == "diesel" else STOICH_GASOLINE
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")

        boost = params.get("boost_psi", 0.0)
        afr_wot = params.get("afr_wot", stoich)
        timing = params.get("timing_advance", 15.0)
        rev_limit = params.get("rev_limit", engine.get("rev_limit", 6500))
        fuel_trim = params.get("fuel_trim_pct", 0.0)

        # Power estimate: ~6 hp per PSI on a turbo 4-cyl, ~4 hp per extra degree timing
        power_gain = 0.0
        if is_boosted:
            stock_boost_map = engine.get("boost_map", {})
            peak_stock_boost = max(stock_boost_map.values()) if stock_boost_map else 0.0
            power_gain += (boost - peak_stock_boost) * 6.0
        power_gain += max(0, timing - 15.0) * 2.0
        power_gain += (rev_limit - engine.get("rev_limit", 6500)) * 0.01

        est_power = stock_hp + power_gain

        # Economy indicator: closer to stoich at cruise is better
        economy_score = max(0, 10.0 - abs(afr_wot - stoich))

        # Safety penalties
        penalty = 0.0
        if afr_wot > stoich - 0.3 and is_boosted:
            # Too lean under boost – serious detonation risk
            penalty += (afr_wot - (stoich - 0.5)) * 30.0
        if timing > 38.0 and is_boosted:
            penalty += (timing - 38.0) * 20.0
        if timing > 42.0:
            penalty += (timing - 42.0) * 40.0
        if boost > 28.0:
            penalty += (boost - 28.0) * 25.0
        if abs(fuel_trim) > 12.0:
            penalty += (abs(fuel_trim) - 12.0) * 10.0

        # Target-weighted composite
        weights = {
            "power":    {"power": 1.0, "economy": 0.1, "penalty": 1.0},
            "economy":  {"power": 0.3, "economy": 1.0, "penalty": 1.0},
            "balanced": {"power": 0.6, "economy": 0.5, "penalty": 1.0},
        }
        w = weights.get(target, weights["balanced"])

        score = (
            w["power"] * est_power
            + w["economy"] * economy_score * 10.0
            - w["penalty"] * penalty
        )
        return round(score, 2)

    # ---- main optimization loop -------------------------------------
    def optimize(
        self,
        engine_id: str,
        target: str = "power",
        constraints: Optional[Dict[str, Tuple[float, float]]] = None,
        max_iterations: int = 200,
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """Run iterative hill-climbing optimization.

        Args:
            engine_id:      Engine identifier.
            target:         ``"power"`` | ``"economy"`` | ``"balanced"``.
            constraints:    Optional per-param ``(min, max)`` overrides.
            max_iterations: Maximum number of iterations.
            tolerance:      Stop when fitness improvement < tolerance.

        Returns:
            Dict with ``best_params``, ``best_fitness``, ``iterations``,
            ``history``, and ``converged`` flag.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        aspiration = engine.get("aspiration", "naturally_aspirated")
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")

        # Build initial params from stock data
        boost_map = engine.get("boost_map", {})
        peak_stock_boost = max(boost_map.values()) if boost_map else 0.0
        stock_timing_map = self.db.get_timing_map(engine_id, "stock")
        avg_timing = 20.0
        if stock_timing_map:
            all_vals = [v for row in stock_timing_map.values() for v in row.values()]
            avg_timing = sum(all_vals) / len(all_vals) if all_vals else 20.0

        params: Dict[str, float] = {
            "boost_psi": peak_stock_boost,
            "afr_wot": 12.5 if is_boosted else 13.0,
            "timing_advance": round(avg_timing, 1),
            "rev_limit": float(engine.get("rev_limit", 6500)),
            "fuel_trim_pct": 0.0,
        }

        # Merge user constraints with default bounds
        bounds = dict(self.PARAM_BOUNDS)
        if constraints:
            for k, v in constraints.items():
                if k in bounds:
                    bounds[k] = (v[0], v[1], bounds[k][2])

        if not is_boosted:
            params["boost_psi"] = 0.0
            bounds["boost_psi"] = (0.0, 0.0, 0.0)

        best_params = dict(params)
        best_fitness = self._fitness(params, engine, target)
        history: List[Dict[str, Any]] = [{"iteration": 0, "fitness": best_fitness, "params": dict(params)}]

        for iteration in range(1, max_iterations + 1):
            improved = False
            for key in params:
                lo, hi, step = bounds[key]
                if step == 0.0:
                    continue
                for direction in (step, -step):
                    trial = dict(params)
                    trial[key] = max(lo, min(hi, trial[key] + direction))
                    f = self._fitness(trial, engine, target)
                    if f > best_fitness + tolerance:
                        best_fitness = f
                        best_params = dict(trial)
                        params = dict(trial)
                        improved = True
                        break
            history.append({"iteration": iteration, "fitness": best_fitness, "params": dict(best_params)})
            if not improved:
                break

        return {
            "best_params": best_params,
            "best_fitness": best_fitness,
            "iterations": len(history) - 1,
            "history": history,
            "converged": len(history) - 1 < max_iterations,
            "engine_id": engine_id,
            "target": target,
        }


# ===================================================================
# 4. GeneticAlgorithmTuner – Evolutionary tune optimization
# ===================================================================
class GeneticAlgorithmTuner:
    """Genetic-algorithm optimizer for ECU tune parameter sets.

    Each *individual* in the population is a dict of tune parameters.
    Selection uses tournament selection, crossover is uniform, and
    mutation adds Gaussian noise.
    """

    GENE_SPECS: Dict[str, Dict[str, float]] = {
        "boost_psi":      {"min": 0.0,   "max": 30.0,  "mut_sigma": 0.5},
        "afr_wot":        {"min": 10.5,  "max": 15.0,  "mut_sigma": 0.15},
        "timing_advance": {"min": 0.0,   "max": 45.0,  "mut_sigma": 1.0},
        "rev_limit":      {"min": 5000,  "max": 9500,  "mut_sigma": 100},
        "fuel_trim_pct":  {"min": -15.0, "max": 15.0,  "mut_sigma": 0.5},
    }

    def __init__(self) -> None:
        self.db = PerformanceDatabase()

    # ---- fitness (reuses same logic as IterativeOptimizer) -----------
    @staticmethod
    def _fitness(
        individual: Dict[str, float],
        engine: Dict[str, Any],
        target: str,
    ) -> float:
        stock_hp = engine.get("stock_power_hp", 200)
        aspiration = engine.get("aspiration", "naturally_aspirated")
        fuel_type = engine.get("fuel_type", "gasoline")
        stoich = STOICH_DIESEL if fuel_type == "diesel" else STOICH_GASOLINE
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")

        boost = individual.get("boost_psi", 0.0)
        afr_wot = individual.get("afr_wot", stoich)
        timing = individual.get("timing_advance", 15.0)
        rev_limit = individual.get("rev_limit", engine.get("rev_limit", 6500))
        fuel_trim = individual.get("fuel_trim_pct", 0.0)

        power_gain = 0.0
        if is_boosted:
            stock_boost_map = engine.get("boost_map", {})
            peak_stock = max(stock_boost_map.values()) if stock_boost_map else 0.0
            power_gain += (boost - peak_stock) * 6.0
        power_gain += max(0, timing - 15.0) * 2.0
        power_gain += (rev_limit - engine.get("rev_limit", 6500)) * 0.01
        est_power = stock_hp + power_gain

        economy_score = max(0, 10.0 - abs(afr_wot - stoich))

        penalty = 0.0
        if afr_wot > stoich - 0.3 and is_boosted:
            penalty += (afr_wot - (stoich - 0.5)) * 30.0
        if timing > 38.0 and is_boosted:
            penalty += (timing - 38.0) * 20.0
        if timing > 42.0:
            penalty += (timing - 42.0) * 40.0
        if boost > 28.0:
            penalty += (boost - 28.0) * 25.0
        if abs(fuel_trim) > 12.0:
            penalty += (abs(fuel_trim) - 12.0) * 10.0

        weights = {
            "power":    {"power": 1.0, "economy": 0.1, "penalty": 1.0},
            "economy":  {"power": 0.3, "economy": 1.0, "penalty": 1.0},
            "balanced": {"power": 0.6, "economy": 0.5, "penalty": 1.0},
        }
        w = weights.get(target, weights["balanced"])
        return round(
            w["power"] * est_power
            + w["economy"] * economy_score * 10.0
            - w["penalty"] * penalty,
            2,
        )

    # ---- GA operators ------------------------------------------------
    def _random_individual(self, engine: Dict[str, Any]) -> Dict[str, float]:
        aspiration = engine.get("aspiration", "naturally_aspirated")
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
        ind: Dict[str, float] = {}
        for gene, spec in self.GENE_SPECS.items():
            if gene == "boost_psi" and not is_boosted:
                ind[gene] = 0.0
            else:
                ind[gene] = round(random.uniform(spec["min"], spec["max"]), 2)
        return ind

    @staticmethod
    def _tournament_select(
        population: List[Dict[str, float]],
        fitnesses: List[float],
        k: int = 3,
    ) -> Dict[str, float]:
        """Select the best individual from *k* randomly-chosen candidates."""
        indices = random.sample(range(len(population)), min(k, len(population)))
        best_idx = max(indices, key=lambda i: fitnesses[i])
        return copy.deepcopy(population[best_idx])

    def _crossover(
        self,
        parent_a: Dict[str, float],
        parent_b: Dict[str, float],
    ) -> Dict[str, float]:
        """Uniform crossover – each gene randomly inherited from either parent."""
        child: Dict[str, float] = {}
        for gene in self.GENE_SPECS:
            child[gene] = parent_a[gene] if random.random() < 0.5 else parent_b[gene]
        return child

    def _mutate(
        self,
        individual: Dict[str, float],
        mutation_rate: float,
        engine: Dict[str, Any],
    ) -> Dict[str, float]:
        """Apply Gaussian mutation to each gene with probability *mutation_rate*."""
        aspiration = engine.get("aspiration", "naturally_aspirated")
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
        for gene, spec in self.GENE_SPECS.items():
            if gene == "boost_psi" and not is_boosted:
                continue
            if random.random() < mutation_rate:
                noise = random.gauss(0, spec["mut_sigma"])
                individual[gene] = round(
                    max(spec["min"], min(spec["max"], individual[gene] + noise)),
                    2,
                )
        return individual

    # ---- main evolution loop ----------------------------------------
    def evolve(
        self,
        engine_id: str,
        generations: int = 100,
        population_size: int = 50,
        target: str = "power",
        mutation_rate: float = 0.15,
        elitism: int = 2,
    ) -> Dict[str, Any]:
        """Run the genetic algorithm.

        Args:
            engine_id:       Engine identifier.
            generations:     Number of evolutionary generations.
            population_size: Population count.
            target:          ``"power"`` | ``"economy"`` | ``"balanced"``.
            mutation_rate:   Per-gene mutation probability.
            elitism:         Number of top individuals carried to next generation.

        Returns:
            Dict with ``best_individual``, ``best_fitness``,
            ``generations_run``, ``history``, and ``population_stats``.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        population = [self._random_individual(engine) for _ in range(population_size)]
        history: List[Dict[str, Any]] = []
        best_ever: Optional[Dict[str, float]] = None
        best_fitness_ever = float("-inf")

        for gen in range(generations):
            fitnesses = [self._fitness(ind, engine, target) for ind in population]
            gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
            gen_best_fit = fitnesses[gen_best_idx]
            gen_avg_fit = sum(fitnesses) / len(fitnesses)

            if gen_best_fit > best_fitness_ever:
                best_fitness_ever = gen_best_fit
                best_ever = copy.deepcopy(population[gen_best_idx])

            history.append({
                "generation": gen,
                "best_fitness": gen_best_fit,
                "avg_fitness": round(gen_avg_fit, 2),
                "best_individual": copy.deepcopy(population[gen_best_idx]),
            })

            # Build next generation
            ranked = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
            next_gen: List[Dict[str, float]] = [copy.deepcopy(population[ranked[i]]) for i in range(min(elitism, len(ranked)))]

            while len(next_gen) < population_size:
                p1 = self._tournament_select(population, fitnesses)
                p2 = self._tournament_select(population, fitnesses)
                child = self._crossover(p1, p2)
                child = self._mutate(child, mutation_rate, engine)
                next_gen.append(child)

            population = next_gen

        # Final evaluation
        fitnesses = [self._fitness(ind, engine, target) for ind in population]
        final_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        if fitnesses[final_best_idx] > best_fitness_ever:
            best_fitness_ever = fitnesses[final_best_idx]
            best_ever = copy.deepcopy(population[final_best_idx])

        return {
            "best_individual": best_ever,
            "best_fitness": best_fitness_ever,
            "generations_run": generations,
            "history": history,
            "population_stats": {
                "final_best": fitnesses[final_best_idx],
                "final_avg": round(sum(fitnesses) / len(fitnesses), 2),
                "final_worst": min(fitnesses),
            },
            "engine_id": engine_id,
            "target": target,
        }


# ===================================================================
# 5. VolumetricEfficiencyModel – Speed-density fuel calculation
# ===================================================================
class VolumetricEfficiencyModel:
    """Speed-density based volumetric-efficiency and fuel-requirement model.

    Calculates the air mass entering the engine using the ideal-gas law
    and a VE lookup, then derives the required injector pulse-width to
    achieve a target AFR.
    """

    def __init__(self) -> None:
        self.db = PerformanceDatabase()

    @staticmethod
    def calculate_ve(
        rpm: float,
        map_pressure_kpa: float,
        iat_celsius: float,
        displacement_litres: float,
    ) -> float:
        """Estimate volumetric efficiency (0-1) from operating conditions.

        Uses the speed-density equation ratio of actual air mass to
        theoretical air mass at the given manifold absolute pressure and
        intake-air temperature.

        Args:
            rpm:                  Engine speed (RPM).
            map_pressure_kpa:    Manifold absolute pressure (kPa).
            iat_celsius:          Intake-air temperature (°C).
            displacement_litres: Total engine displacement in litres.

        Returns:
            Estimated VE as a fraction (e.g. 0.85 for 85 %).
        """
        if rpm <= 0 or displacement_litres <= 0:
            return 0.0

        iat_kelvin = iat_celsius + 273.15
        if iat_kelvin <= 0:
            iat_kelvin = 293.15

        # Ideal air mass per cycle (one intake stroke per 2 revs in 4-stroke)
        disp_m3 = displacement_litres / 1000.0
        theoretical_mass = (ATMOSPHERIC_KPA * 1000.0 * disp_m3) / (GAS_CONSTANT_AIR * 293.15)

        # Actual air mass using MAP & IAT
        actual_mass = (map_pressure_kpa * 1000.0 * disp_m3) / (GAS_CONSTANT_AIR * iat_kelvin)

        if theoretical_mass == 0.0:
            return 0.0

        base_ve = actual_mass / theoretical_mass

        # RPM-dependent breathing penalty (simplified)
        peak_ve_rpm = 4500.0
        rpm_factor = 1.0 - 0.15 * ((rpm - peak_ve_rpm) / peak_ve_rpm) ** 2
        rpm_factor = max(0.5, min(1.05, rpm_factor))

        return round(min(base_ve * rpm_factor, 1.15), 4)

    @staticmethod
    def calculate_fuel_requirement(
        rpm: float,
        load_pct: float,
        ve: float,
        target_afr: float,
        displacement_litres: float = 2.0,
        iat_celsius: float = 25.0,
    ) -> Dict[str, float]:
        """Calculate fuel requirement for a single operating point.

        Args:
            rpm:                  Engine speed (RPM).
            load_pct:             Load percentage (0-100).
            ve:                   Volumetric efficiency (0-1).
            target_afr:           Target air-fuel ratio.
            displacement_litres: Engine displacement (litres).
            iat_celsius:          Intake-air temperature (°C).

        Returns:
            Dict with ``air_mass_mg``, ``fuel_mass_mg``,
            ``injector_pw_ms``, ``fuel_flow_cc_min``.
        """
        if rpm <= 0 or target_afr <= 0 or ve <= 0:
            return {"air_mass_mg": 0.0, "fuel_mass_mg": 0.0,
                    "injector_pw_ms": 0.0, "fuel_flow_cc_min": 0.0}

        iat_k = iat_celsius + 273.15
        map_kpa = ATMOSPHERIC_KPA * (load_pct / 100.0)
        map_kpa = max(20.0, map_kpa)  # Minimum vacuum ~20 kPa

        disp_m3 = displacement_litres / 1000.0
        air_mass_per_cycle_kg = (map_kpa * 1000.0 * disp_m3 * ve) / (GAS_CONSTANT_AIR * iat_k)
        air_mass_mg = air_mass_per_cycle_kg * 1e6

        fuel_mass_mg = air_mass_mg / target_afr

        # Injector pulse width (assume ~250 cc/min injector flow at 3 bar)
        injector_flow_mg_per_ms = 3.5
        injector_pw_ms = fuel_mass_mg / injector_flow_mg_per_ms if injector_flow_mg_per_ms > 0 else 0.0

        # Total fuel flow: cycles per minute = RPM / 2 (4-stroke)
        cycles_per_min = rpm / 2.0
        fuel_mass_per_min_mg = fuel_mass_mg * cycles_per_min
        fuel_density_mg_per_cc = 750.0  # gasoline ≈ 0.75 g/cc
        fuel_flow_cc_min = fuel_mass_per_min_mg / fuel_density_mg_per_cc

        return {
            "air_mass_mg": round(air_mass_mg, 2),
            "fuel_mass_mg": round(fuel_mass_mg, 2),
            "injector_pw_ms": round(injector_pw_ms, 3),
            "fuel_flow_cc_min": round(fuel_flow_cc_min, 2),
        }

    def generate_ve_table(
        self,
        engine_id: str,
    ) -> Dict[str, Any]:
        """Generate a complete VE table for the given engine.

        Args:
            engine_id: Engine identifier.

        Returns:
            Dict with ``ve_table`` (RPM → Load% → VE), ``fuel_table``
            (RPM → Load% → fuel mg), and engine metadata.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        displacement = engine.get("displacement", 2.0)
        aspiration = engine.get("aspiration", "naturally_aspirated")
        is_boosted = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
        boost_map = engine.get("boost_map", {})

        afr_map = self.db.get_afr_map(engine_id, "stock")
        if afr_map is None:
            return {"error": "No AFR map available"}

        rpm_points = _sorted_keys(afr_map)
        load_points = _sorted_keys(afr_map[rpm_points[0]]) if rpm_points else list(range(0, 101, 10))

        ve_table: Dict[int, Dict[int, float]] = {}
        fuel_table: Dict[int, Dict[int, float]] = {}

        for rpm_val in rpm_points:
            ve_table[rpm_val] = {}
            fuel_table[rpm_val] = {}

            # Estimate MAP from load + boost
            boost_psi = 0.0
            if is_boosted and boost_map:
                closest_rpm = min(boost_map.keys(), key=lambda r: abs(r - rpm_val))
                boost_psi = boost_map[closest_rpm]

            for load_val in load_points:
                map_kpa = ATMOSPHERIC_KPA * (load_val / 100.0)
                if is_boosted and load_val > 40:
                    map_kpa += boost_psi * KPA_PER_PSI * (load_val - 40) / 60.0

                ve = self.calculate_ve(rpm_val, map_kpa, 25.0, displacement)
                ve_table[rpm_val][load_val] = ve

                target_afr = afr_map[rpm_val].get(load_val, STOICH_GASOLINE)
                fuel_req = self.calculate_fuel_requirement(
                    rpm_val, load_val, ve, target_afr, displacement,
                )
                fuel_table[rpm_val][load_val] = fuel_req["fuel_mass_mg"]

        return {
            "ve_table": ve_table,
            "fuel_table": fuel_table,
            "engine_id": engine_id,
            "engine_name": engine.get("name", engine_id),
            "displacement": displacement,
            "aspiration": aspiration,
            "rpm_points": rpm_points,
            "load_points": load_points,
        }


# ===================================================================
# 6. TuningAlgorithmComparator – Head-to-head comparison
# ===================================================================
class TuningAlgorithmComparator:
    """Run every algorithm on the same engine and compare results."""

    def __init__(self) -> None:
        self.db = PerformanceDatabase()

    def compare_all(
        self,
        engine_id: str,
        target: str = "power",
    ) -> Dict[str, Any]:
        """Execute all tuning algorithms and return a comparison table.

        Args:
            engine_id: Engine identifier.
            target:    ``"power"`` | ``"economy"`` | ``"balanced"``.

        Returns:
            Dict keyed by algorithm name, each containing ``result``,
            ``elapsed_ms``, and ``quality_score``.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        results: Dict[str, Any] = {"engine_id": engine_id, "target": target, "algorithms": {}}

        # 1. Map Interpolation
        t0 = time.monotonic()
        mit = MapInterpolationTuner()
        fuel_map = mit.generate_fuel_map(engine_id, target)
        timing_map = mit.generate_timing_map(engine_id, target)
        elapsed = (time.monotonic() - t0) * 1000
        results["algorithms"]["MapInterpolationTuner"] = {
            "description": "2D bilinear map interpolation & profile-based adjustment",
            "result_summary": {
                "fuel_map_generated": "error" not in fuel_map,
                "timing_map_generated": "error" not in timing_map,
            },
            "elapsed_ms": round(elapsed, 2),
            "quality_score": 0.80 if "error" not in fuel_map else 0.0,
        }

        # 2. PID Fuel Trim
        t0 = time.monotonic()
        pid = PIDFuelTrimTuner()
        disturbance = [14.7 + 0.8 * math.sin(i * 0.3) + random.uniform(-0.2, 0.2) for i in range(200)]
        pid_result = pid.simulate(14.7 if target != "power" else 12.5, disturbance)
        elapsed = (time.monotonic() - t0) * 1000
        results["algorithms"]["PIDFuelTrimTuner"] = {
            "description": "Closed-loop PID AFR controller with anti-windup",
            "result_summary": {
                "settled": pid_result["settled"],
                "final_trim": pid_result["final_trim"],
                "max_error": round(pid_result["max_error"], 3),
            },
            "elapsed_ms": round(elapsed, 2),
            "quality_score": 0.90 if pid_result["settled"] else 0.60,
        }

        # 3. Iterative Optimizer
        t0 = time.monotonic()
        opt = IterativeOptimizer()
        iter_result = opt.optimize(engine_id, target=target, max_iterations=100)
        elapsed = (time.monotonic() - t0) * 1000
        if "error" not in iter_result:
            results["algorithms"]["IterativeOptimizer"] = {
                "description": "Hill-climbing gradient-approximation optimizer",
                "result_summary": {
                    "best_fitness": iter_result["best_fitness"],
                    "iterations": iter_result["iterations"],
                    "converged": iter_result["converged"],
                    "best_params": iter_result["best_params"],
                },
                "elapsed_ms": round(elapsed, 2),
                "quality_score": min(1.0, iter_result["best_fitness"] / 300.0),
            }

        # 4. Genetic Algorithm (smaller pop for speed in comparison)
        t0 = time.monotonic()
        ga = GeneticAlgorithmTuner()
        ga_result = ga.evolve(engine_id, generations=30, population_size=20, target=target)
        elapsed = (time.monotonic() - t0) * 1000
        if "error" not in ga_result:
            results["algorithms"]["GeneticAlgorithmTuner"] = {
                "description": "Evolutionary / genetic algorithm tune search",
                "result_summary": {
                    "best_fitness": ga_result["best_fitness"],
                    "generations": ga_result["generations_run"],
                    "best_individual": ga_result["best_individual"],
                },
                "elapsed_ms": round(elapsed, 2),
                "quality_score": min(1.0, ga_result["best_fitness"] / 300.0),
            }

        # 5. VE Model
        t0 = time.monotonic()
        ve_model = VolumetricEfficiencyModel()
        ve_result = ve_model.generate_ve_table(engine_id)
        elapsed = (time.monotonic() - t0) * 1000
        results["algorithms"]["VolumetricEfficiencyModel"] = {
            "description": "Speed-density VE-based fuel calculation model",
            "result_summary": {
                "ve_table_generated": "error" not in ve_result,
                "rpm_points": len(ve_result.get("rpm_points", [])),
                "load_points": len(ve_result.get("load_points", [])),
            },
            "elapsed_ms": round(elapsed, 2),
            "quality_score": 0.85 if "error" not in ve_result else 0.0,
        }

        return results


# ===================================================================
# Demo / CLI entry point
# ===================================================================
if __name__ == "__main__":
    print("=" * 72)
    print("  NATOS Tuning Algorithms – Demonstration")
    print("=" * 72)

    ENGINE = "20t_i4"
    db = PerformanceDatabase()
    engine_info = db.get_engine(ENGINE)
    if engine_info is None:
        print(f"Engine '{ENGINE}' not found in database.")
        raise SystemExit(1)
    print(f"\nEngine: {engine_info['name']}  ({engine_info['stock_power_hp']} HP stock)")

    # -- 1. MapInterpolationTuner ------------------------------------
    print("\n" + "-" * 72)
    print("1. MapInterpolationTuner – 2D Map Interpolation")
    print("-" * 72)
    mit = MapInterpolationTuner()
    sample_afr = mit.interpolate_afr(ENGINE, "stock", 3500, 75)
    sample_timing = mit.interpolate_timing(ENGINE, "stock", 3500, 75)
    print(f"   AFR at 3500 RPM / 75% load (stock):    {sample_afr:.2f}")
    print(f"   Timing at 3500 RPM / 75% load (stock): {sample_timing:.1f}° BTDC")
    fuel_map = mit.generate_fuel_map(ENGINE, "power")
    timing_map = mit.generate_timing_map(ENGINE, "power")
    print(f"   Generated fuel map:   {fuel_map.get('description', 'N/A')}")
    print(f"   Generated timing map: {timing_map.get('description', 'N/A')}")

    # -- 2. PIDFuelTrimTuner -----------------------------------------
    print("\n" + "-" * 72)
    print("2. PIDFuelTrimTuner – Closed-Loop PID AFR Control")
    print("-" * 72)
    pid = PIDFuelTrimTuner(kp=2.5, ki=0.8, kd=0.15)
    disturbance = [14.7 + 1.0 * math.sin(i * 0.2) for i in range(100)]
    sim = pid.simulate(14.7, disturbance, dt=0.05)
    print(f"   Samples: {sim['samples']}, Settled: {sim['settled']}")
    print(f"   Max error: {sim['max_error']:.3f} AFR, Final trim: {sim['final_trim']:.2f}%")

    # -- 3. IterativeOptimizer ---------------------------------------
    print("\n" + "-" * 72)
    print("3. IterativeOptimizer – Hill-Climbing Optimization")
    print("-" * 72)
    opt = IterativeOptimizer()
    opt_result = opt.optimize(ENGINE, target="power", max_iterations=150)
    print(f"   Iterations: {opt_result['iterations']}, Converged: {opt_result['converged']}")
    print(f"   Best fitness: {opt_result['best_fitness']}")
    bp = opt_result["best_params"]
    print(f"   Best params → Boost: {bp['boost_psi']:.1f} PSI, AFR WOT: {bp['afr_wot']:.1f}, "
          f"Timing: {bp['timing_advance']:.1f}°")

    # -- 4. GeneticAlgorithmTuner ------------------------------------
    print("\n" + "-" * 72)
    print("4. GeneticAlgorithmTuner – Evolutionary Optimization")
    print("-" * 72)
    ga = GeneticAlgorithmTuner()
    ga_result = ga.evolve(ENGINE, generations=50, population_size=30, target="power")
    print(f"   Generations: {ga_result['generations_run']}")
    print(f"   Best fitness: {ga_result['best_fitness']}")
    bi = ga_result["best_individual"]
    if bi:
        print(f"   Best tune → Boost: {bi['boost_psi']:.1f} PSI, AFR WOT: {bi['afr_wot']:.1f}, "
              f"Timing: {bi['timing_advance']:.1f}°")
    stats = ga_result["population_stats"]
    print(f"   Final population – Best: {stats['final_best']}, Avg: {stats['final_avg']}, "
          f"Worst: {stats['final_worst']}")

    # -- 5. VolumetricEfficiencyModel --------------------------------
    print("\n" + "-" * 72)
    print("5. VolumetricEfficiencyModel – Speed-Density Fuel Calculation")
    print("-" * 72)
    ve_model = VolumetricEfficiencyModel()
    ve = VolumetricEfficiencyModel.calculate_ve(3500, 101.3, 25.0, 2.0)
    print(f"   VE at 3500 RPM, 101 kPa MAP, 25 °C IAT, 2.0 L: {ve:.2%}")
    fuel_req = VolumetricEfficiencyModel.calculate_fuel_requirement(3500, 80, ve, 12.5, 2.0)
    print(f"   Fuel requirement at 80% load, AFR 12.5:")
    print(f"     Air mass: {fuel_req['air_mass_mg']:.1f} mg, Fuel mass: {fuel_req['fuel_mass_mg']:.1f} mg")
    print(f"     Injector PW: {fuel_req['injector_pw_ms']:.2f} ms, Flow: {fuel_req['fuel_flow_cc_min']:.1f} cc/min")
    ve_table = ve_model.generate_ve_table(ENGINE)
    print(f"   VE table generated: {len(ve_table.get('rpm_points', []))} RPM × "
          f"{len(ve_table.get('load_points', []))} Load points")

    # -- 6. TuningAlgorithmComparator --------------------------------
    print("\n" + "-" * 72)
    print("6. TuningAlgorithmComparator – Head-to-Head Comparison")
    print("-" * 72)
    comp = TuningAlgorithmComparator()
    comparison = comp.compare_all(ENGINE, target="power")
    for name, info in comparison.get("algorithms", {}).items():
        print(f"   {name:30s}  Quality: {info['quality_score']:.2f}  "
              f"Time: {info['elapsed_ms']:8.2f} ms")

    print("\n" + "=" * 72)
    print("  All algorithms demonstrated successfully.")
    print("=" * 72)
