"""
Unit tests for OsdagBridge Report Generator enhancements.
Verifies all 6 requirements:
  Req 1: Repeated table headers on multi-page longtables.
  Req 2: Layout & footer geometry (no negative vspace in footrule, safe bottom margin).
  Req 3: Load and geometry table split into Vehicle and Footpath Live Loads.
  Req 4: Utilization ratio bar chart generation and Section 5.5 embedding.
  Req 5: Material quantity charts (Steel tonnage breakdown and Concrete vs. Rebar).
  Req 6: Centralized formatting system (styles.py).
"""

import os
import pytest

from osdagbridge.core.reports.styles import (
    GEOMETRY_OPTIONS,
    LATEX_COLOR_DEFS,
    COLOR_OSDAG_GREEN_HEX,
    COLOR_PASS_HEX,
    COLOR_FAIL_HEX,
    make_longtable_header,
    make_table_note,
    MPL_REPORT_THEME,
)
from osdagbridge.core.reports.report_charts import (
    generate_ur_summary_chart,
    generate_steel_tonnage_chart,
    generate_concrete_rebar_chart,
    extract_ur_chart_items,
)
from osdagbridge.core.boq.boq_generator import calculate_material_quantities
from osdagbridge.core.reports.report_generator import preamble, ReportDataBridge
from osdagbridge.core.reports.chap2 import ch2_input_parameters
from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_GIRDER_SPACING,
    KEY_DESIGN_MODE,
    KEY_DD_MU_BOT,
    KEY_DD_M_ULS_SAG,
    KEY_DD_MU_TOP,
    KEY_DD_M_ULS_HOG,
    KEY_DD_VRD_C_MPA,
    KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_SHEAR_VED,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_BOT,
    KEY_DD_WK_TOP,
    KEY_UTIL_FLEXURE,
    KEY_UTIL_SHEAR,
    KEY_UTIL_LTB,
)


class DummyMetadata:
    project_name = "Test Bridge"
    project_location = "Mumbai"
    job_number = "TB-001"
    report_date = "2026-11-14"
    subtitle = "Rev 0"
    client = "FOSSEE"
    designer = "Engineer"


# =============================================================================
# Requirement 6: Centralized Formatting System
# =============================================================================

def test_styles_configuration():
    assert "footskip=12mm" in GEOMETRY_OPTIONS
    assert "bottom=25mm" in GEOMETRY_OPTIONS
    assert "osdagGreen" in LATEX_COLOR_DEFS
    assert COLOR_OSDAG_GREEN_HEX == "91B014"
    assert COLOR_PASS_HEX == "2E7D32"
    assert COLOR_FAIL_HEX == "C62828"
    assert MPL_REPORT_THEME["figure.dpi"] == 200


def test_styles_helpers():
    header = make_longtable_header(
        col_spec="|C{3cm}|C{3cm}|",
        caption="Sample Table",
        header_row=r"\textbf{Col A} & \textbf{Col B}",
        num_cols=2,
        label="tab:sample"
    )
    assert r"\endfirsthead" in header
    assert r"\endhead" in header
    assert r"\endfoot" in header
    assert r"\endlastfoot" in header

    note = make_table_note("Test note text")
    assert r"\nopagebreak" in note
    assert "Test note text" in note


# =============================================================================
# Requirement 2: Layout & Footer Overlap Prevention
# =============================================================================

def test_preamble_clean_footrule():
    tex = preamble("Project", "Job1", "2026-11-14")
    # Must NOT have negative vertical space pulling footer into text body
    assert r"\vspace{-8pt}" not in tex
    assert r"\vspace{-20pt}" not in tex
    # Must include updated geometry options
    assert "footskip=12mm" in tex
    assert "bottom=25mm" in tex


# =============================================================================
# Requirement 1: Repeated Table Headers in Chapter 2, 3, 5, 7
# =============================================================================

def test_chap2_repeated_headers():
    input_dict = {KEY_SPAN: "30.0", KEY_TS_NO_OF_GIRDERS: "2"}
    tex = ch2_input_parameters(DummyMetadata(), input_dict, {})
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"\endfoot" in tex
    assert r"\endlastfoot" in tex


