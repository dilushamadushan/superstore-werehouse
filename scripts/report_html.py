"""
HTML Report Template & Generator - Superstore Data Warehouse
============================================================
Clean light-theme BI Dashboard using Plotly + Jinja2.
Features:
  - Plotly interactive charts (hover, zoom, pan) for 22 queries
  - Jinja2 HTML templating (clean, maintainable)
  - Sticky sidebar navigation grouped by 7 domains
  - Smart number formatting
  - Self-contained HTML (no external server needed)
"""

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from jinja2 import Template


# ---------------------------------------------------------------------------
# Smart formatter
# ---------------------------------------------------------------------------

def _fmt(v, col: str = "") -> str:
    """Smart value formatter - years never formatted as dollars."""
    if v is None or (isinstance(v, float) and v != v):
        return "--"
    col_l = col.lower()
    if any(k in col_l for k in ("year_no", "month_no", "quarter_no", "fiscal")):
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)
    if isinstance(v, float):
        if any(k in col_l for k in ("pct", "margin", "growth", "discount_pct")):
            return f"{v:,.2f}%"
        if col_l in ("avg_lag_days", "avg_ship_lag"):
            return f"{v:,.2f} days"
        if any(k in col_l for k in (
                "sales", "profit", "revenue", "value",
                "avg_order", "avg_line", "avg_sales_per")):
            cls = ' class="neg"' if v < 0 else ""
            sign = "-" if v < 0 else ""
            return f'<span{cls}>{sign}${abs(v):,.2f}</span>'
        if v == int(v):
            return f"{int(v):,}"
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


# ---------------------------------------------------------------------------
# DataFrame -> HTML table
# ---------------------------------------------------------------------------

def _df_to_html(df: pd.DataFrame, qid: str = "") -> str:
    if df is None or df.empty:
        return '<p class="no-data">No data available - run the warehouse pipeline first (options 2-5).</p>'
    rows = ""
    for i, (_, row) in enumerate(df.iterrows()):
        cls = "odd" if i % 2 == 0 else "even"
        cells = "".join(f"<td>{_fmt(v, col)}</td>" for col, v in zip(df.columns, row))
        rows += f"<tr class='{cls}'>{cells}</tr>"
    headers = "".join(f"<th>{c.replace('_', ' ').title()}</th>" for c in df.columns)
    return (
        '<div class="table-wrap">'
        f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Plotly chart builder
# ---------------------------------------------------------------------------

CHART_COLORS = [
    "#2563EB", "#16A34A", "#EA580C", "#7C3AED",
    "#DC2626", "#0891B2", "#CA8A04", "#6366F1",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#334155"),
    margin=dict(l=50, r=20, t=10, b=50),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        font=dict(size=11, color="#64748B"),
    ),
    xaxis=dict(
        gridcolor="#E2E8F0", linecolor="#CBD5E1",
        tickfont=dict(color="#64748B", size=10),
    ),
    yaxis=dict(
        gridcolor="#E2E8F0", linecolor="#CBD5E1",
        tickfont=dict(color="#64748B", size=10),
    ),
    hoverlabel=dict(
        bgcolor="#1E293B", font_size=12,
        font_color="white", bordercolor="#334155",
    ),
    bargap=0.25,
    height=280,
)


def _build_chart(df: pd.DataFrame, chart_cfg, qid: str) -> str:
    """Build a Plotly chart and return its HTML div (no full page wrapper)."""
    if chart_cfg is None or df is None or df.empty:
        return ""
    c_type, label_col, value_cols, colors = chart_cfg
    if label_col not in df.columns:
        return ""

    labels = []
    for v in df[label_col]:
        if isinstance(v, float) and v == int(v):
            labels.append(str(int(v)))
        else:
            labels.append(str(v))

    fig = go.Figure()
    palette = colors + CHART_COLORS

    for i, vc in enumerate(value_cols):
        if vc not in df.columns:
            continue
        vals = [float(x) if (x == x) else 0 for x in df[vc]]
        color = palette[i % len(palette)]
        name = vc.replace("_", " ").title()

        if c_type == "line":
            fig.add_trace(go.Scatter(
                x=labels, y=vals, name=name, mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(size=7, color=color),
                hovertemplate="%{x}<br>" + name + ": %{y:,.2f}<extra></extra>",
            ))
        else:
            fig.add_trace(go.Bar(
                x=labels, y=vals, name=name,
                marker_color=color, marker_line_width=0,
                hovertemplate="%{x}<br>" + name + ": %{y:,.2f}<extra></extra>",
            ))

    layout = {**PLOTLY_LAYOUT}
    if c_type == "bar" and len(value_cols) > 1:
        layout["barmode"] = "group"

    fig.update_layout(**layout)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False,
                       div_id=f"chart_{qid}", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Query metadata
