"""Generate an interactive HTML dashboard from pipeline metrics."""

import json
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from jinja2 import Template

OUTPUT_DIR = Path(__file__).parent / "output"
METRICS_PATH = OUTPUT_DIR / "metrics.json"

# ── Color Palette ────────────────────────────────────────────────────────────

COLORS = {
    "blue": "#6C8EBF",
    "green": "#82B366",
    "orange": "#D4A574",
    "purple": "#9B8EC4",
    "pink": "#C78EAD",
    "teal": "#6DBFB0",
    "text": "#374151",
    "text_light": "#6B7280",
    "bg": "#f8f9fa",
    "card_bg": "#ffffff",
    "grid": "#f0f0f0",
    "border": "#e5e7eb",
}

CATEGORY_COLORS = [
    COLORS["blue"],
    COLORS["green"],
    COLORS["orange"],
    COLORS["purple"],
    COLORS["pink"],
]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color=COLORS["text"], size=13),
    margin=dict(l=50, r=30, t=50, b=40),
    hoverlabel=dict(
        bgcolor=COLORS["card_bg"],
        font_color=COLORS["text"],
        font_size=13,
        bordercolor=COLORS["border"],
    ),
)


# ── Chart Builders ───────────────────────────────────────────────────────────


def build_revenue_trend(monthly_revenue: list[dict]) -> str:
    """Monthly revenue line chart with area fill."""
    months = [r["month"] for r in monthly_revenue]
    values = [r["revenue"] for r in monthly_revenue]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=values,
            mode="lines+markers",
            line=dict(color=COLORS["blue"], width=2.5, shape="spline"),
            marker=dict(size=5, color=COLORS["blue"]),
            fill="tozeroy",
            fillcolor="rgba(108, 142, 191, 0.08)",
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(
            text="Monthly Revenue Trend", font=dict(size=16, color=COLORS["text"])
        ),
        xaxis=dict(
            showgrid=False,
            tickangle=-45,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            gridwidth=1,
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(size=11),
        ),
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_category_chart(by_category: list[dict]) -> str:
    """Horizontal bar chart of revenue by category."""
    categories = [r["category"] for r in by_category]
    values = [r["revenue"] for r in by_category]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=values,
            y=categories,
            orientation="h",
            marker=dict(color=CATEGORY_COLORS[: len(categories)], cornerradius=4),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(
            text="Revenue by Category", font=dict(size=16, color=COLORS["text"])
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            gridwidth=1,
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(size=11),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=12)),
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_top_products(top_products: list[dict]) -> str:
    """Bar chart of top 10 products by revenue."""
    # Reverse so highest is on top in horizontal layout
    products = [r["product"] for r in reversed(top_products)]
    values = [r["revenue"] for r in reversed(top_products)]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=values,
            y=products,
            orientation="h",
            marker=dict(color=COLORS["green"], cornerradius=4),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(
            text="Top 10 Products by Revenue", font=dict(size=16, color=COLORS["text"])
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            gridwidth=1,
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(size=11),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_country_chart(by_country: list[dict]) -> str:
    """Horizontal bar chart of revenue by country."""
    countries = [r["country"] for r in by_country]
    values = [r["revenue"] for r in by_country]

    bar_colors = [
        COLORS["teal"],
        COLORS["blue"],
        COLORS["green"],
        COLORS["orange"],
        COLORS["purple"],
        COLORS["pink"],
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=values,
            y=countries,
            orientation="h",
            marker=dict(color=bar_colors[: len(countries)], cornerradius=4),
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Revenue by Country", font=dict(size=16, color=COLORS["text"])),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            gridwidth=1,
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(size=11),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=12)),
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_cohort_chart(cohorts: list[dict]) -> str:
    """Stacked bar chart of new vs returning customers by month."""
    months = [r["month"] for r in cohorts]
    new_customers = [r.get("new", 0) for r in cohorts]
    returning = [r.get("returning", 0) for r in cohorts]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=months,
            y=new_customers,
            name="New Customers",
            marker=dict(color=COLORS["blue"], cornerradius=4),
            hovertemplate="<b>%{x}</b><br>New: %{y:,}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=months,
            y=returning,
            name="Returning Customers",
            marker=dict(color=COLORS["green"], cornerradius=4),
            hovertemplate="<b>%{x}</b><br>Returning: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        barmode="stack",
        title=dict(
            text="New vs Returning Customers by Month",
            font=dict(size=16, color=COLORS["text"]),
        ),
        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=11)),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            gridwidth=1,
            tickformat=",",
            tickfont=dict(size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        height=400,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# ── HTML Template ────────────────────────────────────────────────────────────

HTML_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-commerce Analytics Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <style>
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: {{ colors.bg }};
            color: {{ colors.text }};
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        /* ── Header ── */
        .header {
            margin-bottom: 36px;
        }

        .header h1 {
            font-size: 24px;
            font-weight: 700;
            color: {{ colors.text }};
            letter-spacing: -0.02em;
        }

        .header-meta {
            display: flex;
            gap: 24px;
            margin-top: 8px;
            font-size: 13px;
            color: {{ colors.text_light }};
        }

        /* ── KPI Cards ── */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: {{ colors.card_bg }};
            border: 1px solid {{ colors.border }};
            border-radius: 12px;
            padding: 24px;
            transition: box-shadow 0.15s ease;
        }

        .kpi-card:hover {
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
        }

        .kpi-label {
            font-size: 13px;
            font-weight: 500;
            color: {{ colors.text_light }};
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 8px;
        }

        .kpi-value {
            font-size: 28px;
            font-weight: 700;
            color: {{ colors.text }};
            letter-spacing: -0.02em;
        }

        .kpi-delta {
            display: inline-block;
            margin-top: 8px;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
        }

        .kpi-delta.positive {
            color: #16a34a;
            background: #f0fdf4;
        }

        .kpi-delta.negative {
            color: #dc2626;
            background: #fef2f2;
        }

        /* ── Chart Grid ── */
        .chart-row {
            display: grid;
            gap: 16px;
            margin-bottom: 24px;
        }

        .chart-row.two-col {
            grid-template-columns: 1fr 1fr;
        }

        .chart-row.full-width {
            grid-template-columns: 1fr;
        }

        .chart-card {
            background: {{ colors.card_bg }};
            border: 1px solid {{ colors.border }};
            border-radius: 12px;
            padding: 8px;
            overflow: hidden;
        }

        .chart-card .js-plotly-plot {
            border-radius: 8px;
        }

        /* ── Footer ── */
        .footer {
            text-align: center;
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid {{ colors.border }};
            font-size: 12px;
            color: {{ colors.text_light }};
        }

        /* ── Responsive ── */
        @media (max-width: 768px) {
            .kpi-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .chart-row.two-col {
                grid-template-columns: 1fr;
            }

            .container {
                padding: 24px 16px;
            }

            .kpi-value {
                font-size: 22px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>E-commerce Analytics Dashboard</h1>
            <div class="header-meta">
                <span>Data period: {{ data_period.start }} to {{ data_period.end }}</span>
                <span>Generated: {{ generated_at }}</span>
            </div>
        </div>

        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Revenue</div>
                <div class="kpi-value">${{ "{:,.0f}".format(kpis.total_revenue) }}</div>
                {% if kpis.rev_delta >= 0 %}
                <span class="kpi-delta positive">+{{ "{:.1%}".format(kpis.rev_delta) }} vs prev month</span>
                {% else %}
                <span class="kpi-delta negative">{{ "{:.1%}".format(kpis.rev_delta) }} vs prev month</span>
                {% endif %}
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Orders</div>
                <div class="kpi-value">{{ "{:,}".format(kpis.total_orders) }}</div>
                {% if kpis.orders_delta >= 0 %}
                <span class="kpi-delta positive">+{{ "{:.1%}".format(kpis.orders_delta) }} vs prev month</span>
                {% else %}
                <span class="kpi-delta negative">{{ "{:.1%}".format(kpis.orders_delta) }} vs prev month</span>
                {% endif %}
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Avg Order Value</div>
                <div class="kpi-value">${{ "{:.2f}".format(kpis.aov) }}</div>
                {% if kpis.aov_delta >= 0 %}
                <span class="kpi-delta positive">+{{ "{:.1%}".format(kpis.aov_delta) }} vs prev month</span>
                {% else %}
                <span class="kpi-delta negative">{{ "{:.1%}".format(kpis.aov_delta) }} vs prev month</span>
                {% endif %}
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Refund Rate</div>
                <div class="kpi-value">{{ "{:.1%}".format(kpis.refund_rate) }}</div>
                <span class="kpi-delta" style="color: {{ colors.text_light }}; background: #f3f4f6;">All time</span>
            </div>
        </div>

        <!-- Row 2: Revenue Trend + Category -->
        <div class="chart-row two-col">
            <div class="chart-card">{{ chart_revenue_trend }}</div>
            <div class="chart-card">{{ chart_category }}</div>
        </div>

        <!-- Row 3: Top Products + Country -->
        <div class="chart-row two-col">
            <div class="chart-card">{{ chart_top_products }}</div>
            <div class="chart-card">{{ chart_country }}</div>
        </div>

        <!-- Row 4: Customer Cohorts -->
        <div class="chart-row full-width">
            <div class="chart-card">{{ chart_cohorts }}</div>
        </div>

        <!-- Footer -->
        <div class="footer">
            Automated E-commerce Analytics Pipeline &middot; Python, pandas, plotly
        </div>
    </div>
</body>
</html>
""")


# ── Main ─────────────────────────────────────────────────────────────────────


class _DotDict(dict):
    """Allow dict.key access for Jinja2 templates."""

    __getattr__ = dict.__getitem__


def generate_dashboard() -> Path:
    """Build the HTML dashboard from pipeline metrics."""
    print("=== Dashboard Generator ===\n")

    print("[1/3] Loading metrics...")
    with open(METRICS_PATH) as f:
        metrics = json.load(f)

    print("[2/3] Building charts...")
    chart_revenue_trend = build_revenue_trend(metrics["monthly_revenue"])
    chart_category = build_category_chart(metrics["by_category"])
    chart_top_products = build_top_products(metrics["top_products"])
    chart_country = build_country_chart(metrics["by_country"])
    chart_cohorts = build_cohort_chart(metrics["customer_cohorts"])

    print("[3/3] Rendering HTML...")
    html = HTML_TEMPLATE.render(
        colors=_DotDict(COLORS),
        kpis=_DotDict(metrics["kpis"]),
        data_period=_DotDict(metrics["data_period"]),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        chart_revenue_trend=chart_revenue_trend,
        chart_category=chart_category,
        chart_top_products=chart_top_products,
        chart_country=chart_country,
        chart_cohorts=chart_cohorts,
    )

    output_path = OUTPUT_DIR / "dashboard.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    size_kb = output_path.stat().st_size / 1024
    print(f"\n  Dashboard saved to {output_path} ({size_kb:.0f} KB)")
    print("Done.")
    return output_path


if __name__ == "__main__":
    generate_dashboard()
