# =============================================================================
# Chapter 3: Loads and Load Combinations
# Refactored for separate Vehicle Live Loads & Footpath Live Loads tables
# =============================================================================

from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_LOAD,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE
)

from osdagbridge.core.reports.report_utils import _tex, _render_value
from osdagbridge.core.reports.styles import make_table_note


def _is_true(val) -> bool:
    """Robust boolean evaluation for UI checkbox values."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes")


def ch3_loads(input_dict):
    # ── 1. Vehicles Selection ────────────────────────────────────────────────
    vehicles = []
    if _is_true(input_dict.get(KEY_LL_IRC_CLASS_A)):
        vehicles.append("Class A")
    if _is_true(input_dict.get(KEY_LL_IRC_70R_WHEELED)):
        vehicles.append("Class 70R (Wheeled)")
    if _is_true(input_dict.get(KEY_LL_IRC_70R_TRACKED)):
        vehicles.append("Class 70R (Tracked)")
    if _is_true(input_dict.get(KEY_LL_IRC_AA_WHEELED)):
        vehicles.append("Class AA (Wheeled)")
    if _is_true(input_dict.get(KEY_LL_IRC_AA_TRACKED)):
        vehicles.append("Class AA (Tracked)")
    if _is_true(input_dict.get(KEY_LL_IRC_CLASS_SV)):
        vehicles.append("Class SV")
    if _is_true(input_dict.get(KEY_LL_IRC_70R_BOGIE)):
        vehicles.append("Class 70R (Bogie)")
    if _is_true(input_dict.get(KEY_LL_IRC_CLASS_FATIGUE)):
        vehicles.append("Class Fatigue")

    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict) and c.get("name"):
                vehicles.append(c["name"])
            elif isinstance(c, str):
                vehicles.append(c)

    vehicles_str = ", ".join(vehicles) if vehicles else "None"

    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    # ── 2. Impact Factors ────────────────────────────────────────────────────
    span = input_dict.get(KEY_SPAN)
    impact_factor_str = ""
    if span not in (None, ""):
        try:
            span_m = float(span)
            factors = []
            if _is_true(input_dict.get(KEY_LL_IRC_CLASS_A)):
                im_a = IRC6_2017.cl_208_2_impact_factor(span_m)
                factors.append(f"Class A: {1.0 + im_a:.3f}")
            is_wheeled_heavy = (
                _is_true(input_dict.get(KEY_LL_IRC_70R_WHEELED)) or
                _is_true(input_dict.get(KEY_LL_IRC_AA_WHEELED)) or
                _is_true(input_dict.get(KEY_LL_IRC_70R_BOGIE))
            )
            is_tracked_heavy = (
                _is_true(input_dict.get(KEY_LL_IRC_70R_TRACKED)) or
                _is_true(input_dict.get(KEY_LL_IRC_AA_TRACKED))
            )
            if is_wheeled_heavy or is_tracked_heavy:
                im_aa = IRC6_2017.cl_208_3_impact_factor(span_m)
                factors.append(f"Class AA/70R: {1.0 + im_aa:.3f}")

            impact_factor_str = ", ".join(factors) if factors else "N/A"
        except Exception:
            impact_factor_str = "N/A"
    else:
        impact_factor_str = "N/A"

    # ── 3. Braking Load (with dynamic lane fallback) ─────────────────────────
    lanes = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if lanes in (None, ""):
        # Fall back to design lanes derived from carriageway width per IRC 6 Table 6
        cw = input_dict.get(KEY_CARRIAGEWAY_WIDTH)
        if cw not in (None, ""):
            try:
                lanes = IRC6_2017.table_6(float(cw))
            except Exception:
                lanes = 1
        else:
            lanes = 1

    braking_force_str = ""
    try:
        lanes_int = int(lanes)
        braking_force_t = IRC6_2017.cl_211_2_braking_force(lanes_int)
        braking_force_kN = braking_force_t * 9.81
        braking_force_str = f"{braking_force_kN:.2f} kN ({braking_force_t:.2f} tonnes)"
    except Exception:
        braking_force_str = "N/A"

    ecc_val = input_dict.get(KEY_LL_ECCENTRICITY) or "1.2"
    braking_ecc_str = f"{ecc_val} m above deck surface (IRC 6 Cl. 211.3)"

    # ── 4. Footpath Live Load ────────────────────────────────────────────────
    fp_mode = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")
    fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    if str(fp_mode).strip().lower() in ("as per irc 6", "as per irc6", "automatic", ""):
        try:
            fp_val_num = IRC6_2017.cl_206_1_footway_load()
            fp_str = f"{fp_val_num:.3f} kN/m²"
        except Exception:
            fp_str = "4.905 kN/m²"
    elif fp_value not in (None, ""):
        fp_str = f"{fp_value} kN/m²"
    else:
        fp_str = "N/A"

    footpath_choice = input_dict.get(KEY_FOOTPATH, "None")
    footpath_width = input_dict.get(KEY_TS_FOOTPATH_WIDTH, "0.0")

    # ── 5. Wind Load Vz / Pz ─────────────────────────────────────────────────
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get("wind_speed")
            _h = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            if _vb and _h:
                _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
                if not vz_val:
                    vz_val = _res.get("Vz")
                if not pz_val:
                    pz_val = _res.get("Pz")
        except Exception:
            pass

    # ── 6. Seismic Values ────────────────────────────────────────────────────
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get("seismic_zone")
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2, "Type III – Soft Soil": 3}
            _st = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res = IRC6_2017.cl_218_5_1(
                zone=f"Zone {_z}",
                soil_type=_st,
                dead_load_kN=_dead,
                live_load_kN=_live,
                period_T=float(_tp) if _tp else None,
                damping_percent=float(_damp)
            )
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah = _res.get("Ah")
            if not sl_av:
                sl_av = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    # ── 7. Load Combinations ─────────────────────────────────────────────────
    _LOAD_LABEL_MAP = {
        "dead_load": "DL",
        "surfacing": "SIDL",
        "live_load": "LL",
        "wind_load": "WL",
        "thermal_load": "TL",
        "vehicle_collision": "VC",
        "barge_impact": "BI",
        "floating_bodies": "FB",
        "seismic": "EQ",
    }

    def _fmt_factors(factors):
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):
                add = val.get("adding")
                rel = val.get("relieving")
                add_s = f"{add:.2f}" if add is not None else "--"
                rel_s = f"{rel:.2f}" if rel is not None else "--"
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue
                parts.append(f"{label}({val:.2f})")
        return " + ".join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(f"ULS-{i:02d} & {cases} \\\\[6pt]\n\\hline")
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(f"SLS-{i:02d} & {cases} \\\\[6pt]\n\\hline")

    lc_rows_str = "\n".join(lc_rows)

    return r"""
