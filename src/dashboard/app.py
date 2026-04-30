"""
Dashboard de rendimiento ANTIGRAVITY.
Ejecutar con: streamlit run src/dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.etl.pipeline import run_pipeline

# ------------------------------------------------------------------
# Configuración de página
# ------------------------------------------------------------------

st.set_page_config(
    page_title="ANTIGRAVITY | Dashboard",
    page_icon="https://cdn-icons-png.flaticon.com/512/3135/3135706.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #a3e635; }

/* ── Main background ── */
.stApp { background: #000000 !important; }
.main .block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #000000 !important;
    border-right: 1px solid #1a1a1a !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {
    color: #4b5563 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: .8px !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #0a0a0a !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 12px !important;
    color: #fff !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 20px !important;
    padding: 24px 28px !important;
    transition: border-color .2s ease !important;
}
[data-testid="metric-container"]:hover {
    border-color: #a3e635 !important;
}
[data-testid="stMetricLabel"] p {
    color: #4b5563 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-weight: 800 !important;
    font-size: 28px !important;
    letter-spacing: -1px !important;
}
[data-testid="stMetricDelta"] {
    color: #a3e635 !important;
    font-weight: 600 !important;
}

/* ── Section headers ── */
.dash-title {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 2rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -1.5px;
    margin-bottom: 4px;
}
.dash-title i { color: #a3e635; font-size: 1.8rem; }

.dash-header {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #9ca3af;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 16px 0 8px 0;
}
.dash-header i { color: #a3e635; font-size: 13px; width: 16px; text-align: center; }

.dash-header-inner {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #9ca3af;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 12px 0 6px 0;
}
.dash-header-inner i { color: #3b82f6; font-size: 12px; width: 14px; text-align: center; }

/* ── Dividers ── */
hr { border-color: #111111 !important; margin: 16px 0 !important; }

/* ── Buttons ── */
.stButton > button {
    background: #0a0a0a !important;
    color: #a3e635 !important;
    border: 1px solid #a3e635 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    letter-spacing: .5px !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    background: #a3e635 !important;
    color: #000 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 20px !important;
}
[data-testid="stExpander"] summary {
    color: #9ca3af !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1a1a1a !important;
    border-radius: 16px !important;
    overflow: hidden !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: #0a0a0a !important;
    border-left: 3px solid #a3e635 !important;
    border-radius: 12px !important;
    color: #9ca3af !important;
}

/* ── Caption ── */
[data-testid="stCaptionContainer"] p {
    color: #374151 !important;
    font-size: 12px !important;
    letter-spacing: .5px !important;
}

/* ── Date input ── */
[data-testid="stDateInput"] input {
    background: #0a0a0a !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 10px !important;
    color: #fff !important;
}

/* ── Status badge ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Carga de datos con caché (refresca cada 15 minutos)
# ------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner="Actualizando datos...")
def load_data(days_back: int, ad_account_id: str | None = None):
    result = run_pipeline(days_back=days_back, ad_account_id=ad_account_id)
    return result


# ------------------------------------------------------------------
# Sidebar — Filtros
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 10px 0;">
        <div style="font-size:20px;font-weight:900;color:#ffffff;letter-spacing:-1px;">
            <i class="fa-solid fa-arrow-up" style="color:#a3e635;margin-right:6px;"></i>ANTIGRAVITY
        </div>
        <div style="font-size:10px;color:#374151;margin-top:3px;letter-spacing:2px;font-weight:600;">
            PERFORMANCE DASHBOARD
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Selector de cuenta publicitaria
    @st.cache_data(ttl=3600)
    def fetch_accounts():
        from src.connectors.meta_ads_client import MetaAdsClient
        from facebook_business.api import FacebookAdsApi
        from dotenv import load_dotenv
        import os
        load_dotenv()
        FacebookAdsApi.init(access_token=os.getenv("META_ACCESS_TOKEN"))
        return MetaAdsClient.get_all_accounts()

    accounts     = fetch_accounts()
    account_map  = {a["name"]: a["id"] for a in accounts}
    account_names = list(account_map.keys())

    selected_account_name = st.selectbox("Cuenta publicitaria", account_names)
    selected_account_id   = account_map[selected_account_name]

    days_back = st.selectbox(
        "Período", [1, 7, 14, 30, 60], index=1,
        format_func=lambda x: "Hoy" if x == 1 else f"Últimos {x} días"
    )

    data = load_data(days_back, selected_account_id)
    fact = data["fact"].copy()

    if fact.empty or "campaign_name" not in fact.columns:
        st.markdown('<div class="dash-title"><i class="fa-solid fa-rocket"></i>ANTIGRAVITY</div>', unsafe_allow_html=True)
        st.warning(f"La cuenta **{selected_account_name}** no tiene datos de Meta Ads para los últimos {days_back} días. Prueba con otro período o selecciona otra cuenta.")
        st.stop()

    st.markdown("### Filtros")

    # Filtro por estado de entrega
    STATUS_LABELS = {
        "ACTIVE":   "Activa",
        "PAUSED":   "Pausada",
        "DELETED":  "Eliminada",
        "ARCHIVED": "Archivada",
        "UNKNOWN":  "Desconocido",
    }
    if "campaign_effective_status" in fact.columns:
        raw_statuses   = fact["campaign_effective_status"].dropna().unique().tolist()
        status_options = ["Todos"] + [STATUS_LABELS.get(s, s) for s in sorted(raw_statuses)]
        selected_status_label = st.selectbox("Estado de entrega", status_options)
        selected_status = next((k for k, v in STATUS_LABELS.items() if v == selected_status_label), None)
    else:
        selected_status = None

    # Mapa de códigos ISO → nombres de países (principales mercados LATAM + otros)
    COUNTRY_NAMES = {
        "AR": "Argentina", "BO": "Bolivia", "BR": "Brasil", "CL": "Chile",
        "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "DO": "República Dominicana",
        "EC": "Ecuador", "SV": "El Salvador", "GT": "Guatemala", "HN": "Honduras",
        "MX": "México", "NI": "Nicaragua", "PA": "Panamá", "PY": "Paraguay",
        "PE": "Perú", "PR": "Puerto Rico", "UY": "Uruguay", "VE": "Venezuela",
        "US": "Estados Unidos", "ES": "España", "UNKNOWN": "Desconocido",
    }

    # Filtro por país (solo si el campo existe en los datos)
    if "country_code" in fact.columns:
        raw_codes = fact["country_code"].dropna().unique().tolist()
        country_options = ["Todos"] + sorted(
            [COUNTRY_NAMES.get(c, c) for c in raw_codes],
            key=lambda x: x
        )
        selected_country_label = st.selectbox("País", country_options)
        selected_country = next(
            (code for code, name in COUNTRY_NAMES.items() if name == selected_country_label),
            selected_country_label if selected_country_label != "Todos" else None,
        )
    else:
        selected_country = None

    # Filtro por campaña
    campaigns = ["Todas"] + sorted(fact["campaign_name"].dropna().unique().tolist())
    selected_campaign = st.selectbox("Campaña", campaigns)

    # Filtro por conjunto de anuncios (cascada: depende de campaña)
    fact_for_adset = fact if selected_campaign == "Todas" else fact[fact["campaign_name"] == selected_campaign]
    adsets = ["Todos"] + sorted(fact_for_adset["adset_name"].dropna().unique().tolist())
    selected_adset = st.selectbox("Conjunto de anuncios", adsets)

    # Filtro por anuncio (cascada: depende de campaña + conjunto)
    fact_for_ad = fact_for_adset if selected_adset == "Todos" else fact_for_adset[fact_for_adset["adset_name"] == selected_adset]
    ads = ["Todos"] + sorted(fact_for_ad["ad_name"].dropna().unique().tolist())
    selected_ad = st.selectbox("Anuncio", ads)

    # Filtro por chip
    chips = ["Todos"] + sorted(fact["chip"].dropna().unique().tolist())
    selected_chip = st.selectbox("Chip (SIM)", chips)

    # Filtro por fecha
    if not fact.empty and "date" in fact.columns:
        min_date = fact["date"].min().date()
        max_date = fact["date"].max().date()
        date_range = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    st.markdown("---")
    if st.button("Refrescar datos"):
        st.cache_data.clear()
        st.rerun()

# ------------------------------------------------------------------
# Aplicar filtros
# ------------------------------------------------------------------

if selected_status and "campaign_effective_status" in fact.columns:
    fact = fact[fact["campaign_effective_status"] == selected_status]

if selected_country and "country_code" in fact.columns:
    fact = fact[fact["country_code"] == selected_country]

if selected_campaign != "Todas":
    fact = fact[fact["campaign_name"] == selected_campaign]

if selected_adset != "Todos":
    fact = fact[fact["adset_name"] == selected_adset]

if selected_ad != "Todos":
    fact = fact[fact["ad_name"] == selected_ad]

if selected_chip != "Todos":
    fact = fact[fact["chip"] == selected_chip]

if len(date_range) == 2:
    fact = fact[
        (fact["date"] >= pd.Timestamp(date_range[0])) &
        (fact["date"] <= pd.Timestamp(date_range[1]))
    ]

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------

if fact.empty:
    st.markdown('<div class="dash-title"><i class="fa-solid fa-rocket"></i>ANTIGRAVITY — Performance Dashboard</div>', unsafe_allow_html=True)
    st.warning(f"La cuenta **{selected_account_name}** no tiene datos de Meta Ads para los últimos {days_back} días. Prueba con otro período o selecciona otra cuenta.")
    st.stop()

st.markdown('<div class="dash-title"><i class="fa-solid fa-rocket"></i>ANTIGRAVITY — Performance Dashboard</div>', unsafe_allow_html=True)
st.caption(f"Datos de los últimos {days_back} días · {len(fact)} registros activos")
st.markdown("---")

# ------------------------------------------------------------------
# KPI Cards
# ------------------------------------------------------------------

total_spend        = fact["spend"].sum()
total_sales_value  = fact["sales_value"].sum()
total_sales_count  = int(fact["sales_count"].sum())
total_convs        = int(fact["conversations_started"].sum())
avg_roas           = fact["roas"].mean() if not fact.empty else 0
avg_conv_rate      = fact["conversion_rate"].mean() if not fact.empty else 0
cost_per_sale      = total_spend / total_sales_count if total_sales_count > 0 else 0
cost_per_conv      = total_spend / total_convs if total_convs > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Spend Total",        f"${total_spend:,.0f}")
col2.metric("Ventas (valor)",     f"${total_sales_value:,.0f}")
col3.metric("Ventas (cantidad)",  f"{total_sales_count:,}")
col4.metric("Conversaciones",     f"{total_convs:,}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("ROAS",               f"{avg_roas:.2f}x")
col6.metric("Tasa de Conversión", f"{avg_conv_rate:.1%}")
col7.metric("Costo por Venta",    f"${cost_per_sale:,.0f}")
col8.metric("Costo por Conv.",    f"${cost_per_conv:,.0f}")

st.markdown("---")

# ------------------------------------------------------------------
# Meta de Facturación
# ------------------------------------------------------------------

# Cargar config guardada desde Google Sheets (una vez por sesión)
if "config_loaded" not in st.session_state:
    # Defaults
    st.session_state.setdefault("meta_tipo", "Esta semana")
    st.session_state.setdefault("meta_valor", 10000)
    try:
        from src.connectors.sheets_client import SheetsClient as _SC
        _cfg = _SC().get_config()
        if "meta_tipo" in _cfg:
            st.session_state["meta_tipo"] = _cfg["meta_tipo"]
        if "meta_valor" in _cfg:
            st.session_state["meta_valor"] = int(float(_cfg["meta_valor"]))
    except Exception:
        pass
    st.session_state["config_loaded"] = True

def _save_meta_config():
    try:
        from src.connectors.sheets_client import SheetsClient as _SC
        _c = _SC()
        _c.set_config("meta_tipo", st.session_state.get("meta_tipo", "Esta semana"))
        _c.set_config("meta_valor", st.session_state.get("meta_valor", 10000))
        st.toast("Meta guardada", icon="✅")
    except Exception as e:
        st.toast(f"Error al guardar: {e}", icon="❌")

st.markdown('<div class="dash-header"><i class="fa-solid fa-bullseye"></i>Meta de Facturación</div>', unsafe_allow_html=True)

cfg1, cfg2, cfg3 = st.columns([1, 1, 1])
with cfg1:
    meta_tipo = st.selectbox(
        "Período", ["Hoy", "Esta semana", "Este mes", "Rango personalizado"],
        key="meta_tipo", on_change=_save_meta_config,
    )
with cfg2:
    meta_valor = st.number_input(
        "Meta de ventas ($)", min_value=0, step=500,
        key="meta_valor", on_change=_save_meta_config,
    )
with cfg3:
    meta_rango = None
    if meta_tipo == "Rango personalizado":
        from datetime import date, timedelta
        _default_end = date.today()
        _default_start = _default_end - timedelta(days=6)
        meta_rango = st.date_input(
            "Rango",
            value=(_default_start, _default_end),
            key="meta_rango_dates",
        )

# Calcular ventas del período elegido sobre datos crudos (sin filtros del dashboard)
_sales_raw = data["sales_raw"].copy()
_sales_raw["_date"] = pd.to_datetime(_sales_raw["timestamp_venta"]).dt.normalize()
_today = pd.Timestamp.now().normalize()

if meta_tipo == "Hoy":
    _mask = _sales_raw["_date"] == _today
elif meta_tipo == "Esta semana":
    _start = _today - pd.Timedelta(days=_today.dayofweek)
    _mask = _sales_raw["_date"] >= _start
elif meta_tipo == "Este mes":
    _mask = (_sales_raw["_date"].dt.year == _today.year) & (_sales_raw["_date"].dt.month == _today.month)
elif meta_tipo == "Rango personalizado" and isinstance(meta_rango, (list, tuple)) and len(meta_rango) == 2:
    _mask = (_sales_raw["_date"] >= pd.Timestamp(meta_rango[0])) & (_sales_raw["_date"] <= pd.Timestamp(meta_rango[1]))
else:
    _mask = pd.Series([True] * len(_sales_raw), index=_sales_raw.index)

_ventas_periodo = float(_sales_raw[_mask]["valor_venta"].sum()) if not _sales_raw[_mask].empty else 0.0
_n_ventas       = int(_sales_raw[_mask]["valor_venta"].count())
_pct            = min(_ventas_periodo / meta_valor * 100, 100) if meta_valor > 0 else 0
_restante       = max(meta_valor - _ventas_periodo, 0)
_color_ring     = "#a3e635" if _pct >= 60 else "#3b82f6" if _pct >= 30 else "#f97316"

gauge_col, stats_col = st.columns([1, 1])

with gauge_col:
    _fig_g = go.Figure()
    _fig_g.add_trace(go.Pie(
        values=[100], hole=0.72,
        marker=dict(colors=["#111111"], line=dict(width=0)),
        textinfo="none", hoverinfo="none", showlegend=False,
    ))
    _fig_g.add_trace(go.Pie(
        values=[max(_pct, 0.5), 100 - max(_pct, 0.5)],
        hole=0.72,
        marker=dict(colors=[_color_ring, "rgba(0,0,0,0)"], line=dict(width=0)),
        textinfo="none", hoverinfo="none", showlegend=False,
        direction="clockwise", rotation=90,
    ))
    _fig_g.update_layout(
        annotations=[
            dict(text=f"<b>{_pct:.0f}%</b>", x=0.5, y=0.60,
                 font=dict(size=48, color="#ffffff", family="Inter"), showarrow=False),
            dict(text="Avance", x=0.5, y=0.44,
                 font=dict(size=13, color="#4b5563", family="Inter"), showarrow=False),
            dict(text=f"<b>${_ventas_periodo:,.0f}</b>", x=0.5, y=0.30,
                 font=dict(size=16, color=_color_ring, family="Inter"), showarrow=False),
            dict(text=f"{_n_ventas} ventas", x=0.5, y=0.17,
                 font=dict(size=11, color="#374151", family="Inter"), showarrow=False),
        ],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        height=290, showlegend=False,
    )
    st.plotly_chart(_fig_g, use_container_width=True)

with stats_col:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.metric("Meta total",   f"${meta_valor:,.0f}")
    st.metric("Facturado",    f"${_ventas_periodo:,.0f}")
    st.metric("Restante",     f"${_restante:,.0f}")
    st.metric("Transacciones", f"{_n_ventas:,}")

st.markdown("---")

# ------------------------------------------------------------------
# Fila 1: ROAS en el tiempo + Ventas vs Spend
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<div class="dash-header"><i class="fa-solid fa-chart-line"></i>ROAS diario</div>', unsafe_allow_html=True)
    if not fact.empty:
        roas_daily = (
            fact.groupby("date")
            .apply(lambda x: x["sales_value"].sum() / x["spend"].sum() if x["spend"].sum() > 0 else 0)
            .reset_index(name="roas")
        )
        fig_roas = px.area(
            roas_daily, x="date", y="roas",
            color_discrete_sequence=["#a3e635"],
            labels={"roas": "ROAS", "date": "Fecha"},
        )
        fig_roas.update_traces(
            fill="tozeroy",
            fillcolor="rgba(163,230,53,0.08)",
            line=dict(color="#a3e635", width=2),
        )
        fig_roas.add_hline(y=1, line_dash="dot", line_color="#374151", annotation_text="Break-even",
                           annotation_font_color="#4b5563")
        fig_roas.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#6b7280", height=300,
            xaxis=dict(gridcolor="#111", showgrid=True),
            yaxis=dict(gridcolor="#111", showgrid=True),
        )
        st.plotly_chart(fig_roas, use_container_width=True)

with col_right:
    st.markdown('<div class="dash-header"><i class="fa-solid fa-dollar-sign"></i>Spend vs Ventas diario</div>', unsafe_allow_html=True)
    if not fact.empty:
        daily = fact.groupby("date").agg(
            spend=("spend", "sum"),
            sales_value=("sales_value", "sum"),
        ).reset_index()
        fig_bar = go.Figure()
        fig_bar.add_bar(x=daily["date"], y=daily["spend"],
                        name="Spend", marker=dict(color="#3b82f6", opacity=0.85))
        fig_bar.add_bar(x=daily["date"], y=daily["sales_value"],
                        name="Ventas", marker=dict(color="#a3e635", opacity=0.95))
        fig_bar.update_layout(
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#6b7280", height=300,
            legend=dict(orientation="h", y=1.1, font=dict(color="#6b7280")),
            xaxis=dict(gridcolor="#111"), yaxis=dict(gridcolor="#111"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------------
# Fila 2: Top Ads por ROAS + Rendimiento por Chip
# ------------------------------------------------------------------

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.markdown('<div class="dash-header"><i class="fa-solid fa-trophy"></i>Top 10 Ads por ROAS</div>', unsafe_allow_html=True)
    if not fact.empty:
        top_ads = (
            fact.groupby("ad_name")
            .apply(lambda x: pd.Series({
                "spend":       x["spend"].sum(),
                "sales_value": x["sales_value"].sum(),
                "roas":        x["sales_value"].sum() / x["spend"].sum() if x["spend"].sum() > 0 else 0,
            }))
            .reset_index()
            .sort_values("roas", ascending=False)
            .head(10)
        )
        fig_top = px.bar(
            top_ads, x="roas", y="ad_name", orientation="h",
            color="roas", color_continuous_scale=[[0,"#14532d"],[1,"#a3e635"]],
            labels={"roas": "ROAS", "ad_name": "Anuncio"},
            text=top_ads["roas"].apply(lambda x: f"{x:.1f}x"),
        )
        fig_top.update_traces(textfont_color="#000", textfont_size=11, textfont_family="Inter")
        fig_top.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#6b7280", height=350, showlegend=False,
            coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending", "tickfont": {"color": "#6b7280", "size": 11}},
            xaxis=dict(gridcolor="#111"),
        )
        st.plotly_chart(fig_top, use_container_width=True)

with col_right2:
    st.markdown('<div class="dash-header"><i class="fa-solid fa-mobile-screen-button"></i>Rendimiento por Chip</div>', unsafe_allow_html=True)
    if not fact.empty:
        by_chip = (
            fact.groupby("chip")
            .agg(
                ventas=("sales_count", "sum"),
                valor=("sales_value", "sum"),
                conversion=("conversion_rate", "mean"),
            )
            .reset_index()
            .sort_values("ventas", ascending=False)
        )
        fig_chip = px.scatter(
            by_chip, x="ventas", y="conversion",
            size="valor", color="chip",
            hover_data=["chip", "ventas", "valor"],
            labels={"ventas": "Ventas", "conversion": "Tasa de Conversión", "valor": "Valor"},
        )
        fig_chip.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#6b7280", height=350, showlegend=True,
            legend=dict(font=dict(color="#6b7280", size=11)),
            xaxis=dict(gridcolor="#111"), yaxis=dict(gridcolor="#111"),
        )
        st.plotly_chart(fig_chip, use_container_width=True)

# ------------------------------------------------------------------
# Fila 3: Ventas por Chip en el tiempo
# ------------------------------------------------------------------

st.markdown('<div class="dash-header"><i class="fa-solid fa-sim-card"></i>Ventas por Chip</div>', unsafe_allow_html=True)

if not fact.empty and "chip" in fact.columns:
    _cp1, _cp2 = st.columns([1, 2])
    with _cp1:
        _chip_period = st.selectbox(
            "Período", ["Hoy", "Esta semana", "Este mes", "Rango personalizado"],
            key="chip_period"
        )
    with _cp2:
        _chip_range = None
        if _chip_period == "Rango personalizado":
            from datetime import date as _d, timedelta as _td
            _chip_range = st.date_input(
                "Rango", value=(_d.today() - _td(days=6), _d.today()), key="chip_rng"
            )

    # Usar sales_raw para tener datos en tiempo real (incluyendo hoy)
    _cdf = data["sales_raw"][["timestamp_venta", "chip"]].copy()
    _cdf["chip"] = _cdf["chip"].astype(str)
    _cdf["_date"] = pd.to_datetime(_cdf["timestamp_venta"]).dt.normalize()
    _ct = pd.Timestamp.now().normalize()

    if _chip_period == "Hoy":
        _cdf = _cdf[_cdf["_date"] == _ct]
    elif _chip_period == "Esta semana":
        _cdf = _cdf[_cdf["_date"] >= _ct - pd.Timedelta(days=_ct.dayofweek)]
    elif _chip_period == "Este mes":
        _cdf = _cdf[(_cdf["_date"].dt.year == _ct.year) & (_cdf["_date"].dt.month == _ct.month)]
    elif _chip_period == "Rango personalizado" and isinstance(_chip_range, (list, tuple)) and len(_chip_range) == 2:
        _cdf = _cdf[(_cdf["_date"] >= pd.Timestamp(_chip_range[0])) & (_cdf["_date"] <= pd.Timestamp(_chip_range[1]))]

    _by_chip = (
        _cdf.groupby("chip")
        .size()
        .reset_index(name="sales_count")
        .sort_values("sales_count", ascending=False)
    )

    if not _by_chip.empty:
        # Mostrar últimos 8 dígitos del chip para que quepa en el eje X
        _by_chip["chip_label"] = _by_chip["chip"].apply(
            lambda x: f"…{str(x)[-8:]}" if len(str(x)) > 8 else str(x)
        )

        fig_chip_bar = go.Figure()
        fig_chip_bar.add_trace(go.Bar(
            x=_by_chip["chip_label"],
            y=_by_chip["sales_count"],
            text=_by_chip["sales_count"].astype(int),
            textposition="outside",
            textfont=dict(color="#ffffff", size=14, family="Inter"),
            hovertext=_by_chip["chip"],
            hovertemplate="<b>%{hovertext}</b><br>Ventas: %{y}<extra></extra>",
            marker=dict(
                color=_by_chip["sales_count"],
                colorscale=[[0, "#1a4a1a"], [1, "#a3e635"]],
                line=dict(width=0),
            ),
        ))
        fig_chip_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#6b7280", height=420,
            bargap=0.15,
            margin=dict(t=50, b=100),
            xaxis=dict(
                type="category",
                gridcolor="rgba(0,0,0,0)",
                tickfont=dict(color="#9ca3af", size=12, family="Inter"),
                tickangle=0,
            ),
            yaxis=dict(gridcolor="#111", showgrid=True),
        )
        st.plotly_chart(fig_chip_bar, use_container_width=True)

# ------------------------------------------------------------------
# Fila 4: Desglose por Campaña
# ------------------------------------------------------------------

st.markdown('<div class="dash-header"><i class="fa-solid fa-chart-column"></i>Desglose por Campaña</div>', unsafe_allow_html=True)
if not fact.empty:
    STATUS_ICON_TABLE = {
        "ACTIVE":   "Activa",
        "PAUSED":   "Pausada",
        "DELETED":  "Eliminada",
        "ARCHIVED": "Archivada",
        "UNKNOWN":  "Desconocido",
    }
    group_camp = ["campaign_name"]
    if "campaign_effective_status" in fact.columns:
        group_camp.append("campaign_effective_status")

    by_campaign = (
        fact.groupby(group_camp)
        .apply(lambda x: pd.Series({
            "spend":     x["spend"].sum(),
            "ventas":    x["sales_count"].sum(),
            "valor":     x["sales_value"].sum(),
            "roas":      x["sales_value"].sum() / x["spend"].sum() if x["spend"].sum() > 0 else 0,
            "conv_rate": x["conversion_rate"].mean(),
        }))
        .reset_index()
        .sort_values("valor", ascending=False)
    )
    by_campaign_display = by_campaign.copy()
    if "campaign_effective_status" in by_campaign_display.columns:
        by_campaign_display["campaign_effective_status"] = by_campaign_display["campaign_effective_status"].apply(
            lambda x: STATUS_ICON_TABLE.get(str(x).upper(), x)
        )
    by_campaign_display["spend"]     = by_campaign_display["spend"].apply(lambda x: f"${x:,.0f}")
    by_campaign_display["valor"]     = by_campaign_display["valor"].apply(lambda x: f"${x:,.0f}")
    by_campaign_display["roas"]      = by_campaign_display["roas"].apply(lambda x: f"{x:.2f}x")
    by_campaign_display["conv_rate"] = by_campaign_display["conv_rate"].apply(lambda x: f"{x:.1%}")
    by_campaign_display["ventas"]    = by_campaign_display["ventas"].apply(lambda x: f"{int(x):,}")

    rename_map = {"campaign_name": "Campaña", "campaign_effective_status": "Estado",
                  "spend": "Spend", "ventas": "Ventas", "valor": "Valor",
                  "roas": "ROAS", "conv_rate": "Conv. Rate"}
    by_campaign_display = by_campaign_display.rename(columns=rename_map)
    st.dataframe(by_campaign_display, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Tabla detallada
# ------------------------------------------------------------------

with st.expander("Ver tabla completa de fact_performance"):
    display_cols = ["date", "campaign_name", "ad_name", "chip", "effective_status",
                    "spend", "sales_count", "sales_value", "roas",
                    "conversion_rate", "conversations_started", "cost_per_conversation"]
    existing = [c for c in display_cols if c in fact.columns]
    st.dataframe(fact[existing], use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Panel de Inteligencia
# ------------------------------------------------------------------

sales_raw      = data["sales_raw"]
fact_all       = data["fact"]

total_ventas_archivo  = len(sales_raw)
ventas_id_valido      = len(sales_raw[~sales_raw["ad_id"].str.strip().str.lower().isin(["{source_id}", "", "nan", "none", "null"])])
ventas_no_atribuibles = len(sales_raw) - ventas_id_valido
ventas_cruzadas       = int(fact_all["sales_count"].sum())
post_ids_analizados   = fact_all["ad_id"].nunique()
roas_total            = fact_all["sales_value"].sum() / fact_all["spend"].sum() if fact_all["spend"].sum() > 0 else 0

with st.expander("Panel de Inteligencia", expanded=True):

    st.markdown('<div class="dash-header-inner"><i class="fa-solid fa-clipboard-list"></i>Resumen</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    r1.metric("Post IDs analizados",      f"{post_ids_analizados:,}")
    r2.metric("Ventas en archivo",        f"{total_ventas_archivo:,}")
    r3.metric("Ventas con ID válido",     f"{ventas_id_valido:,}")
    r4, r5, r6 = st.columns(3)
    r4.metric("Ventas no atribuibles",    f"{ventas_no_atribuibles:,}")
    r5.metric("Ventas cruzadas con Meta", f"{ventas_cruzadas:,}")
    r6.metric("ROAS total",               f"{roas_total:.2f}x")

    st.markdown("---")
    st.markdown('<div class="dash-header-inner"><i class="fa-solid fa-lightbulb"></i>Insights por Creativo</div>', unsafe_allow_html=True)

    STATUS_ICON_HTML = {
        "ACTIVE":   '<i class="fa-solid fa-circle-check" style="color:#22c55e;"></i> Activo',
        "PAUSED":   '<i class="fa-solid fa-circle-pause" style="color:#eab308;"></i> Pausado',
        "DELETED":  '<i class="fa-solid fa-circle-xmark" style="color:#ef4444;"></i> Eliminado',
        "ARCHIVED": '<i class="fa-solid fa-circle-minus" style="color:#6b7280;"></i> Archivado',
        "UNKNOWN":  '<i class="fa-solid fa-circle-question" style="color:#4b5563;"></i> Desconocido',
    }

    if not fact_all.empty:
        group_cols_ad = ["ad_id", "ad_name"]
        if "campaign_effective_status" in fact_all.columns:
            group_cols_ad.append("campaign_effective_status")

        by_ad = (
            fact_all.groupby(group_cols_ad)
            .apply(lambda x: pd.Series({
                "spend":  x["spend"].sum(),
                "ventas": x["sales_count"].sum(),
                "valor":  x["sales_value"].sum(),
                "roas":   x["sales_value"].sum() / x["spend"].sum() if x["spend"].sum() > 0 else 0,
            }))
            .reset_index()
        )
        if "campaign_effective_status" not in by_ad.columns:
            by_ad["campaign_effective_status"] = "UNKNOWN"

        def fmt_status(s):
            return STATUS_ICON_HTML.get(str(s).upper(), f'<i class="fa-solid fa-circle-question" style="color:#4b5563;"></i> {s}')

        mayor_roas = by_ad[by_ad["spend"] > 0].sort_values("roas", ascending=False).iloc[0]
        mas_ventas = by_ad.sort_values("ventas", ascending=False).iloc[0]
        escalar_df = by_ad[(by_ad["roas"] > 1.5) & (by_ad["ventas"] >= 3)].sort_values("ventas", ascending=False)
        escalar    = escalar_df.iloc[0] if not escalar_df.empty else None
        apagar_df  = by_ad[(by_ad["spend"] > 0) & ((by_ad["ventas"] == 0) | (by_ad["roas"] < 0.5))].sort_values("spend", ascending=False)
        apagar     = apagar_df.iloc[0] if not apagar_df.empty else None

        i1, i2 = st.columns(2)
        with i1:
            st.markdown(f'<i class="fa-solid fa-star" style="color:#a3e635;margin-right:6px;"></i><b>Creativo con mayor ROAS</b><br><code>{mayor_roas["ad_name"]}</code><br>{fmt_status(mayor_roas["campaign_effective_status"])} · ROAS: <b>{mayor_roas["roas"]:.2f}x</b> · Ventas: <b>{int(mayor_roas["ventas"])}</b> · Spend: <b>${mayor_roas["spend"]:,.0f}</b>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<i class="fa-solid fa-arrow-trend-up" style="color:#a3e635;margin-right:6px;"></i><b>Creativo con más ventas</b><br><code>{mas_ventas["ad_name"]}</code><br>{fmt_status(mas_ventas["campaign_effective_status"])} · Ventas: <b>{int(mas_ventas["ventas"])}</b> · Valor: <b>${mas_ventas["valor"]:,.0f}</b> · ROAS: <b>{mas_ventas["roas"]:.2f}x</b>', unsafe_allow_html=True)
        with i2:
            if escalar is not None:
                st.markdown(f'<i class="fa-solid fa-rocket" style="color:#3b82f6;margin-right:6px;"></i><b>Creativo que debería escalarse</b><br><code>{escalar["ad_name"]}</code><br>{fmt_status(escalar["campaign_effective_status"])} · ROAS: <b>{escalar["roas"]:.2f}x</b> · Ventas: <b>{int(escalar["ventas"])}</b> · Spend: <b>${escalar["spend"]:,.0f}</b>', unsafe_allow_html=True)
            else:
                st.markdown('<i class="fa-solid fa-rocket" style="color:#3b82f6;margin-right:6px;"></i><b>Creativo que debería escalarse</b><br>No hay candidatos claros aún.', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if apagar is not None:
                st.markdown(f'<i class="fa-solid fa-power-off" style="color:#ef4444;margin-right:6px;"></i><b>Creativo que debería apagarse</b><br><code>{apagar["ad_name"]}</code><br>{fmt_status(apagar["campaign_effective_status"])} · Ventas: <b>{int(apagar["ventas"])}</b> · ROAS: <b>{apagar["roas"]:.2f}x</b> · Spend quemado: <b>${apagar["spend"]:,.0f}</b>', unsafe_allow_html=True)
            else:
                st.markdown('<i class="fa-solid fa-power-off" style="color:#ef4444;margin-right:6px;"></i><b>Creativo que debería apagarse</b><br>No hay candidatos con gasto y 0 ventas.', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="dash-header-inner"><i class="fa-solid fa-bolt"></i>Recomendación rápida</div>', unsafe_allow_html=True)
        recs = []
        n_escalar            = len(escalar_df)
        n_apagar             = len(apagar_df)
        n_roas_alto_gasto_bajo = len(by_ad[(by_ad["roas"] > 5) & (by_ad["spend"] < by_ad["spend"].quantile(0.2))])
        if n_escalar > 0:
            recs.append(f'<i class="fa-solid fa-circle-check" style="color:#a3e635;margin-right:6px;"></i><b>Escala {n_escalar} anuncio(s)</b> con ROAS > 1.5x y al menos 3 ventas — tienen demanda probada.')
        if n_roas_alto_gasto_bajo > 0:
            recs.append(f'<i class="fa-solid fa-triangle-exclamation" style="color:#eab308;margin-right:6px;"></i><b>{n_roas_alto_gasto_bajo} anuncio(s)</b> tienen ROAS muy alto pero gasto casi nulo — no escales agresivo sin más datos.')
        if n_apagar > 0:
            recs.append(f'<i class="fa-solid fa-circle-xmark" style="color:#ef4444;margin-right:6px;"></i><b>Apaga o recorta {n_apagar} anuncio(s)</b> con gasto activo y 0 ventas o ROAS < 0.5x.')
        if ventas_no_atribuibles > ventas_id_valido * 0.2:
            recs.append(f'<i class="fa-solid fa-magnifying-glass" style="color:#3b82f6;margin-right:6px;"></i><b>{ventas_no_atribuibles} ventas sin atribución</b> ({ventas_no_atribuibles/total_ventas_archivo:.0%}) — revisa el flujo de Make para capturar el ad_id correctamente.')
        for rec in recs:
            st.markdown(rec, unsafe_allow_html=True)
        if not recs:
            st.markdown("Sin recomendaciones urgentes para el período seleccionado.")

# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------

st.markdown("---")
unmatched_pct = len(data["unmatched"]) / max(len(data["sales_raw"]), 1) * 100
st.caption(
    f"{len(data['unmatched'])} ventas sin cruce Meta ({unmatched_pct:.1f}%) · "
    f"Actualizado: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}"
)
