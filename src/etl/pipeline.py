"""
Pipeline principal: orquesta la ingesta de ambas fuentes y ejecuta el ETL.
Punto de entrada para el dashboard y para ejecuciones programadas.
"""

from datetime import datetime, timedelta

from loguru import logger

from src.connectors.meta_ads_client import MetaAdsClient
from src.connectors.sheets_client import SheetsClient
from src.etl.transformer import Transformer


def run_pipeline(days_back: int = 30, ad_account_id: str | None = None) -> dict:
    """
    Ejecuta el pipeline completo y retorna los DataFrames listos.

    Args:
        days_back: cuántos días hacia atrás consultar en ambas fuentes

    Returns:
        dict con keys: fact, unmatched, no_sales, sales_raw, meta_raw
    """
    logger.info(f"=== Iniciando pipeline ANTIGRAVITY | últimos {days_back} días | cuenta: {ad_account_id or 'default'} ===")

    # 1. Ingesta
    sheets = SheetsClient()
    meta   = MetaAdsClient(ad_account_id=ad_account_id)

    sales_df        = sheets.get_sales()
    meta_df         = meta.get_insights(days_back=days_back)
    camp_status     = meta.get_campaign_statuses()
    adset_countries = meta.get_adset_countries()

    # Agregar estado de campaña al DataFrame de Meta antes del cruce
    if not camp_status.empty and not meta_df.empty:
        meta_df = meta_df.merge(camp_status, on="campaign_id", how="left")
        meta_df["campaign_effective_status"] = meta_df["campaign_effective_status"].fillna("UNKNOWN")

    # Agregar países de segmentación al DataFrame de Meta
    if not adset_countries.empty and not meta_df.empty:
        meta_df = meta_df.merge(adset_countries, on="adset_id", how="left")
        meta_df["country_code"] = meta_df["country_code"].fillna("UNKNOWN")

    # 2. Transformación y cruce
    transformer = Transformer()
    result = transformer.build_fact_performance(sales_df, meta_df)

    result["sales_raw"] = sales_df
    result["meta_raw"]  = meta_df

    logger.info("=== Pipeline completado ===")
    return result


if __name__ == "__main__":
    result = run_pipeline(days_back=7)
    fact = result["fact"]

    print("\n── RESUMEN GENERAL ──────────────────────────────")
    print(f"  Registros en fact_performance : {len(fact)}")
    print(f"  Spend total                   : {fact['spend'].sum():,.2f}")
    print(f"  Ventas totales (valor)         : {fact['sales_value'].sum():,.2f}")
    print(f"  Ventas totales (cantidad)      : {int(fact['sales_count'].sum())}")
    print(f"  ROAS promedio ponderado        : {fact['roas'].mean():.2f}")
    print(f"  Conversaciones iniciadas       : {int(fact['conversations_started'].sum())}")
    print(f"  Tasa de conversión promedio    : {fact['conversion_rate'].mean():.2%}")

    print("\n── TOP 5 ADS POR ROAS ───────────────────────────")
    top = (
        fact.groupby("ad_name")
        .agg(spend=("spend","sum"), sales_value=("sales_value","sum"), roas=("roas","mean"))
        .sort_values("roas", ascending=False)
        .head(5)
    )
    print(top.to_string())

    print("\n── RENDIMIENTO POR CHIP ─────────────────────────")
    by_chip = (
        fact.groupby("chip")
        .agg(
            ventas=("sales_count", "sum"),
            valor=("sales_value", "sum"),
            conversion=("conversion_rate", "mean"),
        )
        .sort_values("ventas", ascending=False)
    )
    print(by_chip.to_string())
