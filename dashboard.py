"""
Finance Vault Dashboard — Streamlit + Plotly
Reads YAML frontmatter from Obsidian vault markdown files.
"""

import re
from pathlib import Path
import yaml
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design tokens ──────────────────────────────────────────────────────────────
BG       = "#080c14"
CARD     = "#0f1623"
CARD2    = "#131d2e"
BORDER   = "#1e293b"
BORDER2  = "#263348"
TEXT1    = "#f1f5f9"
TEXT2    = "#94a3b8"
TEXT3    = "#475569"
GREEN    = "#10b981"
RED      = "#f43f5e"
AMBER    = "#f59e0b"
BLUE     = "#3b82f6"
BLUE2    = "#60a5fa"
PURPLE   = "#a78bfa"
TEAL     = "#2dd4bf"
ORANGE   = "#fb923c"

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  #MainMenu, header[data-testid="stHeader"], footer {{ display: none !important; }}
  .stDeployButton {{ display: none !important; }}
  [data-testid="stToolbar"] {{ display: none !important; }}

  .stApp, [data-testid="stAppViewContainer"] {{ background: {BG}; }}
  [data-testid="stMain"] .block-container {{ padding: 2rem 2.5rem 4rem; max-width: 1400px; }}

  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: {BG}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER2}; border-radius: 3px; }}

  /* Tab styling */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {CARD}; border-radius: 12px; padding: 4px;
    border: 1px solid {BORDER}; gap: 4px;
  }}
  [data-testid="stTabs"] [data-baseweb="tab"] {{
    border-radius: 8px; padding: 8px 20px;
    color: {TEXT2}; font-size: 0.8rem; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase;
    background: transparent; border: none;
  }}
  [data-testid="stTabs"] [aria-selected="true"] {{
    background: {BORDER2} !important; color: {TEXT1} !important;
  }}
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ display: none; }}
  [data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none; }}

  /* KPI card */
  .kpi-card {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 14px; padding: 20px 24px 18px;
    position: relative; overflow: hidden; height: 100%;
  }}
  .kpi-card::before {{
    content: ""; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%; border-radius: 14px 0 0 14px;
  }}
  .kpi-card.red::before   {{ background: {RED}; }}
  .kpi-card.green::before {{ background: {GREEN}; }}
  .kpi-card.amber::before {{ background: {AMBER}; }}
  .kpi-card.blue::before  {{ background: {BLUE}; }}
  .kpi-card.purple::before{{ background: {PURPLE}; }}
  .kpi-card.teal::before  {{ background: {TEAL}; }}
  .kpi-card.orange::before{{ background: {ORANGE}; }}
  .kpi-glow {{
    position: absolute; top: 0; right: 0;
    width: 80px; height: 80px; border-radius: 50%;
    opacity: 0.06; transform: translate(25%, -25%);
  }}
  .kpi-card.red    .kpi-glow {{ background: {RED}; }}
  .kpi-card.green  .kpi-glow {{ background: {GREEN}; }}
  .kpi-card.amber  .kpi-glow {{ background: {AMBER}; }}
  .kpi-card.blue   .kpi-glow {{ background: {BLUE}; }}
  .kpi-card.purple .kpi-glow {{ background: {PURPLE}; }}
  .kpi-card.teal   .kpi-glow {{ background: {TEAL}; }}
  .kpi-card.orange .kpi-glow {{ background: {ORANGE}; }}
  .kpi-icon  {{ font-size: 1.1rem; margin-bottom: 10px; opacity: 0.7; }}
  .kpi-label {{ color: {TEXT3}; font-size: 0.68rem; text-transform: uppercase;
                letter-spacing: 0.12em; font-weight: 600; margin-bottom: 6px; }}
  .kpi-value {{ color: {TEXT1}; font-size: 2rem; font-weight: 800;
                letter-spacing: -0.02em; line-height: 1; }}
  .kpi-delta {{ font-size: 0.75rem; margin-top: 8px; font-weight: 500; }}
  .kpi-delta.neg {{ color: {RED}; }}
  .kpi-delta.pos {{ color: {GREEN}; }}
  .kpi-delta.neu {{ color: {TEXT2}; }}

  .sec-header {{ display: flex; align-items: center; gap: 12px; margin: 2rem 0 1rem; }}
  .sec-header-bar {{ width: 3px; height: 20px; border-radius: 2px; }}
  .sec-header-text {{ color: {TEXT1}; font-size: 0.85rem; font-weight: 700;
                      text-transform: uppercase; letter-spacing: 0.1em; }}

  .chart-card {{ background: {CARD}; border: 1px solid {BORDER};
                 border-radius: 14px; padding: 4px; overflow: hidden; }}

  /* Sentiment badge */
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
            text-transform: uppercase; }}
  .badge-bearish {{ background: rgba(244,63,94,0.15); color: {RED}; border: 1px solid rgba(244,63,94,0.3); }}
  .badge-bullish {{ background: rgba(16,185,129,0.15); color: {GREEN}; border: 1px solid rgba(16,185,129,0.3); }}
  .badge-neutral {{ background: rgba(245,158,11,0.15); color: {AMBER}; border: 1px solid rgba(245,158,11,0.3); }}

  [data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden; }}
  [data-testid="column"] > div {{ height: 100%; }}
