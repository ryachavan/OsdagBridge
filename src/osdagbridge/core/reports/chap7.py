# =============================================================================
# Chapter 7: Material Take-off & Quantity Summary
# =============================================================================

from typing import Optional, Dict
from osdagbridge.core.reports.report_utils import _fig_embed
from osdagbridge.core.reports.styles import make_table_note


def ch7_quantities(input_dict: dict, fig_paths: Optional[Dict[str, str]] = None) -> str:
    """
    Render Chapter 7: Bill of Materials table and material quantity visualizations.
    """
    fps = fig_paths or {}

    # Extract BOQ quantities
    steel_girders_f = str(input_dict.get("steel_girders_vol_formula", "N.A."))
    steel_girders_q = str(input_dict.get("steel_girders_qty", "N.A."))
    steel_girders_vt = str(input_dict.get("steel_girders_vol_total", "N.A."))
    steel_girders_ws = str(input_dict.get("steel_girders_wt_single", "N.A."))
    steel_girders_wt = str(input_dict.get("steel_girders_wt_total", "N.A."))

    bracing_top_f = str(input_dict.get("bracing_top_vol_formula", "N.A."))
    bracing_top_q = str(input_dict.get("bracing_top_qty", "N.A."))
    bracing_top_vt = str(input_dict.get("bracing_top_vol_total", "N.A."))
    bracing_top_ws = str(input_dict.get("bracing_top_wt_single", "N.A."))
    bracing_top_wt = str(input_dict.get("bracing_top_wt_total", "N.A."))

    bracing_bot_f = str(input_dict.get("bracing_bot_vol_formula", "N.A."))
    bracing_bot_q = str(input_dict.get("bracing_bot_qty", "N.A."))
    bracing_bot_vt = str(input_dict.get("bracing_bot_vol_total", "N.A."))
    bracing_bot_ws = str(input_dict.get("bracing_bot_wt_single", "N.A."))
    bracing_bot_wt = str(input_dict.get("bracing_bot_wt_total", "N.A."))

    bracing_diag_f = str(input_dict.get("bracing_diag_vol_formula", "N.A."))
    bracing_diag_q = str(input_dict.get("bracing_diag_qty", "N.A."))
    bracing_diag_vt = str(input_dict.get("bracing_diag_vol_total", "N.A."))
    bracing_diag_ws = str(input_dict.get("bracing_diag_wt_single", "N.A."))
    bracing_diag_wt = str(input_dict.get("bracing_diag_wt_total", "N.A."))

    ed_wt = str(input_dict.get("steel_ed_wt_total", "0.00"))
    ed_vt = str(input_dict.get("steel_ed_vol_total", "0.00"))
    ed_q = str(input_dict.get("steel_ed_qty", "N.A."))
    ed_f = str(input_dict.get("steel_ed_vol_formula", "N.A."))

    concrete_deck_f = str(input_dict.get("concrete_deck_vol_formula", "N.A."))
    concrete_deck_q = str(input_dict.get("concrete_deck_qty", "N.A."))
    concrete_deck_vt = str(input_dict.get("concrete_deck_vol_total", "N.A."))
    concrete_deck_ws = str(input_dict.get("concrete_deck_wt_single", "N.A."))
    concrete_deck_wt = str(input_dict.get("concrete_deck_wt_total", "N.A."))

    rebar_deck_f = str(input_dict.get("rebar_deck_vol_formula", "N.A."))
    rebar_deck_q = str(input_dict.get("rebar_deck_qty", "N.A."))
    rebar_deck_vt = str(input_dict.get("rebar_deck_vol_total", "N.A."))
    rebar_deck_ws = str(input_dict.get("rebar_deck_wt_single", "N.A."))
    rebar_deck_wt = str(input_dict.get("rebar_deck_wt_total", "N.A."))

    shear_studs_f = str(input_dict.get("shear_studs_vol_formula", "N.A."))
    shear_studs_q = str(input_dict.get("shear_studs_qty", "N.A."))
    shear_studs_vt = str(input_dict.get("shear_studs_vol_total", "N.A."))
    shear_studs_ws = str(input_dict.get("shear_studs_wt_single", "N.A."))
    shear_studs_wt = str(input_dict.get("shear_studs_wt_total", "N.A."))

    crash_barrier_f = str(input_dict.get("crash_barrier_vol_formula", "N.A."))
    crash_barrier_q = str(input_dict.get("crash_barrier_qty", "N.A."))
    crash_barrier_vt = str(input_dict.get("crash_barrier_vol_total", "N.A."))
    crash_barrier_ws = str(input_dict.get("crash_barrier_wt_single", "N.A."))
    crash_barrier_wt = str(input_dict.get("crash_barrier_wt_total", "N.A."))

    fig_steel = _fig_embed(
        fps.get("boq_steel_tonnage"),
        "Figure 7.1: Structural Steel Tonnage Breakdown",
        width=r"0.75\textwidth"
    ) if fps.get("boq_steel_tonnage") else ""

    fig_concrete_rebar = _fig_embed(
        fps.get("boq_concrete_rebar"),
        "Figure 7.2: Concrete Deck Volume vs. Reinforcement Steel Weight",
        width=r"0.75\textwidth"
    ) if fps.get("boq_concrete_rebar") else ""

    charts_section = ""
    if fig_steel or fig_concrete_rebar:
        charts_section = r"""
\newpage
\section{Material Quantity Visualizations}
\label{sec:material-charts}

""" + fig_steel + r"""

\vspace{1.0em}

""" + fig_concrete_rebar + r"""
"""

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

