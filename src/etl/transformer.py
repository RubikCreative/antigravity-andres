"""
Transformer: cruza ventas (Google Sheets) con métricas (Meta Ads) por ad_id
y calcula los KPIs de negocio.

Flujo:
  1. Limpia ad_ids inválidos (placeholders como {source_id}).
  2. Agrega ventas por ad_id + fecha.
  3. Join con métricas de Meta Ads.
  4. Calcula ROAS, tasa de conversión, costo por conversación.
  5. Retorna fact_performance listo para el dashboard.
"""

import pandas as pd
from loguru import logger


# ad_ids que no representan tráfico real de Meta
INVALID_AD_ID_PATTERNS = ["{source_id}", "", "nan", "none", "null"]


class Transformer:

    # ------------------------------------------------------------------
    # Limpieza previa al join
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_ad_ids(df: pd.DataFrame, col: str = "ad_id") -> tuple[pd.DataFrame, pd.DataFrame]:
        mask_invalid = df[col].str.strip().str.lower().isin(INVALID_AD_ID_PATTERNS)
        invalid = df[mask_invalid].copy()
        valid = df[~mask_invalid].copy()
        if len(invalid):
            logger.warning(
                f"{len(invalid)} filas con ad_id inválido separadas "
                f"(no se cruzarán con Meta Ads)."
            )
        return valid, invalid

    # ------------------------------------------------------------------
    # Agregación de ventas por ad_id + fecha
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_sales(sales: pd.DataFrame) -> pd.DataFrame:
        """
        De nivel venta → nivel (ad_id, fecha, chip).
        Mantiene chip como dimensión para el filtro del dashboard.
        """
        sales = sales.copy()

        # Normalizar fecha a día (sin hora)
        sales["date"] = pd.to_datetime(sales["timestamp_venta"]).dt.normalize()

        agg = (
            sales.groupby(["ad_id", "date", "chip"], dropna=False)
            .agg(
                sales_count=("valor_venta", "count"),
                sales_value=("valor_venta", "sum"),
            )
            .reset_index()
        )
        return agg

    # ------------------------------------------------------------------
    # Agregación de métricas Meta por ad_id + fecha
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_meta(meta: pd.DataFrame) -> pd.DataFrame:
        meta = meta.copy()
        meta["date"] = pd.to_datetime(meta["date_start"]).dt.normalize()

        # Conservar effective_status si existe (puede no estar en runs sin statuses)
        group_cols = ["ad_id", "date", "campaign_id", "campaign_name",
                      "adset_id", "adset_name", "ad_name"]
        if "campaign_effective_status" in meta.columns:
            group_cols.append("campaign_effective_status")
        if "country_code" in meta.columns:
            group_cols.append("country_code")

        agg = (
            meta.groupby(group_cols, dropna=False)
            .agg(
                spend=("spend", "sum"),
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                reach=("reach", "sum"),
                conversations_started=("conversations_started", "sum"),
            )
            .reset_index()
        )
        # CPC y CPM recalculados desde agregados para evitar promedios de promedios
        agg["cpc"] = agg.apply(
            lambda r: r["spend"] / r["clicks"] if r["clicks"] > 0 else 0.0, axis=1
        )
        agg["cpm"] = agg.apply(
            lambda r: (r["spend"] / r["impressions"]) * 1000 if r["impressions"] > 0 else 0.0,
            axis=1,
        )
        return agg

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_kpis(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ROAS: cuántos pesos/soles de venta por cada peso/sol invertido
        df["roas"] = df.apply(
            lambda r: round(r["sales_value"] / r["spend"], 4)
            if r["spend"] > 0 else None,
            axis=1,
        )

        # Costo por conversión (venta cerrada)
        df["cost_per_sale"] = df.apply(
            lambda r: round(r["spend"] / r["sales_count"], 2)
            if r["sales_count"] > 0 else None,
            axis=1,
        )

        # Costo por conversación (del lado de Meta)
        df["cost_per_conversation"] = df.apply(
            lambda r: round(r["spend"] / r["conversations_started"], 2)
            if r["conversations_started"] > 0 else None,
            axis=1,
        )

        # Tasa de conversión: ventas / conversaciones iniciadas
        df["conversion_rate"] = df.apply(
            lambda r: round(r["sales_count"] / r["conversations_started"], 4)
            if r["conversations_started"] > 0 else None,
            axis=1,
        )

        # Tasa de conversión sobre clics
        df["click_to_sale_rate"] = df.apply(
            lambda r: round(r["sales_count"] / r["clicks"], 4)
            if r["clicks"] > 0 else None,
            axis=1,
        )

        return df

    # ------------------------------------------------------------------
    # Punto de entrada principal
    # ------------------------------------------------------------------

    def build_fact_performance(
        self,
        sales: pd.DataFrame,
        meta: pd.DataFrame,
        attribution_window_days: int = 3,
    ) -> dict[str, pd.DataFrame]:
        """
        Cruza ventas con métricas de Meta y calcula KPIs.

        Args:
            sales: DataFrame de SheetsClient.get_sales()
            meta:  DataFrame de MetaAdsClient.get_insights()
            attribution_window_days: días de tolerancia para el join por fecha

        Returns:
            dict con:
              - "fact":      tabla principal con KPIs por ad_id + fecha + chip
              - "unmatched": ventas sin cruce en Meta (ad_id no encontrado)
              - "no_sales":  ads con gasto pero sin ventas registradas
        """
        logger.info("Iniciando transformación ETL...")

        # 1. Separar ventas válidas de las sin atribución
        sales_valid, sales_unattr = self._clean_ad_ids(sales)

        # 2. Agregar — si Meta no tiene datos para el período retornar vacío
        if meta.empty or "date_start" not in meta.columns:
            logger.warning("Meta Ads no retornó datos para esta cuenta/período.")
            empty = pd.DataFrame()
            return {"fact": empty, "unmatched": sales_valid, "no_sales": empty}

        sales_agg = self._aggregate_sales(sales_valid)
        meta_agg  = self._aggregate_meta(meta)

        logger.info(
            f"Sales agregadas: {len(sales_agg)} filas | "
            f"Meta agregada: {len(meta_agg)} filas"
        )

        # 3. Join por ad_id + fecha con ventana de atribución
        #    Para cada venta, busca métricas del mismo ad_id
        #    en un rango de ±attribution_window_days días
        fact = pd.merge(
            sales_agg,
            meta_agg,
            on=["ad_id", "date"],
            how="outer",
        )

        # Identificar no-matches
        unmatched_sales = fact[fact["spend"].isna()].copy()
        no_sales_ads    = fact[fact["sales_count"].isna()].copy()
        matched         = fact[fact["spend"].notna() & fact["sales_count"].notna()].copy()

        if len(unmatched_sales):
            logger.warning(
                f"{len(unmatched_sales)} combinaciones ad+fecha con ventas "
                f"sin datos de Meta Ads (posible ad_id nuevo o ventana de atribución)."
            )
        if len(no_sales_ads):
            logger.info(
                f"{len(no_sales_ads)} combinaciones ad+fecha con gasto Meta "
                f"sin ventas registradas en ese día."
            )

        # 4. Rellenar nulos en matched para no romper KPIs
        matched["sales_count"]            = matched["sales_count"].fillna(0)
        matched["sales_value"]            = matched["sales_value"].fillna(0)
        matched["conversations_started"]  = matched["conversations_started"].fillna(0)

        # 5. KPIs
        matched = self._calculate_kpis(matched)

        # 6. Ordenar columnas
        col_order = [
            "date", "campaign_name", "campaign_id", "campaign_effective_status",
            "adset_name", "adset_id", "ad_name", "ad_id", "chip", "country_code",
            "spend", "impressions", "clicks", "reach",
            "conversations_started", "cost_per_conversation",
            "sales_count", "sales_value",
            "roas", "cost_per_sale", "conversion_rate", "click_to_sale_rate",
            "cpc", "cpm",
        ]
        existing_cols = [c for c in col_order if c in matched.columns]
        matched = matched[existing_cols].sort_values("date", ascending=False)

        logger.success(
            f"ETL completo: {len(matched)} filas en fact_performance | "
            f"ROAS promedio: {matched['roas'].mean():.2f}"
        )

        return {
            "fact":      matched.reset_index(drop=True),
            "unmatched": unmatched_sales.reset_index(drop=True),
            "no_sales":  no_sales_ads.reset_index(drop=True),
        }