def test_chap3_repeated_headers_and_split_tables():
    input_dict = {
        KEY_SPAN: "30.0",
        "carriageway_width": 7.5,
        "selected_vehicles": ["Class A", "Class 70R Tracked"],
        "footpath_live_load": 5.0,
    }
    tex = ch3_loads(input_dict)
    # Requirement 1: Repeated headers
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    # Requirement 3: Split into Table 3.3 and Table 3.4
    assert r"\label{tab:vehicle-live-loads}" in tex
    assert r"\label{tab:footpath-live-loads}" in tex
    assert "Vehicle Live Loads" in tex
    assert "Footpath Live Loads" in tex
    assert "Impact Factor" in tex
    assert "Braking Load" in tex


def test_chap5_repeated_headers_and_page30_fix():
    bridge_payload = type("Payload", (), {
        "inputs": {KEY_SPAN: "30.0", KEY_TS_NO_OF_GIRDERS: "2", KEY_DESIGN_MODE: "Optimized"},
        "output_dict": {
            "design_results": {
                "per_girder": {
                    "G1": {
                        "checks": [
                            {"check_id": 1, "dcr": 0.16, "demand": 697.45, "capacity": 4409.64, "demand_unit": "kN-m", "capacity_unit": "kN-m"},
                            {"check_id": 2, "dcr": 0.29, "demand": 160.94, "capacity": 550.70, "demand_unit": "kN", "capacity_unit": "kN"},
                            {"check_id": 8, "dcr": 1.35, "demand": 125.03, "capacity": 92.49, "demand_unit": "MPa", "capacity_unit": "MPa"},
                        ]
                    }
                }
            },
            "deck_report_values": {
                KEY_DD_MU_BOT: 37.05,
                KEY_DD_M_ULS_SAG: 33.60,
                KEY_DD_MU_TOP: 40.16,
                KEY_DD_M_ULS_HOG: 25.20,
            }
        }
    })()
    bridge = ReportDataBridge(bridge_payload.output_dict, bridge_payload.inputs, bridge_payload)
    tex = ch5_design_checks({}, bridge, fig_paths={"ur_summary": "assets/ur_summary.png"})

    # Requirement 1: Repeated headers
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"\endfoot" in tex
    assert r"\endlastfoot" in tex

    # Requirement 2: Clean page break before Shear Connector Design
    assert r"\clearpage" in tex
    assert r"\subsection{Shear Connector Design}" in tex

    # Requirement 4: Embedded Figure 5.1
    assert "Figure 5.1: Overall Structural Utilization Ratios" in tex
    assert "assets/ur_summary.png" in tex


# =============================================================================
# Requirement 4: Utilization Ratio Chart Generation
# =============================================================================

def test_ur_chart_generation():
    items = [
        ("Girder Moment", 0.16, "Steel Plate Girder"),
        ("Girder Shear", 0.29, "Steel Plate Girder"),
        ("Girder Fatigue", 1.35, "Steel Plate Girder"),
        ("Deck Sagging", 0.91, "Concrete Deck Slab"),
        ("CB Compression", 0.60, "Cross Bracing"),
        ("ED Compression", 0.60, "End Diaphragm"),
    ]
    img_bytes = generate_ur_summary_chart(items)
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 1000
    # PNG signature check: \x89PNG\r\n\x1a\n
    assert img_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_extract_ur_chart_items():
    output_dict = {
        "design_results": {
            "per_girder": {
                "G1": {
                    "checks": [
                        {"check_id": 1, "dcr": 0.16},
                        {"check_id": 2, "dcr": 0.29},
                        {"check_id": 8, "dcr": 1.35},
                    ]
                }
            }
        },
        "deck_report_values": {
            KEY_DD_MU_BOT: 37.05,
            KEY_DD_M_ULS_SAG: 33.60,
        }
    }
    input_dict = {KEY_SPAN: "30.0"}
    items = extract_ur_chart_items(output_dict, input_dict)
    assert len(items) >= 4
    labels = [it[0] for it in items]
    assert "Girder Moment" in labels
    assert "Girder Shear" in labels
    assert "Girder Fatigue" in labels
    assert "Deck Sagging" in labels
    fatigue_ur = next(it[1] for it in items if it[0] == "Girder Fatigue")
    assert fatigue_ur == 1.35


# =============================================================================
# Requirement 5: Material Quantity Charts and End Diaphragm BOQ
# =============================================================================

