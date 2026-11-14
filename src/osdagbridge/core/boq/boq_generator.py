# =============================================================================
# OsdagBridge — BOQ (Bill of Quantities) Generator
# =============================================================================

import logging
import math
from typing import Any

from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
)

logger = logging.getLogger("osdagbridge.core.boq_generator")


def resolve_girder_value(source: dict, base_key: str, i: int = 0) -> Any:
    """Resolve a girder property from an input/output dict, tolerating both the
    per-girder dynamic key scheme and the legacy scalar key.
    """
    candidates = [
        f"{base_key}.G{i + 1}.M1",
        base_key,
        f"{base_key}.G1.M1"
    ]
    for key in candidates:
        if key in source:
            return source[key]
    raise KeyError(base_key)


def calculate_material_quantities(inputs: dict, outputs: dict) -> dict:
    """Calculate quantities (steel tonnage, concrete volume, rebar, studs)
    needed for the material take-off summary (Chapter 7).
    """
    quantities = {
        "steel_girders_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_girders_qty": "N.A.",
        "steel_girders_vol_total": "N.A.",
        "steel_girders_wt_single": "N.A.",
        "steel_girders_wt_total": "N.A.",
        
        "steel_bracing_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_bracing_qty": "N.A.",
        "steel_bracing_vol_total": "N.A.",
        "steel_bracing_wt_single": "N.A.",
        "steel_bracing_wt_total": "N.A.",

        "bracing_top_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_top_qty": "N.A.",
        "bracing_top_vol_total": "N.A.",
        "bracing_top_wt_single": "N.A.",
        "bracing_top_wt_total": "N.A.",

        "bracing_bot_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_bot_qty": "N.A.",
        "bracing_bot_vol_total": "N.A.",
        "bracing_bot_wt_single": "N.A.",
        "bracing_bot_wt_total": "N.A.",

        "bracing_diag_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_diag_qty": "N.A.",
        "bracing_diag_vol_total": "N.A.",
        "bracing_diag_wt_single": "N.A.",
        "bracing_diag_wt_total": "N.A.",

        "steel_ed_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_ed_qty": "N.A.",
        "steel_ed_vol_total": "N.A.",
        "steel_ed_wt_single": "N.A.",
        "steel_ed_wt_total": "0.00",

        "ed_top_vol_formula": r"\placeholder{Area $\times$ Length}",
        "ed_top_qty": "N.A.",
        "ed_top_vol_total": "N.A.",
        "ed_top_wt_single": "N.A.",
        "ed_top_wt_total": "0.00",

        "ed_bot_vol_formula": r"\placeholder{Area $\times$ Length}",
        "ed_bot_qty": "N.A.",
        "ed_bot_vol_total": "N.A.",
        "ed_bot_wt_single": "N.A.",
        "ed_bot_wt_total": "0.00",

        "ed_diag_vol_formula": r"\placeholder{Area $\times$ Length}",
        "ed_diag_qty": "N.A.",
        "ed_diag_vol_total": "N.A.",
        "ed_diag_wt_single": "N.A.",
        "ed_diag_wt_total": "0.00",
        
        "concrete_deck_vol_formula": r"\placeholder{Width $\times$ Thickness $\times$ Length}",
        "concrete_deck_qty": "N.A.",
        "concrete_deck_vol_total": "N.A.",
        "concrete_deck_wt_single": "N.A.",
        "concrete_deck_wt_total": "N.A.",
        
        "rebar_deck_vol_formula": r"\placeholder{Area $\times$ Length}",
        "rebar_deck_qty": "N.A.",
        "rebar_deck_vol_total": "N.A.",
        "rebar_deck_wt_single": "N.A.",
        "rebar_deck_wt_total": "N.A.",
        
        "shear_studs_vol_formula": r"\placeholder{Area $\times$ Height}",
        "shear_studs_qty": "N.A.",
        "shear_studs_vol_total": "N.A.",
        "shear_studs_wt_single": "N.A.",
        "shear_studs_wt_total": "N.A.",

        "crash_barrier_vol_formula": r"\placeholder{Area $\times$ Length}",
        "crash_barrier_qty": "N.A.",
        "crash_barrier_vol_total": "N.A.",
        "crash_barrier_wt_single": "N.A.",
        "crash_barrier_wt_total": "N.A.",
    }
    try:
        span_val = inputs.get(KEY_SPAN)
        n_girders_val = inputs.get(KEY_TS_NO_OF_GIRDERS)
        if span_val is None or n_girders_val is None:
            return quantities
            
        try:
            span = float(span_val)
            n_girders = int(n_girders_val)
        except Exception:
            return quantities

        if span <= 0 or n_girders <= 0:
            return quantities

        # 1. Concrete deck volume (Cu.m) and Weight (MT)
        overall_width_val = (
            inputs.get("typical_section.overall_bridge_width")
            or inputs.get("typical_section.deck.overall_width")
            or inputs.get("overall_width")
        )
        deck_thickness_val = (
            inputs.get(KEY_TS_DECK_THICKNESS)
            or inputs.get("typical_section.deck.thickness")
            or inputs.get("deck_thickness")
        )
        
        if overall_width_val is not None and deck_thickness_val is not None:
            try:
                overall_width = float(overall_width_val)
                deck_thickness = float(deck_thickness_val) / 1000.0  # mm to m
                if overall_width > 0 and deck_thickness > 0:
                    concrete_vol = span * overall_width * deck_thickness
                    quantities["concrete_deck_vol_formula"] = f"${overall_width:.2f}\\text{{ m}} \\times {deck_thickness:.2f}\\text{{ m}} \\times {span:.2f}\\text{{ m}} = {concrete_vol:.2f}\\text{{ m}}^3$"
                    quantities["concrete_deck_qty"] = "1"
                    quantities["concrete_deck_vol_total"] = f"{concrete_vol:.2f}"
                    quantities["concrete_deck_wt_single"] = f"{(concrete_vol * 2.5):.2f}"
                    quantities["concrete_deck_wt_total"] = f"{(concrete_vol * 2.5):.2f}"

                    # 2. Reinforcement Steel (Cu.m) and Weight (MT)
                    dd_results = outputs.get("deck_design_results", {}) or {}
                    as_bot = dd_results.get("rebar_bottom_area")
                    as_top = dd_results.get("rebar_top_area")
                    as_long = dd_results.get("rebar_long_area")

                    has_detailed_rebar = False
                    if as_bot is not None and as_top is not None:
                        try:
                            as_bot_f = float(as_bot)  # mm²/m
                            as_top_f = float(as_top)  # mm²/m
                            as_long_f = float(as_long) if as_long is not None else (0.2 * (as_bot_f + as_top_f))
                            if as_bot_f > 0 and as_top_f > 0:
                                vol_trans = (as_bot_f + as_top_f) * 1e-6 * overall_width * span
                                vol_long = as_long_f * 1e-6 * overall_width * span
                                rebar_vol = (vol_trans + vol_long) * 1.15  # 15% allowance for laps and hooks
                                rebar_wt_kg = rebar_vol * 7850.0
                                rebar_wt_mt = rebar_wt_kg / 1000.0
                                quantities["rebar_deck_vol_formula"] = (
                                    f"\\makecell{{Designed $A_s$ (15\\% laps) \\\\ "
                                    f"${rebar_vol:.5f}\\text{{ m}}^3$}}"
                                )
                                quantities["rebar_deck_qty"] = "1"
                                quantities["rebar_deck_vol_total"] = f"{rebar_vol:.2f}"
                                quantities["rebar_deck_wt_single"] = f"{rebar_wt_mt:.2f}"
                                quantities["rebar_deck_wt_total"] = f"{rebar_wt_mt:.2f}"
                                has_detailed_rebar = True
                        except (TypeError, ValueError):
                            has_detailed_rebar = False

                    if not has_detailed_rebar:
                        # Standard empirical estimate per IRC guidelines (120 kg/m³ of deck concrete)
                        rebar_wt_kg = concrete_vol * 120.0
                        rebar_vol = rebar_wt_kg / 7850.0
                        rebar_wt_mt = rebar_wt_kg / 1000.0
                        quantities["rebar_deck_vol_formula"] = (
                            f"\\makecell{{Est. ($120\\text{{ kg/m}}^3\\text{{ conc.}})$ \\\\ "
                            f"$= {rebar_vol:.5f}\\text{{ m}}^3$}}"
                        )
                        quantities["rebar_deck_qty"] = "1"
                        quantities["rebar_deck_vol_total"] = f"{rebar_vol:.2f}"
                        quantities["rebar_deck_wt_single"] = f"{rebar_wt_mt:.2f} (est.)"
                        quantities["rebar_deck_wt_total"] = f"{rebar_wt_mt:.2f}"
            except Exception:
                pass

        # 3. Steel Girders (Cu.m) and Weight (MT)
        girder_area = 0.0
        try:
            # Resolve representative girder sectional area
            girder_area = float(resolve_girder_value(inputs, "member_properties.girder_details.section_properties.area", 0))
        except Exception:
            pass

        # Calculate from inputs if not in properties
        if girder_area <= 0:
            try:
                dw_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_depth", 0)
                tw_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_thickness", 0)
                bft_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_width", 0)
                tft_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_thickness", 0)
                bfb_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_width", 0)
                tfb_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_thickness", 0)
                
                if (dw_val is not None and tw_val is not None and 
                    bft_val is not None and tft_val is not None and 
                    bfb_val is not None and tfb_val is not None):
                    
                    dw = float(dw_val)
                    tw = float(tw_val)
                    bft = float(bft_val)
                    tft = float(tft_val)
                    bfb = float(bfb_val)
                    tfb = float(tfb_val)
                    
                    # All dimensions in mm, compute in m²
                    girder_area = ((dw * tw) + (bft * tft) + (bfb * tfb)) / 1e6
            except Exception:
                pass

        total_girder_mass = 0.0
        if girder_area > 0:
            girder_vol = girder_area * span
            quantities["steel_girders_vol_formula"] = f"${girder_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {girder_vol:.5f}\\text{{ m}}^3$"
            quantities["steel_girders_qty"] = str(n_girders)
            
            # calculate tonnage / volume
            for gi in range(n_girders):
                try:
                    mass_per_m = float(resolve_girder_value(inputs, "member_properties.girder_details.section_properties.mass", gi))
                    total_girder_mass += mass_per_m * span
                except Exception:
                    total_girder_mass += girder_area * span * 7850.0
            
            girder_total_vol = n_girders * girder_vol
            quantities["steel_girders_vol_total"] = f"{girder_total_vol:.2f}"
            
            single_girder_wt = (total_girder_mass / n_girders) / 1000.0
            total_girder_wt = total_girder_mass / 1000.0
            quantities["steel_girders_wt_single"] = f"{single_girder_wt:.2f}"
            quantities["steel_girders_wt_total"] = f"{total_girder_wt:.2f}"

        # 4. Shear Stud Connectors (Cu.m) and Weight (MT)
        spacing_mm = 0.0
        studs_per_sec = 0
        stud_d = 0.0
        stud_h_mm = 0.0

        spacing_val = outputs.get("steeldesign.details.shear.longitudinal_spacing")
        studs_val = outputs.get("steeldesign.details.shear.studs_per_section")
        stud_d_val = outputs.get("steeldesign.details.shear.diameter") or inputs.get("design_options.shear_studs.diameter")
        stud_h_val = outputs.get("steeldesign.details.shear.height") or inputs.get("design_options.shear_studs.height")

        if spacing_val is not None and studs_val is not None and stud_d_val is not None and stud_h_val is not None:
            try:
                spacing_mm = float(spacing_val)
                studs_per_sec = int(studs_val)
                stud_d = float(stud_d_val)
                stud_h_mm = float(stud_h_val)
            except Exception:
                pass

        if spacing_mm > 0.0 and studs_per_sec > 0 and stud_d > 0.0 and stud_h_mm > 0.0:
            stud_h = stud_h_mm / 1000.0  # mm to m
            n_sections = int(span * 1000.0 / spacing_mm) + 1
            total_studs = n_girders * studs_per_sec * n_sections
            
            stud_area = (3.14159 * (stud_d / 1000.0) ** 2) / 4.0
            stud_vol = stud_area * stud_h
            quantities["shear_studs_vol_formula"] = f"${stud_area:.6f}\\text{{ m}}^2 \\times {stud_h:.3f}\\text{{ m}} = {stud_vol:.6f}\\text{{ m}}^3$"
            quantities["shear_studs_qty"] = str(total_studs)
            
            studs_total_vol = total_studs * stud_vol
            quantities["shear_studs_vol_total"] = f"{studs_total_vol:.2f}"
            
            # density of steel = 7850 kg/m^3 = 7.85 tonnes/m^3
            single_stud_wt = stud_vol * 7.85
            total_studs_wt = studs_total_vol * 7.85
            quantities["shear_studs_wt_single"] = f"{single_stud_wt:.6f}"
            quantities["shear_studs_wt_total"] = f"{total_studs_wt:.3f}"
        else:
            quantities["shear_studs_vol_formula"] = "N.A."
            quantities["shear_studs_qty"] = "N.A."
            quantities["shear_studs_vol_total"] = "N.A."
            quantities["shear_studs_wt_single"] = "N.A."
            quantities["shear_studs_wt_total"] = "N.A."

        # 5. Steel Bracings (Cu.m) and Weight (MT)
        # Find bracing section properties from outputs or skip if not present
        bracing_area = 0.0
        bracing_len = 0.0
        top_chord_enabled = True
        bot_chord_enabled = True

        bracing_area_val = outputs.get("transverse_member_design.cb.section_properties.bracing.G1G2.A")
        cb_forces = outputs.get("crossbracing_forces_dict")
        bracing_len_val = None
        if cb_forces:
            cb_geom = cb_forces.get("geometry")
            if cb_geom:
                bracing_len_val = cb_geom.get("diagonal_length_m")

        if bracing_area_val is not None and bracing_len_val is not None:
            try:
                bracing_area = float(bracing_area_val) / 10000.0  # Convert cm² to m²
                bracing_len = float(bracing_len_val)
            except Exception:
                pass

        spacing_val = inputs.get(KEY_TS_GIRDER_SPACING)
        spacing = 0.0
        if spacing_val is not None:
            try:
                spacing = float(spacing_val)
            except Exception:
                pass

        # Only perform calculations if bracing is designed (area and length are positive)
        if bracing_area > 0.0 and bracing_len > 0.0 and spacing > 0.0:
            cb_forces = outputs.get("crossbracing_forces_dict", {}) or {}
            cb_geom = cb_forces.get("geometry", {}) or {}
            cb_spacing_val = cb_geom.get("cb_spacing_m")
            cb_spacing = 0.0
            if cb_spacing_val is not None:
                try:
                    cb_spacing = float(cb_spacing_val)
                except Exception:
                    pass

            if cb_spacing <= 0.0:
                for k, v in inputs.items():
                    if "cross_bracing_spacing" in str(k).lower() and v:
                        try:
                            cb_spacing = float(v)
                            break
                        except Exception:
                            pass

            panel_assumed = False
            if cb_spacing > 0.0:
                n_panels = max(1, round(span / cb_spacing) - 1)
            else:
                n_brac = None
                for k, v in inputs.items():
                    if "no_of_cross_bracings" in str(k).lower() and v:
                        try:
                            n_brac = int(v)
                            break
                        except Exception:
                            pass
                if n_brac is not None and n_brac > 0:
                    n_panels = n_brac + 1
                else:
                    n_panels = max(3, int(span / 5.0))
                    panel_assumed = True

            panel_note = r"\text{ (assumed 5m panel spacing)}" if panel_assumed else ""

            # 5a. Top Chord
            top_chord_qty = (n_girders - 1) * n_panels if top_chord_enabled else 0
            top_chord_vol_single = bracing_area * spacing
            top_chord_vol_total = top_chord_qty * top_chord_vol_single
            top_chord_wt_single = top_chord_vol_single * 7.85
            top_chord_wt_total = top_chord_vol_total * 7.85
            
            quantities["bracing_top_vol_formula"] = f"${bracing_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {top_chord_vol_single:.5f}\\text{{ m}}^3{panel_note}$"
            quantities["bracing_top_qty"] = str(top_chord_qty)
            quantities["bracing_top_vol_total"] = f"{top_chord_vol_total:.2f}" if top_chord_enabled else "0.00"
            quantities["bracing_top_wt_single"] = f"{top_chord_wt_single:.4f}"
            quantities["bracing_top_wt_total"] = f"{top_chord_wt_total:.2f}" if top_chord_enabled else "0.00"

            # 5b. Bottom Chord
            bot_chord_qty = (n_girders - 1) * n_panels if bot_chord_enabled else 0
            bot_chord_vol_single = bracing_area * spacing
            bot_chord_vol_total = bot_chord_qty * bot_chord_vol_single
            bot_chord_wt_single = bot_chord_vol_single * 7.85
            bot_chord_wt_total = bot_chord_vol_total * 7.85
            
            quantities["bracing_bot_vol_formula"] = f"${bracing_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {bot_chord_vol_single:.5f}\\text{{ m}}^3{panel_note}$"
            quantities["bracing_bot_qty"] = str(bot_chord_qty)
            quantities["bracing_bot_vol_total"] = f"{bot_chord_vol_total:.2f}" if bot_chord_enabled else "0.00"
            quantities["bracing_bot_wt_single"] = f"{bot_chord_wt_single:.4f}"
            quantities["bracing_bot_wt_total"] = f"{bot_chord_wt_total:.2f}" if bot_chord_enabled else "0.00"

            # 5c. Diagonal
            diags_qty = (n_girders - 1) * n_panels * 2
            diag_vol_single = bracing_area * bracing_len
            diag_vol_total = diags_qty * diag_vol_single
            diag_wt_single = diag_vol_single * 7.85
            diag_wt_total = diag_vol_total * 7.85
            
            quantities["bracing_diag_vol_formula"] = f"${bracing_area:.5f}\\text{{ m}}^2 \\times {bracing_len:.2f}\\text{{ m}} = {diag_vol_single:.5f}\\text{{ m}}^3{panel_note}$"
            quantities["bracing_diag_qty"] = str(diags_qty)
            quantities["bracing_diag_vol_total"] = f"{diag_vol_total:.2f}"
            quantities["bracing_diag_wt_single"] = f"{diag_wt_single:.4f}"
            quantities["bracing_diag_wt_total"] = f"{diag_wt_total:.2f}"
        else:
            # Keep all bracing volumes, quantities, and weights as default placeholder "N.A."
            for prefix in ("bracing_top", "bracing_bot", "bracing_diag"):
                quantities[f"{prefix}_vol_formula"] = "N.A."
                quantities[f"{prefix}_qty"] = "N.A."
                quantities[f"{prefix}_vol_total"] = "N.A."
                quantities[f"{prefix}_wt_single"] = "N.A."
                quantities[f"{prefix}_wt_total"] = "N.A."

        # 5d. End Diaphragms (Cu.m) and Weight (MT)
        # End diaphragms are present at the 2 ends of the span across each girder bay.
        ed_area = 0.0
        ed_len = 0.0

        # Query actual end-diaphragm section properties only.
        # NEVER substitute cross-bracing section properties for end diaphragms.
        for k, v in outputs.items():
            if str(k).startswith("transverse_member_design.ed.section_properties.bracing.") and str(k).endswith(".A"):
                try:
                    val = float(v)
                    if val > 0.0:
                        ed_area = val / 10000.0  # cm² to m²
                        break
                except (TypeError, ValueError):
                    pass

        if ed_area <= 0.0:
            for k, v in outputs.items():
                if "transverse_member_design.ed.section_properties." in str(k) and str(k).endswith(".A"):
                    try:
                        val = float(v)
                        if val > 0.0:
                            ed_area = val / 10000.0  # cm² to m²
                            break
                    except (TypeError, ValueError):
                        pass

        ed_forces = outputs.get("end_diaphragm_forces_dict")
        if ed_forces and isinstance(ed_forces, dict):
            ed_geom = ed_forces.get("geometry", {}) or {}
            ed_len_val = ed_geom.get("diagonal_length_m")
            if ed_len_val is not None:
                try:
                    ed_len = float(ed_len_val)
                except (TypeError, ValueError):
                    pass

        ed_type = ""
        for k, v in inputs.items():
            if "end_diaphragm_type" in str(k).lower() and v:
                ed_type = str(v)
                break

        is_ed_cb = "brac" in ed_type.strip().lower()

        if ed_area > 0.0 and spacing > 0.0:
            n_ed_bays = (n_girders - 1) * 2
            if is_ed_cb and ed_len > 0.0:
                # Cross-braced end diaphragm
                ed_top_qty = n_ed_bays
                ed_bot_qty = n_ed_bays
                ed_diag_qty = n_ed_bays * 2

                ed_top_vol_single = ed_area * spacing
                ed_top_vol_tot = ed_top_qty * ed_top_vol_single
                ed_bot_vol_single = ed_area * spacing
                ed_bot_vol_tot = ed_bot_qty * ed_bot_vol_single
                ed_diag_vol_single = ed_area * ed_len
                ed_diag_vol_tot = ed_diag_qty * ed_diag_vol_single

                ed_vol_tot = ed_top_vol_tot + ed_bot_vol_tot + ed_diag_vol_tot
                ed_wt_tot = ed_vol_tot * 7.85

                quantities["ed_top_vol_formula"] = f"${ed_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {ed_top_vol_single:.5f}\\text{{ m}}^3$"
                quantities["ed_top_qty"] = str(ed_top_qty)
                quantities["ed_top_vol_total"] = f"{ed_top_vol_tot:.2f}"
                quantities["ed_top_wt_single"] = f"{ed_top_vol_single * 7.85:.4f}"
                quantities["ed_top_wt_total"] = f"{ed_top_vol_tot * 7.85:.2f}"

                quantities["ed_bot_vol_formula"] = f"${ed_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {ed_bot_vol_single:.5f}\\text{{ m}}^3$"
                quantities["ed_bot_qty"] = str(ed_bot_qty)
                quantities["ed_bot_vol_total"] = f"{ed_bot_vol_tot:.2f}"
                quantities["ed_bot_wt_single"] = f"{ed_bot_vol_single * 7.85:.4f}"
                quantities["ed_bot_wt_total"] = f"{ed_bot_vol_tot * 7.85:.2f}"

                quantities["ed_diag_vol_formula"] = f"${ed_area:.5f}\\text{{ m}}^2 \\times {ed_len:.2f}\\text{{ m}} = {ed_diag_vol_single:.5f}\\text{{ m}}^3$"
                quantities["ed_diag_qty"] = str(ed_diag_qty)
                quantities["ed_diag_vol_total"] = f"{ed_diag_vol_tot:.2f}"
                quantities["ed_diag_wt_single"] = f"{ed_diag_vol_single * 7.85:.4f}"
                quantities["ed_diag_wt_total"] = f"{ed_diag_vol_tot * 7.85:.2f}"

                quantities["steel_ed_vol_formula"] = f"${ed_area:.5f}\\text{{ m}}^2$"
                quantities["steel_ed_qty"] = str(ed_top_qty + ed_bot_qty + ed_diag_qty)
                quantities["steel_ed_vol_total"] = f"{ed_vol_tot:.2f}"
                quantities["steel_ed_wt_total"] = f"{ed_wt_tot:.2f}"
            else:
                # Beam end diaphragm (Rolled Beam or Welded Beam): 1 transverse beam per bay at each end
                n_ed_beams = n_ed_bays
                ed_beam_vol_single = ed_area * spacing
                ed_vol_tot = n_ed_beams * ed_beam_vol_single
                ed_wt_tot = ed_vol_tot * 7.85

                quantities["steel_ed_vol_formula"] = f"${ed_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {ed_beam_vol_single:.5f}\\text{{ m}}^3$"
                quantities["steel_ed_qty"] = str(n_ed_beams)
                quantities["steel_ed_vol_total"] = f"{ed_vol_tot:.2f}"
                quantities["steel_ed_wt_total"] = f"{ed_wt_tot:.2f}"

                for prefix in ("ed_top", "ed_bot", "ed_diag"):
                    quantities[f"{prefix}_vol_formula"] = "N.A."
                    quantities[f"{prefix}_qty"] = "N.A."
                    quantities[f"{prefix}_vol_total"] = "N.A."
                    quantities[f"{prefix}_wt_single"] = "N.A."
                    quantities[f"{prefix}_wt_total"] = "0.00"
        else:
            # End diaphragms not designed / no valid section properties found
            for prefix in ("ed_top", "ed_bot", "ed_diag", "steel_ed"):
                quantities[f"{prefix}_vol_formula"] = "N.A."
                quantities[f"{prefix}_qty"] = "N.A."
                quantities[f"{prefix}_vol_total"] = "N.A."
                quantities[f"{prefix}_wt_single"] = "N.A."
                quantities[f"{prefix}_wt_total"] = "0.00"

        # 6. Crash Barrier (Cu.m) and Weight (MT)
        KEY_CB_AREA = "typical_section.crash_barrier.area"
        cb_area = 0.0
        cb_area_val = inputs.get(KEY_CB_AREA)
        
        if cb_area_val is not None:
            try:
                cb_area = float(cb_area_val) / 1e6
            except Exception:
                pass
        
        if cb_area > 0.0:
            cb_vol = cb_area * span
            quantities["crash_barrier_vol_formula"] = f"${cb_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {cb_vol:.5f}\\text{{ m}}^3$"
            quantities["crash_barrier_qty"] = "2"
            
            cb_total_vol = 2 * cb_vol
            quantities["crash_barrier_vol_total"] = f"{cb_total_vol:.2f}"
            
            single_cb_wt = cb_vol * 2.5
            total_cb_wt = cb_total_vol * 2.5
            quantities["crash_barrier_wt_single"] = f"{single_cb_wt:.2f}"
            quantities["crash_barrier_wt_total"] = f"{total_cb_wt:.2f}"
        else:
            quantities["crash_barrier_vol_formula"] = "N.A."
            quantities["crash_barrier_qty"] = "N.A."
            quantities["crash_barrier_vol_total"] = "N.A."
            quantities["crash_barrier_wt_single"] = "N.A."
            quantities["crash_barrier_wt_total"] = "N.A."

    except Exception as exc:
        logger.warning(f"Error calculating material quantities: {exc}")

    return quantities