# ---------------------------------------------------------------------------

# Lucide icon names mapped per query
ICON_MAP = {
    "Q1": "calendar", "Q2": "trending-up", "Q3": "columns-3", "Q4": "trophy",
    "Q5": "alert-triangle", "Q6": "package", "Q7": "users", "Q8": "star",
    "Q9": "globe", "Q10": "map-pin", "Q11": "store", "Q12": "calendar-days",
    "Q13": "party-popper", "Q14": "target", "Q15": "megaphone", "Q16": "percent",
    "Q17": "grid-3x3", "Q18": "circle-alert", "Q19": "bar-chart-3", "Q20": "layers",
    "Q21": "truck", "Q22": "medal", "Q23": "repeat", "Q24": "clipboard-list",
    "Q25": "gem",
}

KPI_ICONS = {
    "revenue": "dollar-sign", "profit": "trending-up", "margin": "pie-chart",
    "orders": "shopping-cart", "customers": "users", "products": "package",
    "ship": "truck", "promo": "target",
}

def _lucide(name: str, size: int = 18, color: str = "currentColor") -> str:
    return f'<i data-lucide="{name}" style="width:{size}px;height:{size}px;color:{color}"></i>'

QUERY_META = {
    "Q1":  {"desc": "Yearly sales and profit trend across 2014-2017.",
             "chart": ("bar", "year_no", ["total_sales", "total_profit"], ["#2563EB", "#16A34A"])},
    "Q2":  {"desc": "Monthly sales trend revealing seasonal patterns.",
             "chart": ("line", "month_name", ["total_sales", "total_profit"], ["#2563EB", "#16A34A"])},
    "Q3":  {"desc": "Quarterly revenue breakdown by year.",
             "chart": ("bar", "year_no", ["q1", "q2", "q3", "q4"],
                       ["#2563EB", "#EA580C", "#16A34A", "#7C3AED"])},
    "Q4":  {"desc": "Top 10 products by revenue.",
             "chart": ("bar", "product_name", ["total_sales", "total_profit"], ["#2563EB", "#16A34A"])},
    "Q5":  {"desc": "Bottom 10 products by profit (loss-leaders).",
             "chart": ("bar", "product_name", ["total_profit"], ["#DC2626"])},
    "Q6":  {"desc": "Sales and profit margin by product category.",
             "chart": ("bar", "category", ["total_sales", "total_profit"], ["#2563EB", "#16A34A"])},
    "Q7":  {"desc": "Revenue breakdown by customer segment.",
             "chart": ("bar", "segment", ["total_sales", "total_profit"], ["#7C3AED", "#16A34A"])},
    "Q8":  {"desc": "Top 10 customers by total spend.",
             "chart": ("bar", "customer_name", ["total_sales", "total_profit"], ["#CA8A04", "#16A34A"])},
    "Q9":  {"desc": "Sales and profit by geographic region.",
             "chart": ("bar", "region", ["total_sales", "total_profit"], ["#0891B2", "#16A34A"])},
    "Q10": {"desc": "Top 5 most profitable states.",
             "chart": ("bar", "state", ["total_profit", "total_sales"], ["#16A34A", "#2563EB"])},
    "Q11": {"desc": "Best store per quarter by sales volume.",
             "chart": None},
    "Q12": {"desc": "Weekday vs weekend sales comparison.",
             "chart": ("bar", "day_type", ["total_sales", "order_lines"], ["#2563EB", "#EA580C"])},
    "Q13": {"desc": "Holiday vs normal day revenue comparison.",
             "chart": ("bar", "day_type", ["total_sales", "avg_sales_per_day"], ["#7C3AED", "#CA8A04"])},
    "Q14": {"desc": "Sales with vs without active promotions.",
             "chart": ("bar", "promo_status", ["total_sales", "total_profit"], ["#16A34A", "#DC2626"])},
    "Q15": {"desc": "Top promotional campaigns by revenue.",
             "chart": ("bar", "promo_name", ["total_sales", "total_profit"], ["#EA580C", "#16A34A"])},
    "Q16": {"desc": "Discount band impact on profit margins.",
             "chart": ("bar", "discount_band", ["total_sales", "total_profit"], ["#2563EB", "#DC2626"])},
    "Q17": {"desc": "Category sales across all four regions.",
             "chart": ("bar", "category", ["east", "west", "central", "south"],
                       ["#2563EB", "#16A34A", "#EA580C", "#7C3AED"])},
    "Q18": {"desc": "Top 15 loss-making products.",
             "chart": ("bar", "product_name", ["total_profit"], ["#DC2626"])},
    "Q19": {"desc": "Year-over-year sales growth percentage.",
             "chart": ("line", "year_no", ["total_sales"], ["#2563EB"])},
    "Q20": {"desc": "Category and sub-category rollup with subtotals.",
             "chart": None},
    "Q21": {"desc": "Shipping mode performance comparison.",
             "chart": ("bar", "ship_mode_name", ["total_sales", "total_profit"], ["#0891B2", "#16A34A"])},
    "Q22": {"desc": "Sub-category profitability ranking.",
             "chart": ("bar", "sub_category", ["total_profit"], ["#2563EB"])},
    "Q23": {"desc": "Customer loyalty tiers by order frequency.",
             "chart": ("bar", "loyalty_tier", ["customers"], ["#7C3AED"])},
    "Q24": {"desc": "Fiscal quarter KPI summary.",
             "chart": ("line", "fiscal_quarter", ["total_sales", "total_profit"], ["#2563EB", "#16A34A"])},
    "Q25": {"desc": "Top 10 highest-revenue individual orders.",
             "chart": None},
}