\chapter{Loads and Load Combinations}
\label{ch:loads}

This section summarizes all gravity, dynamic, environmental, and transient loads applied to the bridge superstructure, along with the limit state load combinations considered for analysis and design per IRC 6:2017.

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load --- Self Weight}}\label{tab:dead-load}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.1 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Steel Self-Weight Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, r" kN/m\textsuperscript{3}")) + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Weight} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, r" kN/m\textsuperscript{3}")) + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load for Surfacing (DW)}}\label{tab:surfacing-load}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.2 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Wearing Course Load} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" x """ + (_render_value(input_dict, KEY_WC_THICKNESS)) + r""" \\[6pt]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Vehicle Live Loads (LL)}}\label{tab:vehicle-live-loads}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.3 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Vehicles Considered} & """ + _tex(vehicles_str) + r""" \\[6pt]
\hline
\textnormal{Impact Factor (IRC 6 Cl. 208)} & """ + _tex(impact_factor_str) + r""" \\[6pt]
\hline
\textnormal{Braking Load (IRC 6 Cl. 211.2)} & """ + _tex(braking_force_str) + r""" \\[6pt]
\hline
\textnormal{Braking Load Application} & """ + _tex(braking_ecc_str) + r""" \\[6pt]
\hline
\textnormal{Centrifugal Force (IRC 6 Cl. 212)} & Not Applicable (Straight alignment; $R = \infty$) \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Footpath Live Loads}}\label{tab:footpath-live-loads}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.4 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Footpath Arrangement} & """ + _tex(str(footpath_choice)) + r""" \\[6pt]
\hline
\textnormal{Footpath Width} & """ + _tex(str(footpath_width)) + r""" m \\[6pt]
\hline
\textnormal{Footpath Live Load Intensity} & """ + _tex(str(fp_str)) + r""" \\[6pt]
\hline
\textnormal{Design Standard Reference} & IRC 6:2017 Clause 206.1 \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Wind Load (WL) --- per IRC 6}}\label{tab:wind-load}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.5 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Basic Wind Speed, Vb} & """ + (_render_value(input_dict, "wind_speed", " m/s")) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, H (m)} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, " m")) + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_MEAN_WIND, " m/s")) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_WIND_PRESSURE, r" N/m\textsuperscript{2}")) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + (_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, " kN")) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + (_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, " kN")) + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + (_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, " kN")) + r""" \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Earthquake Load (EL) --- per IRC 6}}\label{tab:seismic-load}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.6 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Seismic Zone} & """ + (_render_value(input_dict, "seismic_zone")) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, Z} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, I} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Sa/g} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (longitudinal)} & """ + "" + r""" kN \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (transverse)} & """ + "" + r""" kN \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Temperature Load (TL) --- per IRC 6}}\label{tab:temperature-load}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.7 continued)}\\
\hline
\textbf{parameter} & \textbf{value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict, "shade_temp_max")) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict, "shade_temp_min")) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / \textminus{}""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[6pt]
\end{longtable}

\vspace{0.8em}
\begin{longtable}{|C{4.0cm}|p{11.5cm}|}
\caption{\textbf{Load Combinations}}\label{tab:load-combos}\\
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]
\hline
\endfirsthead
\caption*{(Table 3.8 continued)}\\
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot
\hline
\endlastfoot
""" + lc_rows_str + r"""
\end{longtable}

""" + make_table_note("Note: All IRC 6 load combinations are auto-generated by OsdagBridge per Table B.2 (ULS) and Table B.3 (SLS). User-defined custom combinations, if any, are appended.")
