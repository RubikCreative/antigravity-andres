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
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid;
    }
    div[data-testid="metric-container"] {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
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
    st.image("https://via.placeholder.com/200x60/6c63ff/ffffff?text=ANTIGRAVITY", width=200)
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

    selected_account_name = st.selectbox("🏢 Cuenta publicitaria", account_names)
    selected_account_id   = account_map[selected_account_name]

    days_back = st.selectbox(
        "Período", [1, 7, 14, 30, 60], index=1,
        format_func=lambda x: "Hoy" if x == 1 else f"Últimos {x} días"
    )

    data = load_data(days_back, selected_account_id)
    fact = data["fact"].copy()

    if fact.empty or "campaign_name" not in fact.columns:
        st.title("🚀 ANTIGRAVITY — Performance Dashboard")
        st.warning(f"La cuenta **{selected_account_name}** no tiene datos de Meta Ads para los últimos {days_back} días. Prueba con otro período o selecciona otra cuenta.")
        st.stop()

    st.markdown("### Filtros")

    # Filtro por estado de entrega
    STATUS_LABELS = {
        "ACTIVE":   "🟢 Activa",
        "PAUSED":   "🟡 Pausada",
        "DELETED":  "🔴 Eliminada",
        "ARCHIVED": "⚫ Archivada",
        "UNKNOWN":  "❓ Desconocido",
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
    if st.button("🔄 Refrescar datos"):
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
    st.title("🚀 ANTIGRAVITY — Performance Dashboard")
    st.warning(f"La cuenta **{selected_account_name}** no tiene datos de Meta Ads para los últimos {days_back} días. Prueba con otro período o selecciona otra cuenta.")
    st.stop()

st.title("🚀 ANTIGRAVITY — Performance Dashboard")
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
col1.metric("💰 Spend Total",        f"${total_spend:,.0f}")
col2.metric("🛒 Ventas (valor)",     f"${total_sales_value:,.0f}")
col3.metric("📦 Ventas (cantidad)",  f"{total_sales_count:,}")
col4.metric("💬 Conversaciones",     f"{total_convs:,}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("📈 ROAS",               f"{avg_roas:.2f}x")
col6.metric("🎯 Tasa de Conversión", f"{avg_conv_rate:.1%}")
col7.metric("💵 Costo por Venta",    f"${cost_per_sale:,.0f}")
col8.metric("💬 Costo por Conv.",    f"${cost_per_conv:,.0f}")

st.markdown("---")

# ------------------------------------------------------------------
# Fila 1: ROAS en el tiempo + Ventas vs Spend
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 ROAS diario")
    if not fact.empty:
        roas_daily = (
            fact.groupby("date")
            .apply(lambda x: x["sales_value"].sum() / x["spend"].sum() if x["spend"].sum() > 0 else 0)
            .reset_index(name="roas")
        )
        fig_roas = px.area(
            roas_daily, x="date", y="roas",
            color_discrete_sequence=["#6c63ff"],
            labels={"roas": "ROAS", "date": "Fecha"},
        )
        fig_roas.add_hline(y=1, line_dash="dot", line_color="red", annotation_text="Break-even")
        fig_roas.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", height=300
        )
        st.plotly_chart(fig_roas, use_container_width=True)

with col_right:
    st.subheader("💰 Spend vs Ventas diario")
    if not fact.empty:
        daily = fact.groupby("date").agg(
            spend=("spend", "sum"),
            sales_value=("sales_value", "sum"),
        ).reset_index()
        fig_bar = go.Figure()
        fig_bar.add_bar(x=daily["date"], y=daily["spend"],       name="Spend",  marker_color="#ff6b6b")
        fig_bar.add_bar(x=daily["date"], y=daily["sales_value"], name="Ventas", marker_color="#6c63ff")
        fig_bar.update_layout(
            barmode="group",
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", height=300,
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------------
# Fila 2: Top Ads por ROAS + Rendimiento por Chip
# ------------------------------------------------------------------

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("🏆 Top 10 Ads por ROAS")
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
            color="roas", color_continuous_scale="Viridis",
            labels={"roas": "ROAS", "ad_name": "Anuncio"},
            text=top_ads["roas"].apply(lambda x: f"{x:.1f}x"),
        )
        fig_top.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", height=350, showlegend=False,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_top, use_container_width=True)

with col_right2:
    st.subheader("📱 Rendimiento por Chip")
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
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="white", height=350, showlegend=False,
        )
        st.plotly_chart(fig_chip, use_container_width=True)

# ------------------------------------------------------------------
# Fila 3: Desglose por Campaña
# ------------------------------------------------------------------

st.subheader("📊 Desglose por Campaña")
if not fact.empty:
    STATUS_ICON = {
        "ACTIVE":   "🟢 Activa",
        "PAUSED":   "🟡 Pausada",
        "DELETED":  "🔴 Eliminada",
        "ARCHIVED": "⚫ Archivada",
        "UNKNOWN":  "❓ Desconocido",
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
            lambda x: STATUS_ICON.get(str(x).upper(), x)
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

with st.expander("🔍 Ver tabla completa de fact_performance"):
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

with st.expander("🧠 Panel de Inteligencia", expanded=True):

    st.markdown("#### 📋 Resumen")
    r1, r2, r3 = st.columns(3)
    r1.metric("Post IDs analizados",      f"{post_ids_analizados:,}")
    r2.metric("Ventas en archivo",        f"{total_ventas_archivo:,}")
    r3.metric("Ventas con ID válido",     f"{ventas_id_valido:,}")
    r4, r5, r6 = st.columns(3)
    r4.metric("Ventas no atribuibles",    f"{ventas_no_atribuibles:,}")
    r5.metric("Ventas cruzadas con Meta", f"{ventas_cruzadas:,}")
    r6.metric("ROAS total",               f"{roas_total:.2f}x")

    st.markdown("---")
    st.markdown("#### 💡 Insights por Creativo")

    STATUS_ICON = {
        "ACTIVE":   "🟢 ACTIVO",
        "PAUSED":   "🟡 PAUSADO",
        "DELETED":  "🔴 ELIMINADO",
        "ARCHIVED": "⚫ ARCHIVADO",
        "UNKNOWN":  "❓ DESCONOCIDO",
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
            return STATUS_ICON.get(str(s).upper(), f"❓ {s}")

        mayor_roas = by_ad[by_ad["spend"] > 0].sort_values("roas", ascending=False).iloc[0]
        mas_ventas = by_ad.sort_values("ventas", ascending=False).iloc[0]
        escalar_df = by_ad[(by_ad["roas"] > 1.5) & (by_ad["ventas"] >= 3)].sort_values("ventas", ascending=False)
        escalar    = escalar_df.iloc[0] if not escalar_df.empty else None
        apagar_df  = by_ad[(by_ad["spend"] > 0) & ((by_ad["ventas"] == 0) | (by_ad["roas"] < 0.5))].sort_values("spend", ascending=False)
        apagar     = apagar_df.iloc[0] if not apagar_df.empty else None

        i1, i2 = st.columns(2)
        with i1:
            st.markdown(f"**1️⃣ Creativo con mayor ROAS**\n> `{mayor_roas['ad_name']}`\n> {fmt_status(mayor_roas['campaign_effective_status'])} · ROAS: **{mayor_roas['roas']:.2f}x** · Ventas: **{int(mayor_roas['ventas'])}** · Spend: **${mayor_roas['spend']:,.0f}**")
            st.markdown(f"**2️⃣ Creativo con más ventas**\n> `{mas_ventas['ad_name']}`\n> {fmt_status(mas_ventas['campaign_effective_status'])} · Ventas: **{int(mas_ventas['ventas'])}** · Valor: **${mas_ventas['valor']:,.0f}** · ROAS: **{mas_ventas['roas']:.2f}x**")
        with i2:
            if escalar is not None:
                st.markdown(f"**3️⃣ Creativo que debería escalarse**\n> `{escalar['ad_name']}`\n> {fmt_status(escalar['campaign_effective_status'])} · ROAS: **{escalar['roas']:.2f}x** · Ventas: **{int(escalar['ventas'])}** · Spend: **${escalar['spend']:,.0f}**")
            else:
                st.markdown("**3️⃣ Creativo que debería escalarse**\n> No hay candidatos claros aún.")
            if apagar is not None:
                st.markdown(f"**4️⃣ Creativo que debería apagarse**\n> `{apagar['ad_name']}`\n> {fmt_status(apagar['campaign_effective_status'])} · Ventas: **{int(apagar['ventas'])}** · ROAS: **{apagar['roas']:.2f}x** · Spend quemado: **${apagar['spend']:,.0f}**")
            else:
                st.markdown("**4️⃣ Creativo que debería apagarse**\n> No hay candidatos con gasto y 0 ventas.")

        st.markdown("---")
        st.markdown("#### ⚡ Recomendación rápida")
        recs = []
        n_escalar            = len(escalar_df)
        n_apagar             = len(apagar_df)
        n_roas_alto_gasto_bajo = len(by_ad[(by_ad["roas"] > 5) & (by_ad["spend"] < by_ad["spend"].quantile(0.2))])
        if n_escalar > 0:
            recs.append(f"✅ **Escala {n_escalar} anuncio(s)** con ROAS > 1.5x y al menos 3 ventas — tienen demanda probada.")
        if n_roas_alto_gasto_bajo > 0:
            recs.append(f"⚠️ **{n_roas_alto_gasto_bajo} anuncio(s)** tienen ROAS muy alto pero gasto casi nulo — no escales agresivo sin más datos.")
        if n_apagar > 0:
            recs.append(f"🔴 **Apaga o recorta {n_apagar} anuncio(s)** con gasto activo y 0 ventas o ROAS < 0.5x.")
        if ventas_no_atribuibles > ventas_id_valido * 0.2:
            recs.append(f"🔍 **{ventas_no_atribuibles} ventas sin atribución** ({ventas_no_atribuibles/total_ventas_archivo:.0%}) — revisa el flujo de Make para capturar el ad_id correctamente.")
        for rec in recs:
            st.markdown(rec)
        if not recs:
            st.markdown("Sin recomendaciones urgentes para el período seleccionado.")

# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------

st.markdown("---")
unmatched_pct = len(data["unmatched"]) / max(len(data["sales_raw"]), 1) * 100
st.caption(
    f"⚠️ {len(data['unmatched'])} ventas sin cruce Meta ({unmatched_pct:.1f}%) · "
    f"Actualizado: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}"
)
