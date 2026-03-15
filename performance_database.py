"""
NATOS Performance Database Module
Comprehensive engine performance database for the NATOS ECU tuning system.

Contains dyno sheet data, torque curves, power curves, boost maps, AFR maps,
timing maps, RWKW (rear-wheel kilowatt) data, and wheel speed data across
15 distinct engine profiles spanning inline-4 turbo, V6, V8, rotary, diesel,
and high-performance platforms.

Each engine includes stock and tuned variant data (stage1, stage2, stage3)
with realistic values derived from well-known engine architectures.

Educational use only - not for real ECU tuning.
"""

from typing import Dict, List, Any, Optional
import math


# ---------------------------------------------------------------------------
# Helper utilities for realistic data generation
# ---------------------------------------------------------------------------

def _interpolate(x: float, points: Dict[int, float]) -> float:
    """
    Linearly interpolate a value from a dict of {x: y} key points.

    Args:
        x: The x value to interpolate at
        points: Dict mapping x -> y at known key points

    Returns:
        Interpolated y value
    """
    keys = sorted(points.keys())
    if x <= keys[0]:
        return points[keys[0]]
    if x >= keys[-1]:
        return points[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= x <= keys[i + 1]:
            x0, x1 = keys[i], keys[i + 1]
            y0, y1 = points[x0], points[x1]
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[keys[-1]]


def _build_dyno_data(torque_points: Dict[int, float],
                     rpm_min: int, rpm_max: int,
                     step: int = 500) -> Dict[int, Dict[str, float]]:
    """
    Generate complete dyno data from torque curve key points.

    Power calculated via HP = Torque_Nm * RPM / 7121, kW = HP * 0.7457.

    Args:
        torque_points: RPM -> Torque (Nm) key points
        rpm_min: Starting RPM
        rpm_max: Ending RPM (inclusive)
        step: RPM increment between data points

    Returns:
        Dict of RPM -> {torque_nm, power_hp, power_kw}
    """
    rpms = set(range(rpm_min, rpm_max + 1, step))
    rpms.add(rpm_max)
    # Include torque-curve key points for accurate peak capture
    for k in torque_points:
        if rpm_min <= k <= rpm_max:
            rpms.add(k)

    data: Dict[int, Dict[str, float]] = {}
    for rpm in sorted(rpms):
        torque_nm = round(_interpolate(rpm, torque_points), 1)
        power_hp = round(torque_nm * rpm / 7121.0, 1)
        power_kw = round(power_hp * 0.7457, 1)
        data[rpm] = {
            "torque_nm": torque_nm,
            "power_hp": power_hp,
            "power_kw": power_kw,
        }
    return data


def _build_rwkw_data(dyno_data: Dict[int, Dict[str, float]],
                     drivetrain_loss: float = 0.15) -> Dict[int, float]:
    """
    Generate rear-wheel kilowatt data accounting for drivetrain loss.

    Typical losses: RWD manual 12-15 %, AWD 18-25 %, FWD manual 10-12 %.

    Args:
        dyno_data: Output from _build_dyno_data
        drivetrain_loss: Fraction of power lost through drivetrain

    Returns:
        Dict of RPM -> RWKW value
    """
    factor = 1.0 - drivetrain_loss
    return {rpm: round(d["power_kw"] * factor, 1) for rpm, d in dyno_data.items()}


def _build_wheel_speed_data(rpm_points: List[int],
                            gear_ratios: List[float],
                            final_drive: float,
                            tire_circumference: float) -> Dict[int, Dict[str, float]]:
    """
    Generate wheel speed (km/h) for each gear at each RPM.

    Formula: speed = (RPM / (gear_ratio * final_drive)) * tire_circ * 60 / 1000

    Args:
        rpm_points: List of RPM values
        gear_ratios: Gear ratios ordered [1st, 2nd, ...]
        final_drive: Final drive ratio
        tire_circumference: Tire circumference in metres

    Returns:
        Dict of RPM -> {gear_1: km/h, gear_2: km/h, ...}
    """
    data: Dict[int, Dict[str, float]] = {}
    for rpm in rpm_points:
        speeds: Dict[str, float] = {}
        for i, ratio in enumerate(gear_ratios, start=1):
            wheel_rpm = rpm / (ratio * final_drive)
            speed_kmh = wheel_rpm * tire_circumference * 60.0 / 1000.0
            speeds[f"gear_{i}"] = round(speed_kmh, 1)
        data[rpm] = speeds
    return data


def _build_boost_map(rpm_points: List[int],
                     peak_boost_psi: float,
                     onset_rpm: int,
                     full_boost_rpm: int) -> Dict[int, float]:
    """
    Generate boost pressure curve for forced-induction engines.

    Models vacuum at idle, spool from onset RPM to peak, slight taper near
    redline from exhaust back-pressure.

    Args:
        rpm_points: RPM values
        peak_boost_psi: Maximum boost in PSI
        onset_rpm: RPM where positive boost begins
        full_boost_rpm: RPM where peak boost is achieved

    Returns:
        Dict of RPM -> boost PSI
    """
    data: Dict[int, float] = {}
    for rpm in rpm_points:
        if rpm < onset_rpm:
            boost = -15.0 + (rpm / onset_rpm) * 10.0
            boost = max(boost, -15.0)
        elif rpm < full_boost_rpm:
            t = (rpm - onset_rpm) / max(full_boost_rpm - onset_rpm, 1)
            boost = t * peak_boost_psi
        else:
            overshoot = (rpm - full_boost_rpm) / 3000.0
            boost = peak_boost_psi * (1.0 - overshoot * 0.08)
            boost = max(boost, peak_boost_psi * 0.85)
        data[rpm] = round(boost, 1)
    return data


def _build_afr_map(rpm_points: List[int],
                   load_points: List[int],
                   fuel_type: str = "gasoline",
                   aspiration: str = "turbocharged") -> Dict[int, Dict[int, float]]:
    """
    Generate air-fuel ratio map indexed by RPM and load%.

    Gasoline stoichiometric: 14.7:1.  Enriched under load for cooling /
    power, leaner at cruise for economy.  Diesel runs much leaner overall.

    Args:
        rpm_points: RPM values
        load_points: Load percentages [0 .. 100]
        fuel_type: 'gasoline' or 'diesel'
        aspiration: Engine aspiration type

    Returns:
        Nested dict  RPM -> load% -> AFR
    """
    is_forced = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
    afr_map: Dict[int, Dict[int, float]] = {}
    for rpm in rpm_points:
        afr_map[rpm] = {}
        for load in load_points:
            if fuel_type == "diesel":
                if load <= 20:
                    afr = 40.0 - (rpm / 1000.0) * 1.5
                elif load <= 60:
                    afr = 30.0 - load * 0.15 - (rpm / 1000.0) * 0.8
                else:
                    afr = 22.0 - (load - 60) * 0.1 - (rpm / 1000.0) * 0.5
                afr = max(afr, 18.0)
            else:
                if load <= 10:
                    afr = 14.7 + (rpm / 10000.0) * 0.3
                elif load <= 40:
                    afr = 14.7
                elif load <= 70:
                    enrich = (load - 40) / 30.0
                    afr = 14.7 - enrich * 2.0
                    if is_forced:
                        afr -= 0.3
                else:
                    base = 12.3 if is_forced else 12.7
                    enrich = (load - 70) / 30.0
                    afr = base - enrich * 1.2
                    afr -= (rpm / 10000.0) * 0.3
                afr = max(afr, 10.8)
            afr_map[rpm][load] = round(afr, 2)
    return afr_map


def _build_timing_map(rpm_points: List[int],
                      load_points: List[int],
                      aspiration: str = "turbocharged",
                      fuel_type: str = "gasoline") -> Dict[int, Dict[int, float]]:
    """
    Generate ignition timing map (degrees BTDC) indexed by RPM and load%.

    Higher advance at low load, retarded under high load / boost to
    prevent knock.  NA engines tolerate more advance than forced-induction.

    Args:
        rpm_points: RPM values
        load_points: Load percentages
        aspiration: Engine aspiration type
        fuel_type: 'gasoline' or 'diesel'

    Returns:
        Nested dict  RPM -> load% -> timing degrees
    """
    is_forced = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
    timing_map: Dict[int, Dict[int, float]] = {}
    for rpm in rpm_points:
        timing_map[rpm] = {}
        rpm_factor = min(rpm / 6000.0, 1.0)
        for load in load_points:
            if fuel_type == "diesel":
                base = 8.0 + rpm_factor * 6.0
                load_retard = (load / 100.0) * 4.0
                timing = base - load_retard
            elif is_forced:
                base = 12.0 + rpm_factor * 16.0
                load_retard = (load / 100.0) * 18.0
                timing = base - load_retard
            else:
                base = 15.0 + rpm_factor * 20.0
                load_retard = (load / 100.0) * 12.0
                timing = base - load_retard
            if load > 80 and rpm_factor > 0.7:
                timing -= 3.0
            timing = max(timing, 2.0)
            timing_map[rpm][load] = round(timing, 1)
    return timing_map


def _build_injector_duty_map(rpm_points: List[int],
                             load_points: List[int],
                             base_max_duty: float = 80.0) -> Dict[int, Dict[int, float]]:
    """
    Generate injector duty-cycle map (%) indexed by RPM and load%.

    Args:
        rpm_points: RPM values
        load_points: Load percentages
        base_max_duty: Maximum duty at full load / redline

    Returns:
        Nested dict  RPM -> load% -> duty %
    """
    duty_map: Dict[int, Dict[int, float]] = {}
    max_rpm = max(rpm_points)
    for rpm in rpm_points:
        duty_map[rpm] = {}
        rpm_f = rpm / max_rpm
        for load in load_points:
            load_f = load / 100.0
            duty = 3.0 + load_f * rpm_f * (base_max_duty - 3.0)
            duty = max(duty, 2.5 + rpm_f * 5.0)
            duty = min(duty, 98.0)
            duty_map[rpm][load] = round(duty, 1)
    return duty_map


def _build_egt_map(rpm_points: List[int],
                   load_points: List[int],
                   aspiration: str = "turbocharged",
                   fuel_type: str = "gasoline") -> Dict[int, Dict[int, float]]:
    """
    Generate exhaust gas temperature map (°F) indexed by RPM and load%.

    EGT rises with load and RPM.  Turbo engines run hotter; diesels
    generally lower than gasoline.

    Args:
        rpm_points: RPM values
        load_points: Load percentages
        aspiration: Engine aspiration type
        fuel_type: 'gasoline' or 'diesel'

    Returns:
        Nested dict  RPM -> load% -> EGT °F
    """
    is_forced = aspiration in ("turbocharged", "supercharged", "twin-turbocharged")
    egt_map: Dict[int, Dict[int, float]] = {}
    max_rpm = max(rpm_points)
    for rpm in rpm_points:
        egt_map[rpm] = {}
        rpm_f = rpm / max_rpm
        for load in load_points:
            load_f = load / 100.0
            if fuel_type == "diesel":
                base, ceiling = 250.0, 1400.0
            elif is_forced:
                base, ceiling = 300.0, 1750.0
            else:
                base, ceiling = 350.0, 1650.0
            temp = base + (ceiling - base) * (0.4 * rpm_f + 0.6 * load_f * rpm_f)
            egt_map[rpm][load] = round(temp)
    return egt_map


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_LOAD_POINTS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


# ---------------------------------------------------------------------------
# Engine specification catalogue
# ---------------------------------------------------------------------------

_ENGINE_SPECS: List[Dict[str, Any]] = [

    # ---- 1. 2.0L Turbo I4 (B48 / FA20DIT platform) ----
    {
        "engine_id": "20t_i4",
        "name": "2.0L Turbo Inline-4",
        "displacement": 2.0,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "fuel_type": "gasoline",
        "redline": 6500,
        "rev_limit": 7000,
        "stock_power_hp": 250,
        "stock_torque_nm": 350,
        "peak_boost_psi": 18.0,
        "boost_onset_rpm": 1500,
        "full_boost_rpm": 2500,
        "drivetrain_loss": 0.15,
        "gear_ratios": [3.63, 2.19, 1.55, 1.17, 0.94, 0.78],
        "final_drive": 3.73,
        "tire_circumference": 2.01,
        "max_injector_duty": 78.0,
        "torque_curve": {
            1000: 180, 1500: 290, 2000: 345, 2500: 350, 3000: 350,
            3500: 348, 4000: 342, 4500: 335, 5000: 328, 5500: 324,
            6000: 295, 6500: 250,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    1000: 195, 1500: 330, 2000: 395, 2500: 405, 3000: 408,
                    3500: 405, 4000: 398, 4500: 388, 5000: 375, 5500: 360,
                    6000: 325, 6500: 275,
                },
                "peak_boost_psi": 21.0,
                "max_injector_duty": 83.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipe + Intake + Remap",
                "torque_curve": {
                    1000: 205, 1500: 355, 2000: 430, 2500: 450, 3000: 455,
                    3500: 450, 4000: 442, 4500: 430, 5000: 415, 5500: 395,
                    6000: 358, 6500: 305,
                },
                "peak_boost_psi": 24.0,
                "max_injector_duty": 88.0,
            },
            "stage3": {
                "label": "Stage 3 - Hybrid Turbo + Fuelling + Remap",
                "torque_curve": {
                    1000: 195, 1500: 320, 2000: 425, 2500: 490, 3000: 510,
                    3500: 515, 4000: 512, 4500: 505, 5000: 488, 5500: 460,
                    6000: 415, 6500: 355,
                },
                "peak_boost_psi": 28.0,
                "max_injector_duty": 94.0,
            },
        },
    },

    # ---- 2. 1.6L Turbo I4 (Prince EP6 / Fiesta ST platform) ----
    {
        "engine_id": "16t_i4",
        "name": "1.6L Turbo Inline-4",
        "displacement": 1.6,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "fuel_type": "gasoline",
        "redline": 6800,
        "rev_limit": 7200,
        "stock_power_hp": 200,
        "stock_torque_nm": 290,
        "peak_boost_psi": 16.5,
        "boost_onset_rpm": 1600,
        "full_boost_rpm": 2800,
        "drivetrain_loss": 0.12,
        "gear_ratios": [3.58, 2.02, 1.35, 1.03, 0.84, 0.68],
        "final_drive": 3.82,
        "tire_circumference": 1.96,
        "max_injector_duty": 75.0,
        "torque_curve": {
            1000: 140, 1500: 220, 2000: 275, 2500: 288, 3000: 290,
            3500: 288, 4000: 282, 4500: 272, 5000: 260, 5500: 250,
            6000: 237, 6500: 210, 6800: 185,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    1000: 155, 1500: 252, 2000: 318, 2500: 335, 3000: 338,
                    3500: 335, 4000: 325, 4500: 312, 5000: 298, 5500: 282,
                    6000: 262, 6500: 232, 6800: 205,
                },
                "peak_boost_psi": 19.5,
                "max_injector_duty": 80.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipe + Intake + Remap",
                "torque_curve": {
                    1000: 162, 1500: 270, 2000: 348, 2500: 370, 3000: 375,
                    3500: 372, 4000: 362, 4500: 348, 5000: 332, 5500: 312,
                    6000: 288, 6500: 255, 6800: 225,
                },
                "peak_boost_psi": 22.0,
                "max_injector_duty": 86.0,
            },
            "stage3": {
                "label": "Stage 3 - Hybrid Turbo + Remap",
                "torque_curve": {
                    1000: 158, 1500: 265, 2000: 358, 2500: 405, 3000: 415,
                    3500: 418, 4000: 412, 4500: 398, 5000: 378, 5500: 355,
                    6000: 325, 6500: 288, 6800: 250,
                },
                "peak_boost_psi": 26.0,
                "max_injector_duty": 92.0,
            },
        },
    },

    # ---- 3. 2.5L Turbo I4 (EJ257 platform) ----
    {
        "engine_id": "25t_i4",
        "name": "2.5L Turbo Boxer-4",
        "displacement": 2.5,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "fuel_type": "gasoline",
        "redline": 6700,
        "rev_limit": 7200,
        "stock_power_hp": 310,
        "stock_torque_nm": 407,
        "peak_boost_psi": 16.2,
        "boost_onset_rpm": 2000,
        "full_boost_rpm": 3500,
        "drivetrain_loss": 0.22,
        "gear_ratios": [3.45, 1.94, 1.37, 1.03, 0.81, 0.67],
        "final_drive": 3.90,
        "tire_circumference": 2.01,
        "max_injector_duty": 76.0,
        "torque_curve": {
            1000: 185, 1500: 265, 2000: 340, 2500: 385, 3000: 400,
            3500: 407, 4000: 405, 4500: 395, 5000: 380, 5500: 362,
            6000: 368, 6500: 330, 6700: 300,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap + Boost Increase",
                "torque_curve": {
                    1000: 200, 1500: 298, 2000: 388, 2500: 438, 3000: 455,
                    3500: 462, 4000: 458, 4500: 445, 5000: 425, 5500: 405,
                    6000: 380, 6500: 350, 6700: 322,
                },
                "peak_boost_psi": 19.0,
                "max_injector_duty": 82.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipe + TBE + TMIC + Remap",
                "torque_curve": {
                    1000: 210, 1500: 318, 2000: 415, 2500: 478, 3000: 502,
                    3500: 512, 4000: 508, 4500: 495, 5000: 475, 5500: 452,
                    6000: 422, 6500: 385, 6700: 355,
                },
                "peak_boost_psi": 22.0,
                "max_injector_duty": 88.0,
            },
            "stage3": {
                "label": "Stage 3 - Rotated Turbo + Built Engine",
                "torque_curve": {
                    1000: 198, 1500: 305, 2000: 418, 2500: 510, 3000: 558,
                    3500: 580, 4000: 582, 4500: 572, 5000: 548, 5500: 518,
                    6000: 482, 6500: 435, 6700: 398,
                },
                "peak_boost_psi": 27.0,
                "max_injector_duty": 95.0,
            },
        },
    },

    # ---- 4. 3.0L I6 Turbo (B58 platform) ----
    {
        "engine_id": "30t_i6",
        "name": "3.0L Turbo Inline-6",
        "displacement": 3.0,
        "cylinders": 6,
        "aspiration": "turbocharged",
        "fuel_type": "gasoline",
        "redline": 6500,
        "rev_limit": 7000,
        "stock_power_hp": 382,
        "stock_torque_nm": 500,
        "peak_boost_psi": 17.4,
        "boost_onset_rpm": 1400,
        "full_boost_rpm": 2500,
        "drivetrain_loss": 0.15,
        "gear_ratios": [4.11, 2.32, 1.54, 1.18, 1.00, 0.85],
        "final_drive": 3.15,
        "tire_circumference": 2.07,
        "max_injector_duty": 74.0,
        "torque_curve": {
            1000: 280, 1500: 420, 1800: 490, 2000: 500, 2500: 500,
            3000: 500, 3500: 498, 4000: 492, 4500: 482, 5000: 470,
            5500: 465, 5800: 469, 6000: 440, 6500: 385,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    1000: 305, 1500: 465, 1800: 548, 2000: 560, 2500: 560,
                    3000: 558, 3500: 555, 4000: 548, 4500: 535, 5000: 520,
                    5500: 510, 5800: 505, 6000: 475, 6500: 418,
                },
                "peak_boost_psi": 20.5,
                "max_injector_duty": 80.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipe + Charge Pipe + Remap",
                "torque_curve": {
                    1000: 320, 1500: 498, 1800: 595, 2000: 620, 2500: 625,
                    3000: 622, 3500: 618, 4000: 608, 4500: 592, 5000: 572,
                    5500: 555, 5800: 542, 6000: 510, 6500: 448,
                },
                "peak_boost_psi": 24.0,
                "max_injector_duty": 87.0,
            },
            "stage3": {
                "label": "Stage 3 - Pure Turbos + Fuelling + Remap",
                "torque_curve": {
                    1000: 310, 1500: 485, 1800: 605, 2000: 668, 2500: 700,
                    3000: 710, 3500: 708, 4000: 698, 4500: 680, 5000: 655,
                    5500: 625, 5800: 598, 6000: 558, 6500: 490,
                },
                "peak_boost_psi": 28.0,
                "max_injector_duty": 94.0,
            },
        },
    },

    # ---- 5. 3.5L V6 NA (VQ35DE platform) ----
    {
        "engine_id": "35na_v6",
        "name": "3.5L Naturally Aspirated V6",
        "displacement": 3.5,
        "cylinders": 6,
        "aspiration": "naturally_aspirated",
        "fuel_type": "gasoline",
        "redline": 7000,
        "rev_limit": 7500,
        "stock_power_hp": 300,
        "stock_torque_nm": 363,
        "peak_boost_psi": 0.0,
        "boost_onset_rpm": 0,
        "full_boost_rpm": 0,
        "drivetrain_loss": 0.14,
        "gear_ratios": [3.79, 2.32, 1.62, 1.27, 1.00, 0.79],
        "final_drive": 3.54,
        "tire_circumference": 2.04,
        "max_injector_duty": 70.0,
        "torque_curve": {
            1000: 180, 1500: 225, 2000: 268, 2500: 302, 3000: 328,
            3500: 345, 4000: 358, 4500: 362, 4800: 363, 5000: 360,
            5500: 350, 6000: 335, 6500: 324, 7000: 285,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - Intake + Exhaust + ECU",
                "torque_curve": {
                    1000: 188, 1500: 238, 2000: 282, 2500: 318, 3000: 345,
                    3500: 365, 4000: 378, 4500: 382, 4800: 385, 5000: 382,
                    5500: 372, 6000: 358, 6500: 348, 7000: 310,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 74.0,
            },
            "stage2": {
                "label": "Stage 2 - Headers + Cams + High-Flow Cat",
                "torque_curve": {
                    1000: 192, 1500: 245, 2000: 295, 2500: 335, 3000: 362,
                    3500: 385, 4000: 398, 4500: 405, 4800: 408, 5000: 405,
                    5500: 395, 6000: 382, 6500: 372, 7000: 338,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 78.0,
            },
            "stage3": {
                "label": "Stage 3 - Ported Heads + Stroker Kit",
                "torque_curve": {
                    1000: 198, 1500: 255, 2000: 310, 2500: 352, 3000: 382,
                    3500: 405, 4000: 422, 4500: 430, 4800: 432, 5000: 430,
                    5500: 420, 6000: 408, 6500: 395, 7000: 365,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 82.0,
            },
        },
    },

    # ---- 6. 3.5L V6 Twin-Turbo (VR30DDTT platform) ----
    {
        "engine_id": "35tt_v6",
        "name": "3.5L Twin-Turbo V6",
        "displacement": 3.5,
        "cylinders": 6,
        "aspiration": "twin-turbocharged",
        "fuel_type": "gasoline",
        "redline": 6800,
        "rev_limit": 7200,
        "stock_power_hp": 400,
        "stock_torque_nm": 475,
        "peak_boost_psi": 14.7,
        "boost_onset_rpm": 1400,
        "full_boost_rpm": 2200,
        "drivetrain_loss": 0.15,
        "gear_ratios": [3.51, 2.08, 1.45, 1.10, 0.87, 0.73],
        "final_drive": 3.36,
        "tire_circumference": 2.07,
        "max_injector_duty": 72.0,
        "torque_curve": {
            1000: 260, 1500: 395, 2000: 468, 2500: 475, 3000: 475,
            3500: 472, 4000: 465, 4500: 455, 5000: 450, 5500: 448,
            6000: 445, 6400: 445, 6800: 380,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    1000: 278, 1500: 432, 2000: 515, 2500: 528, 3000: 528,
                    3500: 525, 4000: 518, 4500: 508, 5000: 498, 5500: 492,
                    6000: 485, 6400: 478, 6800: 412,
                },
                "peak_boost_psi": 17.5,
                "max_injector_duty": 78.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipes + Intakes + Remap",
                "torque_curve": {
                    1000: 295, 1500: 465, 2000: 565, 2500: 588, 3000: 592,
                    3500: 588, 4000: 580, 4500: 568, 5000: 555, 5500: 545,
                    6000: 538, 6400: 525, 6800: 455,
                },
                "peak_boost_psi": 20.5,
                "max_injector_duty": 85.0,
            },
            "stage3": {
                "label": "Stage 3 - Upgraded Turbos + Fuelling",
                "torque_curve": {
                    1000: 285, 1500: 448, 2000: 568, 2500: 635, 3000: 668,
                    3500: 672, 4000: 668, 4500: 655, 5000: 638, 5500: 620,
                    6000: 598, 6400: 575, 6800: 498,
                },
                "peak_boost_psi": 25.0,
                "max_injector_duty": 93.0,
            },
        },
    },

    # ---- 7. 5.0L V8 NA (Coyote platform) ----
    {
        "engine_id": "50na_v8",
        "name": "5.0L Naturally Aspirated V8",
        "displacement": 5.0,
        "cylinders": 8,
        "aspiration": "naturally_aspirated",
        "fuel_type": "gasoline",
        "redline": 7500,
        "rev_limit": 8000,
        "stock_power_hp": 460,
        "stock_torque_nm": 570,
        "peak_boost_psi": 0.0,
        "boost_onset_rpm": 0,
        "full_boost_rpm": 0,
        "drivetrain_loss": 0.14,
        "gear_ratios": [3.36, 2.09, 1.36, 1.01, 0.82, 0.63],
        "final_drive": 3.73,
        "tire_circumference": 2.10,
        "max_injector_duty": 72.0,
        "torque_curve": {
            1000: 285, 1500: 365, 2000: 425, 2500: 468, 3000: 505,
            3500: 535, 4000: 555, 4500: 565, 4600: 570, 5000: 558,
            5500: 542, 6000: 525, 6500: 510, 7000: 468, 7500: 405,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - CAI + Tune + Exhaust",
                "torque_curve": {
                    1000: 295, 1500: 380, 2000: 445, 2500: 490, 3000: 530,
                    3500: 562, 4000: 582, 4500: 592, 4600: 595, 5000: 585,
                    5500: 570, 6000: 555, 6500: 540, 7000: 498, 7500: 432,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 76.0,
            },
            "stage2": {
                "label": "Stage 2 - Headers + Cams + Intake Manifold",
                "torque_curve": {
                    1000: 305, 1500: 395, 2000: 462, 2500: 510, 3000: 552,
                    3500: 588, 4000: 612, 4500: 622, 4600: 625, 5000: 618,
                    5500: 605, 6000: 588, 6500: 572, 7000: 535, 7500: 468,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 80.0,
            },
            "stage3": {
                "label": "Stage 3 - Ported Heads + Stroker + Race Cams",
                "torque_curve": {
                    1000: 310, 1500: 405, 2000: 480, 2500: 535, 3000: 580,
                    3500: 618, 4000: 648, 4500: 660, 4600: 662, 5000: 655,
                    5500: 642, 6000: 625, 6500: 608, 7000: 572, 7500: 502,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 85.0,
            },
        },
    },

    # ---- 8. 6.2L V8 Supercharged (LT4 / Hellcat platform) ----
    {
        "engine_id": "62sc_v8",
        "name": "6.2L Supercharged V8",
        "displacement": 6.2,
        "cylinders": 8,
        "aspiration": "supercharged",
        "fuel_type": "gasoline",
        "redline": 6200,
        "rev_limit": 6600,
        "stock_power_hp": 650,
        "stock_torque_nm": 881,
        "peak_boost_psi": 11.6,
        "boost_onset_rpm": 1000,
        "full_boost_rpm": 2800,
        "drivetrain_loss": 0.15,
        "gear_ratios": [4.06, 2.37, 1.54, 1.16, 0.87, 0.68],
        "final_drive": 3.70,
        "tire_circumference": 2.15,
        "max_injector_duty": 82.0,
        "torque_curve": {
            1000: 520, 1500: 680, 2000: 785, 2500: 845, 3000: 870,
            3500: 878, 4000: 881, 4500: 872, 5000: 848, 5500: 810,
            6000: 771, 6200: 738,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - Pulley + Tune",
                "torque_curve": {
                    1000: 548, 1500: 720, 2000: 835, 2500: 905, 3000: 935,
                    3500: 945, 4000: 948, 4500: 938, 5000: 912, 5500: 870,
                    6000: 828, 6200: 792,
                },
                "peak_boost_psi": 13.5,
                "max_injector_duty": 86.0,
            },
            "stage2": {
                "label": "Stage 2 - Ported Blower + Injectors + Headers",
                "torque_curve": {
                    1000: 568, 1500: 752, 2000: 880, 2500: 958, 3000: 998,
                    3500: 1015, 4000: 1020, 4500: 1008, 5000: 978, 5500: 932,
                    6000: 882, 6200: 842,
                },
                "peak_boost_psi": 15.5,
                "max_injector_duty": 90.0,
            },
            "stage3": {
                "label": "Stage 3 - Larger Supercharger + Built Engine",
                "torque_curve": {
                    1000: 588, 1500: 785, 2000: 932, 2500: 1028, 3000: 1078,
                    3500: 1102, 4000: 1112, 4500: 1098, 5000: 1062, 5500: 1008,
                    6000: 948, 6200: 905,
                },
                "peak_boost_psi": 18.0,
                "max_injector_duty": 96.0,
            },
        },
    },

    # ---- 9. 6.2L V8 NA (LS3 / LT1 platform) ----
    {
        "engine_id": "62na_v8",
        "name": "6.2L Naturally Aspirated V8",
        "displacement": 6.2,
        "cylinders": 8,
        "aspiration": "naturally_aspirated",
        "fuel_type": "gasoline",
        "redline": 6600,
        "rev_limit": 7000,
        "stock_power_hp": 455,
        "stock_torque_nm": 624,
        "peak_boost_psi": 0.0,
        "boost_onset_rpm": 0,
        "full_boost_rpm": 0,
        "drivetrain_loss": 0.14,
        "gear_ratios": [4.06, 2.37, 1.54, 1.16, 0.87, 0.68],
        "final_drive": 3.73,
        "tire_circumference": 2.10,
        "max_injector_duty": 71.0,
        "torque_curve": {
            1000: 350, 1500: 430, 2000: 498, 2500: 548, 3000: 582,
            3500: 605, 4000: 618, 4600: 624, 5000: 615, 5500: 598,
            6000: 540, 6600: 458,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - CAI + Headers + Tune",
                "torque_curve": {
                    1000: 362, 1500: 448, 2000: 520, 2500: 575, 3000: 612,
                    3500: 635, 4000: 650, 4600: 655, 5000: 648, 5500: 632,
                    6000: 575, 6600: 492,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 75.0,
            },
            "stage2": {
                "label": "Stage 2 - Cam + Heads + Intake Manifold",
                "torque_curve": {
                    1000: 370, 1500: 462, 2000: 542, 2500: 600, 3000: 640,
                    3500: 668, 4000: 685, 4600: 692, 5000: 685, 5500: 668,
                    6000: 612, 6600: 528,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 80.0,
            },
            "stage3": {
                "label": "Stage 3 - Stroker + Ported Heads + Comp Cam",
                "torque_curve": {
                    1000: 380, 1500: 478, 2000: 565, 2500: 628, 3000: 672,
                    3500: 705, 4000: 725, 4600: 732, 5000: 725, 5500: 708,
                    6000: 652, 6600: 568,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 85.0,
            },
        },
    },

    # ---- 10. 1.3L Twin-Turbo Rotary (13B-REW platform) ----
    {
        "engine_id": "13tt_rotary",
        "name": "1.3L Twin-Turbo Rotary",
        "displacement": 1.3,
        "cylinders": 2,  # 2 rotors
        "aspiration": "twin-turbocharged",
        "fuel_type": "gasoline",
        "redline": 8000,
        "rev_limit": 8500,
        "stock_power_hp": 276,
        "stock_torque_nm": 314,
        "peak_boost_psi": 10.0,
        "boost_onset_rpm": 2000,
        "full_boost_rpm": 4500,
        "drivetrain_loss": 0.14,
        "gear_ratios": [3.48, 2.02, 1.39, 1.03, 0.81, 0.63],
        "final_drive": 4.10,
        "tire_circumference": 2.01,
        "max_injector_duty": 78.0,
        "torque_curve": {
            1000: 120, 1500: 162, 2000: 205, 2500: 248, 3000: 278,
            3500: 298, 4000: 310, 4500: 314, 5000: 314, 5500: 308,
            6000: 298, 6500: 302, 7000: 295, 7500: 275, 8000: 245,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - Boost-Up + ECU Remap",
                "torque_curve": {
                    1000: 128, 1500: 178, 2000: 228, 2500: 278, 3000: 315,
                    3500: 340, 4000: 355, 4500: 362, 5000: 362, 5500: 355,
                    6000: 345, 6500: 342, 7000: 332, 7500: 310, 8000: 278,
                },
                "peak_boost_psi": 13.0,
                "max_injector_duty": 83.0,
            },
            "stage2": {
                "label": "Stage 2 - Single Turbo Conversion + Porting",
                "torque_curve": {
                    1000: 118, 1500: 165, 2000: 225, 2500: 298, 3000: 358,
                    3500: 398, 4000: 420, 4500: 432, 5000: 435, 5500: 428,
                    6000: 418, 6500: 408, 7000: 392, 7500: 365, 8000: 328,
                },
                "peak_boost_psi": 17.0,
                "max_injector_duty": 89.0,
            },
            "stage3": {
                "label": "Stage 3 - Large Single + Bridge Port + Fuelling",
                "torque_curve": {
                    1000: 110, 1500: 155, 2000: 218, 2500: 308, 3000: 388,
                    3500: 448, 4000: 485, 4500: 508, 5000: 518, 5500: 515,
                    6000: 505, 6500: 492, 7000: 470, 7500: 438, 8000: 395,
                },
                "peak_boost_psi": 22.0,
                "max_injector_duty": 96.0,
            },
        },
    },

    # ---- 11. 3.0L I6 Diesel Turbo (N57 / OM642 platform) ----
    {
        "engine_id": "30td_i6",
        "name": "3.0L Turbo-Diesel Inline-6",
        "displacement": 3.0,
        "cylinders": 6,
        "aspiration": "turbocharged",
        "fuel_type": "diesel",
        "redline": 5000,
        "rev_limit": 5200,
        "stock_power_hp": 258,
        "stock_torque_nm": 560,
        "peak_boost_psi": 22.5,
        "boost_onset_rpm": 1200,
        "full_boost_rpm": 1800,
        "drivetrain_loss": 0.15,
        "gear_ratios": [4.71, 3.14, 2.11, 1.67, 1.29, 1.00, 0.84, 0.67],
        "final_drive": 3.15,
        "tire_circumference": 2.07,
        "max_injector_duty": 68.0,
        "torque_curve": {
            800: 220, 1000: 310, 1200: 420, 1500: 540, 1800: 558,
            2000: 560, 2500: 560, 3000: 548, 3500: 518, 4000: 459,
            4500: 388, 5000: 310,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    800: 245, 1000: 348, 1200: 475, 1500: 612, 1800: 635,
                    2000: 638, 2500: 638, 3000: 622, 3500: 585, 4000: 518,
                    4500: 438, 5000: 348,
                },
                "peak_boost_psi": 26.0,
                "max_injector_duty": 75.0,
            },
            "stage2": {
                "label": "Stage 2 - DPF Delete + Intercooler + Remap",
                "torque_curve": {
                    800: 258, 1000: 372, 1200: 512, 1500: 665, 1800: 695,
                    2000: 700, 2500: 700, 3000: 678, 3500: 635, 4000: 562,
                    4500: 475, 5000: 378,
                },
                "peak_boost_psi": 29.0,
                "max_injector_duty": 82.0,
            },
            "stage3": {
                "label": "Stage 3 - Upgraded Turbo + Injectors + Remap",
                "torque_curve": {
                    800: 262, 1000: 385, 1200: 535, 1500: 710, 1800: 755,
                    2000: 765, 2500: 768, 3000: 748, 3500: 698, 4000: 618,
                    4500: 522, 5000: 415,
                },
                "peak_boost_psi": 34.0,
                "max_injector_duty": 90.0,
            },
        },
    },

    # ---- 12. 3.8L Twin-Turbo V6 (VR38DETT / GT-R platform) ----
    {
        "engine_id": "38tt_v6",
        "name": "3.8L Twin-Turbo V6",
        "displacement": 3.8,
        "cylinders": 6,
        "aspiration": "twin-turbocharged",
        "fuel_type": "gasoline",
        "redline": 7100,
        "rev_limit": 7500,
        "stock_power_hp": 565,
        "stock_torque_nm": 637,
        "peak_boost_psi": 14.5,
        "boost_onset_rpm": 1600,
        "full_boost_rpm": 3000,
        "drivetrain_loss": 0.20,
        "gear_ratios": [3.79, 2.32, 1.62, 1.27, 1.00, 0.79],
        "final_drive": 3.70,
        "tire_circumference": 2.09,
        "max_injector_duty": 80.0,
        "torque_curve": {
            1000: 310, 1500: 438, 2000: 548, 2500: 608, 3000: 632,
            3300: 637, 3500: 635, 4000: 628, 4500: 618, 5000: 612,
            5500: 608, 5800: 608, 6000: 600, 6500: 572, 6800: 591,
            7100: 530,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap + Boost Increase",
                "torque_curve": {
                    1000: 335, 1500: 478, 2000: 602, 2500: 668, 3000: 695,
                    3300: 702, 3500: 700, 4000: 692, 4500: 680, 5000: 670,
                    5500: 662, 5800: 655, 6000: 645, 6500: 618, 6800: 598,
                    7100: 562,
                },
                "peak_boost_psi": 17.0,
                "max_injector_duty": 85.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipes + Intakes + Injectors + Remap",
                "torque_curve": {
                    1000: 355, 1500: 515, 2000: 655, 2500: 732, 3000: 768,
                    3300: 778, 3500: 775, 4000: 765, 4500: 752, 5000: 738,
                    5500: 725, 5800: 718, 6000: 705, 6500: 672, 6800: 648,
                    7100: 608,
                },
                "peak_boost_psi": 20.5,
                "max_injector_duty": 90.0,
            },
            "stage3": {
                "label": "Stage 3 - Larger Turbos + Built Engine + E85",
                "torque_curve": {
                    1000: 348, 1500: 510, 2000: 668, 2500: 778, 3000: 838,
                    3300: 858, 3500: 862, 4000: 855, 4500: 842, 5000: 825,
                    5500: 808, 5800: 798, 6000: 782, 6500: 745, 6800: 715,
                    7100: 668,
                },
                "peak_boost_psi": 25.0,
                "max_injector_duty": 96.0,
            },
        },
    },

    # ---- 13. 4.0L Flat-6 Turbo (9A2 EVO / 992 Turbo platform) ----
    {
        "engine_id": "40t_f6",
        "name": "4.0L Twin-Turbo Flat-6",
        "displacement": 4.0,
        "cylinders": 6,
        "aspiration": "twin-turbocharged",
        "fuel_type": "gasoline",
        "redline": 7200,
        "rev_limit": 7600,
        "stock_power_hp": 572,
        "stock_torque_nm": 750,
        "peak_boost_psi": 16.0,
        "boost_onset_rpm": 1800,
        "full_boost_rpm": 2800,
        "drivetrain_loss": 0.20,
        "gear_ratios": [3.91, 2.29, 1.58, 1.18, 0.95, 0.79, 0.63],
        "final_drive": 3.44,
        "tire_circumference": 2.12,
        "max_injector_duty": 76.0,
        "torque_curve": {
            1000: 340, 1500: 498, 2000: 640, 2300: 720, 2500: 745,
            3000: 750, 3500: 748, 4000: 740, 4500: 725, 5000: 705,
            5500: 682, 6000: 652, 6500: 565, 7000: 542, 7200: 508,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap",
                "torque_curve": {
                    1000: 362, 1500: 538, 2000: 698, 2300: 788, 2500: 818,
                    3000: 825, 3500: 822, 4000: 812, 4500: 795, 5000: 772,
                    5500: 745, 6000: 710, 6500: 618, 7000: 588, 7200: 548,
                },
                "peak_boost_psi": 18.5,
                "max_injector_duty": 82.0,
            },
            "stage2": {
                "label": "Stage 2 - Exhaust + Intake + Remap",
                "torque_curve": {
                    1000: 378, 1500: 570, 2000: 748, 2300: 848, 2500: 882,
                    3000: 892, 3500: 888, 4000: 875, 4500: 855, 5000: 828,
                    5500: 798, 6000: 758, 6500: 665, 7000: 628, 7200: 585,
                },
                "peak_boost_psi": 21.0,
                "max_injector_duty": 88.0,
            },
            "stage3": {
                "label": "Stage 3 - Upgraded Turbos + Fuelling + Remap",
                "torque_curve": {
                    1000: 370, 1500: 558, 2000: 755, 2300: 878, 2500: 935,
                    3000: 968, 3500: 972, 4000: 962, 4500: 942, 5000: 912,
                    5500: 878, 6000: 832, 6500: 735, 7000: 692, 7200: 645,
                },
                "peak_boost_psi": 25.0,
                "max_injector_duty": 95.0,
            },
        },
    },

    # ---- 14. 2.0L Turbo I4 VTEC (K20C1 / FK8 platform) ----
    {
        "engine_id": "20t_i4_vtec",
        "name": "2.0L VTEC Turbo Inline-4",
        "displacement": 2.0,
        "cylinders": 4,
        "aspiration": "turbocharged",
        "fuel_type": "gasoline",
        "redline": 7000,
        "rev_limit": 7400,
        "stock_power_hp": 306,
        "stock_torque_nm": 400,
        "peak_boost_psi": 20.3,
        "boost_onset_rpm": 1600,
        "full_boost_rpm": 2800,
        "drivetrain_loss": 0.11,
        "gear_ratios": [3.64, 2.24, 1.54, 1.13, 0.88, 0.74],
        "final_drive": 4.11,
        "tire_circumference": 2.01,
        "max_injector_duty": 76.0,
        "torque_curve": {
            1000: 195, 1500: 310, 2000: 378, 2500: 398, 3000: 400,
            3500: 400, 4000: 395, 4500: 388, 5000: 378, 5500: 368,
            6000: 352, 6500: 335, 7000: 295,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - ECU Remap + Intake",
                "torque_curve": {
                    1000: 210, 1500: 342, 2000: 418, 2500: 445, 3000: 448,
                    3500: 448, 4000: 442, 4500: 432, 5000: 420, 5500: 408,
                    6000: 390, 6500: 372, 7000: 328,
                },
                "peak_boost_psi": 23.0,
                "max_injector_duty": 82.0,
            },
            "stage2": {
                "label": "Stage 2 - Downpipe + FMIC + Full Exhaust",
                "torque_curve": {
                    1000: 218, 1500: 362, 2000: 452, 2500: 490, 3000: 498,
                    3500: 498, 4000: 492, 4500: 482, 5000: 468, 5500: 452,
                    6000: 432, 6500: 412, 7000: 365,
                },
                "peak_boost_psi": 25.5,
                "max_injector_duty": 87.0,
            },
            "stage3": {
                "label": "Stage 3 - Larger Turbo + Injectors + Cams",
                "torque_curve": {
                    1000: 205, 1500: 345, 2000: 448, 2500: 515, 3000: 542,
                    3500: 552, 4000: 555, 4500: 548, 5000: 535, 5500: 518,
                    6000: 495, 6500: 468, 7000: 418,
                },
                "peak_boost_psi": 29.0,
                "max_injector_duty": 94.0,
            },
        },
    },

    # ---- 15. 5.2L V8 NA High-Rev (Voodoo flat-plane crank platform) ----
    {
        "engine_id": "52na_v8_hr",
        "name": "5.2L Flat-Plane Crank V8",
        "displacement": 5.2,
        "cylinders": 8,
        "aspiration": "naturally_aspirated",
        "fuel_type": "gasoline",
        "redline": 8250,
        "rev_limit": 8500,
        "stock_power_hp": 526,
        "stock_torque_nm": 582,
        "peak_boost_psi": 0.0,
        "boost_onset_rpm": 0,
        "full_boost_rpm": 0,
        "drivetrain_loss": 0.14,
        "gear_ratios": [3.32, 2.05, 1.41, 1.07, 0.84, 0.63],
        "final_drive": 3.73,
        "tire_circumference": 2.12,
        "max_injector_duty": 74.0,
        "torque_curve": {
            1000: 260, 1500: 340, 2000: 398, 2500: 445, 3000: 485,
            3500: 518, 4000: 548, 4500: 570, 4750: 582, 5000: 578,
            5500: 568, 6000: 555, 6500: 540, 7000: 518, 7500: 500,
            8000: 465, 8250: 435,
        },
        "variants": {
            "stage1": {
                "label": "Stage 1 - Tune + Intake + Exhaust",
                "torque_curve": {
                    1000: 272, 1500: 358, 2000: 420, 2500: 470, 3000: 512,
                    3500: 548, 4000: 578, 4500: 600, 4750: 612, 5000: 608,
                    5500: 598, 6000: 585, 6500: 570, 7000: 548, 7500: 528,
                    8000: 492, 8250: 462,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 78.0,
            },
            "stage2": {
                "label": "Stage 2 - Headers + Cams + Ported Intake",
                "torque_curve": {
                    1000: 280, 1500: 370, 2000: 438, 2500: 492, 3000: 538,
                    3500: 575, 4000: 608, 4500: 632, 4750: 645, 5000: 642,
                    5500: 632, 6000: 618, 6500: 602, 7000: 580, 7500: 560,
                    8000: 522, 8250: 490,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 82.0,
            },
            "stage3": {
                "label": "Stage 3 - Ported Heads + Comp Cams + Stroker",
                "torque_curve": {
                    1000: 290, 1500: 385, 2000: 458, 2500: 518, 3000: 568,
                    3500: 608, 4000: 642, 4500: 668, 4750: 682, 5000: 680,
                    5500: 672, 6000: 658, 6500: 642, 7000: 618, 7500: 598,
                    8000: 558, 8250: 525,
                },
                "peak_boost_psi": 0.0,
                "max_injector_duty": 87.0,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# PerformanceDatabase
# ---------------------------------------------------------------------------

class PerformanceDatabase:
    """
    Comprehensive performance database for the NATOS ECU tuning system.

    Stores 15 engine profiles with dyno data, torque / power curves, boost
    maps, AFR maps, timing maps, RWKW data, wheel-speed data, injector-duty
    maps, and EGT maps.  Each engine has stock and tuned variants (stage 1-3).

    All data is generated from physics-correct torque curves at init time.
    Power = Torque_Nm * RPM / 7121 (HP), kW = HP * 0.7457.

    Usage:
        db = PerformanceDatabase()
        engine = db.get_engine("20t_i4")
        dyno   = db.get_dyno_data("20t_i4", variant="stage1")
    """

    def __init__(self) -> None:
        self.engines: Dict[str, Dict[str, Any]] = {}
        self._build_database()

    # ------------------------------------------------------------------ build

    def _build_database(self) -> None:
        """Populate all engine profiles from the specification catalogue."""
        for spec in _ENGINE_SPECS:
            engine = self._build_engine(spec)
            self.engines[engine["engine_id"]] = engine

    def _build_engine(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand a compact engine specification into a full profile.

        Args:
            spec: Compact specification dict from _ENGINE_SPECS

        Returns:
            Complete engine profile with all maps and variant data
        """
        eid = spec["engine_id"]
        rpm_min = min(spec["torque_curve"].keys())
        rpm_max = spec["redline"]
        step = 500

        is_forced = spec["aspiration"] in (
            "turbocharged", "supercharged", "twin-turbocharged"
        )

        # --- stock data ---
        stock_dyno = _build_dyno_data(spec["torque_curve"], rpm_min, rpm_max, step)
        # Use dyno RPM keys as canonical rpm_points for all maps
        rpm_points = sorted(stock_dyno.keys())
        stock_rwkw = _build_rwkw_data(stock_dyno, spec["drivetrain_loss"])
        stock_wheel = _build_wheel_speed_data(
            rpm_points, spec["gear_ratios"],
            spec["final_drive"], spec["tire_circumference"],
        )
        stock_afr = _build_afr_map(
            rpm_points, _LOAD_POINTS, spec["fuel_type"], spec["aspiration"],
        )
        stock_timing = _build_timing_map(
            rpm_points, _LOAD_POINTS, spec["aspiration"], spec["fuel_type"],
        )
        stock_injector = _build_injector_duty_map(
            rpm_points, _LOAD_POINTS, spec["max_injector_duty"],
        )
        stock_egt = _build_egt_map(
            rpm_points, _LOAD_POINTS, spec["aspiration"], spec["fuel_type"],
        )
        stock_boost: Dict[int, float] = {}
        if is_forced:
            stock_boost = _build_boost_map(
                rpm_points, spec["peak_boost_psi"],
                spec["boost_onset_rpm"], spec["full_boost_rpm"],
            )

        # --- tuned variants ---
        tuned_variants: Dict[str, Dict[str, Any]] = {}
        for v_name, v_spec in spec.get("variants", {}).items():
            v_dyno = _build_dyno_data(v_spec["torque_curve"], rpm_min, rpm_max, step)
            v_rwkw = _build_rwkw_data(v_dyno, spec["drivetrain_loss"])
            v_wheel = _build_wheel_speed_data(
                rpm_points, spec["gear_ratios"],
                spec["final_drive"], spec["tire_circumference"],
            )
            v_boost: Dict[int, float] = {}
            if is_forced:
                v_boost = _build_boost_map(
                    rpm_points, v_spec.get("peak_boost_psi", spec["peak_boost_psi"]),
                    spec["boost_onset_rpm"], spec["full_boost_rpm"],
                )
            v_injector = _build_injector_duty_map(
                rpm_points, _LOAD_POINTS,
                v_spec.get("max_injector_duty", spec["max_injector_duty"]),
            )
            # Tuned variants share the same AFR / timing / EGT generation
            # but could diverge in a more advanced model
            v_afr = _build_afr_map(
                rpm_points, _LOAD_POINTS, spec["fuel_type"], spec["aspiration"],
            )
            v_timing = _build_timing_map(
                rpm_points, _LOAD_POINTS, spec["aspiration"], spec["fuel_type"],
            )
            v_egt = _build_egt_map(
                rpm_points, _LOAD_POINTS, spec["aspiration"], spec["fuel_type"],
            )

            # Derive peak figures from dyno data
            peak_hp = max(d["power_hp"] for d in v_dyno.values())
            peak_tq = max(d["torque_nm"] for d in v_dyno.values())
            peak_kw = max(d["power_kw"] for d in v_dyno.values())

            tuned_variants[v_name] = {
                "label": v_spec.get("label", v_name),
                "peak_power_hp": peak_hp,
                "peak_torque_nm": peak_tq,
                "peak_power_kw": peak_kw,
                "dyno_data": v_dyno,
                "rwkw_data": v_rwkw,
                "wheel_speed_data": v_wheel,
                "boost_map": v_boost,
                "afr_map": v_afr,
                "timing_map": v_timing,
                "injector_duty_map": v_injector,
                "egt_map": v_egt,
            }

        # Derive stock peaks
        stock_peak_hp = max(d["power_hp"] for d in stock_dyno.values())
        stock_peak_tq = max(d["torque_nm"] for d in stock_dyno.values())
        stock_peak_kw = max(d["power_kw"] for d in stock_dyno.values())

        return {
            "engine_id": eid,
            "name": spec["name"],
            "displacement": spec["displacement"],
            "cylinders": spec["cylinders"],
            "aspiration": spec["aspiration"],
            "fuel_type": spec["fuel_type"],
            "redline": spec["redline"],
            "rev_limit": spec["rev_limit"],
            "stock_power_hp": stock_peak_hp,
            "stock_torque_nm": stock_peak_tq,
            "stock_power_kw": stock_peak_kw,
            "dyno_data": stock_dyno,
            "rwkw_data": stock_rwkw,
            "wheel_speed_data": stock_wheel,
            "boost_map": stock_boost,
            "afr_map": stock_afr,
            "timing_map": stock_timing,
            "injector_duty_map": stock_injector,
            "egt_map": stock_egt,
            "tuned_variants": tuned_variants,
        }

    # --------------------------------------------------------------- queries

    def get_engine(self, engine_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a complete engine profile by ID.

        Args:
            engine_id: Unique engine identifier (e.g. '20t_i4')

        Returns:
            Full engine profile dict, or None if not found
        """
        return self.engines.get(engine_id)

    def list_engines(self) -> List[Dict[str, str]]:
        """
        List all available engines with summary info.

        Returns:
            List of dicts with engine_id, name, displacement, aspiration,
            stock_power_hp, stock_torque_nm
        """
        result: List[Dict[str, Any]] = []
        for eid, eng in self.engines.items():
            result.append({
                "engine_id": eid,
                "name": eng["name"],
                "displacement": eng["displacement"],
                "cylinders": eng["cylinders"],
                "aspiration": eng["aspiration"],
                "fuel_type": eng["fuel_type"],
                "stock_power_hp": eng["stock_power_hp"],
                "stock_torque_nm": eng["stock_torque_nm"],
            })
        return result

    def get_dyno_data(self, engine_id: str,
                      variant: str = "stock") -> Optional[Dict[int, Dict[str, float]]]:
        """
        Get dyno sheet data (RPM -> torque / power / kW).

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dyno data dict or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            return eng["dyno_data"]
        v = eng["tuned_variants"].get(variant)
        return v["dyno_data"] if v else None

    def get_torque_curve(self, engine_id: str,
                         variant: str = "stock") -> Optional[Dict[int, float]]:
        """
        Get torque vs RPM curve.

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dict of RPM -> torque_nm, or None
        """
        dyno = self.get_dyno_data(engine_id, variant)
        if dyno is None:
            return None
        return {rpm: d["torque_nm"] for rpm, d in dyno.items()}

    def get_power_curve(self, engine_id: str,
                        variant: str = "stock") -> Optional[Dict[int, float]]:
        """
        Get power (HP) vs RPM curve.

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dict of RPM -> power_hp, or None
        """
        dyno = self.get_dyno_data(engine_id, variant)
        if dyno is None:
            return None
        return {rpm: d["power_hp"] for rpm, d in dyno.items()}

    def get_rwkw_curve(self, engine_id: str,
                       variant: str = "stock") -> Optional[Dict[int, float]]:
        """
        Get rear-wheel kilowatt vs RPM curve.

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dict of RPM -> RWKW, or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            return eng["rwkw_data"]
        v = eng["tuned_variants"].get(variant)
        return v["rwkw_data"] if v else None

    def get_afr_map(self, engine_id: str,
                    variant: str = "stock") -> Optional[Dict[int, Dict[int, float]]]:
        """
        Get air-fuel ratio map (RPM x load%).

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Nested dict RPM -> load% -> AFR, or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            return eng["afr_map"]
        v = eng["tuned_variants"].get(variant)
        return v["afr_map"] if v else None

    def get_timing_map(self, engine_id: str,
                       variant: str = "stock") -> Optional[Dict[int, Dict[int, float]]]:
        """
        Get ignition timing map (RPM x load%).

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Nested dict RPM -> load% -> degrees BTDC, or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            return eng["timing_map"]
        v = eng["tuned_variants"].get(variant)
        return v["timing_map"] if v else None

    def get_boost_curve(self, engine_id: str,
                        variant: str = "stock") -> Optional[Dict[int, float]]:
        """
        Get boost pressure vs RPM curve.

        Returns empty dict for naturally-aspirated engines.

        Args:
            engine_id: Engine identifier
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dict of RPM -> boost PSI, or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            return eng["boost_map"]
        v = eng["tuned_variants"].get(variant)
        return v["boost_map"] if v else None

    def get_all_variants(self, engine_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get summary info for all tuned variants of an engine.

        Args:
            engine_id: Engine identifier

        Returns:
            List of variant summaries (label, peak figures), or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        variants: List[Dict[str, Any]] = []
        for v_name, v_data in eng["tuned_variants"].items():
            variants.append({
                "variant": v_name,
                "label": v_data["label"],
                "peak_power_hp": v_data["peak_power_hp"],
                "peak_torque_nm": v_data["peak_torque_nm"],
                "peak_power_kw": v_data["peak_power_kw"],
            })
        return variants

    def search_engines(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search engines by criteria.

        Supported filters:
            min_hp, max_hp, min_torque, max_torque,
            aspiration, cylinders, fuel_type, min_displacement, max_displacement

        Args:
            filters: Dict of filter criteria

        Returns:
            List of matching engine summaries
        """
        results: List[Dict[str, Any]] = []
        for eng in self.engines.values():
            if "min_hp" in filters and eng["stock_power_hp"] < filters["min_hp"]:
                continue
            if "max_hp" in filters and eng["stock_power_hp"] > filters["max_hp"]:
                continue
            if "min_torque" in filters and eng["stock_torque_nm"] < filters["min_torque"]:
                continue
            if "max_torque" in filters and eng["stock_torque_nm"] > filters["max_torque"]:
                continue
            if "aspiration" in filters and eng["aspiration"] != filters["aspiration"]:
                continue
            if "cylinders" in filters and eng["cylinders"] != filters["cylinders"]:
                continue
            if "fuel_type" in filters and eng["fuel_type"] != filters["fuel_type"]:
                continue
            if "min_displacement" in filters and eng["displacement"] < filters["min_displacement"]:
                continue
            if "max_displacement" in filters and eng["displacement"] > filters["max_displacement"]:
                continue
            results.append({
                "engine_id": eng["engine_id"],
                "name": eng["name"],
                "displacement": eng["displacement"],
                "cylinders": eng["cylinders"],
                "aspiration": eng["aspiration"],
                "fuel_type": eng["fuel_type"],
                "stock_power_hp": eng["stock_power_hp"],
                "stock_torque_nm": eng["stock_torque_nm"],
            })
        return results

    def get_wheel_speeds(self, engine_id: str, gear: int,
                         variant: str = "stock") -> Optional[Dict[int, float]]:
        """
        Get wheel speed data for a specific gear across RPM range.

        Args:
            engine_id: Engine identifier
            gear: Gear number (1-based)
            variant: 'stock', 'stage1', 'stage2', or 'stage3'

        Returns:
            Dict of RPM -> speed_kmh, or None
        """
        eng = self.engines.get(engine_id)
        if eng is None:
            return None
        if variant == "stock":
            ws = eng["wheel_speed_data"]
        else:
            v = eng["tuned_variants"].get(variant)
            if v is None:
                return None
            ws = v["wheel_speed_data"]
        gear_key = f"gear_{gear}"
        result: Dict[int, float] = {}
        for rpm, speeds in ws.items():
            if gear_key in speeds:
                result[rpm] = speeds[gear_key]
        return result if result else None

    def compare_engines(self, engine_ids: List[str],
                        metric: str = "stock_power_hp") -> List[Dict[str, Any]]:
        """
        Compare multiple engines on a single metric.

        Supported metrics:
            stock_power_hp, stock_torque_nm, stock_power_kw,
            displacement, redline, rev_limit

        Args:
            engine_ids: List of engine identifiers to compare
            metric: Metric to compare on

        Returns:
            Sorted list (descending) of engine summaries with metric value
        """
        rows: List[Dict[str, Any]] = []
        for eid in engine_ids:
            eng = self.engines.get(eid)
            if eng is None:
                continue
            rows.append({
                "engine_id": eid,
                "name": eng["name"],
                metric: eng.get(metric, 0),
            })
        rows.sort(key=lambda r: r.get(metric, 0), reverse=True)
        return rows


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db = PerformanceDatabase()

    print("=" * 72)
    print("  NATOS Performance Database  -  Engine Catalogue")
    print("=" * 72)

    for info in db.list_engines():
        print(
            f"\n  [{info['engine_id']}]  {info['name']}"
            f"\n    {info['displacement']}L  {info['cylinders']}-cyl"
            f"  {info['aspiration']}  ({info['fuel_type']})"
            f"\n    Stock: {info['stock_power_hp']} hp  /  "
            f"{info['stock_torque_nm']} Nm"
        )
        variants = db.get_all_variants(info["engine_id"])
        if variants:
            for v in variants:
                print(
                    f"      {v['variant']:>8s}: {v['peak_power_hp']:>6.1f} hp"
                    f"  /  {v['peak_torque_nm']:>6.1f} Nm"
                    f"  ({v['label']})"
                )

    # Quick physics sanity check
    print("\n" + "-" * 72)
    print("  Dyno Sample  -  2.0L Turbo I4 (stock)")
    print("-" * 72)
    dyno = db.get_dyno_data("20t_i4")
    if dyno:
        print(f"  {'RPM':>5s}  {'Torque Nm':>10s}  {'Power HP':>10s}"
              f"  {'Power kW':>10s}")
        for rpm in sorted(dyno.keys()):
            d = dyno[rpm]
            print(f"  {rpm:>5d}  {d['torque_nm']:>10.1f}"
                  f"  {d['power_hp']:>10.1f}  {d['power_kw']:>10.1f}")

    # Comparison
    print("\n" + "-" * 72)
    print("  V8 Comparison  -  stock_power_hp")
    print("-" * 72)
    for row in db.compare_engines(
        ["50na_v8", "62na_v8", "62sc_v8", "52na_v8_hr"], "stock_power_hp"
    ):
        print(f"  {row['name']:<40s}  {row['stock_power_hp']:>6.1f} hp")

    # Search example
    print("\n" + "-" * 72)
    print("  Search: >= 500 hp")
    print("-" * 72)
    hits = db.search_engines({"min_hp": 500})
    for h in hits:
        print(f"  {h['name']:<40s}  {h['stock_power_hp']} hp")

    # RWKW sample
    print("\n" + "-" * 72)
    print("  RWKW Sample  -  6.2L SC V8 (stock)")
    print("-" * 72)
    rwkw = db.get_rwkw_curve("62sc_v8")
    if rwkw:
        for rpm in sorted(rwkw.keys()):
            print(f"  {rpm:>5d} RPM  ->  {rwkw[rpm]:>6.1f} rwkW")

    # Wheel speed sample
    print("\n" + "-" * 72)
    print("  Wheel Speed (gear 3)  -  5.0L V8 NA (stock)")
    print("-" * 72)
    ws = db.get_wheel_speeds("50na_v8", 3)
    if ws:
        for rpm in sorted(ws.keys()):
            print(f"  {rpm:>5d} RPM  ->  {ws[rpm]:>6.1f} km/h")

    print("\n" + "=" * 72)
    print(f"  Total engines: {len(db.engines)}")
    print(f"  Total variants (incl. stock): "
          f"{sum(1 + len(e['tuned_variants']) for e in db.engines.values())}")
    print("=" * 72)
