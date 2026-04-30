"""
Conector de Meta Ads API para ingesta de métricas de rendimiento publicitario.

Flujo:
  1. Autenticación via Access Token (Long-Lived Token recomendado).
  2. Consulta de insights a nivel de Ad (granularidad máxima).
  3. Paginación automática de resultados.
  4. Manejo de rate limits con exponential backoff.
  5. Retorna DataFrame normalizado listo para el ETL.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adreportrun import AdReportRun
from facebook_business.adobjects.business import Business
from facebook_business.api import FacebookAdsApi
from loguru import logger

load_dotenv()

# Campos que traemos de la API — agregar aquí si se necesitan más
AD_INSIGHT_FIELDS = [
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "spend",
    "impressions",
    "clicks",
    "cpc",
    "cpm",
    "ctr",
    "reach",
    "frequency",
    "actions",          # contiene conversaciones iniciadas, leads, etc.
    "cost_per_action_type",
]

# Desglose por día para poder filtrar por fecha en el dashboard
AD_INSIGHT_BREAKDOWNS = []  # sin breakdown adicional; fecha viene en date_start

AD_INSIGHT_LEVEL = "ad"     # granularidad: campaign | adset | ad

# Rate limit: Meta permite ~200 req/hora por cuenta. Backoff en segundos.
RATE_LIMIT_BACKOFF = [10, 30, 60, 120]


class MetaAdsClient:
    """Lee métricas de Meta Ads API a nivel de anuncio (ad)."""

    def __init__(
        self,
        access_token: str | None = None,
        ad_account_id: str | None = None,
    ):
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self.ad_account_id = ad_account_id or os.getenv("META_AD_ACCOUNT_ID")
        self._initialized = False

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------

    def _init_api(self):
        if self._initialized:
            return
        if not self.access_token:
            raise ValueError(
                "META_ACCESS_TOKEN no configurado.\n"
                "Obtén un Long-Lived Token en: "
                "https://developers.facebook.com/tools/explorer/"
            )
        if not self.ad_account_id:
            raise ValueError("META_AD_ACCOUNT_ID no configurado en .env")

        FacebookAdsApi.init(access_token=self.access_token)
        self._initialized = True
        logger.info(f"Meta Ads API inicializada para cuenta: {self.ad_account_id}")

    # ------------------------------------------------------------------
    # Consulta con retry y backoff
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, cursor, attempt: int = 0) -> list:
        try:
            return list(cursor)
        except Exception as e:
            # Extraer código de error numérico si es FacebookRequestError
            error_code = getattr(e, "api_error_code", lambda: None)()
            error_msg  = str(e)

            # Códigos 4 y 17 = rate limit de aplicación → esperar y reintentar
            is_rate_limit = (
                error_code in (4, 17)
                or any(p in error_msg for p in ["(#17)", "rate limit", "1504022", "request limit"])
            )
            if is_rate_limit:
                if attempt >= len(RATE_LIMIT_BACKOFF):
                    raise RuntimeError(f"Rate limit excedido tras {attempt} reintentos.") from e
                wait = RATE_LIMIT_BACKOFF[attempt]
                logger.warning(f"Rate limit (código {error_code}). Esperando {wait}s...")
                time.sleep(wait)
                return self._fetch_with_retry(cursor, attempt + 1)

            # Código 190 = token expirado o inválido
            if error_code == 190 or ("OAuthException" in error_msg and "190" in error_msg):
                raise ValueError(
                    "Access Token de Meta expirado o inválido.\n"
                    "Genera uno nuevo en: https://developers.facebook.com/tools/explorer/"
                ) from e

            raise

    # ------------------------------------------------------------------
    # Parseo de acciones (conversaciones, leads, compras, etc.)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_actions(actions: list, action_type: str) -> int:
        if not actions:
            return 0
        for a in actions:
            if a.get("action_type") == action_type:
                return int(float(a.get("value", 0)))
        return 0

    @staticmethod
    def _extract_cost_per_action(cost_list: list, action_type: str) -> float:
        if not cost_list:
            return 0.0
        for a in cost_list:
            if a.get("action_type") == action_type:
                return float(a.get("value", 0))
        return 0.0

    # ------------------------------------------------------------------
    # Normalización de una fila de insights
    # ------------------------------------------------------------------

    def _parse_insight(self, insight: dict) -> dict:
        actions = insight.get("actions", [])
        cost_per_action = insight.get("cost_per_action_type", [])

        return {
            "date_start":            insight.get("date_start"),
            "date_stop":             insight.get("date_stop"),
            "campaign_id":           str(insight.get("campaign_id", "")),
            "campaign_name":         insight.get("campaign_name", ""),
            "adset_id":              str(insight.get("adset_id", "")),
            "adset_name":            insight.get("adset_name", ""),
            "ad_id":                 str(insight.get("ad_id", "")),
            "ad_name":               insight.get("ad_name", ""),
            "spend":                 float(insight.get("spend", 0) or 0),
            "impressions":           int(insight.get("impressions", 0) or 0),
            "clicks":                int(insight.get("clicks", 0) or 0),
            "cpc":                   float(insight.get("cpc", 0) or 0),
            "cpm":                   float(insight.get("cpm", 0) or 0),
            "ctr":                   float(insight.get("ctr", 0) or 0),
            "reach":                 int(insight.get("reach", 0) or 0),
            # Conversaciones iniciadas en WhatsApp
            "conversations_started": self._extract_actions(
                actions, "onsite_conversion.messaging_conversation_started_7d"
            ),
            # Costo por conversación
            "cost_per_conversation": self._extract_cost_per_action(
                cost_per_action,
                "onsite_conversion.messaging_conversation_started_7d"
            ),
        }

    # ------------------------------------------------------------------
    # Ingesta principal
    # ------------------------------------------------------------------

    def get_insights(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        days_back: int = 30,
    ) -> pd.DataFrame:
        """
        Retorna DataFrame con métricas por anuncio para el rango de fechas.

        Args:
            date_from: fecha inicio "YYYY-MM-DD" (opcional, usa days_back si no se pasa)
            date_to:   fecha fin   "YYYY-MM-DD" (opcional, usa hoy si no se pasa)
            days_back: días hacia atrás si no se especifica date_from

        Returns:
            DataFrame con schema SCHEMA_META_ADS
        """
        self._init_api()

        # Calcular rango de fechas
        today = datetime.now(timezone.utc).date()
        d_to = date_to or str(today)
        d_from = date_from or str(today - timedelta(days=days_back))

        logger.info(f"Consultando Meta Ads: {d_from} → {d_to} | nivel: {AD_INSIGHT_LEVEL}")

        params = {
            "level":       AD_INSIGHT_LEVEL,
            "time_range":  {"since": d_from, "until": d_to},
            "time_increment": 1,   # un registro por día por ad
            "limit":       500,    # máximo por página
        }

        account = AdAccount(self.ad_account_id)
        cursor = account.get_insights(
            fields=AD_INSIGHT_FIELDS,
            params=params,
        )

        raw_rows = self._fetch_with_retry(cursor)
        logger.info(f"Filas crudas recibidas de Meta API: {len(raw_rows)}")

        if not raw_rows:
            logger.warning("Meta API no retornó datos para el rango solicitado.")
            return pd.DataFrame()

        rows = [self._parse_insight(dict(r)) for r in raw_rows]
        df = pd.DataFrame(rows)

        # Tipos
        df["date_start"] = pd.to_datetime(df["date_start"])
        df["date_stop"] = pd.to_datetime(df["date_stop"])
        df["ingested_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        logger.success(f"Meta Ads ingesta completa: {len(df)} registros | {df['spend'].sum():.2f} spend total")
        return df.reset_index(drop=True)

    @staticmethod
    def get_all_accounts() -> list[dict]:
        """
        Retorna todas las cuentas publicitarias del Business Manager.
        Requiere META_BUSINESS_ID en .env.
        """
        business_id = os.getenv("META_BUSINESS_ID")
        if not business_id:
            raise ValueError("META_BUSINESS_ID no configurado en .env")

        accounts = Business(business_id).get_owned_ad_accounts(
            fields=["id", "name", "account_status"]
        )
        return [
            {"id": str(a["id"]), "name": a["name"]}
            for a in [dict(r) for r in accounts]
        ]

    def get_campaign_statuses(self) -> pd.DataFrame:
        """
        Consulta el estado de entrega actual de cada campaña.
        Equivale a la columna 'Entrega' en el Ads Manager de Meta.

        Returns:
            DataFrame con columnas: campaign_id, campaign_effective_status
        """
        self._init_api()
        logger.info("Consultando estados de campañas...")

        account = AdAccount(self.ad_account_id)
        cursor  = account.get_campaigns(
            fields=["id", "name", "status", "effective_status"],
            params={"limit": 500},
        )
        raw = self._fetch_with_retry(cursor)

        if not raw:
            return pd.DataFrame(columns=["campaign_id", "campaign_effective_status"])

        rows = [
            {
                "campaign_id":                str(c.get("id", "")),
                "campaign_effective_status":  c.get("effective_status", "UNKNOWN"),
            }
            for c in [dict(r) for r in raw]
        ]
        df = pd.DataFrame(rows)
        logger.success(f"Estados de campañas obtenidos: {len(df)}")
        return df

    def get_adset_countries(self) -> pd.DataFrame:
        """
        Extrae los países de segmentación de cada conjunto de anuncios.

        Returns:
            DataFrame con columnas: adset_id, country_code
            Un adset puede tener múltiples filas si apunta a varios países.
        """
        self._init_api()
        logger.info("Consultando segmentación geográfica de conjuntos de anuncios...")

        account = AdAccount(self.ad_account_id)
        cursor = account.get_ad_sets(
            fields=["id", "targeting"],
            params={"limit": 500},
        )
        raw = self._fetch_with_retry(cursor)

        if not raw:
            return pd.DataFrame(columns=["adset_id", "country_code"])

        rows = []
        for i, adset in enumerate([dict(r) for r in raw]):
            adset_id = str(adset.get("id", ""))
            targeting = adset.get("targeting", {})
            if i == 0:
                logger.debug(f"[DEBUG targeting] tipo={type(targeting)} | valor={targeting}")
            if isinstance(targeting, str):
                import json as _json
                try:
                    targeting = _json.loads(targeting)
                except Exception:
                    targeting = {}
            elif not isinstance(targeting, dict):
                try:
                    targeting = dict(targeting)
                except Exception:
                    targeting = {}
            geo = targeting.get("geo_locations", {})

            codes = set()

            # Targeting directo por país
            for code in geo.get("countries", []):
                codes.add(str(code).upper())

            # Targeting por región (cada región tiene campo "country")
            for region in geo.get("regions", []):
                c = region.get("country") if isinstance(region, dict) else None
                if c:
                    codes.add(str(c).upper())

            # Targeting por ciudad (cada ciudad tiene campo "country")
            for city in geo.get("cities", []):
                c = city.get("country") if isinstance(city, dict) else None
                if c:
                    codes.add(str(c).upper())

            if codes:
                for code in codes:
                    rows.append({"adset_id": adset_id, "country_code": code})
            else:
                rows.append({"adset_id": adset_id, "country_code": "UNKNOWN"})

        df = pd.DataFrame(rows)
        logger.success(f"Segmentación geográfica obtenida: {len(df['adset_id'].unique())} conjuntos, {df['country_code'].nunique()} países")
        return df