def test_boq_end_diaphragm_quantities():
    input_dict = {
        KEY_SPAN: "30.0",
        KEY_TS_NO_OF_GIRDERS: "2",
        KEY_TS_GIRDER_SPACING: "2.5",
        "member_properties.end_diaphragm_details.end_diaphragm_type": "Rolled Beam",
    }
    outputs = {
        "transverse_member_design.ed.section_properties.bracing.G1G2.A": 25.0,
        "end_diaphragm_forces_dict": {"geometry": {"diagonal_length_m": 3.0}}
    }
    quantities = calculate_material_quantities(input_dict, outputs)
    assert "steel_ed_wt_total" in quantities
    assert "steel_ed_vol_total" in quantities
    assert float(quantities["steel_ed_wt_total"]) > 0


# =============================================================================
# Engineering Data Correctness & Independence Tests
# =============================================================================

def test_ur_chart_distinguishes_zero_from_missing():
    """Verify that genuine zero utilization (0.0) is retained while missing data (None) is omitted."""
    output_dict = {
        "design_results": {
            "per_girder": {
                "G1": {
                    "checks": [
                        {"check_id": 1, "dcr": 0.0},     # Genuine zero moment
                        {"check_id": 2, "dcr": None},    # Missing shear check
                        {"check_id": 5, "dcr": 0.55},    # LTB check
                        {"check_id": 8, "dcr": 1.25},    # Failing fatigue check (> 1.0)
                    ]
                }
            }
        },
        "deck_report_values": {
            KEY_DD_MU_BOT: 40.0,
            KEY_DD_M_ULS_SAG: 0.0,   # Genuine zero deck moment -> UR = 0.0
            KEY_DD_MU_TOP: None,     # Missing deck hogging
        }
    }
    input_dict = {KEY_SPAN: "30.0"}
    items = extract_ur_chart_items(output_dict, input_dict)

    labels = [it[0] for it in items]
    val_map = {it[0]: it[1] for it in items}

    # Girder Moment (0.0) must be included, NOT dropped
    assert "Girder Moment" in labels
    assert val_map["Girder Moment"] == 0.0

    # Girder Shear (None) must be omitted
    assert "Girder Shear" not in labels

    # Girder LTB (0.55) must be included
    assert "Girder LTB" in labels
    assert val_map["Girder LTB"] == 0.55

    # Failing Girder Fatigue (1.25 > 1.0) must be preserved
    assert "Girder Fatigue" in labels
    assert val_map["Girder Fatigue"] == 1.25

    # Deck Sagging (0.0) must be included
    assert "Deck Sagging" in labels
    assert val_map["Deck Sagging"] == 0.0

    # Deck Hogging (None) must be omitted
    assert "Deck Hogging" not in labels

    # Chart generation must handle 0.0 and > 1.0 without error
    img_bytes = generate_ur_summary_chart(items)
    assert len(img_bytes) > 1000


def test_end_diaphragm_independence_from_cross_bracing():
    """Verify End Diaphragm results are strictly independent and never borrow Cross Bracing data."""
    # Case A: Cross bracing has data, but End Diaphragm has NO results
    output_dict_no_ed = {
        "design_results": {"per_girder": {}},
        "crossbracing_design_results": {
            "G1-G2": {
                "diagonal": {
                    "compression": {"Member.efficiency": "0.75", "Member.Slenderness": "120"},
                    "tension": {"Member.efficiency": "0.45"},
                }
            }
        },
        # end_diaphragm_design_results is intentionally omitted
    }
    items_no_ed = extract_ur_chart_items(output_dict_no_ed, {KEY_SPAN: "30.0"})
    labels_no_ed = [it[0] for it in items_no_ed]

    assert "CB Compression" in labels_no_ed
    assert "CB Tension" in labels_no_ed
    # ED must NOT be present when ED design results are absent
    assert "ED Compression" not in labels_no_ed
    assert "ED Tension" not in labels_no_ed

    # Case B: Both have distinct, independent results
    output_dict_with_ed = {
        "design_results": {"per_girder": {}},
        "crossbracing_design_results": {
            "G1-G2": {
                "diagonal": {
                    "compression": {"Member.efficiency": "0.85"},
                    "tension": {"Member.efficiency": "0.65"},
                }
            }
        },
        "end_diaphragm_design_results": {
            "G1-G2": {
                "diagonal": {
                    "compression": {"Member.efficiency": "0.42"},
                    "tension": {"Member.efficiency": "0.33"},
                }
            }
        }
    }
    items_with_ed = extract_ur_chart_items(output_dict_with_ed, {KEY_SPAN: "30.0"})
    val_map = {it[0]: it[1] for it in items_with_ed}

    assert val_map["CB Compression"] == 0.85
    assert val_map["CB Tension"] == 0.65
    assert val_map["ED Compression"] == 0.42
    assert val_map["ED Tension"] == 0.33
    # Verify ED did not match or borrow CB
    assert val_map["ED Compression"] != val_map["CB Compression"]
    assert val_map["ED Tension"] != val_map["CB Tension"]


