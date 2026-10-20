"""
Report Generator – Superstore Data Warehouse
==============================================
Generates a professional, multi-sheet Excel workbook plus an HTML summary report.

Excel workbook sheets:
  0. Cover          – title, run timestamp, KPI tiles
  1. KPI Summary    – headline metrics table
  2. Annual Trend   – yearly sales & profit with bar chart
  3. Quarterly      – quarterly pivot with line chart
  4. Category       – category performance with chart
  5. Region         – regional breakdown with chart
  6. Customer Seg.  – segment analysis with chart
  7. Ship Mode      – shipping mode performance with chart
  8. Promotions     – promotion vs no-promotion analysis
  9. Discount       – discount band vs profit
  10. Top Products  – top 10 products
  11. Top Customers – top 10 customers
  12. Fiscal KPI    – fiscal quarter KPI table
  13. YoY Growth    – year-over-year growth
  14. Loyalty Tiers – customer loyalty buckets
  15. All Queries   – raw data for all 25 queries (one sub-section each)

HTML report:
  - KPI cards, embedded charts (ASCII art fallback), tables for all queries
  - Saved as  reports/superstore_report_<timestamp>.html

Usage:
  python -m scripts.generate_report
  or call generate_reports() from main.py
"""

import sys
import math
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.db import get_engine
from scripts.run_queries import load_queries

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ============================================================
#  Color palette
# ============================================================
DARK_BG    = "#1E2130"
ACCENT1    = "#4F8EF7"   # blue
ACCENT2    = "#F7874F"   # orange
ACCENT3    = "#4FC18C"   # green
ACCENT4    = "#F74F7A"   # red/pink
ACCENT5    = "#B04FF7"   # purple
WHITE      = "#FFFFFF"
LIGHT_GREY = "#F5F6FA"
MID_GREY   = "#C8CDD8"
DARK_GREY  = "#3A3F55"
TEXT_DARK  = "#1A1D2E"
TEXT_LIGHT = "#FFFFFF"

CATEGORY_COLORS = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
                   "#F7CC4F", "#4FF7F2", "#FF9F40"]


# ============================================================
#  Helper: fetch a single query result as DataFrame
# ============================================================
def _run_sql(engine, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), engine)


def _kpi(engine, sql: str):
    """Fetch a single scalar KPI value."""
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


# ============================================================
#  openpyxl helpers
# ============================================================
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.styles.numbers import FORMAT_NUMBER_COMMA_SEPARATED1


def _hex_fill(hex_color: str) -> PatternFill:
    """Return a solid PatternFill from a hex color string (with or without #)."""
    c = hex_color.lstrip("#")
    return PatternFill(fill_type="solid", fgColor=c)


def _font(bold=False, color="000000", size=10, italic=False) -> Font:
    c = color.lstrip("#")
    return Font(bold=bold, color=c, size=size, italic=italic,
                name="Calibri")


_thin_side = Side(style="thin", color="D9DDE5")
_border = Border(left=_thin_side, right=_thin_side, top=_thin_side, bottom=_thin_side)
_header_border = Border(
    left=_thin_side,
    right=_thin_side,
    top=_thin_side,
    bottom=Side(style="medium", color=DARK_BG.lstrip("#")),
)