This section summarizes the material quantities computed for the bridge superstructure, including structural steel tonnage, concrete deck volume, reinforcement steel, and connection hardware.

\vspace{0.8em}

\begingroup
\setlength{\tabcolsep}{3.5pt}
\begin{longtable}{|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|}
\caption{\textbf{Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}}\label{tab:bom}\\
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\[6pt]
\hline
\endfirsthead

\caption*{(Table 7.1 continued)}\\
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\[6pt]
\hline
\endhead

\hline
\multicolumn{7}{r}{\footnotesize\textit{Continued on next page\dots}} \\[2pt]
\endfoot

\hline
\endlastfoot

1 & Structural Steel (IS 2062) for Girders & """ + steel_girders_f + r""" & """ + steel_girders_q + r""" & """ + steel_girders_vt + r""" & """ + steel_girders_ws + r""" & """ + steel_girders_wt + r""" \\[6pt]
\hline
2(a) & Cross Bracing - Top Chord & """ + bracing_top_f + r""" & """ + bracing_top_q + r""" & """ + bracing_top_vt + r""" & """ + bracing_top_ws + r""" & """ + bracing_top_wt + r""" \\[6pt]
\hline
2(b) & Cross Bracing - Bottom Chord & """ + bracing_bot_f + r""" & """ + bracing_bot_q + r""" & """ + bracing_bot_vt + r""" & """ + bracing_bot_ws + r""" & """ + bracing_bot_wt + r""" \\[6pt]
\hline
2(c) & Cross Bracing - Diagonal Chord & """ + bracing_diag_f + r""" & """ + bracing_diag_q + r""" & """ + bracing_diag_vt + r""" & """ + bracing_diag_ws + r""" & """ + bracing_diag_wt + r""" \\[6pt]
\hline
2(d) & End Diaphragms & """ + ed_f + r""" & """ + ed_q + r""" & """ + ed_vt + r""" & --- & """ + ed_wt + r""" \\[6pt]
\hline
3 & Concrete (M40) for Deck Slab & """ + concrete_deck_f + r""" & """ + concrete_deck_q + r""" & """ + concrete_deck_vt + r""" & """ + concrete_deck_ws + r""" & """ + concrete_deck_wt + r""" \\[6pt]
\hline
4 & Reinforcement Steel (Fe 500) & """ + rebar_deck_f + r""" & """ + rebar_deck_q + r""" & """ + rebar_deck_vt + r""" & """ + rebar_deck_ws + r""" & """ + rebar_deck_wt + r""" \\[6pt]
\hline
5 & Shear Stud Connectors & """ + shear_studs_f + r""" & """ + shear_studs_q + r""" & """ + shear_studs_vt + r""" & """ + shear_studs_ws + r""" & """ + shear_studs_wt + r""" \\[6pt]
\hline
6 & Crash Barrier & """ + crash_barrier_f + r""" & """ + crash_barrier_q + r""" & """ + crash_barrier_vt + r""" & """ + crash_barrier_ws + r""" & """ + crash_barrier_wt + r""" \\[6pt]
\end{longtable}
\endgroup

""" + make_table_note("Note: Density of structural steel = 7850 kg/m³, concrete = 2500 kg/m³. Quantities are based on theoretical geometric profiles.") + r"""

""" + charts_section