def test_boq_no_cross_bracing_substitution_for_end_diaphragm():
    """Verify BOQ does not borrow cross bracing section properties when ED properties are missing."""
    input_dict = {
        KEY_SPAN: "30.0",
        KEY_TS_NO_OF_GIRDERS: "2",
        KEY_TS_GIRDER_SPACING: "2.5",
    }
    # Cross bracing is defined, but End Diaphragm is completely missing
    outputs = {
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 35.0,
        "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 3.2, "cb_spacing_m": 5.0}}
    }
    quantities = calculate_material_quantities(input_dict, outputs)

    # Cross bracing should have positive quantity and weight
    assert float(quantities["bracing_diag_wt_total"]) > 0

    # End Diaphragms MUST NOT substitute cross bracing; should be N.A. / 0.00
    assert quantities["steel_ed_wt_total"] == "0.00"
    assert quantities["steel_ed_vol_formula"] == "N.A."
    assert quantities["steel_ed_qty"] == "N.A."


def test_boq_documented_assumptions():
    """Verify that empirical estimates for rebar and cross-bracing panel count are documented."""
    input_dict = {
        KEY_SPAN: "30.0",
        KEY_TS_NO_OF_GIRDERS: "2",
        KEY_TS_GIRDER_SPACING: "2.5",
        "typical_section.deck.overall_width": "8.5",
        "typical_section.deck.thickness": "250",
    }
    # outputs with bracing but missing spacing (triggers assumed 5m spacing)
    # and missing deck_design_results (triggers 120 kg/m³ empirical rebar estimate)
    outputs = {
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 20.0,
        "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 3.0}}
    }
    quantities = calculate_material_quantities(input_dict, outputs)

    # Rebar formula must explicitly document the 120 kg/m³ assumption
    assert "Estimated" in quantities["rebar_deck_vol_formula"] or "120" in quantities["rebar_deck_vol_formula"]
    assert "(est.)" in quantities["rebar_deck_wt_single"]

    # Cross bracing formula must document the assumed 5m panel spacing
    assert "assumed 5m panel spacing" in quantities["bracing_diag_vol_formula"]


def test_material_quantity_charts_generation():
    inputs = {
        "steel_girders_wt_total": 45.2,
        "bracing_top_wt_total": 2.1,
        "bracing_bot_wt_total": 2.1,
        "bracing_diag_wt_total": 3.8,
        "steel_ed_wt_total": 3.5,
        "concrete_deck_vol_total": 65.0,
        "rebar_deck_wt_total": 12.5,
    }
    steel_bytes = generate_steel_tonnage_chart(inputs)
    assert isinstance(steel_bytes, bytes)
    assert steel_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    conc_bytes = generate_concrete_rebar_chart(inputs)
    assert isinstance(conc_bytes, bytes)
    assert conc_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_chap7_repeated_headers_and_figures():
    inputs = {
        "steel_girders_wt_total": "45.20",
        "bracing_top_wt_total": "2.10",
        "bracing_bot_wt_total": "2.10",
        "bracing_diag_wt_total": "3.80",
        "steel_ed_wt_total": "3.50",
        "steel_ed_vol_total": "0.45",
        "concrete_deck_vol_total": "65.00",
        "rebar_deck_wt_total": "12.50",
    }
    fig_paths = {
        "boq_steel_tonnage": "assets/boq_steel_tonnage.png",
        "boq_concrete_rebar": "assets/boq_concrete_rebar.png",
    }
    tex = ch7_quantities(inputs, fig_paths)
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"\endfoot" in tex
    assert r"\endlastfoot" in tex
    assert "End Diaphragms" in tex
    assert "Figure 7.1: Structural Steel Tonnage Breakdown" in tex
    assert "Figure 7.2: Concrete Deck Volume vs. Reinforcement Steel Weight" in tex
