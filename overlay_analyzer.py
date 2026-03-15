"""
overlay_analyzer.py - Statistical Overlay & Comparison Engine for NATOS

Overlays and compares performance data from the PerformanceDatabase across all
engine varieties and tuning algorithms to find the "ultimate standard starting
point" for each engine category.

Classes:
  • OverlayAnalyzer      – Overlay curves & maps, compute statistical envelopes
  • StartingPointFinder   – Find consensus-optimal starting tune per category
  • PerformanceScorer     – Score and rank individual tunes
  • AnalysisReport        – Generate human-readable analysis reports

All data is sourced from the local PerformanceDatabase and tuning_algorithms
modules; no external packages required beyond the Python standard library.

Educational use only - not for real ECU tuning.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from performance_database import PerformanceDatabase
from tuning_algorithms import (
    GeneticAlgorithmTuner,
    IterativeOptimizer,
    MapInterpolationTuner,
    TuningAlgorithmComparator,
    VolumetricEfficiencyModel,
    STOICH_GASOLINE,
    STOICH_DIESEL,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENGINE_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "4cyl_turbo": {
        "label": "4-Cylinder Turbocharged",
        "match": {"cylinders": 4, "aspiration_in": [
            "turbocharged", "twin-turbocharged", "supercharged"]},
    },
    "6cyl_turbo": {
        "label": "6-Cylinder Turbocharged",
        "match": {"cylinders": 6, "aspiration_in": [
            "turbocharged", "twin-turbocharged"], "fuel_type": "gasoline"},
    },
    "v8_na": {
        "label": "V8 Naturally Aspirated",
        "match": {"cylinders": 8, "aspiration_in": ["naturally_aspirated"]},
    },
    "v8_forced": {
        "label": "V8 Forced Induction",
        "match": {"cylinders": 8, "aspiration_in": [
            "turbocharged", "twin-turbocharged", "supercharged"]},
    },
    "v6_na": {
        "label": "V6 Naturally Aspirated",
        "match": {"cylinders": 6, "aspiration_in": ["naturally_aspirated"],
                  "fuel_type": "gasoline"},
    },
    "v6_turbo": {
        "label": "V6 Turbo (all forced-induction 6-cyl)",
        "match": {"cylinders": 6, "aspiration_in": [
            "turbocharged", "twin-turbocharged", "supercharged"],
                  "fuel_type": "gasoline"},
    },
    "diesel": {
        "label": "Diesel Engines",
        "match": {"fuel_type": "diesel"},
    },
    "rotary": {
        "label": "Rotary Engines",
        "match": {"cylinders": 2},
    },
    "high_performance": {
        "label": "High Performance (>450 HP stock)",
        "match": {"min_hp": 450},
    },
    "all": {
        "label": "All Engines",
        "match": {},
    },
}

ALL_VARIANTS = ["stock", "stage1", "stage2", "stage3"]

# Scoring weights for composite scoring
_SCORE_WEIGHTS = {
    "power": 0.30,
    "torque": 0.25,
    "efficiency": 0.25,
    "safety": 0.20,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_mean(values: List[float]) -> float:
    """Return the mean of *values*, or 0.0 if empty."""
    return statistics.mean(values) if values else 0.0


def _safe_median(values: List[float]) -> float:
    """Return the median of *values*, or 0.0 if empty."""
    return statistics.median(values) if values else 0.0


def _safe_stdev(values: List[float]) -> float:
    """Return the sample stdev of *values*, or 0.0 if fewer than 2 items."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _percentile(values: List[float], pct: float) -> float:
    """Return the *pct*-th percentile (0-100) of *values*."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (pct / 100.0) * (len(s) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _envelope(values: List[float]) -> Dict[str, float]:
    """Compute a statistical envelope over a list of float values."""
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0,
                "stdev": 0.0, "p10": 0.0, "p90": 0.0, "count": 0}
    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(_safe_mean(values), 2),
        "median": round(_safe_median(values), 2),
        "stdev": round(_safe_stdev(values), 2),
        "p10": round(_percentile(values, 10), 2),
        "p90": round(_percentile(values, 90), 2),
        "count": len(values),
    }


def _engines_for_category(
    db: PerformanceDatabase,
    category: str,
) -> List[Dict[str, Any]]:
    """Return the list-engines summaries that match a category."""
    match = ENGINE_CATEGORIES.get(category, {}).get("match", {})
    all_engines = db.list_engines()
    if not match:
        return all_engines

    results: List[Dict[str, Any]] = []
    for eng in all_engines:
        ok = True
        if "cylinders" in match and eng.get("cylinders") != match["cylinders"]:
            ok = False
        if "fuel_type" in match and eng.get("fuel_type") != match["fuel_type"]:
            ok = False
        if "aspiration_in" in match:
            if eng.get("aspiration") not in match["aspiration_in"]:
                ok = False
        if "min_hp" in match:
            if eng.get("stock_power_hp", 0) < match["min_hp"]:
                ok = False
        if ok:
            results.append(eng)
    return results


# ===================================================================
# 1. OverlayAnalyzer
# ===================================================================
class OverlayAnalyzer:
    """Overlay and statistically compare performance curves across engines.

    Computes statistical envelopes (min, max, mean, median, stdev) at each
    RPM point across multiple engines/variants, enabling quick identification
    of trends, outliers, and consensus values.
    """

    def __init__(self, db: Optional[PerformanceDatabase] = None) -> None:
        self.db = db or PerformanceDatabase()

    # ---- generic 1-D curve overlay ------------------------------------
    def _overlay_1d_curves(
        self,
        engine_ids: List[str],
        variants: List[str],
        getter: str,
    ) -> Dict[str, Any]:
        """Overlay 1-D curves (RPM -> value) from multiple engines/variants.

        Args:
            engine_ids: Engine identifiers to include.
            variants:   Variant names to include (e.g. ["stock", "stage1"]).
            getter:     Name of the PerformanceDatabase method that returns
                        ``Dict[int, float]`` (e.g. ``"get_torque_curve"``).

        Returns:
            Dict with ``rpm_points`` (sorted RPM list), ``envelope`` mapping
            each RPM to its statistical envelope, ``sources`` count, and the
            raw ``curves`` list.
        """
        fetch = getattr(self.db, getter)
        curves: List[Dict[str, Any]] = []
        rpm_set: set[int] = set()

        for eid in engine_ids:
            for var in variants:
                data = fetch(eid, var)
                if data is None:
                    continue
                curves.append({
                    "engine_id": eid,
                    "variant": var,
                    "data": data,
                })
                rpm_set.update(data.keys())

        rpm_points = sorted(rpm_set)
        envelope: Dict[int, Dict[str, float]] = {}
        for rpm in rpm_points:
            vals = [c["data"][rpm] for c in curves if rpm in c["data"]]
            envelope[rpm] = _envelope(vals)

        return {
            "rpm_points": rpm_points,
            "envelope": envelope,
            "sources": len(curves),
            "curves": curves,
        }

    # ---- public 1-D overlay methods -----------------------------------
    def overlay_torque_curves(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Overlay torque curves and compute statistical envelope.

        Args:
            engine_ids: Engine identifiers to overlay.
            variants:   Variant names; defaults to all four.

        Returns:
            Dict with ``rpm_points``, ``envelope``, ``sources``, ``curves``.
        """
        variants = variants or ALL_VARIANTS
        return self._overlay_1d_curves(engine_ids, variants, "get_torque_curve")

    def overlay_power_curves(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Overlay power (HP) curves and compute statistical envelope."""
        variants = variants or ALL_VARIANTS
        return self._overlay_1d_curves(engine_ids, variants, "get_power_curve")

    def overlay_rwkw_curves(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Overlay rear-wheel kW curves and compute statistical envelope."""
        variants = variants or ALL_VARIANTS
        return self._overlay_1d_curves(engine_ids, variants, "get_rwkw_curve")

    def overlay_boost_curves(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Overlay boost pressure curves and compute statistical envelope."""
        variants = variants or ALL_VARIANTS
        return self._overlay_1d_curves(engine_ids, variants, "get_boost_curve")

    # ---- 2-D map overlay ----------------------------------------------
    def _overlay_2d_maps(
        self,
        engine_ids: List[str],
        variants: List[str],
        getter: str,
    ) -> Dict[str, Any]:
        """Overlay 2-D maps (RPM -> Load% -> value) across engines.

        Args:
            engine_ids: Engine identifiers.
            variants:   Variant names.
            getter:     Database method returning ``Dict[int, Dict[int, float]]``.

        Returns:
            Dict with ``rpm_points``, ``load_points``, ``envelope`` mapping
            ``(rpm, load)`` tuples to statistical envelopes, ``sources``.
        """
        fetch = getattr(self.db, getter)
        maps: List[Dict[str, Any]] = []
        rpm_set: set[int] = set()
        load_set: set[int] = set()

        for eid in engine_ids:
            for var in variants:
                data = fetch(eid, var)
                if data is None:
                    continue
                maps.append({
                    "engine_id": eid,
                    "variant": var,
                    "data": data,
                })
                rpm_set.update(data.keys())
                for rpm_row in data.values():
                    if isinstance(rpm_row, dict):
                        load_set.update(rpm_row.keys())

        rpm_points = sorted(rpm_set)
        load_points = sorted(load_set)

        envelope: Dict[str, Dict[str, float]] = {}
        for rpm in rpm_points:
            for load in load_points:
                vals: List[float] = []
                for m in maps:
                    row = m["data"].get(rpm)
                    if row is not None and isinstance(row, dict):
                        val = row.get(load)
                        if val is not None:
                            vals.append(val)
                key = f"{rpm}_{load}"
                envelope[key] = _envelope(vals)

        return {
            "rpm_points": rpm_points,
            "load_points": load_points,
            "envelope": envelope,
            "sources": len(maps),
        }

    def overlay_afr_maps(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Statistical analysis of AFR maps across engines/variants.

        Args:
            engine_ids: Engine identifiers.
            variants:   Variant names; defaults to all four.

        Returns:
            Dict with ``rpm_points``, ``load_points``, ``envelope``,
            ``sources``.
        """
        variants = variants or ALL_VARIANTS
        return self._overlay_2d_maps(engine_ids, variants, "get_afr_map")

    def overlay_timing_maps(
        self,
        engine_ids: List[str],
        variants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Statistical analysis of timing maps across engines/variants."""
        variants = variants or ALL_VARIANTS
        return self._overlay_2d_maps(engine_ids, variants, "get_timing_map")


# ===================================================================
# 2. StartingPointFinder
# ===================================================================
class StartingPointFinder:
    """Analyse every engine in a category to find the consensus-optimal
    starting-point tune parameters.

    Combines statistical overlay analysis with iterative and genetic
    algorithm results to produce a high-confidence recommendation.
    """

    def __init__(
        self,
        db: Optional[PerformanceDatabase] = None,
        iterative: Optional[IterativeOptimizer] = None,
        genetic: Optional[GeneticAlgorithmTuner] = None,
    ) -> None:
        self.db = db or PerformanceDatabase()
        self.iterative = iterative or IterativeOptimizer()
        self.genetic = genetic or GeneticAlgorithmTuner()
        self.overlay = OverlayAnalyzer(self.db)
        self.comparator = TuningAlgorithmComparator()

    # ---- helpers ------------------------------------------------------
    @staticmethod
    def _consensus_params(
        param_sets: List[Dict[str, float]],
    ) -> Dict[str, Any]:
        """Compute statistical consensus across many parameter sets.

        For each parameter key, computes mean, median, stdev, and a
        confidence score (inverse of normalised stdev, 0-100).

        Args:
            param_sets: List of dicts mapping parameter name -> value.

        Returns:
            Dict mapping each parameter to its consensus statistics plus
            an overall ``confidence`` score.
        """
        if not param_sets:
            return {"error": "no parameter sets provided", "confidence": 0.0}

        all_keys: set[str] = set()
        for ps in param_sets:
            all_keys.update(ps.keys())

        consensus: Dict[str, Any] = {}
        confidences: List[float] = []

        for key in sorted(all_keys):
            vals = [ps[key] for ps in param_sets if key in ps]
            if not vals:
                continue
            mean_v = _safe_mean(vals)
            std_v = _safe_stdev(vals)
            med_v = _safe_median(vals)
            # Confidence: 100 when stdev == 0 (perfect agreement)
            range_v = max(vals) - min(vals) if len(vals) > 1 else 1.0
            conf = 100.0 * (1.0 - min(std_v / max(range_v, 1e-9), 1.0))
            conf = round(max(0.0, min(100.0, conf)), 1)
            confidences.append(conf)
            consensus[key] = {
                "recommended": round(med_v, 3),
                "mean": round(mean_v, 3),
                "median": round(med_v, 3),
                "stdev": round(std_v, 3),
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
                "confidence": conf,
                "sample_size": len(vals),
            }

        overall_confidence = round(_safe_mean(confidences), 1) if confidences else 0.0

        return {
            "parameters": consensus,
            "confidence": overall_confidence,
        }

    # ---- primary methods ----------------------------------------------
    def find_optimal_starting_point(
        self,
        category: str,
        target: str = "power",
        ga_generations: int = 60,
        ga_population: int = 30,
        iter_max: int = 120,
    ) -> Dict[str, Any]:
        """Find the ultimate standard starting point for a category.

        Steps:
          1. Gather all engines matching *category*.
          2. For each engine, collect data from all stock + tuned variants.
          3. Run iterative and genetic optimisers on each engine.
          4. Compute consensus optimal parameters via statistical analysis.
          5. Return a comprehensive starting-point recommendation.

        Args:
            category:       Engine category key (see ENGINE_CATEGORIES).
            target:         Optimisation target: "power", "economy", or
                            "balanced".
            ga_generations: Generations for the genetic algorithm.
            ga_population:  Population size for the genetic algorithm.
            iter_max:       Max iterations for the iterative optimiser.

        Returns:
            Dict with ``category``, ``engines_analysed``, ``tune_parameters``
            (consensus), ``confidence``, ``supporting_data``, and
            ``recommended_adjustments``.
        """
        engines = _engines_for_category(self.db, category)
        if not engines:
            return {"error": f"No engines found for category '{category}'",
                    "category": category}

        engine_ids = [e["engine_id"] for e in engines]

        # Collect algorithm results for every engine
        all_params: List[Dict[str, float]] = []
        per_engine: Dict[str, Dict[str, Any]] = {}

        for eid in engine_ids:
            engine_results: Dict[str, Any] = {"engine_id": eid}

            # Iterative optimiser
            iter_res = self.iterative.optimize(
                eid, target=target, max_iterations=iter_max)
            if "best_params" in iter_res:
                all_params.append(iter_res["best_params"])
                engine_results["iterative"] = {
                    "best_params": iter_res["best_params"],
                    "fitness": iter_res.get("best_fitness", 0.0),
                    "converged": iter_res.get("converged", False),
                }

            # Genetic algorithm
            ga_res = self.genetic.evolve(
                eid, generations=ga_generations,
                population_size=ga_population, target=target)
            if "best_individual" in ga_res:
                all_params.append(ga_res["best_individual"])
                engine_results["genetic"] = {
                    "best_params": ga_res["best_individual"],
                    "fitness": ga_res.get("best_fitness", 0.0),
                }

            per_engine[eid] = engine_results

        # Statistical consensus
        consensus = self._consensus_params(all_params)

        # Build recommended adjustments per sub-category
        recommended_adjustments = self._build_adjustments(
            consensus, engines, target)

        # Overlay data for context
        torque_overlay = self.overlay.overlay_torque_curves(
            engine_ids, ALL_VARIANTS)
        power_overlay = self.overlay.overlay_power_curves(
            engine_ids, ALL_VARIANTS)

        return {
            "category": category,
            "category_label": ENGINE_CATEGORIES.get(
                category, {}).get("label", category),
            "target": target,
            "engines_analysed": len(engines),
            "engine_ids": engine_ids,
            "tune_parameters": consensus.get("parameters", {}),
            "confidence": consensus.get("confidence", 0.0),
            "supporting_data": {
                "per_engine_results": per_engine,
                "parameter_sets_count": len(all_params),
                "torque_envelope_sample": {
                    rpm: torque_overlay["envelope"][rpm]
                    for rpm in list(torque_overlay["rpm_points"])[:5]
                } if torque_overlay["rpm_points"] else {},
                "power_envelope_sample": {
                    rpm: power_overlay["envelope"][rpm]
                    for rpm in list(power_overlay["rpm_points"])[:5]
                } if power_overlay["rpm_points"] else {},
            },
            "recommended_adjustments": recommended_adjustments,
        }

    def _build_adjustments(
        self,
        consensus: Dict[str, Any],
        engines: List[Dict[str, Any]],
        target: str,
    ) -> Dict[str, str]:
        """Generate human-readable adjustment notes based on consensus data.

        Args:
            consensus: Output of ``_consensus_params``.
            engines:   List of engine summaries in the category.
            target:    Optimisation target.

        Returns:
            Dict mapping adjustment area to recommendation string.
        """
        adjustments: Dict[str, str] = {}
        params = consensus.get("parameters", {})

        if "boost_psi" in params:
            bp = params["boost_psi"]
            if bp["stdev"] > 3.0:
                adjustments["boost"] = (
                    f"High variance (stdev {bp['stdev']}). "
                    f"Start at median {bp['median']} PSI and adjust per "
                    "engine response.")
            else:
                adjustments["boost"] = (
                    f"Good agreement at {bp['recommended']} PSI "
                    f"(confidence {bp['confidence']}%).")

        if "afr_wot" in params:
            afr = params["afr_wot"]
            adjustments["afr"] = (
                f"Target WOT AFR {afr['recommended']}:1 "
                f"(range {afr['min']}-{afr['max']}).")

        if "timing_advance" in params:
            ta = params["timing_advance"]
            adjustments["timing"] = (
                f"Recommended timing {ta['recommended']}° BTDC. "
                f"Watch for knock above {ta['p90']}° on lower-octane fuel."
                if "p90" in ta else
                f"Recommended timing {ta['recommended']}° BTDC.")

        if "rev_limit" in params:
            rl = params["rev_limit"]
            adjustments["rev_limit"] = (
                f"Consensus rev limit {rl['recommended']} RPM "
                f"(range {rl['min']}-{rl['max']}).")

        if target == "economy":
            adjustments["general"] = (
                "Economy target: lean AFR at part-throttle, reduce boost "
                "where possible.")
        elif target == "power":
            adjustments["general"] = (
                "Power target: richer WOT AFR for safety margin, maximise "
                "boost within hardware limits.")
        else:
            adjustments["general"] = (
                "Balanced target: trade off peak power for broader "
                "torque band and fuel efficiency.")

        return adjustments

    def find_all_starting_points(
        self,
        target: str = "power",
        ga_generations: int = 60,
        ga_population: int = 30,
        iter_max: int = 120,
    ) -> Dict[str, Dict[str, Any]]:
        """Run ``find_optimal_starting_point`` for every category.

        Args:
            target:         Optimisation target.
            ga_generations: GA generations per engine.
            ga_population:  GA population size.
            iter_max:       Iterative optimiser max iterations.

        Returns:
            Dict mapping category key to its starting-point result.
        """
        results: Dict[str, Dict[str, Any]] = {}
        for cat in ENGINE_CATEGORIES:
            results[cat] = self.find_optimal_starting_point(
                cat, target=target, ga_generations=ga_generations,
                ga_population=ga_population, iter_max=iter_max)
        return results

    def rank_tuning_approaches(
        self,
        engine_id: str,
        target: str = "power",
    ) -> Dict[str, Any]:
        """Compare which tuning algorithm works best for a specific engine.

        Runs the ``TuningAlgorithmComparator`` and ranks algorithms by
        quality score.

        Args:
            engine_id: Engine to analyse.
            target:    Optimisation target.

        Returns:
            Dict with ``engine_id``, ``ranking`` (list sorted best-first),
            and the full ``comparison`` data.
        """
        comparison = self.comparator.compare_all(engine_id, target=target)
        algos = comparison.get("algorithms", {})

        ranking: List[Dict[str, Any]] = []
        for name, info in algos.items():
            ranking.append({
                "algorithm": name,
                "quality_score": info.get("quality_score", 0.0),
                "elapsed_ms": info.get("elapsed_ms", 0.0),
            })
        ranking.sort(key=lambda x: x["quality_score"], reverse=True)

        return {
            "engine_id": engine_id,
            "target": target,
            "ranking": ranking,
            "comparison": comparison,
        }


# ===================================================================
# 3. PerformanceScorer
# ===================================================================
class PerformanceScorer:
    """Score and rank engine tunes on power, torque, efficiency, and safety."""

    def __init__(self, db: Optional[PerformanceDatabase] = None) -> None:
        self.db = db or PerformanceDatabase()

    # ---- scoring helpers -----------------------------------------------
    @staticmethod
    def _power_score(
        peak_hp: float,
        stock_hp: float,
    ) -> float:
        """Score power on 0-100 scale based on percentage gain.

        100 = 50 %+ gain over stock, 50 = matches stock, 0 = no data.
        """
        if stock_hp <= 0:
            return 0.0
        ratio = peak_hp / stock_hp
        return round(max(0.0, min(100.0, ratio * 50.0)), 1)

    @staticmethod
    def _torque_score(
        peak_tq: float,
        stock_tq: float,
    ) -> float:
        """Score torque on 0-100 scale based on percentage gain."""
        if stock_tq <= 0:
            return 0.0
        ratio = peak_tq / stock_tq
        return round(max(0.0, min(100.0, ratio * 50.0)), 1)

    @staticmethod
    def _efficiency_score(
        afr_map: Optional[Dict[int, Dict[int, float]]],
        fuel_type: str = "gasoline",
    ) -> float:
        """Score efficiency 0-100 by closeness to stoichiometric AFR.

        Engines that hold AFR near stoich at cruise (30-70 % load) score
        highest.
        """
        if afr_map is None:
            return 50.0  # neutral when no data available
        stoich = STOICH_DIESEL if fuel_type == "diesel" else STOICH_GASOLINE
        deviations: List[float] = []
        for rpm, loads in afr_map.items():
            if not isinstance(loads, dict):
                continue
            for load, afr in loads.items():
                if 30 <= load <= 70:
                    deviations.append(abs(afr - stoich))
        if not deviations:
            return 50.0
        avg_dev = _safe_mean(deviations)
        # Perfect = 0 deviation -> 100; 3+ deviation -> ~0
        return round(max(0.0, min(100.0, 100.0 - avg_dev * 33.3)), 1)

    @staticmethod
    def _safety_score(
        afr_map: Optional[Dict[int, Dict[int, float]]],
        timing_map: Optional[Dict[int, Dict[int, float]]],
        fuel_type: str = "gasoline",
    ) -> float:
        """Score safety 0-100 based on AFR and timing limits.

        Penalties for dangerously lean WOT AFR (>13.5 gasoline) or
        excessive timing advance (>40°).
        """
        score = 100.0

        if afr_map is not None:
            lean_limit = 13.5 if fuel_type == "gasoline" else 16.0
            for rpm, loads in afr_map.items():
                if not isinstance(loads, dict):
                    continue
                wot_afr = loads.get(100) or loads.get(90)
                if wot_afr is not None and wot_afr > lean_limit:
                    score -= min(15.0, (wot_afr - lean_limit) * 10.0)

        if timing_map is not None:
            for rpm, loads in timing_map.items():
                if not isinstance(loads, dict):
                    continue
                for load, timing in loads.items():
                    if timing > 40.0:
                        score -= min(5.0, (timing - 40.0) * 2.0)

        return round(max(0.0, min(100.0, score)), 1)

    # ---- public API ----------------------------------------------------
    def score_tune(
        self,
        engine_id: str,
        variant: str = "stock",
    ) -> Dict[str, Any]:
        """Score an engine variant on power, torque, efficiency, and safety.

        Args:
            engine_id: Engine identifier.
            variant:   Variant name (``"stock"``, ``"stage1"``, etc.).

        Returns:
            Dict with individual scores, composite score (0-100), and
            engine metadata.  Returns an ``error`` key on failure.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        stock_hp = engine.get("stock_power_hp", 0)
        stock_tq = engine.get("stock_torque_nm", 0)
        fuel_type = engine.get("fuel_type", "gasoline")

        # Resolve peak figures for the variant
        if variant == "stock":
            peak_hp = stock_hp
            peak_tq = stock_tq
        else:
            tv = engine.get("tuned_variants", {}).get(variant)
            if tv is None:
                return {"error": f"Variant '{variant}' not found for "
                        f"engine '{engine_id}'"}
            peak_hp = tv.get("peak_power_hp", stock_hp)
            peak_tq = tv.get("peak_torque_nm", stock_tq)

        afr_map = self.db.get_afr_map(engine_id, variant)
        timing_map = self.db.get_timing_map(engine_id, variant)

        pwr = self._power_score(peak_hp, stock_hp)
        tq = self._torque_score(peak_tq, stock_tq)
        eff = self._efficiency_score(afr_map, fuel_type)
        safe = self._safety_score(afr_map, timing_map, fuel_type)

        composite = round(
            pwr * _SCORE_WEIGHTS["power"]
            + tq * _SCORE_WEIGHTS["torque"]
            + eff * _SCORE_WEIGHTS["efficiency"]
            + safe * _SCORE_WEIGHTS["safety"],
            1,
        )

        return {
            "engine_id": engine_id,
            "variant": variant,
            "scores": {
                "power": pwr,
                "torque": tq,
                "efficiency": eff,
                "safety": safe,
            },
            "composite": composite,
            "peak_power_hp": peak_hp,
            "peak_torque_nm": peak_tq,
        }

    def rank_variants(
        self,
        engine_id: str,
    ) -> Dict[str, Any]:
        """Rank all variants of an engine by composite score.

        Args:
            engine_id: Engine identifier.

        Returns:
            Dict with ``engine_id``, ``ranking`` (list sorted best-first),
            and ``best_variant``.
        """
        scores: List[Dict[str, Any]] = []
        for var in ALL_VARIANTS:
            result = self.score_tune(engine_id, var)
            if "error" not in result:
                scores.append(result)

        scores.sort(key=lambda s: s["composite"], reverse=True)

        return {
            "engine_id": engine_id,
            "ranking": scores,
            "best_variant": scores[0]["variant"] if scores else None,
        }

    def find_best_in_class(
        self,
        category: str,
        metric: str = "composite",
    ) -> Dict[str, Any]:
        """Find the best engine/tune combo in a category for a metric.

        Args:
            category: Engine category key.
            metric:   One of ``"composite"``, ``"power"``, ``"torque"``,
                      ``"efficiency"``, ``"safety"``.

        Returns:
            Dict with ``category``, ``metric``, ``best`` entry, and full
            ``results`` list sorted descending.
        """
        engines = _engines_for_category(self.db, category)
        results: List[Dict[str, Any]] = []

        for eng in engines:
            eid = eng["engine_id"]
            for var in ALL_VARIANTS:
                scored = self.score_tune(eid, var)
                if "error" in scored:
                    continue
                if metric in scored.get("scores", {}):
                    sort_val = scored["scores"][metric]
                elif metric == "composite":
                    sort_val = scored["composite"]
                else:
                    sort_val = scored.get(metric, 0)
                scored["_sort_val"] = sort_val
                results.append(scored)

        results.sort(key=lambda r: r.get("_sort_val", 0), reverse=True)

        # Strip internal sort key
        for r in results:
            r.pop("_sort_val", None)

        return {
            "category": category,
            "category_label": ENGINE_CATEGORIES.get(
                category, {}).get("label", category),
            "metric": metric,
            "best": results[0] if results else None,
            "results": results,
        }


# ===================================================================
# 4. AnalysisReport
# ===================================================================
class AnalysisReport:
    """Generate human-readable analysis reports from overlay and scoring data."""

    def __init__(
        self,
        db: Optional[PerformanceDatabase] = None,
    ) -> None:
        self.db = db or PerformanceDatabase()
        self.scorer = PerformanceScorer(self.db)
        self.overlay = OverlayAnalyzer(self.db)
        self.finder = StartingPointFinder(self.db)

    # ---- formatting helpers -------------------------------------------
    @staticmethod
    def _section(title: str, width: int = 60) -> str:
        """Return a formatted section header."""
        return f"\n{'=' * width}\n  {title}\n{'=' * width}"

    @staticmethod
    def _kv(key: str, value: Any, indent: int = 2) -> str:
        """Return a key-value line."""
        return f"{' ' * indent}{key:.<30s} {value}"

    # ---- report generators --------------------------------------------
    def generate_engine_report(
        self,
        engine_id: str,
    ) -> Dict[str, Any]:
        """Generate a complete analysis report for one engine.

        Args:
            engine_id: Engine identifier.

        Returns:
            Dict with ``engine_id``, ``summary`` dict, ``variant_ranking``,
            ``algorithm_ranking``, and ``text_report`` string.
        """
        engine = self.db.get_engine(engine_id)
        if engine is None:
            return {"error": f"Engine '{engine_id}' not found"}

        variant_ranking = self.scorer.rank_variants(engine_id)
        algo_ranking = self.finder.rank_tuning_approaches(engine_id)

        lines: List[str] = []
        lines.append(self._section(
            f"Engine Report: {engine.get('name', engine_id)}"))

        lines.append("\n  Specifications:")
        for key in ("displacement", "cylinders", "aspiration", "fuel_type",
                     "redline", "rev_limit", "stock_power_hp",
                     "stock_torque_nm"):
            lines.append(self._kv(key, engine.get(key, "N/A")))

        lines.append("\n  Variant Ranking (best first):")
        for i, v in enumerate(variant_ranking.get("ranking", []), 1):
            lines.append(
                f"    {i}. {v['variant']:8s}  composite={v['composite']:.1f}"
                f"  power={v['scores']['power']:.1f}"
                f"  torque={v['scores']['torque']:.1f}"
                f"  efficiency={v['scores']['efficiency']:.1f}"
                f"  safety={v['scores']['safety']:.1f}")

        lines.append("\n  Algorithm Ranking:")
        for i, a in enumerate(algo_ranking.get("ranking", []), 1):
            lines.append(
                f"    {i}. {a['algorithm']:.<32s}"
                f" quality={a['quality_score']:.3f}"
                f"  time={a['elapsed_ms']:.0f}ms")

        text_report = "\n".join(lines)

        return {
            "engine_id": engine_id,
            "summary": {
                "name": engine.get("name"),
                "stock_power_hp": engine.get("stock_power_hp"),
                "stock_torque_nm": engine.get("stock_torque_nm"),
                "best_variant": variant_ranking.get("best_variant"),
            },
            "variant_ranking": variant_ranking,
            "algorithm_ranking": algo_ranking,
            "text_report": text_report,
        }

    def generate_category_report(
        self,
        category: str,
    ) -> Dict[str, Any]:
        """Generate a category-wide analysis report.

        Args:
            category: Engine category key.

        Returns:
            Dict with ``category``, ``engines``, ``best_in_class``,
            ``overlay_stats``, and ``text_report``.
        """
        engines = _engines_for_category(self.db, category)
        if not engines:
            return {"error": f"No engines in category '{category}'"}

        engine_ids = [e["engine_id"] for e in engines]
        cat_label = ENGINE_CATEGORIES.get(
            category, {}).get("label", category)

        best_power = self.scorer.find_best_in_class(category, "power")
        best_eff = self.scorer.find_best_in_class(category, "efficiency")
        best_comp = self.scorer.find_best_in_class(category, "composite")

        torque_ov = self.overlay.overlay_torque_curves(
            engine_ids, ALL_VARIANTS)
        power_ov = self.overlay.overlay_power_curves(
            engine_ids, ALL_VARIANTS)

        lines: List[str] = []
        lines.append(self._section(f"Category Report: {cat_label}"))
        lines.append(f"\n  Engines in category: {len(engines)}")
        for e in engines:
            lines.append(f"    • {e['engine_id']:.<20s} {e['name']}"
                         f"  ({e['stock_power_hp']} HP)")

        lines.append("\n  Best in Class:")
        if best_power.get("best"):
            bp = best_power["best"]
            lines.append(
                f"    Power ..... {bp['engine_id']} / {bp['variant']}"
                f"  (score {bp['scores']['power']:.1f})")
        if best_eff.get("best"):
            be = best_eff["best"]
            lines.append(
                f"    Efficiency. {be['engine_id']} / {be['variant']}"
                f"  (score {be['scores']['efficiency']:.1f})")
        if best_comp.get("best"):
            bc = best_comp["best"]
            lines.append(
                f"    Composite.. {bc['engine_id']} / {bc['variant']}"
                f"  (score {bc['composite']:.1f})")

        lines.append(f"\n  Torque Overlay ({torque_ov['sources']} curves):")
        for rpm in list(torque_ov["rpm_points"])[:6]:
            env = torque_ov["envelope"][rpm]
            lines.append(
                f"    {rpm:>5d} RPM  "
                f"mean={env['mean']:.1f}  "
                f"range=[{env['min']:.1f} - {env['max']:.1f}]  "
                f"stdev={env['stdev']:.1f}")

        lines.append(f"\n  Power Overlay ({power_ov['sources']} curves):")
        for rpm in list(power_ov["rpm_points"])[:6]:
            env = power_ov["envelope"][rpm]
            lines.append(
                f"    {rpm:>5d} RPM  "
                f"mean={env['mean']:.1f} HP  "
                f"range=[{env['min']:.1f} - {env['max']:.1f}]  "
                f"stdev={env['stdev']:.1f}")

        text_report = "\n".join(lines)

        return {
            "category": category,
            "category_label": cat_label,
            "engines": engines,
            "best_in_class": {
                "power": best_power.get("best"),
                "efficiency": best_eff.get("best"),
                "composite": best_comp.get("best"),
            },
            "overlay_stats": {
                "torque_sources": torque_ov["sources"],
                "power_sources": power_ov["sources"],
            },
            "text_report": text_report,
        }

    def generate_starting_point_report(
        self,
        category: str,
        target: str = "power",
    ) -> Dict[str, Any]:
        """Detailed report on the optimal starting point for a category.

        Args:
            category: Engine category key.
            target:   Optimisation target.

        Returns:
            Dict with ``category``, ``starting_point`` data, and
            ``text_report``.
        """
        sp = self.finder.find_optimal_starting_point(
            category, target=target)

        if "error" in sp:
            return sp

        cat_label = sp.get("category_label", category)

        lines: List[str] = []
        lines.append(self._section(
            f"Starting Point Report: {cat_label}"))
        lines.append(f"\n  Target: {sp['target']}")
        lines.append(f"  Engines analysed: {sp['engines_analysed']}")
        lines.append(f"  Overall confidence: {sp['confidence']:.1f}%")

        lines.append("\n  Recommended Tune Parameters:")
        for pname, pdata in sp.get("tune_parameters", {}).items():
            lines.append(
                f"    {pname:.<24s} {pdata['recommended']:>8.2f}"
                f"  (±{pdata['stdev']:.2f},"
                f" conf {pdata['confidence']:.0f}%,"
                f" n={pdata['sample_size']})")

        lines.append("\n  Adjustment Notes:")
        for area, note in sp.get("recommended_adjustments", {}).items():
            lines.append(f"    [{area}] {note}")

        text_report = "\n".join(lines)

        return {
            "category": category,
            "category_label": cat_label,
            "starting_point": sp,
            "text_report": text_report,
        }


# ===================================================================
# Main - demonstration & quick-reference
# ===================================================================
if __name__ == "__main__":
    print("=" * 64)
    print("  NATOS Overlay Analyzer - Ultimate Starting Point Finder")
    print("=" * 64)

    # 1. Create core objects
    db = PerformanceDatabase()
    analyzer = OverlayAnalyzer(db)
    scorer = PerformanceScorer(db)
    finder = StartingPointFinder(db)
    report = AnalysisReport(db)

    # 2. Quick overlay analysis on 4cyl_turbo engines
    cat_engines = _engines_for_category(db, "4cyl_turbo")
    cat_ids = [e["engine_id"] for e in cat_engines]
    print(f"\n--- Overlay Analysis: 4cyl_turbo ({len(cat_ids)} engines) ---")
    torque_ov = analyzer.overlay_torque_curves(cat_ids, ["stock", "stage1"])
    print(f"  Torque overlay sources: {torque_ov['sources']}")
    for rpm in list(torque_ov["rpm_points"])[:5]:
        env = torque_ov["envelope"][rpm]
        print(f"    {rpm:>5d} RPM  mean={env['mean']:.1f} Nm"
              f"  range=[{env['min']:.1f} - {env['max']:.1f}]"
              f"  stdev={env['stdev']:.1f}")

    # 3. Find the optimal starting point for 4cyl_turbo
    print("\n--- Finding Optimal Starting Point: 4cyl_turbo ---")
    sp = finder.find_optimal_starting_point("4cyl_turbo", target="power")
    print(f"  Engines analysed: {sp['engines_analysed']}")
    print(f"  Overall confidence: {sp['confidence']:.1f}%")
    print("  Recommended tune parameters:")
    for pname, pdata in sp.get("tune_parameters", {}).items():
        print(f"    {pname:.<24s} {pdata['recommended']:>8.2f}"
              f"  stdev={pdata['stdev']:.2f}"
              f"  conf={pdata['confidence']:.0f}%")

    # 4. Score and rank engine variants
    print("\n--- Variant Ranking: 20t_i4 ---")
    ranking = scorer.rank_variants("20t_i4")
    for i, v in enumerate(ranking.get("ranking", []), 1):
        print(f"  {i}. {v['variant']:8s}  composite={v['composite']:.1f}"
              f"  P={v['scores']['power']:.1f}"
              f"  T={v['scores']['torque']:.1f}"
              f"  E={v['scores']['efficiency']:.1f}"
              f"  S={v['scores']['safety']:.1f}")

    # 5. Best in class
    print("\n--- Best in Class: 4cyl_turbo (composite) ---")
    bic = scorer.find_best_in_class("4cyl_turbo", "composite")
    if bic.get("best"):
        b = bic["best"]
        print(f"  Winner: {b['engine_id']} / {b['variant']}"
              f"  composite={b['composite']:.1f}")

    # 6. Generate starting point report
    print("\n--- Starting Point Report: 4cyl_turbo ---")
    sp_report = report.generate_starting_point_report(
        "4cyl_turbo", target="power")
    print(sp_report.get("text_report", "No report generated."))

    # 7. Print ultimate summary
    print("\n" + "=" * 64)
    print("  ULTIMATE STANDARD STARTING POINT - 4cyl_turbo")
    print("=" * 64)
    params = sp.get("tune_parameters", {})
    for pname, pdata in params.items():
        print(f"  {pname:.<28s} {pdata['recommended']}")
    print(f"  {'confidence':.<28s} {sp['confidence']:.1f}%")
    print(f"  {'engines sampled':.<28s} {sp['engines_analysed']}")
    print("=" * 64)