def _align(h="left", v="center", wrap=False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _write_df_to_ws(ws, df: pd.DataFrame, title: str = "",
                    start_row: int = 1) -> int:
    """
    Write a DataFrame to an openpyxl worksheet.
    Returns the next empty row number after the data.
    """
    row = start_row

    # Title
    if title:
        ws.cell(row, 1, title)
        ws.cell(row, 1).font      = _font(bold=True, size=13, color=DARK_BG.lstrip("#"))
        ws.cell(row, 1).fill      = _hex_fill("FFFFFF")
        ws.cell(row, 1).alignment = _align()
        row += 2

    # Header row
    for ci, col in enumerate(df.columns, 1):
        c = ws.cell(row, ci, str(col).replace("_", " ").title())
        c.font      = _font(bold=True, color="FFFFFF", size=10)
        c.fill      = _hex_fill(DARK_BG)
        c.alignment = _align(h="center")
        c.border    = _header_border
    row += 1

    # Data rows
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

    # Auto-fit columns
    for ci, col in enumerate(df.columns, 1):
        col_series = df.iloc[:, ci-1]
        max_data_len = 0
        if len(col_series) > 0:
            str_lens = col_series.dropna().astype(str).str.len()
            if not str_lens.empty:
                max_data_len = int(str_lens.max())
        max_len = max(len(str(col)), max_data_len)
        ws.column_dimensions[get_column_letter(ci)].width = max(min(max_len + 4, 45), 12)

    return row


# ============================================================
#  Generate Excel report  (openpyxl-based, no xlsxwriter)
# ============================================================
def _generate_excel(engine, ts_str: str, kpis: dict, all_dfs: dict) -> Path:
    path = REPORTS_DIR / f"superstore_report_{ts_str}.xlsx"

    wb = Workbook()
    wb.remove(wb.active)

    # ── helper: create + style a sheet ──────────────────────────────────
    def _make_sheet(name: str) -> object:
        ws = wb.create_sheet(title=name)
        ws.sheet_view.showGridLines = True
        ws.freeze_panes = "A4"
        return ws

    # ────────────────────────────────────────────────────────────────────
    # Cover sheet
    # ────────────────────────────────────────────────────────────────────
    ws_cover = wb.create_sheet(title="Cover")
    ws_cover.sheet_view.showGridLines = False
    ws_cover.sheet_view.zoomScale = 90

    # Background fill entire block
    for r in range(1, 30):
        for c_ in range(1, 8):
            ws_cover.cell(r, c_).fill = _hex_fill(DARK_BG)

    # Title
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

    # KPI tiles – row 8–10 and 12–14
    tile_data = [
        ("B", "Total Revenue ($)",   f"${kpis.get('total_revenue', 0):,.2f}", ACCENT3),
        ("C", "Total Profit ($)",    f"${kpis.get('total_profit', 0):,.2f}",  ACCENT1),
        ("D", "Total Orders",        f"{kpis.get('total_orders', 0):,}",       ACCENT2),
        ("E", "Unique Customers",    f"{kpis.get('total_customers', 0):,}",    ACCENT4),
        ("F", "Products",            f"{kpis.get('total_products', 0):,}",     ACCENT5),
    ]
    tile_data2 = [
        ("B", "Profit Margin (%)",   f"{kpis.get('avg_margin', 0):,.2f}%",    ACCENT1),
        ("C", "Avg Ship Lag",        f"{kpis.get('avg_ship_lag', 0):,.1f} d", ACCENT2),
        ("D", "Promo Orders",        f"{kpis.get('promo_orders', 0):,}",       ACCENT3),
        ("E", "Holiday Days",        f"{kpis.get('holiday_days', 0):,}",       ACCENT4),
    ]
    for col_letter, label, val, color in tile_data:
        ws_cover.merge_cells(f"{col_letter}8:{col_letter}9")
        lc = ws_cover[f"{col_letter}8"]
        lc.value = label; lc.font = _font(size=9, color=MID_GREY.lstrip("#"), bold=True)
        lc.fill = _hex_fill(DARK_GREY); lc.alignment = _align(h="center")
        ws_cover.merge_cells(f"{col_letter}10:{col_letter}11")
        vc = ws_cover[f"{col_letter}10"]
        vc.value = val; vc.font = _font(size=16, color=color.lstrip("#"), bold=True)
        vc.fill = _hex_fill(DARK_GREY); vc.alignment = _align(h="center")

    for col_letter, label, val, color in tile_data2:
        ws_cover.merge_cells(f"{col_letter}13:{col_letter}14")
        lc = ws_cover[f"{col_letter}13"]
        lc.value = label; lc.font = _font(size=9, color=MID_GREY.lstrip("#"), bold=True)
        lc.fill = _hex_fill(DARK_GREY); lc.alignment = _align(h="center")
        ws_cover.merge_cells(f"{col_letter}15:{col_letter}16")
        vc = ws_cover[f"{col_letter}15"]
        vc.value = val; vc.font = _font(size=16, color=color.lstrip("#"), bold=True)
        vc.fill = _hex_fill(DARK_GREY); vc.alignment = _align(h="center")

    for col_letter in "ABCDEFG":
        ws_cover.column_dimensions[col_letter].width = 22
    ws_cover.row_dimensions[2].height = 36

    # ────────────────────────────────────────────────────────────────────
    # KPI Summary sheet
    # ────────────────────────────────────────────────────────────────────
    ws_kpi = _make_sheet("KPI Summary")
    kpi_df = pd.DataFrame([
        {"Metric": "Total Revenue ($)",    "Value": kpis.get("total_revenue", 0)},
        {"Metric": "Total Profit ($)",     "Value": kpis.get("total_profit",  0)},
        {"Metric": "Profit Margin (%)",    "Value": kpis.get("avg_margin",    0)},
        {"Metric": "Total Orders",         "Value": kpis.get("total_orders",  0)},
        {"Metric": "Unique Customers",     "Value": kpis.get("total_customers", 0)},
        {"Metric": "Unique Products",      "Value": kpis.get("total_products",  0)},
        {"Metric": "Avg Ship Lag (days)",  "Value": kpis.get("avg_ship_lag",  0)},
        {"Metric": "Promotion Orders",     "Value": kpis.get("promo_orders",  0)},
        {"Metric": "Holiday Sales Days",   "Value": kpis.get("holiday_days",  0)},
    ])
    _write_df_to_ws(ws_kpi, kpi_df, "Key Performance Indicators")

    # ────────────────────────────────────────────────────────────────────
    # helper: add bar chart to a sheet
    # ────────────────────────────────────────────────────────────────────
    def _add_bar(ws, df, cat_col_idx, val_col_idxs, data_start_row,
                 title, anchor, colors=None):
        chart = BarChart()
        chart.type        = "col"
        chart.grouping    = "clustered"
        chart.title       = title
        chart.style       = 10
        chart.width       = 20
        chart.height      = 12
        chart.gapWidth    = 60
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

    def _add_line(ws, df, cat_col_idx, val_col_idxs, data_start_row,
                  title, anchor, colors=None):
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

    def _add_pie(ws, df, cat_col_idx, val_col_idx, data_start_row,
                 title, anchor):
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
    # Individual analysis sheets
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
        data_start = 3     # row 1 = title, row 2 = blank, row 3 = headers, row 4+ = data
        data_row   = data_start + 1   # first actual data row (1-indexed)
        anchor_row = next_row + 2

        if chart_type == "bar" and val_cols:
            _add_bar(ws, df, 1, val_cols, data_row, title,
                     f"A{anchor_row}")
        elif chart_type == "line" and val_cols:
            _add_line(ws, df, 1, val_cols, data_row, title,
                      f"A{anchor_row}")
        elif chart_type == "pie" and val_cols:
            _add_pie(ws, df, 1, val_cols[0], data_row, title,
                     f"A{anchor_row}")

    # ────────────────────────────────────────────────────────────────────
    # All Queries raw dump
    # ────────────────────────────────────────────────────────────────────
    ws_all = _make_sheet("All Queries")
    ws_all.freeze_panes = None
    row_ptr = 1
    for qid, qtitle, _ in load_queries():
        df = all_dfs.get(qid)
        if df is None or df.empty:
            continue
        # Section header
        max_col = max(len(df.columns), 1)
        ws_all.merge_cells(start_row=row_ptr, start_column=1,
                           end_row=row_ptr,   end_column=max_col)
        hc = ws_all.cell(row_ptr, 1, f"[{qid}]  {qtitle}")
        hc.font      = _font(bold=True, size=11, color="FFFFFF")
        hc.fill      = _hex_fill(DARK_BG)
        hc.alignment = _align(h="left")
        row_ptr += 1
        row_ptr = _write_df_to_ws(ws_all, df, start_row=row_ptr)
        row_ptr += 2   # gap

    # ────────────────────────────────────────────────────────────────────
    # Save
    # ────────────────────────────────────────────────────────────────────
    wb.save(str(path))
    return path

# ============================================================
#  Generate HTML report
# ============================================================
def _generate_html(kpis: dict, all_dfs: dict, ts_str: str) -> Path:
    path = REPORTS_DIR / f"superstore_report_{ts_str}.html"

    def _df_to_html(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "<p class='no-data'>No data available.</p>"
        rows = ""
        for i, (_, row) in enumerate(df.iterrows()):
            cls = "odd" if i % 2 == 0 else "even"
            cells = "".join(
                f"<td>{'${:,.2f}'.format(v) if isinstance(v, float) else v}</td>"
                for v in row
            )
            rows += f"<tr class='{cls}'>{cells}</tr>"
        headers = "".join(
            f"<th>{c.replace('_',' ').title()}</th>" for c in df.columns
        )
        return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"

    def _kpi_card(label: str, value, color: str, prefix: str = "", suffix: str = "") -> str:
        if isinstance(value, float):
            disp = f"{prefix}{value:,.2f}{suffix}"
        else:
            disp = f"{prefix}{value:,}{suffix}"
        return f"""
        <div class="kpi-card" style="border-top: 4px solid {color}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="color:{color}">{disp}</div>
        </div>"""

    kpi_cards = (
        _kpi_card("Total Revenue", kpis.get("total_revenue", 0), ACCENT1, "$")
        + _kpi_card("Total Profit",   kpis.get("total_profit",  0), ACCENT3, "$")
        + _kpi_card("Profit Margin",  kpis.get("avg_margin",    0), ACCENT5, "", "%")
        + _kpi_card("Total Orders",   kpis.get("total_orders",  0), ACCENT2)
        + _kpi_card("Customers",      kpis.get("total_customers", 0), ACCENT4)
        + _kpi_card("Products",       kpis.get("total_products", 0), "#F7CC4F")
        + _kpi_card("Avg Ship Lag",   kpis.get("avg_ship_lag",  0), "#4FF7F2", "", " days")
        + _kpi_card("Promo Orders",   kpis.get("promo_orders",  0), ACCENT1)
    )

    # Build query sections
    query_sections = ""
    for qid, title, _ in load_queries():
        df = all_dfs.get(qid)
        query_sections += f"""
        <div class="query-section">
          <h3 class="query-title"><span class="qbadge">{qid}</span> {title}</h3>
          {_df_to_html(df)}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Superstore DW Report – {ts_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: #F0F2F8;
    color: {TEXT_DARK};
    font-size: 14px;
    line-height: 1.6;
  }}
  .page-header {{
    background: linear-gradient(135deg, {DARK_BG} 0%, {DARK_GREY} 100%);
    color: white;
    padding: 40px 48px 30px;
    position: relative;
  }}
  .page-header h1 {{
    font-size: 32px;
    font-weight: 700;
    color: {ACCENT1};
    letter-spacing: -0.5px;
  }}
  .page-header .subtitle {{
    color: {MID_GREY};
    margin-top: 6px;
    font-size: 14px;
  }}
  .main-content {{ max-width: 1400px; margin: 0 auto; padding: 32px 24px; }}
  /* KPI cards */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }}
  .kpi-card {{
    background: white;
    border-radius: 12px;
    padding: 20px 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,.06);
    transition: transform .2s;
  }}
  .kpi-card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.10); }}
  .kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .8px; color: #888; margin-bottom: 8px; }}
  .kpi-value {{ font-size: 26px; font-weight: 700; }}
  /* Section headings */
  .section-title {{
    font-size: 20px;
    font-weight: 700;
    color: {DARK_BG};
    margin: 40px 0 16px;
    padding-bottom: 10px;
    border-bottom: 3px solid {ACCENT1};
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  /* Query sections */
  .query-section {{
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
  }}
  .query-title {{
    font-size: 14px;
    font-weight: 600;
    color: {DARK_BG};
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .qbadge {{
    background: {ACCENT1};
    color: white;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .5px;
  }}
  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead tr {{ background: {DARK_BG}; color: white; }}
  thead th {{
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .6px;
    white-space: nowrap;
  }}
  tbody tr.odd  {{ background: {LIGHT_GREY}; }}
  tbody tr.even {{ background: white; }}
  tbody td {{
    padding: 9px 14px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
  }}
  tbody tr:hover {{ background: #EBF2FF; }}
  .no-data {{ color: #aaa; font-style: italic; padding: 16px; }}
  .footer {{
    text-align: center;
    padding: 32px;
    color: #aaa;
    font-size: 12px;
  }}
  /* scrollable tables */
  .query-section {{ overflow-x: auto; }}
</style>
</head>
<body>
<div class="page-header">
  <h1>SUPERSTORE DATA WAREHOUSE</h1>
  <div class="subtitle">Business Intelligence Report &nbsp;|&nbsp; Generated: {ts_str.replace('_', ' ')}</div>
</div>
<div class="main-content">
  <h2 class="section-title">&#128200; Key Performance Indicators</h2>
  <div class="kpi-grid">{kpi_cards}</div>

  <h2 class="section-title">&#128203; Analytics Query Results</h2>
  {query_sections}
</div>
<div class="footer">
  Superstore Data Warehouse Manager &nbsp;&bull;&nbsp; Supabase + PostgreSQL &nbsp;&bull;&nbsp; {ts_str}
</div>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    return path


# ============================================================
#  Public entry-point
# ============================================================
def generate_reports(selected_formats: set[str] | None = None) -> dict[str, Path]:
    """
    Runs all 25 queries, computes KPIs, and generates reports.

    Parameters
    ----------
    selected_formats : set of 'excel' and/or 'html'. None = both.

    Returns a dict mapping format name -> output file path.
    """
    if selected_formats is None:
        selected_formats = {"excel", "html"}

    engine  = get_engine()
    queries = load_queries()

    # ---- Fetch all query DataFrames ----
    print("\n[REPORT] Running all queries for report generation...")
    all_dfs: dict[str, pd.DataFrame] = {}
    for qid, title, sql in queries:
        try:
            all_dfs[qid] = pd.read_sql(text(sql), engine)
            print(f"  -> {qid}: {len(all_dfs[qid])} rows")
        except Exception as e:
            print(f"  [WARN] {qid} failed: {e}")
            all_dfs[qid] = pd.DataFrame()

    total_rows = sum(len(df) for df in all_dfs.values())
    if total_rows == 0:
        print("  [NOTE] Warehouse tables have no rows or have not been created/built yet.")
        print("         To populate the warehouse, run Menu options 2, 3, 4, then 5.")

    # ---- KPI scalars ----
    print("[REPORT] Computing headline KPIs...")
    with engine.connect() as conn:
        def qs(sql):
            try:
                return conn.execute(text(sql)).scalar() or 0
            except Exception:
                return 0

        kpis = {
            "total_revenue":   qs("SELECT ROUND(SUM(sales_amount),2) FROM dw.fact_sales;"),
            "total_profit":    qs("SELECT ROUND(SUM(profit),2) FROM dw.fact_sales;"),
            "avg_margin":      qs("""
                SELECT ROUND(SUM(profit)/NULLIF(SUM(sales_amount),0)*100, 2)
                FROM dw.fact_sales;"""),
            "total_orders":    qs("SELECT COUNT(DISTINCT order_id) FROM dw.fact_sales;"),
            "total_customers": qs("SELECT COUNT(*) FROM dw.dim_customer WHERE is_current;"),
            "total_products":  qs("SELECT COUNT(*) FROM dw.dim_product;"),
            "avg_ship_lag":    qs("SELECT ROUND(AVG(ship_lag_days),2) FROM dw.fact_sales;"),
            "promo_orders":    qs("""
                SELECT COUNT(*) FROM dw.fact_sales f
                JOIN dw.dim_promo p USING (promo_key)
                WHERE p.promo_id <> 0;"""),
            "holiday_days":    qs("SELECT COUNT(*) FROM dw.dim_date WHERE is_holiday;"),
        }

    ts_str   = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputs: dict[str, Path] = {}

    if "excel" in selected_formats:
        print("[REPORT] Building Excel workbook...")
        try:
            xls_path = _generate_excel(engine, ts_str, kpis, all_dfs)
            outputs["excel"] = xls_path
            print(f"  [OK] Excel: {xls_path.name}")
        except Exception as e:
            print(f"  [ERROR] Excel generation failed: {e}")

    if "html" in selected_formats:
        print("[REPORT] Building HTML report...")
        try:
            html_path = _generate_html(kpis, all_dfs, ts_str)
            outputs["html"] = html_path
            print(f"  [OK] HTML:  {html_path.name}")
        except Exception as e:
            print(f"  [ERROR] HTML generation failed: {e}")

    return outputs


if __name__ == "__main__":
    paths = generate_reports()
    for fmt, p in paths.items():
        print(f"[{fmt.upper()}] Saved -> {p}")
