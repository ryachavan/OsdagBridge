# =============================================================================
# OsdagBridge — Report Chart Generation Engine
# =============================================================================
"""
Matplotlib-based chart generator for OsdagBridge design reports.
Renders headless vector/raster images for:
  - Section 5.5: Structural Utilization Ratio Summary (Bar Chart with UR=1.0 threshold)
  - Chapter 7: Material Quantities (Steel Tonnage Breakdown & Concrete vs. Rebar)
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
    KEY_DD_CRACK_WK_BOTTOM,
    KEY_DD_CRACK_WK_TOP,
    KEY_DD_CRACK_WK_LIMIT,
    KEY_MP_ED_TYPE,
    KEY_UTIL_FLEXURE,
    KEY_UTIL_LTB,
    KEY_UTIL_SHEAR,
    KEY_UTIL_INTERACTION,
    KEY_UTIL_FATIGUE,
    KEY_UTIL_STRESS_LIMITATION,
    KEY_UTIL_DEFLECTION_CRACK,
)
try:
    from osdagbridge.core.bridge_types.plate_girder.results_data import _extract_osdag_summary
except Exception:
    def _extract_osdag_summary(result: dict) -> dict:
        if not result or not isinstance(result, dict):
            return {}
        def _first(*keys):
            for k in keys:
                v = result.get(k)
                if v is not None:
                    return v
            return None

        return {
            "section":     _first("section_size.designation", "Optimum.Designation"),
            "capacity_kN": _first("Member.tension_capacity",  "Design.Strength"),
            "efficiency":  _first("Member.efficiency",        "Optimum.UR"),
            "slenderness": result.get("Member.Slenderness"),
            "connection":  "Welded" if "Weld.Type" in result else "Bolted",
        }

from .styles import (
    COLOR_ACCENT_HEX,
    COLOR_FAIL_HEX,
    COLOR_NEUTRAL_HEX,
    COLOR_OSDAG_GREEN_HEX,
    COLOR_PASS_HEX,
    MPL_REPORT_THEME,
)

logger = logging.getLogger(__name__)


def generate_ur_summary_chart(
    items: List[Tuple[str, float, str]],
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate the Section 5.5 Overall Utilization Ratio bar chart.

    Parameters:
        items: List of tuples (check_label, ur_value, category)
               e.g. [("Girder Moment", 0.16, "Girder"), ..., ("Girder Fatigue", 1.35, "Girder")]
        output_path: Optional path to save PNG file directly

    Returns:
        bytes: Raw PNG image bytes
    """
    if not items:
        # Fallback empty chart if no items provided
        items = [("No checks available", 0.0, "General")]

    with plt.rc_context(MPL_REPORT_THEME):
        fig, ax = plt.subplots(figsize=(10.5, 4.8))

        labels = [it[0] for it in items]
        values = [max(0.0, float(it[1])) for it in items]
        categories = [it[2] for it in items]

        x = np.arange(len(labels))
        width = 0.55

        # Colors based on pass (<= 1.0) vs fail (> 1.0)
        colors = [
            f"#{COLOR_FAIL_HEX}" if v > 1.0 else f"#{COLOR_PASS_HEX}"
            for v in values
        ]

        bars = ax.bar(x, values, width=width, color=colors, edgecolor="#37474F", linewidth=0.7, zorder=3)

        # UR = 1.0 Reference threshold line
        ax.axhline(
            1.0,
            color=f"#{COLOR_FAIL_HEX}",
            linestyle="--",
            linewidth=1.8,
            zorder=4,
            label="Limiting Threshold (UR = 1.0)"
        )

        # Soft shaded region for failing zone (UR > 1.0)
        max_val = max(max(values, default=1.0) * 1.15, 1.25)
        ax.axhspan(1.0, max_val, color="#FFEBEE", alpha=0.6, zorder=1)

        # Value annotations above bars
        for bar, val in zip(bars, values):
            yval = bar.get_height()
            color = f"#{COLOR_FAIL_HEX}" if val > 1.0 else "#212121"
            fontweight = "bold" if val > 1.0 else "normal"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                yval + (max_val * 0.02),
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=color,
                fontweight=fontweight
            )

        # Grouping divider lines across categories
        curr_cat = categories[0]
        for i in range(1, len(categories)):
            if categories[i] != curr_cat:
                ax.axvline(i - 0.5, color="#CFD8DC", linestyle=":", linewidth=1.0, zorder=2)
                curr_cat = categories[i]

        ax.set_ylabel("Utilization Ratio (UR = Demand / Capacity)", fontsize=9.5, fontweight="bold")
        ax.set_title("Overall Design Check Summary — Utilization Ratios", fontsize=11, fontweight="bold", pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right", rotation_mode="anchor", fontsize=8.5)
        ax.set_ylim(0, max_val)
        ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)

        # Legend with rectangular color patches and threshold line
        custom_lines = [
            Patch(facecolor=f"#{COLOR_PASS_HEX}", edgecolor="#37474F", linewidth=0.6, label="Passing (UR $\\leq$ 1.0)"),
            Patch(facecolor=f"#{COLOR_FAIL_HEX}", edgecolor="#37474F", linewidth=0.6, label="Failing (UR > 1.0)"),
            plt.Line2D([0], [0], color=f"#{COLOR_FAIL_HEX}", lw=1.8, linestyle="--", label="Code Limit (UR = 1.0)"),
        ]
        ax.legend(handles=custom_lines, loc="upper right", framealpha=0.92, fontsize=8.5)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=200)
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(img_bytes)

        return img_bytes


