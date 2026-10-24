"""
Excel Report Template & Generator – Superstore Data Warehouse
============================================================
Builds an executive-grade, multi-sheet Excel workbook using openpyxl.

Workbook structure:
  0. Cover          – Title banner, generation timestamp, stylized KPI tiles
  1. KPI Summary    – Headline metrics table
  2. Query Results  – Quick access to the full query output by business question
  3. Annual Trend   – Yearly sales, profit & margin with bar chart
  4. Quarterly Trend– Quarterly pivot with line chart
  5. Category       – Category performance with bar chart
  6. Region         – Regional breakdown with bar chart
  7. Customer Seg   – Segment analysis with pie chart
  8. Ship Mode      – Shipping mode performance with bar chart
  9. Promotions     – Promotional vs non-promotional analysis
  10. Discount      – Discount band vs profit with bar chart
  11. Top Products  – Top 10 revenue products
  12. Top Customers – Top 10 revenue customers
  13. Fiscal KPI    – Fiscal quarter KPIs with line chart
  14. YoY Growth    – Year-over-year revenue growth %
  15. Loyalty Tiers – Customer loyalty tiers with bar chart
  16. Sub-Category  – Sub-category profitability ranking
  17. Loss Products – Loss-making catalog products
  18. Top Orders    – Top 10 high-value order transactions
  19. All Queries   – Complete raw data dump for all 25 queries
"""

import math
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ============================================================
#  Color Palette
# ============================================================
DARK_BG    = "#1E2130"
ACCENT1    = "#4F8EF7"   # Blue
ACCENT2    = "#F7874F"   # Orange
ACCENT3    = "#4FC18C"   # Green
ACCENT4    = "#F74F7A"   # Red/Pink
ACCENT5    = "#B04FF7"   # Purple
WHITE      = "#FFFFFF"
LIGHT_GREY = "#F5F6FA"
MID_GREY   = "#C8CDD8"
DARK_GREY  = "#3A3F55"
TEXT_DARK  = "#1A1D2E"

_thin_side = Side(style="thin", color="D9DDE5")
_border = Border(left=_thin_side, right=_thin_side, top=_thin_side, bottom=_thin_side)
_header_border = Border(
    left=_thin_side,
    right=_thin_side,
    top=_thin_side,
    bottom=Side(style="medium", color=DARK_BG.lstrip("#")),
)


def _hex_fill(hex_color: str) -> PatternFill:
    """Return a solid PatternFill from a hex string."""
    return PatternFill(fill_type="solid", fgColor=hex_color.lstrip("#"))


def _font(bold: bool = False, color: str = "000000", size: int = 10, italic: bool = False) -> Font:
    return Font(bold=bold, color=color.lstrip("#"), size=size, italic=italic, name="Calibri")