GROUPS = [
    ("Time & Trends",    ["Q1", "Q2", "Q3", "Q19", "Q24"]),
    ("Products",         ["Q4", "Q5", "Q6", "Q18", "Q20", "Q22"]),
    ("Customers",        ["Q7", "Q8", "Q23", "Q25"]),
    ("Geography",        ["Q9", "Q10", "Q17"]),
    ("Stores & Ops",     ["Q11", "Q21"]),
    ("Promotions",       ["Q14", "Q15", "Q16"]),
    ("Calendar",         ["Q12", "Q13"]),
]


# ---------------------------------------------------------------------------
# KPI card helper
# ---------------------------------------------------------------------------

def _kpi_card(lucide_name, label, value, color, prefix="", suffix=""):
    if isinstance(value, float):
        disp = f"{prefix}{value:,.2f}{suffix}"
    else:
        disp = f"{prefix}{value:,}{suffix}"
    icon_html = _lucide(lucide_name, 22, color)
    return {"icon": icon_html, "label": label, "disp": disp, "color": color}


# ---------------------------------------------------------------------------
# Jinja2 HTML Template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = Template(r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Superstore BI Dashboard - {{ ts_str }}</title>
<meta name="description" content="Superstore Data Warehouse: 25 executive analytics queries with interactive Plotly charts."/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script src="https://unpkg.com/lucide@latest"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #F1F5F9; --surface: #FFFFFF; --card: #FFFFFF;
  --border: #E2E8F0; --text: #1E293B; --muted: #64748B;
  --accent: #2563EB; --green: #16A34A; --red: #DC2626;
  --sidebar-w: 268px;
}
html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', sans-serif;
  background: var(--bg); color: var(--text);
  font-size: 14px; line-height: 1.6;
  display: flex; min-height: 100vh;
}

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-w); min-height: 100vh;
  background: var(--surface); border-right: 1px solid var(--border);
  position: fixed; top:0; left:0; bottom:0;
  overflow-y: auto; z-index: 100;
  scrollbar-width: thin; scrollbar-color: #CBD5E1 transparent;
}
.sidebar-brand {
  padding: 20px 18px 14px; border-bottom: 1px solid var(--border);
  position: sticky; top:0; background: var(--surface); z-index:10;
}
.sidebar-brand h2 { font-size:13px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:1px; }
.sidebar-brand p  { font-size:11px; color:var(--muted); margin-top:2px; }
.nav-group { padding:6px 0; border-bottom:1px solid var(--border); }
.nav-group-title {
  font-size:10px; font-weight:700; text-transform:uppercase;
  letter-spacing:1.2px; color:var(--muted); padding:8px 16px 4px;
}
.nav-item {
  display:flex; align-items:flex-start; gap:8px;
  padding:6px 16px; text-decoration:none; color:var(--muted);
  font-size:12px; transition:all .15s; border-left:3px solid transparent;
}
.nav-item:hover { color:var(--accent); background:#EFF6FF; border-left-color:var(--accent); }
.nav-badge {
  font-size:9px; font-weight:700; background:#EFF6FF;
  color:var(--accent); border:1px solid #BFDBFE;
  border-radius:4px; padding:1px 5px;
  white-space:nowrap; flex-shrink:0; margin-top:1px;
}
.nav-text { line-height:1.3; }

/* ── Main ── */
.main { margin-left:var(--sidebar-w); flex:1; display:flex; flex-direction:column; }

/* ── Header ── */
.page-header {
  background: linear-gradient(135deg,#1E40AF 0%,#2563EB 50%,#3B82F6 100%);
  border-bottom:1px solid var(--border); padding:40px 48px 32px;
  position:relative; overflow:hidden;
}
.page-header::before {
  content:''; position:absolute; top:-60px; right:-60px;
  width:280px; height:280px;
  background:radial-gradient(circle,rgba(255,255,255,.12) 0%,transparent 70%);
  border-radius:50%;
}
.page-header h1 { font-size:34px; font-weight:800; color:#FFF; letter-spacing:-1px; position:relative; }
.page-header .subtitle { color:rgba(255,255,255,.75); margin-top:8px; font-size:14px; position:relative; }
.page-header .subtitle strong { color:#FFF; }

/* ── Content ── */
.content { padding:32px 40px; max-width:1180px; }

.section-heading {
  font-size:11px; font-weight:700; text-transform:uppercase;
  letter-spacing:1.5px; color:var(--muted); margin:40px 0 16px;
  display:flex; align-items:center; gap:10px;
}
.section-heading::after { content:''; flex:1; height:1px; background:var(--border); }

/* ── KPI ── */
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(185px,1fr)); gap:14px; margin-bottom:8px; }
.kpi-card {
  background:var(--card); border:1px solid var(--border);
  border-top:3px solid var(--kpi-color);
  border-radius:12px; padding:16px 18px;
  display:flex; align-items:center; gap:14px;
  transition:transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform:translateY(-3px); box-shadow:0 8px 24px rgba(37,99,235,.12); }
.kpi-icon { display:flex; align-items:center; justify-content:center; width:42px; height:42px; border-radius:10px; background:#EFF6FF; flex-shrink:0; }
.kpi-label { font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.8px; color:var(--muted); margin-bottom:4px; }
.kpi-value { font-size:20px; font-weight:700; }

/* ── Query section ── */
.query-section {
  background:var(--card); border:1px solid var(--border);
  border-radius:14px; padding:26px; margin-bottom:22px;
  transition:border-color .2s, box-shadow .2s; scroll-margin-top:20px;
}
.query-section:hover { border-color:#93C5FD; box-shadow:0 4px 16px rgba(37,99,235,.08); }
.query-header { display:flex; align-items:center; gap:12px; margin-bottom:6px; }
.qbadge {
  background:#EFF6FF; color:var(--accent); border:1px solid #BFDBFE;
  border-radius:8px; padding:4px 10px;
  font-size:11px; font-weight:800; letter-spacing:.5px; flex-shrink:0;
}
.query-title { font-size:16px; font-weight:700; color:var(--text); line-height:1.3; }
.query-desc  { font-size:13px; color:var(--muted); margin-bottom:20px; }

/* ── Plotly chart wrapper ── */
.chart-wrap { margin-bottom:20px; border-radius:8px; overflow:hidden; }

/* ── Table ── */
.table-wrap { overflow-x:auto; border-radius:8px; border:1px solid var(--border); }
table { width:100%; border-collapse:collapse; font-size:13px; }
thead tr { background:linear-gradient(90deg,#1E40AF,#2563EB); }
thead th {
  padding:10px 14px; text-align:left; font-weight:600;
  font-size:11px; text-transform:uppercase; letter-spacing:.6px;
  color:#FFF; white-space:nowrap; border-bottom:1px solid var(--border);
}
tbody tr.odd  { background:#F8FAFC; }
tbody tr.even { background:#FFF; }
tbody tr:hover { background:#EFF6FF; }
tbody td { padding:9px 14px; border-bottom:1px solid var(--border); white-space:nowrap; color:var(--text); }
.neg { color:var(--red) !important; font-weight:500; }
.no-data { color:var(--muted); font-style:italic; padding:24px; text-align:center; font-size:13px; }

/* ── Footer ── */
.footer { text-align:center; padding:32px; color:var(--muted); font-size:12px; border-top:1px solid var(--border); margin-top:40px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#CBD5E1; border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:#94A3B8; }
</style>
</head>
<body>

<!-- Sidebar -->
<nav class="sidebar">
  <div class="sidebar-brand">
    <h2><i data-lucide="bar-chart-3" style="width:16px;height:16px;vertical-align:-2px"></i> BI Dashboard</h2>
    <p>Superstore Data Warehouse</p>
  </div>
  {% for group_name, items in sidebar_groups %}
  <div class="nav-group">
    <div class="nav-group-title">{{ group_name }}</div>
    {% for qid, title, icon_html in items %}
    <a class="nav-item" href="#{{ qid }}">
      <span class="nav-badge">{{ qid }}</span>
      <span class="nav-text">{{ title }}</span>
    </a>
    {% endfor %}
  </div>
  {% endfor %}
</nav>

<!-- Main -->
<div class="main">
  <div class="page-header">
    <h1>Superstore Analytics</h1>
    <div class="subtitle">{{ ts_display }} &nbsp;&bull;&nbsp; 25 Queries</div>
  </div>

  <div class="content">
    <!-- KPIs -->
    <div class="section-heading">Overview</div>
    <div class="kpi-grid">
      {% for kpi in kpis %}
      <div class="kpi-card" style="--kpi-color:{{ kpi.color }}">
        <div class="kpi-icon" style="background:{{ kpi.color }}12">{{ kpi.icon }}</div>
        <div class="kpi-body">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" style="color:{{ kpi.color }}">{{ kpi.disp }}</div>
        </div>
      </div>
      {% endfor %}
    </div>

    <!-- Query sections -->
    <div class="section-heading" style="margin-top:48px">Query Results</div>
    {% for q in queries %}
    <div class="query-section" id="{{ q.qid }}">
      <div class="query-header">
        <span class="qbadge">{{ q.icon_html }} {{ q.qid }}</span>
        <h3 class="query-title">{{ q.title }}</h3>
      </div>
      <p class="query-desc">{{ q.desc }}</p>
      {% if q.chart_html %}
      <div class="chart-wrap">{{ q.chart_html }}</div>
      {% endif %}
      {{ q.table_html }}
    </div>
    {% endfor %}
  </div>

  <div class="footer">Superstore DW &bull; {{ ts_display }}</div>
</div>
<script>lucide.createIcons();</script>
</body>
</html>''')


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_html_report(path: Path, kpis: dict, all_dfs: dict,
                         ts_str: str, queries_catalog: list = None) -> Path:
    """Builds and writes a clean light-theme HTML BI dashboard with Plotly charts."""

    # KPI cards
    kpi_cards = [
        _kpi_card("dollar-sign",   "Revenue",      kpis.get("total_revenue",   0), "#2563EB", "$"),
        _kpi_card("trending-up",   "Profit",       kpis.get("total_profit",    0), "#16A34A", "$"),
        _kpi_card("pie-chart",     "Margin",       kpis.get("avg_margin",      0), "#7C3AED", "", "%"),
        _kpi_card("shopping-cart",  "Orders",       kpis.get("total_orders",    0), "#EA580C"),
        _kpi_card("users",         "Customers",    kpis.get("total_customers", 0), "#DC2626"),
        _kpi_card("package",       "Products",     kpis.get("total_products",  0), "#CA8A04"),
        _kpi_card("truck",         "Ship Lag",     kpis.get("avg_ship_lag",    0), "#0891B2", "", " days"),
        _kpi_card("target",        "Promo Orders", kpis.get("promo_orders",    0), "#6366F1"),
    ]

    # Sidebar nav groups
    catalog_map = {qid: title for qid, title, _ in (queries_catalog or [])}
    sidebar_groups = []
    for group_name, qids in GROUPS:
        items = []
        for qid in qids:
            title = catalog_map.get(qid, qid)
            icon_html = _lucide(ICON_MAP.get(qid, "file-text"), 14)
            items.append((qid, title, icon_html))
        sidebar_groups.append((group_name, items))

    # Query sections
    query_data = []
    for qid, title, _ in (queries_catalog or []):
        df = all_dfs.get(qid)
        meta = QUERY_META.get(qid, {})
        chart_html = _build_chart(df, meta.get("chart"), qid)
        icon_html = _lucide(ICON_MAP.get(qid, "file-text"), 14, "#2563EB")
        query_data.append({
            "qid": qid,
            "title": title,
            "icon_html": icon_html,
            "desc": meta.get("desc", ""),
            "chart_html": chart_html,
            "table_html": _df_to_html(df, qid),
        })

    ts_display = ts_str.replace("_", " ")

    html = HTML_TEMPLATE.render(
        ts_str=ts_str,
        ts_display=ts_display,
        kpis=kpi_cards,
        sidebar_groups=sidebar_groups,
        queries=query_data,
    )

    path.write_text(html, encoding="utf-8")
    return path
