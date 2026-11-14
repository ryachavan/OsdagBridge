# =============================================================================
# OsdagBridge — Centralized Report Styling & Formatting System
# =============================================================================
"""
Centralized style configuration and LaTeX formatting utilities for OsdagBridge
design reports. Provides consistent geometry, color palette, table formatting,
repeated table header builders, and chart theming.
"""

from typing import Optional

# -----------------------------------------------------------------------------
# Color Palette
# -----------------------------------------------------------------------------
COLOR_OSDAG_GREEN_HEX = "91B014"
COLOR_PASS_HEX        = "2E7D32"  # Deep green for passing checks
COLOR_FAIL_HEX        = "C62828"  # Clear red for failing checks
COLOR_WARNING_HEX     = "E65100"  # Amber/orange for warnings
COLOR_NEUTRAL_HEX     = "546E7A"  # Slate grey for neutral bars / secondary data
COLOR_ACCENT_HEX      = "1565C0"  # Blue accent

# LaTeX color definitions to inject into preamble
LATEX_COLOR_DEFS = rf"""
\definecolor{{osdagGreen}}{{HTML}}{{{COLOR_OSDAG_GREEN_HEX}}}
\definecolor{{passGreen}}{{HTML}}{{{COLOR_PASS_HEX}}}
\definecolor{{failRed}}{{HTML}}{{{COLOR_FAIL_HEX}}}
\definecolor{{warnAmber}}{{HTML}}{{{COLOR_WARNING_HEX}}}
"""

# -----------------------------------------------------------------------------
# Page Geometry & Layout Buffers
# -----------------------------------------------------------------------------
# Explicit allocation of top, bottom, footskip, headheight, and headsep guarantees
# a clean buffer between the text/table body and the fancyhdr footer line.
GEOMETRY_OPTIONS = (
    "a4paper, "
    "left=22mm, right=22mm, "
    "top=20mm, bottom=25mm, "
    "headheight=15pt, headsep=8pt, "
    "footskip=12mm"
)

# -----------------------------------------------------------------------------
# Table Metrics & Spacing
# -----------------------------------------------------------------------------
TABCOLSEP         = "5pt"
ARRAYSTRETCH      = "1.15"
ARRAYRULEWIDTH    = "0.5pt"
EXTRAROWHEIGHT    = "0.6pt"
LTPRE             = "0pt"
LTPOST            = "6pt"

# Baseline skips before tables to trigger a clean page-break rather than orphan rows
NEEDSPACE_DEFAULT = r"\needspace{6\baselineskip}"
NEEDSPACE_TALL    = r"\needspace{10\baselineskip}"

# -----------------------------------------------------------------------------
# LongTable Repeated Header Generator
# -----------------------------------------------------------------------------
def make_longtable_header(
    col_spec: str,
    caption: str,
    header_row: str,
    num_cols: int,
    label: Optional[str] = None,
    cont_caption: Optional[str] = None
) -> str:
    """
    Construct a robust longtable opening with repeated headers across page breaks.

    Parameters:
        col_spec: LaTeX column specification (e.g. '|C{2.5cm}|L{8.0cm}|...|')
        caption: Title shown on the first page
        header_row: The column header text and formatting (ending without \\\\ or \\hline)
        num_cols: Number of columns for \\multicolumn spans
        label: Optional LaTeX label (e.g. 'tab:girder-props')
        cont_caption: Optional subtitle on continuation pages
    """
    lbl_tex = f"\\label{{{label}}}" if label else ""
    cont_text = cont_caption or f"{caption} (Continued)"

    return (
        f"\\begin{{longtable}}{{{col_spec}}}\n"
        f"\\caption{{\\textbf{{{caption}}}}}{lbl_tex}\\\\\n"
        f"\\hline\n"
        f"{header_row} \\\\[6pt]\n"
        f"\\hline\n"
        f"\\endfirsthead\n\n"
        f"\\caption*{{{cont_text}}}\\\\\n"
        f"\\hline\n"
        f"{header_row} \\\\[6pt]\n"
        f"\\hline\n"
        f"\\endhead\n\n"
        f"\\hline\n"
        f"\\multicolumn{{{num_cols}}}{{r}}{{\\footnotesize\\textit{{Continued on next page\\dots}}}} \\\\[2pt]\n"
        f"\\endfoot\n\n"
        f"\\hline\n"
        f"\\endlastfoot\n"
    )

# -----------------------------------------------------------------------------
# Table Note Attachment Helper
# -----------------------------------------------------------------------------
def make_table_note(text: str) -> str:
    """
    Bind a table footnote to its parent table preventing it from being
    orphaned onto the next page by LaTeX page break logic.
    """
    if not text:
        return ""
    return (
        "\\nopagebreak[4]\n"
        f"\\noindent\\textit{{{text}}}\n"
    )

# -----------------------------------------------------------------------------
# Matplotlib Chart Theme Preset
# -----------------------------------------------------------------------------
MPL_REPORT_THEME = {
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 9,
    "axes.labelsize": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "axes.edgecolor": "#9E9E9E",
    "axes.linewidth": 0.8,
    "grid.color": "#E0E0E0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
}