def _align(h: str = "left", v: str = "center", wrap: bool = False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _write_df_to_ws(ws, df: pd.DataFrame, title: str = "", start_row: int = 1) -> int:
    """Writes a DataFrame to an openpyxl worksheet and formats cells."""
    row = start_row

    # Section Title
    if title:
        ws.cell(row, 1, title)
        ws.cell(row, 1).font      = _font(bold=True, size=13, color=DARK_BG.lstrip("#"))
        ws.cell(row, 1).fill      = _hex_fill("FFFFFF")
        ws.cell(row, 1).alignment = _align()
        row += 2

    # Header Row
    for ci, col in enumerate(df.columns, 1):
        c = ws.cell(row, ci, str(col).replace("_", " ").title())
        c.font      = _font(bold=True, color="FFFFFF", size=10)
        c.fill      = _hex_fill(DARK_BG)
        c.alignment = _align(h="center")
        c.border    = _header_border
    row += 1

    # Data Rows
    num_fmt = '#,##0.00'
    for i, (_, data_row) in enumerate(df.iterrows()):
        bg = LIGHT_GREY if i % 2 == 0 else WHITE
        for ci, val in enumerate(data_row, 1):
            c = ws.cell(row, ci)
            c.fill      = _hex_fill(bg)
            c.alignment = _align()
            c.font      = _font(size=9, color=TEXT_DARK.lstrip("#"))
            c.border    = _border

            if val is None or (isinstance(val, float) and math.isnan(val)):
                c.value = ""
            elif isinstance(val, (float, Decimal)):
                c.value = float(val)
                c.number_format = num_fmt
            elif isinstance(val, (int, np.integer)):
                c.value = int(val)
                c.number_format = '#,##0'
            elif hasattr(val, 'item'):
                v_item = val.item()
                if isinstance(v_item, float):
                    c.value = float(v_item)
                    c.number_format = num_fmt
                elif isinstance(v_item, (int, np.integer)):
                    c.value = int(v_item)
                    c.number_format = '#,##0'
                else:
                    c.value = v_item
            else:
                c.value = val
        row += 1

    # Auto-fit Column Widths
    for ci, col in enumerate(df.columns, 1):
        col_series = df.iloc[:, ci - 1]
        max_data_len = 0
        if len(col_series) > 0:
            str_lens = col_series.dropna().astype(str).str.len()
            if not str_lens.empty:
                max_data_len = int(str_lens.max())
        max_len = max(len(str(col)), max_data_len)
        ws.column_dimensions[get_column_letter(ci)].width = max(min(max_len + 4, 45), 12)

    return row


def generate_excel_report(path: Path, kpis: dict, all_dfs: dict, ts_str: str, queries_catalog: list = None) -> Path:
    """
    Builds and saves the complete Superstore BI Excel workbook.
    """
    wb = Workbook()
    wb.remove(wb.active)

    def _make_sheet(name: str):
        ws = wb.create_sheet(title=name)
        ws.sheet_view.showGridLines = True
        ws.freeze_panes = "A4"
        return ws

    # ────────────────────────────────────────────────────────────────────
    # 0. Cover Sheet
    # ────────────────────────────────────────────────────────────────────
    ws_cover = wb.create_sheet(title="Cover")
    ws_cover.sheet_view.showGridLines = False
    ws_cover.sheet_view.zoomScale = 90

    for r in range(1, 30):
        for c_ in range(1, 8):
            ws_cover.cell(r, c_).fill = _hex_fill(DARK_BG)

    # Title & Subtitle
    ws_cover.merge_cells("B2:F4")
    t = ws_cover["B2"]
    t.value     = "SUPERSTORE DATA WAREHOUSE"
    t.font      = _font(bold=True, size=26, color=ACCENT1.lstrip("#"))
    t.alignment = _align(h="center", v="center")

    ws_cover.merge_cells("B5:F5")
    s = ws_cover["B5"]
    s.value     = "Business Intelligence Report"
    s.font      = _font(size=13, color=MID_GREY.lstrip("#"))
    s.alignment = _align(h="center")

    ws_cover.merge_cells("B6:F6")
    dt = ws_cover["B6"]
    dt.value     = f"Generated: {ts_str.replace('_', ' ')}"
    dt.font      = _font(size=10, color=MID_GREY.lstrip("#"), italic=True)
    dt.alignment = _align(h="center")

    # KPI Tiles Row 1
    tile_data1 = [
        ("B", "Total Revenue ($)", f"${kpis.get('total_revenue', 0):,.2f}", ACCENT3),
        ("C", "Total Profit ($)",  f"${kpis.get('total_profit', 0):,.2f}",  ACCENT1),
        ("D", "Total Orders",      f"{kpis.get('total_orders', 0):,}",       ACCENT2),
        ("E", "Unique Customers",  f"{kpis.get('total_customers', 0):,}",    ACCENT4),
        ("F", "Products",          f"{kpis.get('total_products', 0):,}",     ACCENT5),
    ]
    for col_letter, label, val, color in tile_data1:
        ws_cover.merge_cells(f"{col_letter}8:{col_letter}9")
        lc = ws_cover[f"{col_letter}8"]
        lc.value = label
        lc.font  = _font(size=9, color=MID_GREY.lstrip("#"), bold=True)
        lc.fill  = _hex_fill(DARK_GREY)
        lc.alignment = _align(h="center")

        ws_cover.merge_cells(f"{col_letter}10:{col_letter}11")
        vc = ws_cover[f"{col_letter}10"]
        vc.value = val
        vc.font  = _font(size=16, color=color.lstrip("#"), bold=True)
        vc.fill  = _hex_fill(DARK_GREY)
        vc.alignment = _align(h="center")

    # KPI Tiles Row 2
    tile_data2 = [
        ("B", "Profit Margin (%)", f"{kpis.get('avg_margin', 0):,.2f}%",    ACCENT1),
        ("C", "Avg Ship Lag",      f"{kpis.get('avg_ship_lag', 0):,.1f} d", ACCENT2),
        ("D", "Promo Orders",      f"{kpis.get('promo_orders', 0):,}",       ACCENT3),
        ("E", "Holiday Days",      f"{kpis.get('holiday_days', 0):,}",       ACCENT4),
    ]
    for col_letter, label, val, color in tile_data2:
        ws_cover.merge_cells(f"{col_letter}13:{col_letter}14")
        lc = ws_cover[f"{col_letter}13"]
        lc.value = label
        lc.font  = _font(size=9, color=MID_GREY.lstrip("#"), bold=True)
        lc.fill  = _hex_fill(DARK_GREY)
        lc.alignment = _align(h="center")

        ws_cover.merge_cells(f"{col_letter}15:{col_letter}16")
        vc = ws_cover[f"{col_letter}15"]
        vc.value = val
        vc.font  = _font(size=16, color=color.lstrip("#"), bold=True)
        vc.fill  = _hex_fill(DARK_GREY)
        vc.alignment = _align(h="center")

    for col_letter in "ABCDEFG":
        ws_cover.column_dimensions[col_letter].width = 22
    ws_cover.row_dimensions[2].height = 36

    # ────────────────────────────────────────────────────────────────────
    # 1. KPI Summary Sheet
    # ────────────────────────────────────────────────────────────────────
    ws_kpi = _make_sheet("KPI Summary")
    kpi_df = pd.DataFrame([
        {"Metric": "Total Revenue ($)",    "Value": kpis.get("total_revenue", 0)},
        {"Metric": "Total Profit ($)",     "Value": kpis.get("total_profit", 0)},
        {"Metric": "Profit Margin (%)",    "Value": kpis.get("avg_margin", 0)},
        {"Metric": "Total Orders",         "Value": kpis.get("total_orders", 0)},
        {"Metric": "Unique Customers",     "Value": kpis.get("total_customers", 0)},
        {"Metric": "Unique Products",      "Value": kpis.get("total_products", 0)},
        {"Metric": "Avg Ship Lag (days)",  "Value": kpis.get("avg_ship_lag", 0)},
        {"Metric": "Promotion Orders",     "Value": kpis.get("promo_orders", 0)},
        {"Metric": "Holiday Sales Days",   "Value": kpis.get("holiday_days", 0)},
    ])
    _write_df_to_ws(ws_kpi, kpi_df, "Key Performance Indicators")

    # ────────────────────────────────────────────────────────────────────
    # 2. Query Results Sheet
    # ────────────────────────────────────────────────────────────────────
    ws_query = _make_sheet("Query Results")
    ws_query.freeze_panes = "A3"
    ws_query.merge_cells("A1:F1")
    title = ws_query["A1"]
    title.value = "Query Results"
    title.font = _font(bold=True, size=16, color="FFFFFF")
    title.fill = _hex_fill(DARK_BG)
    title.alignment = _align(h="center")

    catalog = queries_catalog or []
    row_ptr = 3
    for qid, qtitle, _ in catalog:
        df = all_dfs.get(qid)
        if df is None or df.empty:
            continue
        max_col = max(len(df.columns), 1)
        ws_query.merge_cells(start_row=row_ptr, start_column=1, end_row=row_ptr, end_column=max_col)
        header_cell = ws_query.cell(row_ptr, 1, f"[{qid}]  {qtitle}")
        header_cell.font = _font(bold=True, size=11, color="FFFFFF")
        header_cell.fill = _hex_fill(DARK_BG)
        header_cell.alignment = _align(h="left")
        row_ptr += 1
        row_ptr = _write_df_to_ws(ws_query, df, start_row=row_ptr)
        row_ptr += 2

    # ────────────────────────────────────────────────────────────────────
    # Chart Helper Functions
    # ────────────────────────────────────────────────────────────────────
    def _add_bar(ws, df, cat_col_idx, val_col_idxs, data_start_row, title, anchor, colors=None):
        chart = BarChart()
        chart.type     = "col"
        chart.grouping = "clustered"
        chart.title    = title
        chart.style    = 10
        chart.width    = 20
        chart.height   = 12
        chart.gapWidth = 60
        cats = Reference(ws, min_col=cat_col_idx, max_col=cat_col_idx,
                         min_row=data_start_row, max_row=data_start_row + len(df) - 1)
        palette = [ACCENT1, ACCENT3, ACCENT2, ACCENT4, ACCENT5]
        for i, vi in enumerate(val_col_idxs):
            data = Reference(ws, min_col=vi, max_col=vi,
                             min_row=data_start_row - 1,
                             max_row=data_start_row + len(df) - 1)
            chart.add_data(data, titles_from_data=True)
            s = chart.series[i]
            clr = (colors or palette)[i % len(palette)].lstrip("#")
            s.graphicalProperties.solidFill = clr
        chart.set_categories(cats)
        ws.add_chart(chart, anchor)

    def _add_line(ws, df, cat_col_idx, val_col_idxs, data_start_row, title, anchor, colors=None):
        chart = LineChart()
        chart.title  = title
        chart.style  = 10
        chart.width  = 20
        chart.height = 12
        cats = Reference(ws, min_col=cat_col_idx, max_col=cat_col_idx,
                         min_row=data_start_row, max_row=data_start_row + len(df) - 1)
        palette = [ACCENT1, ACCENT2, ACCENT3, ACCENT4]
        for i, vi in enumerate(val_col_idxs):
            data = Reference(ws, min_col=vi, max_col=vi,
                             min_row=data_start_row - 1,
                             max_row=data_start_row + len(df) - 1)
            chart.add_data(data, titles_from_data=True)
            s = chart.series[i]
            clr = (colors or palette)[i % len(palette)].lstrip("#")
            s.graphicalProperties.line.solidFill = clr
            s.graphicalProperties.line.width = 25000
            s.marker.symbol = "circle"
            s.marker.size   = 5
            s.marker.graphicalProperties.solidFill = clr
            s.marker.graphicalProperties.line.solidFill = clr
        chart.set_categories(cats)
        ws.add_chart(chart, anchor)

    def _add_pie(ws, df, cat_col_idx, val_col_idx, data_start_row, title, anchor):
        chart = PieChart()
        chart.title  = title
        chart.style  = 10
        chart.width  = 18
        chart.height = 14
        cats = Reference(ws, min_col=cat_col_idx, max_col=cat_col_idx,
                         min_row=data_start_row, max_row=data_start_row + len(df) - 1)
        data = Reference(ws, min_col=val_col_idx, max_col=val_col_idx,
                         min_row=data_start_row - 1,
                         max_row=data_start_row + len(df) - 1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        ws.add_chart(chart, anchor)

    # ────────────────────────────────────────────────────────────────────
    # Individual Analysis Sheets & Embedded Charts
    # ────────────────────────────────────────────────────────────────────
    sheet_specs = [
        ("Annual Trend",    "Q1",  "Annual Sales & Profit",        "bar",  [2, 3]),
        ("Quarterly Trend", "Q3",  "Quarterly Sales Pivot",         "line", [2, 3, 4, 5]),
        ("Category",        "Q6",  "Category Performance",          "bar",  [2, 3]),
        ("Region",          "Q9",  "Regional Performance",          "bar",  [2, 3]),
        ("Customer Seg",    "Q7",  "Customer Segment Analysis",     "pie",  [3]),
        ("Ship Mode",       "Q21", "Shipping Mode Performance",     "bar",  [5, 6]),
        ("Promotions",      "Q14", "Promotion Impact Analysis",     None,   []),
        ("Discount",        "Q16", "Discount Band vs Profit",       "bar",  [3, 4]),
        ("Top Products",    "Q4",  "Top 10 Products by Sales",      None,   []),
        ("Top Customers",   "Q8",  "Top 10 Customers by Sales",     None,   []),
        ("Fiscal KPI",      "Q24", "Fiscal Quarter KPIs",           "line", [4, 5]),
        ("YoY Growth",      "Q19", "Year-over-Year Sales Growth",   None,   []),
        ("Loyalty Tiers",   "Q23", "Customer Loyalty Tiers",        "bar",  [2]),
        ("Sub-Category",    "Q22", "Sub-Category Profitability",    None,   []),
        ("Loss Products",   "Q18", "Loss-Making Products",          None,   []),
        ("Top Orders",      "Q25", "Top 10 High-Value Orders",      None,   []),
    ]

    for sheet_name, qid, title, chart_type, val_cols in sheet_specs:
        df = all_dfs.get(qid, pd.DataFrame())
        if df.empty:
            continue
        ws = _make_sheet(sheet_name)
        next_row = _write_df_to_ws(ws, df, title, start_row=1)
        data_start = 3
        data_row   = data_start + 1
        anchor_row = next_row + 2

        if chart_type == "bar" and val_cols:
            _add_bar(ws, df, 1, val_cols, data_row, title, f"A{anchor_row}")
        elif chart_type == "line" and val_cols:
            _add_line(ws, df, 1, val_cols, data_row, title, f"A{anchor_row}")
        elif chart_type == "pie" and val_cols:
            _add_pie(ws, df, 1, val_cols[0], data_row, title, f"A{anchor_row}")

    # ────────────────────────────────────────────────────────────────────
    # All Queries Raw Data Sheet
    # ────────────────────────────────────────────────────────────────────
    ws_all = _make_sheet("All Queries")
    ws_all.freeze_panes = None
    row_ptr = 1

    catalog = queries_catalog or []
    for qid, qtitle, _ in catalog:
        df = all_dfs.get(qid)
        if df is None or df.empty:
            continue
        max_col = max(len(df.columns), 1)
        ws_all.merge_cells(start_row=row_ptr, start_column=1, end_row=row_ptr, end_column=max_col)
        hc = ws_all.cell(row_ptr, 1, f"[{qid}]  {qtitle}")
        hc.font      = _font(bold=True, size=11, color="FFFFFF")
        hc.fill      = _hex_fill(DARK_BG)
        hc.alignment = _align(h="left")
        row_ptr += 1
        row_ptr = _write_df_to_ws(ws_all, df, start_row=row_ptr)
        row_ptr += 2

    # Save
    wb.save(str(path))
    return path