</style>
""", unsafe_allow_html=True)

VAULT_ROOT = Path(__file__).parent

# ── Helpers ────────────────────────────────────────────────────────────────────
def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}

def load_latest(folder: str, type_key: str) -> dict:
    files = sorted((VAULT_ROOT / "Analysis" / folder).glob("*.md"), reverse=True)
    for f in files:
        fm = parse_frontmatter(f)
        if fm.get("type") == type_key:
            return fm
    return {}

def load_history(folder: str, type_key: str, date_field: str = "date") -> pd.DataFrame:
    files = sorted((VAULT_ROOT / "Analysis" / folder).glob("*.md"))
    rows = [parse_frontmatter(f) for f in files]
    rows = [r for r in rows if r.get("type") == type_key and r.get(date_field)]
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def chart_layout(fig, title="", height=340, margin=None, **kwargs):
    m = margin or dict(t=48, b=16, l=16, r=16)
    base_xaxis = dict(showgrid=False, zeroline=False, tickcolor=TEXT3,
                      linecolor=BORDER2, tickfont=dict(size=11, color=TEXT2))
    base_yaxis = dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                      tickcolor=TEXT3, linecolor="rgba(0,0,0,0)",
                      tickfont=dict(size=11, color=TEXT2))
    if "xaxis" in kwargs: base_xaxis.update(kwargs.pop("xaxis"))
    if "yaxis" in kwargs: base_yaxis.update(kwargs.pop("yaxis"))
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=13, color=TEXT2, family="Inter, sans-serif"),
                   x=0, xanchor="left", pad=dict(l=8)),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT2, family="Inter, sans-serif", size=11),
        height=height, margin=m, xaxis=base_xaxis, yaxis=base_yaxis, **kwargs,
    )
    return fig

def section_header(label, color=BLUE):
    st.markdown(f"""
    <div class="sec-header">
      <div class="sec-header-bar" style="background:{color}"></div>
      <span class="sec-header-text">{label}</span>
    </div>""", unsafe_allow_html=True)

def chart_card(fig, col):
    with col:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

def kpi(accent, icon, label, value, delta, delta_class):
    return f"""
    <div class="kpi-card {accent}">
      <div class="kpi-glow"></div>
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-delta {delta_class}">{delta}</div>
    </div>"""

def table_style(df):
    return (df.style
        .set_properties(**{"background-color": CARD, "color": TEXT2,
                           "border-color": BORDER, "font-size": "12px"})
        .set_table_styles([{"selector": "th", "props": [
            ("background-color", CARD2), ("color", TEXT3),
            ("font-size","11px"), ("text-transform","uppercase"),
            ("letter-spacing","0.06em"), ("border-color", BORDER)]}]))

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem;">
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
    <span style="font-size:1.6rem;">📈</span>
    <h1 style="color:{TEXT1}; font-size:1.75rem; font-weight:800;
               letter-spacing:-0.03em; margin:0; line-height:1;">
      Finance Dashboard
    </h1>
  </div>
  <p style="color:{TEXT3}; font-size:0.72rem; letter-spacing:0.14em;
             text-transform:uppercase; margin:0; font-weight:500;">
    Real Estate &nbsp;·&nbsp; Market Analysis &nbsp;·&nbsp; Powered by Obsidian
  </p>
</div>
<div style="height:1px; background:linear-gradient(90deg,{BLUE}44,{PURPLE}44,{TEAL}44,transparent);
            margin-bottom:1.5rem;"></div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_re, tab_mkt = st.tabs(["🏠  Real Estate", "📊  Market Analysis"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REAL ESTATE
# ══════════════════════════════════════════════════════════════════════════════
with tab_re:
    fm = load_latest("Real Estate", "real-estate-analysis")
    hist_re = load_history("Real Estate", "real-estate-analysis", "period")

    if not fm:
        st.error("No real-estate-analysis data found in Analysis/Real Estate/")
    else:
        period = fm.get("period", "")
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin:1rem 0 1.5rem;">
          <span style="color:{TEXT2}; font-size:0.72rem; letter-spacing:0.1em;
                       text-transform:uppercase; font-weight:600;">Period</span>
          <span style="background:{CARD2}; border:1px solid {BORDER2}; color:{TEXT2};
                       font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
                       padding:3px 10px; border-radius:20px; text-transform:uppercase;">
            {period}
          </span>
        </div>""", unsafe_allow_html=True)

        # KPIs
        c1, c2, c3, c4 = st.columns(4, gap="medium")
        with c1:
            st.markdown(kpi("red","🏦","30-yr Mortgage Rate",
                f"{fm.get('thirty_yr_rate','—')}%", "↑ Cash-flow pressure","neg"), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi("green","📊","10-yr Treasury Yield",
                f"{fm.get('ten_yr_yield','—')}%", "Risk-free benchmark","pos"), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi("amber","💱","USD / INR",
                f"₹{fm.get('usd_inr_rate','—')}", "↑ NRI remittance cost","neg"), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi("blue","🇮🇳","RBI Repo Rate",
                f"{fm.get('rbi_repo_rate','—')}%", "India benchmark","neu"), unsafe_allow_html=True)

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        # Prices & Yield
        section_header("Market Overview", BLUE)
        cities = ["Austin, TX", "Dallas, TX", "Hyderabad", "Guntur"]
        prices = [fm.get("austin_median_price",0), fm.get("dallas_median_price",0),
                  fm.get("hyd_price_usd",0), fm.get("guntur_price_usd",0)]
        yields_v = [fm.get("austin_rental_yield",0), fm.get("dallas_rental_yield",0),
                    fm.get("hyd_rental_yield",0), fm.get("guntur_rental_yield",0)]
        treasury = fm.get("ten_yr_yield", 4.42)

        fig_prices = go.Figure(go.Bar(
            x=cities, y=prices,
            marker=dict(color=[BLUE, BLUE2, AMBER, ORANGE], line=dict(width=0), cornerradius=6),
            text=[f"${p:,.0f}" for p in prices], textposition="outside",
            textfont=dict(color=TEXT1, size=11), cliponaxis=False,
        ))
        chart_layout(fig_prices, "Median Home Price (USD)", 340,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                tickformat="$,.0f", tickfont=dict(size=10, color=TEXT3)))

        fig_yield = go.Figure()
        fig_yield.add_trace(go.Bar(
            x=cities, y=yields_v,
            marker=dict(color=[GREEN if y > treasury else RED for y in yields_v],
                        line=dict(width=0), cornerradius=6),
            text=[f"{y:.2f}%" for y in yields_v], textposition="outside",
            textfont=dict(color=TEXT1, size=11), cliponaxis=False,
        ))
        fig_yield.add_hline(y=treasury, line_dash="dot", line_color=AMBER, line_width=1.5,
            annotation_text=f"Treasury {treasury}%",
            annotation_font=dict(color=AMBER, size=10), annotation_position="top right")
        chart_layout(fig_yield, "Gross Rental Yield vs Treasury Benchmark", 340,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                ticksuffix="%", tickfont=dict(size=10, color=TEXT3)))
        fig_yield.update_layout(showlegend=False)

        ca, cb = st.columns(2, gap="medium")
        chart_card(fig_prices, ca)
        chart_card(fig_yield, cb)

        # Cash Flow & Cap Rate
        section_header("Cash Flow & Benchmarks", RED)
        austin_rent    = fm.get("austin_rent_monthly", 0)
        austin_payment = fm.get("austin_monthly_payment", 0)
        austin_other   = max(0, abs(fm.get("austin_net_cashflow",0)) - austin_payment + austin_rent)
        dallas_rent    = fm.get("dallas_rent_monthly", 0)
        dallas_payment = fm.get("dallas_monthly_payment", 0)
        dallas_other   = max(0, abs(fm.get("dallas_net_cashflow",0)) - dallas_payment + dallas_rent)

        fig_cf = go.Figure()
        for label, rent, payment, other in [
            ("Austin, TX", austin_rent, austin_payment, austin_other),
            ("Dallas, TX", dallas_rent, dallas_payment, dallas_other),
        ]:
            show = label == "Austin, TX"
            fig_cf.add_trace(go.Bar(x=[label], y=[rent],
                marker=dict(color=GREEN, line=dict(width=0), cornerradius=4),
                name="Monthly Rent", legendgroup="rent", showlegend=show, width=0.4))
            fig_cf.add_trace(go.Bar(x=[label], y=[-payment],
                marker=dict(color="#e11d48", line=dict(width=0), cornerradius=4),
                name="Mortgage", legendgroup="mort", showlegend=show, width=0.4))
            if other > 0:
                fig_cf.add_trace(go.Bar(x=[label], y=[-other],
                    marker=dict(color="#9f1239", line=dict(width=0), cornerradius=4),
                    name="Tax / Insurance", legendgroup="other", showlegend=show, width=0.4))
        fig_cf.add_hline(y=0, line_color=BORDER2, line_width=1.5)
        chart_layout(fig_cf, "Monthly Cash Flow (US Markets)", 380,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                tickprefix="$", tickfont=dict(size=10, color=TEXT3)))
        fig_cf.update_layout(barmode="relative",
            legend=dict(orientation="h", y=-0.12, x=0, font=dict(size=11),
                        bgcolor="rgba(0,0,0,0)", borderwidth=0))

        benchmarks = {
            "Austin Cap Rate": fm.get("austin_cap_rate", 0),
            "Dallas Cap Rate": fm.get("dallas_cap_rate", 0),
            "S&P Dividend":    1.3,
            "2-yr Treasury":   fm.get("two_yr_yield", 3.83),
            "10-yr Treasury":  fm.get("ten_yr_yield", 4.42),
        }
        fig_cap = go.Figure(go.Bar(
            x=list(benchmarks.values()), y=list(benchmarks.keys()), orientation="h",
            marker=dict(color=[RED, AMBER, BLUE2, TEAL, GREEN], line=dict(width=0), cornerradius=5),
            text=[f"{v:.2f}%" for v in benchmarks.values()], textposition="outside",
            textfont=dict(color=TEXT1, size=11), cliponaxis=False,
        ))
        chart_layout(fig_cap, "Cap Rate vs Yield Benchmarks", 320,
                     margin=dict(t=48, b=16, l=140, r=60),
                     xaxis=dict(showgrid=False, zeroline=False, ticksuffix="%",
                                tickfont=dict(size=10, color=TEXT3)),
                     yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11, color=TEXT2)))

        cc, cd = st.columns(2, gap="medium")
        chart_card(fig_cf, cc)
        chart_card(fig_cap, cd)

        # Neighborhood Table
        section_header("Neighborhood Investment Scores", GREEN)
        neighborhoods = [
            ("Austin","North",5.5,6.0,6.0,9.0,6.5,"🟡 Hold"),
            ("Austin","South",5.9,3.5,5.5,9.0,5.6,"🟡 Selective"),
            ("Austin","East", 6.9,4.5,6.5,9.0,6.3,"🟢 Buy Dip"),
            ("Austin","West", 4.4,2.7,2.0,9.0,2.1,"🔴 Avoid"),
            ("Dallas","North",5.0,3.5,5.0,9.0,4.2,"🟡 Watch"),
            ("Dallas","South",10.0,7.5,9.5,9.0,9.6,"🟢 Strong Buy"),
            ("Dallas","East", 7.5,4.5,7.5,9.0,6.9,"🟢 Buy"),
            ("Dallas","West", 7.8,9.0,7.0,9.0,8.3,"🟢 Buy"),
            ("Hyderabad","West", 5.6,9.0,4.0,6.0,4.2,"🟢 IT Corridor"),
            ("Hyderabad","East", 5.0,5.5,7.0,6.0,4.2,"🟡 Selective"),
            ("Hyderabad","North",5.3,6.5,6.5,6.0,3.8,"🟡 Watch"),
            ("Hyderabad","South",4.4,4.5,7.5,5.0,3.3,"🟡 Hold"),
            ("Guntur","North", 3.1,10.0,7.5,4.0,2.5,"🟡 Amaravati Bet"),
            ("Guntur","South", 3.4,4.5,9.5,4.0,1.7,"🔴 Illiquid"),
            ("Guntur","East",  3.8,6.5,8.5,4.0,3.3,"🟡 Speculative"),
            ("Guntur","Centre",4.0,5.5,5.0,4.0,5.0,"🟡 Balanced"),
        ]
        cols_n = ["City","Area","Yield","Appreciation","Affordability","NRI-Friendly","Liquidity","Verdict"]
        df_n = pd.DataFrame(neighborhoods, columns=cols_n)
        df_n["Score"] = ((df_n["Yield"]+df_n["Appreciation"]+df_n["Affordability"]
                          +df_n["NRI-Friendly"]+df_n["Liquidity"])/5).round(1)

        def color_score(val):
            if not isinstance(val, float): return ""
            if val >= 7.5: return f"color:{GREEN};font-weight:600"
            if val >= 5.5: return f"color:{AMBER}"
            return f"color:{RED}"

        num_cols = ["Yield","Appreciation","Affordability","NRI-Friendly","Liquidity","Score"]
        st.markdown('<div class="chart-card" style="padding:0;">', unsafe_allow_html=True)
        st.dataframe(table_style(df_n).applymap(color_score, subset=num_cols)
                     .format({c:"{:.1f}" for c in num_cols}),
                     use_container_width=True, height=460)
        st.markdown('</div>', unsafe_allow_html=True)

        # Breakeven Table
        section_header("Breakeven by Down Payment", AMBER)
        r_mo = fm.get("thirty_yr_rate", 6.38) / 100 / 12
        n = 360
        def calc_pmt(price, dp):
            loan = price * (1 - dp)
            return loan * r_mo * (1+r_mo)**n / ((1+r_mo)**n - 1)

        rows_be = []
        for dp in [0.05, 0.10, 0.20, 0.25, 0.30]:
            for city, price, rent in [
                ("Austin", fm.get("austin_median_price",411280), fm.get("austin_rent_monthly",1875)),
                ("Dallas", fm.get("dallas_median_price",410000), fm.get("dallas_rent_monthly",1950)),
            ]:
                pay = calc_pmt(price, dp)
                net = rent - pay - price * 0.02 / 12
                rows_be.append({"City": city, "Down %": f"{int(dp*100)}%",
                    "Down ($)": f"${price*dp:,.0f}", "Payment/mo": f"${pay:,.0f}",
                    "Net CF/mo": net,
                    "Status": "✅ Positive" if net>0 else ("⚠️ Near" if net>-200 else "❌ Negative")})

        df_be = pd.DataFrame(rows_be)
        df_be["Net CF/mo"] = df_be["Net CF/mo"].apply(lambda x: f"${x:+,.0f}")

        def color_status(col):
            return [f"color:{GREEN};font-weight:600" if "✅" in v
                    else f"color:{AMBER}" if "⚠️" in v else f"color:{RED}" for v in col]

        st.markdown('<div class="chart-card" style="padding:0;">', unsafe_allow_html=True)
        st.dataframe(table_style(df_be).apply(color_status, subset=["Status"]),
                     use_container_width=True, height=340)
        st.markdown('</div>', unsafe_allow_html=True)

        # Radar Charts
        section_header("Neighborhood Quadrant Radar", PURPLE)
        radar_data = {
            "Austin 🇺🇸":    {"North":[5.5,6.0,6.0,9.0,6.5],"South":[5.9,3.5,5.5,9.0,5.6],
                              "East": [6.9,4.5,6.5,9.0,6.3],"West": [4.4,2.7,2.0,9.0,2.1]},
            "Dallas 🇺🇸":    {"North":[5.0,3.5,5.0,9.0,4.2],"South":[10.0,7.5,9.5,9.0,9.6],
                              "East": [7.5,4.5,7.5,9.0,6.9],"West": [7.8,9.0,7.0,9.0,8.3]},
            "Hyderabad 🇮🇳": {"West": [5.6,9.0,4.0,6.0,4.2],"East": [5.0,5.5,7.0,6.0,4.2],
                              "North":[5.3,6.5,6.5,6.0,3.8],"South":[4.4,4.5,7.5,5.0,3.3]},
            "Guntur 🇮🇳":    {"North":[3.1,10.0,7.5,4.0,2.5],"South":[3.4,4.5,9.5,4.0,1.7],
                              "East": [3.8,6.5,8.5,4.0,3.3],"Centre":[4.0,5.5,5.0,4.0,5.0]},
        }
        cats = ["Yield","Appreciation","Affordability","NRI-Friendly","Liquidity"]
        r_pal = [BLUE, GREEN, AMBER, RED]
        radar_cols = st.columns(4, gap="medium")
        for ci, (city, areas) in enumerate(radar_data.items()):
            fig_r = go.Figure()
            for i, (area, vals) in enumerate(areas.items()):
                rgb = tuple(int(r_pal[i].lstrip('#')[j:j+2], 16) for j in (0,2,4))
                fig_r.add_trace(go.Scatterpolar(
                    r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
                    fillcolor=f"rgba{rgb+(0.12,)}", line=dict(color=r_pal[i], width=2), name=area))
            fig_r.update_layout(
                template="plotly_dark",
                polar=dict(bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0,10], tickfont=dict(size=7,color=TEXT3),
                                   gridcolor=BORDER, linecolor=BORDER),
                    angularaxis=dict(tickfont=dict(size=9,color=TEXT2), gridcolor=BORDER, linecolor=BORDER)),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT2, family="Inter, sans-serif"),
                title=dict(text=city, font=dict(size=12, color=TEXT1), x=0.5, xanchor="center"),
                margin=dict(t=52,b=36,l=36,r=36), height=300,
                legend=dict(font=dict(size=9), x=0.5, xanchor="center", y=-0.12,
                            orientation="h", bgcolor="rgba(0,0,0,0)"),
            )
            with radar_cols[ci]:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

        # Historical RE Trends
        if len(hist_re) > 1 and "period" in hist_re.columns:
            section_header("Historical Trends", TEAL)
            hs = hist_re.sort_values("period")
            fig_hp = go.Figure()
            for col, label, color in [("austin_median_price","Austin",BLUE),
                                       ("dallas_median_price","Dallas",TEAL)]:
                if col in hs.columns:
                    fig_hp.add_trace(go.Scatter(x=hs["period"], y=hs[col], name=label,
                        line=dict(color=color, width=2), mode="lines+markers",
                        marker=dict(size=6, color=color)))
            chart_layout(fig_hp, "US Median Home Prices", 300)
            fig_hr = go.Figure()
            for col, label, color in [("thirty_yr_rate","30-yr Rate",RED),
                                       ("ten_yr_yield","10-yr Yield",AMBER)]:
                if col in hs.columns:
                    fig_hr.add_trace(go.Scatter(x=hs["period"], y=hs[col], name=label,
                        line=dict(color=color, width=2), mode="lines+markers",
                        marker=dict(size=6, color=color)))
            chart_layout(fig_hr, "Rate Trends", 300)
            h1, h2 = st.columns(2, gap="medium")
            chart_card(fig_hp, h1)
            chart_card(fig_hr, h2)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MARKET ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_mkt:
    mkt = load_latest("Market", "daily-market-analysis")
    hist_mkt = load_history("Market", "daily-market-analysis", "date")

    if not mkt:
        st.error("No daily-market-analysis data found in Analysis/Market/")
    else:
        mkt_date = str(mkt.get("date", ""))
        sentiment = mkt.get("sentiment", "neutral").lower()
        badge_cls = f"badge-{sentiment}" if sentiment in ("bearish","bullish") else "badge-neutral"
        sentiment_icon = "🔴" if sentiment == "bearish" else ("🟢" if sentiment == "bullish" else "🟡")

        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin:1rem 0 1.5rem;">
          <span style="color:{TEXT2}; font-size:0.72rem; letter-spacing:0.1em;
                       text-transform:uppercase; font-weight:600;">As of</span>
          <span style="background:{CARD2}; border:1px solid {BORDER2}; color:{TEXT2};
                       font-size:0.7rem; font-weight:700; padding:3px 10px;
                       border-radius:20px; letter-spacing:0.1em;">{mkt_date}</span>
          <span class="badge {badge_cls}">{sentiment_icon} {sentiment.title()}</span>
        </div>""", unsafe_allow_html=True)

        # ── KPI tiles ─────────────────────────────────────────────────────────
        section_header("Global Snapshot", BLUE)
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        with k1:
            st.markdown(kpi("blue","🇺🇸","S&P 500 (SPY)",
                f"{mkt.get('sp500_close','—')}",
                "US Large Cap","neu"), unsafe_allow_html=True)
        with k2:
            st.markdown(kpi("purple","💻","Nasdaq (QQQ)",
                f"{mkt.get('nasdaq_close','—')}",
                "Tech-heavy index","neu"), unsafe_allow_html=True)
        with k3:
            st.markdown(kpi("teal","🇮🇳","Nifty 50",
                f"{mkt.get('nifty_close','—'):,.0f}" if isinstance(mkt.get('nifty_close'), (int,float)) else "—",
                "India benchmark","neu"), unsafe_allow_html=True)
        with k4:
            st.markdown(kpi("amber","💱","USD / INR",
                f"₹{mkt.get('usd_inr','—')}",
                "FX rate","neu"), unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        k5, k6, k7, k8 = st.columns(4, gap="medium")
        with k5:
            btc = mkt.get('btc_price', 0)
            st.markdown(kpi("orange","₿","Bitcoin (BTC)",
                f"${btc:,.0f}" if btc else "—",
                f"Dominance {mkt.get('btc_dominance','—')}%","neu"), unsafe_allow_html=True)
        with k6:
            eth = mkt.get('eth_price', 0)
            st.markdown(kpi("purple","⬡","Ethereum (ETH)",
                f"${eth:,.0f}" if eth else "—",
                "Layer-1 benchmark","neu"), unsafe_allow_html=True)
        with k7:
            fg = mkt.get('crypto_fear_greed', 0)
            fg_cls = "neg" if fg < 30 else ("pos" if fg > 60 else "neu")
            fg_label = "Extreme Fear" if fg < 25 else ("Fear" if fg < 45 else ("Greed" if fg > 55 else "Neutral"))
            st.markdown(kpi("red","😱","Fear & Greed Index",
                str(fg), fg_label, fg_cls), unsafe_allow_html=True)
        with k8:
            gold = mkt.get('gold_price', 0)
            st.markdown(kpi("amber","🏅","Gold (GLD / Spot)",
                f"${gold:,.2f}" if isinstance(gold, float) else f"${gold:,.0f}" if gold else "—",
                "Safe haven","neu"), unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── US vs India comparison ─────────────────────────────────────────────
        section_header("US vs India Markets", TEAL)

        us_data   = {"S&P 500 (SPY)": mkt.get("sp500_close",0), "Nasdaq (QQQ)": mkt.get("nasdaq_close",0)}
        india_data= {"Nifty 50": mkt.get("nifty_close",0), "Sensex": mkt.get("sensex_close",0)}

        fig_us = go.Figure()
        fig_us.add_trace(go.Bar(
            x=list(us_data.keys()), y=list(us_data.values()),
            marker=dict(color=[BLUE, PURPLE], line=dict(width=0), cornerradius=6),
            text=[f"{v:,.2f}" if isinstance(v,float) else f"{v:,}" for v in us_data.values()],
            textposition="outside", textfont=dict(color=TEXT1, size=11), cliponaxis=False,
        ))
        chart_layout(fig_us, "US Markets", 300,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                tickfont=dict(size=10, color=TEXT3)))

        fig_india = go.Figure()
        fig_india.add_trace(go.Bar(
            x=list(india_data.keys()), y=list(india_data.values()),
            marker=dict(color=[TEAL, "#22d3ee"], line=dict(width=0), cornerradius=6),
            text=[f"{v:,.0f}" for v in india_data.values()],
            textposition="outside", textfont=dict(color=TEXT1, size=11), cliponaxis=False,
        ))
        chart_layout(fig_india, "India Markets", 300,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                tickfont=dict(size=10, color=TEXT3)))

        ma, mb = st.columns(2, gap="medium")
        chart_card(fig_us, ma)
        chart_card(fig_india, mb)

        # ── Crypto section ─────────────────────────────────────────────────────
        section_header("Crypto", ORANGE)

        fig_crypto = go.Figure()
        crypto_items = [
            ("BTC", mkt.get("btc_price",0), ORANGE),
            ("ETH", mkt.get("eth_price",0), PURPLE),
        ]
        fig_crypto.add_trace(go.Bar(
            x=[c[0] for c in crypto_items],
            y=[c[1] for c in crypto_items],
            marker=dict(color=[c[2] for c in crypto_items], line=dict(width=0), cornerradius=6),
            text=[f"${c[1]:,.0f}" for c in crypto_items],
            textposition="outside", textfont=dict(color=TEXT1, size=12), cliponaxis=False,
        ))
        chart_layout(fig_crypto, "Crypto Prices (USD)", 300,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                tickprefix="$", tickfont=dict(size=10, color=TEXT3)))

        # Fear & Greed gauge
        fg_val = mkt.get("crypto_fear_greed", 50)
        fig_fg = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fg_val,
            domain={"x": [0,1], "y": [0,1]},
            title={"text": "Fear & Greed Index", "font": {"color": TEXT2, "size": 13}},
            number={"font": {"color": TEXT1, "size": 48}},
            gauge={
                "axis": {"range": [0,100], "tickfont": {"color": TEXT3, "size": 9},
                         "tickcolor": TEXT3, "linecolor": BORDER},
                "bar": {"color": AMBER if 30 <= fg_val <= 60 else (GREEN if fg_val > 60 else RED),
                        "thickness": 0.25},
                "bgcolor": CARD2,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [0,25],  "color": "rgba(244,63,94,0.15)"},
                    {"range": [25,45], "color": "rgba(251,146,60,0.1)"},
                    {"range": [45,55], "color": "rgba(245,158,11,0.1)"},
                    {"range": [55,75], "color": "rgba(45,212,191,0.1)"},
                    {"range": [75,100],"color": "rgba(16,185,129,0.15)"},
                ],
                "threshold": {"line": {"color": TEXT1, "width": 2}, "thickness": 0.75, "value": fg_val},
            }
        ))
        fig_fg.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT2, family="Inter"),
            height=300, margin=dict(t=40, b=20, l=30, r=30),
        )

        mc, md = st.columns(2, gap="medium")
        chart_card(fig_crypto, mc)
        with md:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(fig_fg, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Rates ──────────────────────────────────────────────────────────────
        section_header("Rates & Yields", GREEN)

        rates = {
            "10-yr Treasury":  mkt.get("ten_yr_yield", 0),
            "BTC Dominance %": mkt.get("btc_dominance", 0),
        }
        fig_rates = go.Figure(go.Bar(
            x=list(rates.keys()), y=list(rates.values()),
            marker=dict(color=[GREEN, ORANGE], line=dict(width=0), cornerradius=6),
            text=[f"{v:.2f}%" for v in rates.values()],
            textposition="outside", textfont=dict(color=TEXT1, size=12), cliponaxis=False,
        ))
        chart_layout(fig_rates, "Key Rates & Dominance", 280,
                     yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                ticksuffix="%", tickfont=dict(size=10, color=TEXT3)))

        # ── Historical market trends ───────────────────────────────────────────
        if len(hist_mkt) > 1:
            section_header("Historical Trends", TEAL)
            hm = hist_mkt.sort_values("date").copy()
            hm["date"] = hm["date"].astype(str)

            me1, me2 = st.columns(2, gap="medium")

            fig_mh1 = go.Figure()
            for col, label, color in [("sp500_close","S&P 500",BLUE),
                                       ("nasdaq_close","Nasdaq",PURPLE)]:
                if col in hm.columns:
                    fig_mh1.add_trace(go.Scatter(x=hm["date"], y=pd.to_numeric(hm[col], errors="coerce"),
                        name=label, line=dict(color=color, width=2),
                        mode="lines+markers", marker=dict(size=7, color=color)))
            chart_layout(fig_mh1, "US Markets Over Time", 300)

            fig_mh2 = go.Figure()
            for col, label, color in [("btc_price","BTC",ORANGE),("eth_price","ETH",PURPLE)]:
                if col in hm.columns:
                    fig_mh2.add_trace(go.Scatter(x=hm["date"], y=pd.to_numeric(hm[col], errors="coerce"),
                        name=label, line=dict(color=color, width=2),
                        mode="lines+markers", marker=dict(size=7, color=color)))
            chart_layout(fig_mh2, "Crypto Over Time", 300)

            fig_mh3 = go.Figure()
            if "crypto_fear_greed" in hm.columns:
                fg_vals = pd.to_numeric(hm["crypto_fear_greed"], errors="coerce")
                fig_mh3.add_trace(go.Scatter(x=hm["date"], y=fg_vals,
                    name="Fear & Greed", line=dict(color=RED, width=2),
                    mode="lines+markers", marker=dict(size=7, color=RED),
                    fill="tozeroy", fillcolor="rgba(244,63,94,0.08)"))
            fig_mh3.add_hline(y=50, line_dash="dot", line_color=BORDER2, line_width=1)
            chart_layout(fig_mh3, "Fear & Greed Over Time", 280,
                         yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False,
                                    range=[0,100], tickfont=dict(size=10, color=TEXT3)))

            chart_card(fig_mh1, me1)
            chart_card(fig_mh2, me2)
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(fig_mh3, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(fig_rates, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem; padding-top:1.5rem;
            border-top:1px solid {BORDER};
            display:flex; justify-content:space-between; align-items:center;">
  <span style="color:{TEXT3}; font-size:0.7rem; letter-spacing:0.06em;">
    DATA &nbsp;·&nbsp; Analysis/Real Estate/ &nbsp;·&nbsp; Analysis/Market/
  </span>
  <span style="color:{TEXT3}; font-size:0.7rem; letter-spacing:0.06em;">
    Streamlit + Plotly
  </span>
</div>
""", unsafe_allow_html=True)