def generate_steel_tonnage_chart(
    girder_mt: Union[float, dict],
    cb_mt: float = 0.0,
    ed_mt: float = 0.0,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate Chapter 7 Structural Steel Tonnage Breakdown bar chart.
    Accepts either (girder_mt, cb_mt, ed_mt) or (input_dict, output_path=...).
    """
    if isinstance(girder_mt, dict):
        d = girder_mt
        try:
            g_mt = float(d.get("steel_girders_wt_total") or 0.0)
        except (TypeError, ValueError):
            g_mt = 0.0
        try:
            cb_tot = (float(d.get("bracing_top_wt_total") or 0.0)
                      + float(d.get("bracing_bot_wt_total") or 0.0)
                      + float(d.get("bracing_diag_wt_total") or 0.0))
        except (TypeError, ValueError):
            cb_tot = 0.0
        try:
            ed_tot = float(d.get("steel_ed_wt_total") or 0.0)
        except (TypeError, ValueError):
            ed_tot = 0.0
        if isinstance(cb_mt, str) and not output_path:
            output_path = cb_mt
        girder_mt, cb_mt, ed_mt = g_mt, cb_tot, ed_tot

    with plt.rc_context(MPL_REPORT_THEME):
        fig, ax = plt.subplots(figsize=(6.5, 3.8))

        components = ["Girders", "Cross Bracing", "End Diaphragms"]
        tonnages = [float(girder_mt), float(cb_mt), float(ed_mt)]
        colors = [f"#{COLOR_OSDAG_GREEN_HEX}", f"#{COLOR_ACCENT_HEX}", f"#{COLOR_NEUTRAL_HEX}"]

        x = np.arange(len(components))
        width = 0.48

        bars = ax.bar(x, tonnages, width=width, color=colors, edgecolor="#37474F", linewidth=0.7, zorder=3)

        max_val = max(tonnages) * 1.25 if max(tonnages) > 0 else 1.0
        ax.set_ylim(0, max_val)
        ax.set_ylabel("Weight (Metric Tonnes, MT)", fontsize=9, fontweight="bold")
        ax.set_title("Structural Steel Tonnage Breakdown", fontsize=10.5, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(components, fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)

        total_t = sum(tonnages)
        for bar, val in zip(bars, tonnages):
            pct = (val / total_t * 100.0) if total_t > 0 else 0.0
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + (max_val * 0.02),
                f"{val:.2f} MT\n({pct:.1f}%)",
                ha="center",
                va="bottom",
                fontsize=8.5,
                color="#212121"
            )

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=200)
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(img_bytes)

        return img_bytes


def generate_concrete_rebar_chart(
    concrete_vol_m3: Union[float, dict],
    rebar_wt_mt: float = 0.0,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate Chapter 7 Concrete Volume (m³) vs Reinforcement Steel Weight (MT) comparison.
    Dual-axis representation ensures both metrics are visually balanced and clearly legible.
    Accepts either (concrete_vol_m3, rebar_wt_mt) or (input_dict, output_path=...).
    """
    if isinstance(concrete_vol_m3, dict):
        d = concrete_vol_m3
        try:
            c_vol = float(d.get("concrete_deck_vol_total") or 0.0)
        except (TypeError, ValueError):
            c_vol = 0.0
        try:
            r_wt = float(d.get("rebar_deck_wt_total") or 0.0)
        except (TypeError, ValueError):
            r_wt = 0.0
        if isinstance(rebar_wt_mt, str) and not output_path:
            output_path = rebar_wt_mt
        concrete_vol_m3, rebar_wt_mt = c_vol, r_wt

    with plt.rc_context(MPL_REPORT_THEME):
        fig, ax1 = plt.subplots(figsize=(6.5, 3.8))

        x = np.array([0, 1])
        width = 0.45

        c_vol = float(concrete_vol_m3)
        r_wt = float(rebar_wt_mt)

        # Primary Axis: Concrete Volume
        bar1 = ax1.bar(
            x[0],
            c_vol,
            width=width,
            color="#78909C",
            edgecolor="#37474F",
            linewidth=0.7,
            zorder=3,
            label="Concrete Volume (m³)"
        )
        ax1.set_ylabel("Concrete Volume (m³)", color="#37474F", fontsize=9, fontweight="bold")
        ax1.tick_params(axis="y", labelcolor="#37474F")
        ax1.set_ylim(0, c_vol * 1.3 if c_vol > 0 else 10.0)

        # Secondary Axis: Rebar Weight
        ax2 = ax1.twinx()
        bar2 = ax2.bar(
            x[1],
            r_wt,
            width=width,
            color=f"#{COLOR_OSDAG_GREEN_HEX}",
            edgecolor="#37474F",
            linewidth=0.7,
            zorder=3,
            label="Rebar Weight (MT)"
        )
        ax2.set_ylabel("Reinforcement Steel Weight (MT)", color=f"#{COLOR_PASS_HEX}", fontsize=9, fontweight="bold")
        ax2.tick_params(axis="y", labelcolor=f"#{COLOR_PASS_HEX}")
        ax2.set_ylim(0, r_wt * 1.3 if r_wt > 0 else 5.0)

        # Annotations
        ax1.text(
            bar1[0].get_x() + bar1[0].get_width() / 2.0,
            c_vol + (c_vol * 0.03 if c_vol > 0 else 0.1),
            f"{c_vol:.2f} m³",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color="#263238"
        )

        ax2.text(
            bar2[0].get_x() + bar2[0].get_width() / 2.0,
            r_wt + (r_wt * 0.03 if r_wt > 0 else 0.1),
            f"{r_wt:.2f} MT",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color=f"#{COLOR_PASS_HEX}"
        )

        ax1.set_xticks(x)
        ax1.set_xticklabels(["Concrete Deck Slab\nVolume", "Deck Reinforcement\nSteel"], fontsize=9)
        ax1.set_title("Deck Slab Concrete vs. Reinforcement Steel", fontsize=10.5, fontweight="bold", pad=10)
        ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=200)
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(img_bytes)

        return img_bytes


