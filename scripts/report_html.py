"""
HTML Report Template & Generator – Superstore Data Warehouse
============================================================
Builds an executive-grade, standalone HTML business intelligence report.
Features:
  - Gradient header banner with run timestamp
  - Interactive KPI summary cards
  - Clean data tables with alternating row styles
  - Responsive layout for browser viewing
"""

from pathlib import Path
import pandas as pd

# Color Palette
DARK_BG    = "#1E2130"
ACCENT1    = "#4F8EF7"   # Blue
ACCENT2    = "#F7874F"   # Orange
ACCENT3    = "#4FC18C"   # Green
ACCENT4    = "#F74F7A"   # Red/Pink
ACCENT5    = "#B04FF7"   # Purple
LIGHT_GREY = "#F5F6FA"
MID_GREY   = "#C8CDD8"
DARK_GREY  = "#3A3F55"
TEXT_DARK  = "#1A1D2E"


def _df_to_html(df: pd.DataFrame) -> str:
    """Converts a pandas DataFrame to a styled HTML table."""
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
    headers = "".join(f"<th>{c.replace('_',' ').title()}</th>" for c in df.columns)
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"


def _kpi_card(label: str, value, color: str, prefix: str = "", suffix: str = "") -> str:
    """Generates an HTML KPI metric card."""
    if isinstance(value, float):
        disp = f"{prefix}{value:,.2f}{suffix}"
    else:
        disp = f"{prefix}{value:,}{suffix}"
    return f"""
    <div class="kpi-card" style="border-top: 4px solid {color}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{disp}</div>
    </div>"""


def generate_html_report(path: Path, kpis: dict, all_dfs: dict, ts_str: str, queries_catalog: list = None) -> Path:
    """
    Builds and writes a styled standalone HTML report.
    """
    kpi_cards = (
        _kpi_card("Total Revenue",  kpis.get("total_revenue", 0), ACCENT1, "$")
        + _kpi_card("Total Profit", kpis.get("total_profit", 0),  ACCENT3, "$")
        + _kpi_card("Profit Margin",kpis.get("avg_margin", 0),    ACCENT5, "", "%")
        + _kpi_card("Total Orders", kpis.get("total_orders", 0),  ACCENT2)
        + _kpi_card("Customers",    kpis.get("total_customers", 0), ACCENT4)
        + _kpi_card("Products",     kpis.get("total_products", 0), "#F7CC4F")
        + _kpi_card("Avg Ship Lag", kpis.get("avg_ship_lag", 0),  "#4FF7F2", "", " days")
        + _kpi_card("Promo Orders", kpis.get("promo_orders", 0),  ACCENT1)
    )

    catalog = queries_catalog or []
    query_sections = ""
    for qid, title, _ in catalog:
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
    overflow-x: auto;
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