def _is_valid_ur(val) -> bool:
    """Return True if val is a valid non-negative finite utilization ratio (including 0.0)."""
    if val is None or isinstance(val, bool):
        return False
    try:
        f = float(val)
        return not (np.isnan(f) or np.isinf(f)) and f >= 0.0
    except (TypeError, ValueError):
        return False


def extract_ur_chart_items(
    output_dict: dict,
    input_dict: dict,
    bridge=None
) -> List[Tuple[str, float, str]]:
    """
    Extract overall utilization ratios for the Section 5.5 bar chart across the 4 key element categories:
      1. Steel Plate Girders
      2. Concrete Deck Slab
      3. Cross Bracing
      4. End Diaphragms

    Returns:
        List[Tuple[label, ur_value, category]]
    """
    items: List[Tuple[str, float, str]] = []

    # 1. Steel Plate Girders
    pg_summary = (output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}

    def _get_max_dcr(check_ids):
        best_dcr = None
        for g, gd in pg_summary.items():
            if str(g).startswith("EB"):
                continue
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in check_ids:
                    d = chk.get("dcr")
                    if _is_valid_ur(d):
                        df = float(d)
                        if best_dcr is None or df > best_dcr:
                            best_dcr = df
        if best_dcr is None:
            for g, gd in pg_summary.items():
                if str(g).startswith("EB"):
                    continue
                for _lc, _ld in (gd.get("per_lc") or {}).items():
                    if str(_lc).lower().startswith("envelope"):
                        continue
                    for chk in (_ld.get("checks") or []):
                        if chk.get("id") in check_ids or chk.get("check_id") in check_ids:
                            d = chk.get("dcr")
                            if _is_valid_ur(d):
                                df = float(d)
                                if best_dcr is None or df > best_dcr:
                                    best_dcr = df
        return best_dcr

    # Girder Moment (Check 1: ULS Flexure, fallback KEY_UTIL_FLEXURE / 100)
    d_mom = _get_max_dcr({1})
    if d_mom is None and KEY_UTIL_FLEXURE in output_dict:
        val = output_dict.get(KEY_UTIL_FLEXURE)
        if _is_valid_ur(val):
            d_mom = float(val) / 100.0
    if _is_valid_ur(d_mom):
        items.append(("Girder Moment", float(d_mom), "Steel Plate Girder"))

    # Girder Shear (Check 2: ULS Shear & Buckling, fallback KEY_UTIL_SHEAR / 100)
    d_shr = _get_max_dcr({2})
    if d_shr is None and KEY_UTIL_SHEAR in output_dict:
        val = output_dict.get(KEY_UTIL_SHEAR)
        if _is_valid_ur(val):
            d_shr = float(val) / 100.0
    if _is_valid_ur(d_shr):
        items.append(("Girder Shear", float(d_shr), "Steel Plate Girder"))

    # Girder Interaction (Checks 3 & 4: M-V, M-N Interaction, fallback KEY_UTIL_INTERACTION / 100)
    d_int = _get_max_dcr({3, 4})
    if d_int is None and KEY_UTIL_INTERACTION in output_dict:
        val = output_dict.get(KEY_UTIL_INTERACTION)
        if _is_valid_ur(val):
            d_int = float(val) / 100.0
    if _is_valid_ur(d_int):
        items.append(("Girder Interaction", float(d_int), "Steel Plate Girder"))

    # Girder LTB (Check 5: LTB, fallback KEY_UTIL_LTB / 100)
    d_ltb = _get_max_dcr({5})
    if d_ltb is None and KEY_UTIL_LTB in output_dict:
        val = output_dict.get(KEY_UTIL_LTB)
        if _is_valid_ur(val):
            d_ltb = float(val) / 100.0
    if _is_valid_ur(d_ltb):
        items.append(("Girder LTB", float(d_ltb), "Steel Plate Girder"))

    # Girder Deflection (Checks 13 & 14: Deflection, fallback KEY_UTIL_DEFLECTION_CRACK / 100)
    d_defl = _get_max_dcr({13, 14})
    if d_defl is None and KEY_UTIL_DEFLECTION_CRACK in output_dict:
        val = output_dict.get(KEY_UTIL_DEFLECTION_CRACK)
        if _is_valid_ur(val):
            d_defl = float(val) / 100.0
    if _is_valid_ur(d_defl):
        items.append(("Girder Deflection", float(d_defl), "Steel Plate Girder"))

    # Girder Stress (Check 11: SLS Steel Equiv. Stress, fallback KEY_UTIL_STRESS_LIMITATION / 100)
    d_str = _get_max_dcr({11})
    if d_str is None and KEY_UTIL_STRESS_LIMITATION in output_dict:
        val = output_dict.get(KEY_UTIL_STRESS_LIMITATION)
        if _is_valid_ur(val):
            d_str = float(val) / 100.0
    if _is_valid_ur(d_str):
        items.append(("Girder Stress", float(d_str), "Steel Plate Girder"))

    # Girder Fatigue (Checks 8 & 9: Fatigue Normal & Shear, fallback KEY_UTIL_FATIGUE / 100)
    d_fat = _get_max_dcr({8, 9})
    if d_fat is None and KEY_UTIL_FATIGUE in output_dict:
        val = output_dict.get(KEY_UTIL_FATIGUE)
        if _is_valid_ur(val):
            d_fat = float(val) / 100.0
    if _is_valid_ur(d_fat):
        items.append(("Girder Fatigue", float(d_fat), "Steel Plate Girder"))

    # 2. Concrete Deck Slab
    deck_rpt = output_dict.get("deck_report_values", {}) or {}
    dd_res = output_dict.get("deck_design_results", {}) or {}

    def _deck_val(k):
        v = deck_rpt.get(k)
        if v is None or isinstance(v, bool):
            return None
        try:
            f = float(v)
            return f if not (np.isnan(f) or np.isinf(f)) else None
        except (TypeError, ValueError):
            return None

    # Sagging flexure
    mu_bot = _deck_val(KEY_DD_MU_BOT)
    m_sag = _deck_val(KEY_DD_M_ULS_SAG)
    if mu_bot is not None and mu_bot > 0 and m_sag is not None and m_sag >= 0:
        items.append(("Deck Sagging", m_sag / mu_bot, "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("ur_bot_uls")):
        items.append(("Deck Sagging", float(dd_res["ur_bot_uls"]), "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("rebar_bottom_ur")):
        items.append(("Deck Sagging", float(dd_res["rebar_bottom_ur"]), "Concrete Deck Slab"))

    # Hogging flexure
    mu_top = _deck_val(KEY_DD_MU_TOP)
    m_hog = _deck_val(KEY_DD_M_ULS_HOG)
    if mu_top is not None and mu_top > 0 and m_hog is not None and m_hog >= 0:
        items.append(("Deck Hogging", m_hog / mu_top, "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("ur_top_uls")):
        items.append(("Deck Hogging", float(dd_res["ur_top_uls"]), "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("rebar_top_ur")):
        items.append(("Deck Hogging", float(dd_res["rebar_top_ur"]), "Concrete Deck Slab"))

    # Cantilever Overhang
    if deck_rpt.get(KEY_DD_HAS_OVERHANG) or dd_res.get("has_overhang"):
        mu_oh = _deck_val(KEY_DD_MU_OH)
        m_oh = _deck_val(KEY_DD_M_ULS_OH)
        if mu_oh is not None and mu_oh > 0 and m_oh is not None and m_oh >= 0:
            items.append(("Deck Overhang", m_oh / mu_oh, "Concrete Deck Slab"))
        elif _is_valid_ur(dd_res.get("ur_oh_uls")):
            items.append(("Deck Overhang", float(dd_res["ur_oh_uls"]), "Concrete Deck Slab"))

    # Punching shear
    vrd_p = _deck_val(KEY_DD_VRD_C_MPA)
    ved_p = _deck_val(KEY_DD_PUNCH_VED)
    if vrd_p is not None and vrd_p > 0 and ved_p is not None and ved_p >= 0:
        items.append(("Deck Punching", ved_p / vrd_p, "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("ur_bot_punch")):
        items.append(("Deck Punching", float(dd_res["ur_bot_punch"]), "Concrete Deck Slab"))

    # One-way shear
    vrd_s = _deck_val(KEY_DD_SHEAR_VRDC)
    ved_s = _deck_val(KEY_DD_SHEAR_VED)
    if vrd_s is not None and vrd_s > 0 and ved_s is not None and ved_s >= 0:
        items.append(("Deck One-Way", ved_s / vrd_s, "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("ur_bot_shear")):
        items.append(("Deck One-Way", float(dd_res["ur_bot_shear"]), "Concrete Deck Slab"))

    # Crack width
    wk_lim = _deck_val(KEY_DD_CRACK_WK_LIMIT) or _deck_val(KEY_DD_WK_LIMIT)
    wks = [w for w in [_deck_val(KEY_DD_CRACK_WK_BOTTOM) or _deck_val(KEY_DD_WK_BOT),
                       _deck_val(KEY_DD_CRACK_WK_TOP) or _deck_val(KEY_DD_WK_TOP)] if w is not None]
    if deck_rpt.get(KEY_DD_HAS_OVERHANG) or dd_res.get("has_overhang"):
        w_oh = _deck_val(KEY_DD_WK_OH)
        if w_oh is not None:
            wks.append(w_oh)
    gov_wk = max(wks) if wks else None
    if wk_lim is not None and wk_lim > 0 and gov_wk is not None and gov_wk >= 0:
        items.append(("Deck Crack Width", gov_wk / wk_lim, "Concrete Deck Slab"))
    elif _is_valid_ur(dd_res.get("ur_bot_crack")):
        items.append(("Deck Crack Width", float(dd_res["ur_bot_crack"]), "Concrete Deck Slab"))

    # 3. Cross Bracing
    best_comp_ur = None
    best_tens_ur = None
    best_slnd_ur = None

    if bridge and hasattr(bridge, "get_cb_pairs"):
        pairs = bridge.get_cb_pairs()
        for pair in pairs:
            for member in ("diagonal", "chord"):
                eff_c = bridge.get_cb_efficiency(pair, member, "compression")
                if _is_valid_ur(eff_c):
                    f = float(eff_c)
                    best_comp_ur = f if best_comp_ur is None else max(best_comp_ur, f)
                eff_t = bridge.get_cb_efficiency(pair, member, "tension")
                if _is_valid_ur(eff_t):
                    f = float(eff_t)
                    best_tens_ur = f if best_tens_ur is None else max(best_tens_ur, f)
                slnd = bridge.get_cb_slenderness(pair, member)
                if _is_valid_ur(slnd):
                    lim = 400.0 if member == "chord" else 250.0
                    f = float(slnd) / lim
                    best_slnd_ur = f if best_slnd_ur is None else max(best_slnd_ur, f)

    # Also inspect output_dict crossbracing_design_results if available
    cb_dump = output_dict.get("crossbracing_design_results")
    if (best_comp_ur is None or best_tens_ur is None) and isinstance(cb_dump, dict):
        for pair_name, members in cb_dump.items():
            if not isinstance(members, dict):
                continue
            for mem_name, ftypes in members.items():
                if not isinstance(ftypes, dict):
                    continue
                raw_c = ftypes.get("compression")
                if raw_c:
                    val_c = _extract_osdag_summary(raw_c).get("efficiency")
                    if _is_valid_ur(val_c):
                        f = float(val_c)
                        best_comp_ur = f if best_comp_ur is None else max(best_comp_ur, f)
                raw_t = ftypes.get("tension")
                if raw_t:
                    val_t = _extract_osdag_summary(raw_t).get("efficiency")
                    if _is_valid_ur(val_t):
                        f = float(val_t)
                        best_tens_ur = f if best_tens_ur is None else max(best_tens_ur, f)

    if best_comp_ur is not None:
        items.append(("CB Compression", best_comp_ur, "Cross Bracing"))
    if best_tens_ur is not None:
        items.append(("CB Tension", best_tens_ur, "Cross Bracing"))
    if best_slnd_ur is not None:
        items.append(("CB Slenderness", best_slnd_ur, "Cross Bracing"))

    # 4. End Diaphragms — extract actual ED design check results independently.
    # NEVER reuse Cross Bracing values. Omit if no valid ED results exist.
    ed_comp_ur = None
    ed_tens_ur = None

    ed_dump = output_dict.get("end_diaphragm_design_results")
    if not ed_dump and bridge and hasattr(bridge, "_ed_pair_designs"):
        ed_dump = bridge._ed_pair_designs()

    if isinstance(ed_dump, dict):
        for pair_name, members in ed_dump.items():
            if not isinstance(members, dict):
                continue
            for mem_name, ftypes in members.items():
                if not isinstance(ftypes, dict):
                    continue
                raw_c = ftypes.get("compression")
                if raw_c:
                    val_c = _extract_osdag_summary(raw_c).get("efficiency")
                    if _is_valid_ur(val_c):
                        f = float(val_c)
                        ed_comp_ur = f if ed_comp_ur is None else max(ed_comp_ur, f)
                raw_t = ftypes.get("tension")
                if raw_t:
                    val_t = _extract_osdag_summary(raw_t).get("efficiency")
                    if _is_valid_ur(val_t):
                        f = float(val_t)
                        ed_tens_ur = f if ed_tens_ur is None else max(ed_tens_ur, f)

    if ed_comp_ur is not None:
        items.append(("ED Compression", ed_comp_ur, "End Diaphragm"))
    if ed_tens_ur is not None:
        items.append(("ED Tension", ed_tens_ur, "End Diaphragm"))

    return items

