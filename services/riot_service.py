"""
VALORANT ACCOUNT CHECKER & DATABASE
Riot Games Kimlik Doğrulama ve PVP / PD İstemcisi
Tüm envanter (skinler, uğurluklar, spreyler, kartlar, unvanlar, ajanlar), kontratlar, görevler, mağaza ve MMR verilerini çeker.
"""

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import (
    AP_PER_LEVEL,
    CLIENT_PLATFORM_B64,
    CURRENCY_IDS,
    DEFAULT_REGION,
    ENTITLEMENTS_URL,
    ITEM_TYPES,
    MATCH_COUNT,
    PENALTY_EFFECTS,
    PLATFORM_DATA,
    PVP_BASE_URL,
    REGION_TO_SHARD,
    SHARED_BASE_URL,
    USERINFO_URL,
)
from services.content_service import content_service

logger = logging.getLogger("ValoChecker.RiotService")


def decode_jwt_payload(token: Optional[str]) -> Dict[str, Any]:
    """JWT token'ın payload kısmını (ortadaki bölümü) base64url ile çözer."""
    if not token or "." not in token:
        return {}
    try:
        parts = token.strip().split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += "=" * (4 - rem)
            decoded = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
            return json.loads(decoded.decode("utf-8"))
    except Exception as e:
        logger.debug(f"JWT payload çözümleme hatası: {e}")
    return {}


def parse_timestamp(value: Any) -> Optional[datetime]:
    """API zaman damgasını UTC datetime nesnesine dönüştürür."""
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 10_000_000_000:
                ts /= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        val_str = str(value).strip()
        try:
            ts = float(val_str)
            if ts > 10_000_000_000:
                ts /= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except ValueError:
            pass

        if val_str.endswith("Z"):
            val_str = val_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(val_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def format_time_local(dt: Optional[datetime]) -> str:
    """Yerel saat formatına çevirir (GG.AA.YYYY SS:DD)."""
    if not dt:
        return "Bilinmiyor"
    return dt.astimezone().strftime("%d.%m.%Y %H:%M")


def format_remaining_duration(seconds: int) -> str:
    """Saniyeyi gün, saat ve dakikaya çevirir."""
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    parts = []
    if days:
        parts.append(f"{days} gün")
    if hours:
        parts.append(f"{hours} saat")
    if minutes or not parts:
        parts.append(f"{minutes} dakika")
    return " ".join(parts)


class RiotClient:
    """Riot Games API isteklerini yöneten istemci."""

    def __init__(self, region: str = DEFAULT_REGION):
        self.region = region.lower().strip()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "RiotClient/Windows"})

        self.access_token: Optional[str] = None
        self.id_token: Optional[str] = None
        self.entitlements_token: Optional[str] = None
        self.puuid: Optional[str] = None
        self.user_info: Dict[str, Any] = {}
        self.game_name: str = ""
        self.tag_line: str = ""
        self.riot_id: str = ""

        # Sürüm ve Platform bilgisi
        content_service.ensure_initialized()
        self.client_version = content_service.get_client_version_string()
        self.platform_b64 = CLIENT_PLATFORM_B64

    def pd_url(self, path: str, shard: Optional[str] = None) -> str:
        """PD uç noktası URL'sini döndürür (Bölgeyi doğru sunucu shard'ına yönlendirir)."""
        target_shard = shard or REGION_TO_SHARD.get(str(self.region or "eu").lower(), str(self.region or "eu").lower())
        base = PVP_BASE_URL.format(region=target_shard)
        return f"{base}{path}"

    def shared_url(self, path: str, shard: Optional[str] = None) -> str:
        """Shared uç noktası URL'sini döndürür (Bölgeyi doğru sunucu shard'ına yönlendirir)."""
        target_shard = shard or REGION_TO_SHARD.get(str(self.region or "eu").lower(), str(self.region or "eu").lower())
        base = SHARED_BASE_URL.format(region=target_shard)
        return f"{base}{path}"

    def detect_region_and_shard(self):
        """Oyuncunun gerçek shard ve bölgesini Riot Geo (PAS) veya userinfo ile otomatik tespit eder."""
        if self.id_token:
            try:
                geo_resp = self.session.put(
                    "https://riot-geo.pas.si.riotgames.com/pas/v1/product/valorant",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={"id_token": self.id_token},
                    timeout=10,
                )
                if geo_resp.ok:
                    affinities = geo_resp.json().get("affinities", {})
                    live_region = affinities.get("live")
                    if live_region:
                        self.region = str(live_region).lower().strip()
                        logger.info(f"Riot PAS üzerinden canlı bölge tespit edildi: {self.region}")
                        return
            except Exception as e:
                logger.debug(f"Riot Geo PAS tespiti atlandı: {e}")

        # Fallback: country kodu kontrolü
        country = (self.user_info.get("country") or "").lower().strip()
        if country in ("tur", "deu", "fra", "gbr", "esp", "ita", "rus", "pol", "ukr", "nld", "swe", "nor"):
            self.region = "eu"
        elif country in ("usa", "can", "mex"):
            self.region = "na"
        elif country in ("kor",):
            self.region = "kr"
        elif country in ("jpn", "vnm", "tha", "sgp", "aus", "ind", "phl", "mys", "twn"):
            self.region = "ap"
        elif country in ("bra",):
            self.region = "br"
        elif country in ("col", "chl", "arg", "per"):
            self.region = "latam"

    def authenticate_url(self, redirect_url: str):
        """Kullanıcının tarayıcıdan yapıştırdığı yönlendirme URL'sinden giriş yapar."""
        url_str = redirect_url.strip()
        parsed = urlparse(url_str)

        token = parse_qs(parsed.fragment).get("access_token", [None])[0]
        id_token = parse_qs(parsed.fragment).get("id_token", [None])[0]

        if not token:
            token = parse_qs(parsed.query).get("access_token", [None])[0]
        if not id_token:
            id_token = parse_qs(parsed.query).get("id_token", [None])[0]

        if not token and ("access_token=" in url_str):
            try:
                token = url_str.split("access_token=")[1].split("&")[0]
            except Exception:
                pass

        if not id_token and ("id_token=" in url_str):
            try:
                id_token = url_str.split("id_token=")[1].split("&")[0]
            except Exception:
                pass

        if not token:
            raise ValueError("Geçerli bir access_token bulunamadı. Lütfen Riot giriş URL'sini tam yapıştırın.")

        self.authenticate_token(token, id_token=id_token)

    def authenticate_token(self, access_token: str, id_token: Optional[str] = None):
        """access_token ve varsa id_token ile kimlik doğrular."""
        self.access_token = access_token.strip()
        self.id_token = id_token.strip() if id_token else None

        # Token payload'larından önceden PUUID ve Riot ID'yi kurtar (DNS/ağ kesintilerine karşı yedek)
        id_payload = decode_jwt_payload(self.id_token) if self.id_token else {}
        access_payload = decode_jwt_payload(self.access_token)

        self.puuid = id_payload.get("sub") or access_payload.get("sub")
        acct = id_payload.get("acct") or access_payload.get("acct") or {}
        if isinstance(acct, dict):
            self.game_name = acct.get("game_name", "")
            self.tag_line = acct.get("tag_line", "")
            if self.game_name and self.tag_line:
                self.riot_id = f"{self.game_name}#{self.tag_line}"

        # 1. Entitlements Token Al
        resp = self.session.post(
            ENTITLEMENTS_URL,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=15,
        )
        resp.raise_for_status()
        self.entitlements_token = resp.json()["entitlements_token"]

        # 2. UserInfo Al
        try:
            resp = self.session.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=15,
            )
            if resp.ok:
                self.user_info = resp.json()
                if self.user_info.get("sub"):
                    self.puuid = self.user_info["sub"]

                u_acct = self.user_info.get("acct", {})
                if isinstance(u_acct, dict):
                    if u_acct.get("game_name") and u_acct.get("tag_line"):
                        self.game_name = u_acct["game_name"]
                        self.tag_line = u_acct["tag_line"]
                        self.riot_id = f"{self.game_name}#{self.tag_line}"
            else:
                logger.warning(f"userinfo endpoint başarısız: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"auth.riotgames.com/userinfo isteği başarısız oldu ({e}). Token içerisindeki PUUID ({self.puuid}) ile devam ediliyor.")

        if not self.puuid:
            raise ValueError("Kullanıcı kimliği (PUUID) belirlenemedi. Lütfen tekrar giriş yapıp yönlendirme bağlantısını yapıştırın.")

        # 3. Bölge ve Shard tespiti (Riot Geo PAS veya Ülke Kodu)
        self.detect_region_and_shard()

        # Oturum başlıklarını güncelle
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "X-Riot-Entitlements-JWT": self.entitlements_token,
            "X-Riot-ClientVersion": self.client_version,
            "X-Riot-ClientPlatform": self.platform_b64,
            "Content-Type": "application/json",
        })

        # Riot ID henüz yoksa Name-Service'ten çöz
        if not self.riot_id:
            self.fetch_name_from_service()

    def fetch_name_from_service(self):
        """PUUID ile Riot Name-Service'ten GameName#TagLine alır."""
        if not self.puuid:
            return
        for base_func in [self.pd_url, self.shared_url]:
            try:
                url = base_func("/name-service/v2/players")
                resp = self.session.put(url, json=[self.puuid], timeout=10)
                if resp.ok:
                    data = resp.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        player = data[0]
                        self.game_name = player.get("GameName", "")
                        self.tag_line = player.get("TagLine", "")
                        self.riot_id = f"{self.game_name}#{self.tag_line}"
                        return
            except Exception as e:
                logger.debug(f"Name-Service isteği atlandı: {e}")

        if not self.riot_id:
            self.riot_id = f"Oyuncu#{self.puuid[:5]}"

    # ========================================================
    # HESAP VERİ ÇEKME METOTLARI
    # ========================================================

    def get_account_xp(self) -> Dict[str, Any]:
        """Hesap seviyesi, XP ve Günlük İlk Galibiyet bonus verisini çeker."""
        try:
            url = self.pd_url(f"/account-xp/v1/players/{self.puuid}")
            resp = self.session.get(url, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception as e:
            logger.debug(f"account-xp isteği hatası: {e}")
        return {}

    def get_wallet(self) -> Dict[str, int]:
        """Cüzdan bakiyelerini (VP, RP, KC) çeker."""
        try:
            url = self.pd_url(f"/store/v1/wallet/{self.puuid}")
            resp = self.session.get(url, timeout=15)
            if resp.ok:
                balances = resp.json().get("Balances", {})
                return {
                    "VP": balances.get(CURRENCY_IDS["VP"], 0),
                    "RP": balances.get(CURRENCY_IDS["RP"], 0),
                    "KC": balances.get(CURRENCY_IDS["KC"], 0),
                }
        except Exception as e:
            logger.debug(f"wallet isteği hatası: {e}")
        return {"VP": 0, "RP": 0, "KC": 0}

    def get_mmr(self) -> Dict[str, Any]:
        """Dereceli MMR, mevcut kademe, RR ve sezonluk dereceleri çeker."""
        try:
            url = self.pd_url(f"/mmr/v1/players/{self.puuid}")
            resp = self.session.get(url, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception as e:
            logger.debug(f"mmr isteği hatası: {e}")
        return {}

    def get_storefront(self) -> Dict[str, Any]:
        """Günlük mağaza (Daily Shop), Öne Çıkan Paket ve Gece Pazarı tekliflerini çeker (Storefront v3)."""
        # 1. Öncelikli modern v3 endpoint (POST with empty body {})
        try:
            url_v3 = self.pd_url(f"/store/v3/storefront/{self.puuid}")
            resp = self.session.post(url_v3, json={}, timeout=15)
            if resp.ok:
                data = resp.json()
                if data and isinstance(data, dict):
                    logger.info(f"Storefront v3 verisi başarıyla alındı: {url_v3}")
                    return data
            else:
                logger.debug(f"Storefront v3 POST HTTP {resp.status_code}: {url_v3}")
        except Exception as e:
            logger.debug(f"Storefront v3 isteği hatası: {e}")

        # 2. Yedek v2 endpoint (POST ve GET)
        for method in ["post", "get"]:
            try:
                url_v2 = self.pd_url(f"/store/v2/storefront/{self.puuid}")
                if method == "post":
                    resp = self.session.post(url_v2, json={}, timeout=15)
                else:
                    resp = self.session.get(url_v2, timeout=15)
                if resp.ok:
                    data = resp.json()
                    if data and isinstance(data, dict):
                        logger.info(f"Storefront v2 ({method.upper()}) verisi başarıyla alındı: {url_v2}")
                        return data
            except Exception as e:
                logger.debug(f"Storefront fallback ({method}) hatası: {e}")

        return {}

    def get_player_loadout(self) -> Dict[str, Any]:
        """Kullanıcının kuşanmış olduğu envanter (Kullanıcı talebi doğrultusunda pasifleştirildi)."""
        return {}

    def get_all_entitlements(self) -> Dict[str, List[str]]:
        """Kullanıcının sahip olduğu TÜM envanter kategorilerini (skinler, uğurluklar, spreyler, kartlar, unvanlar, ajanlar) çeker."""
        results: Dict[str, List[str]] = {
            "skins": [],
            "chromas": [],
            "buddies": [],
            "sprays": [],
            "cards": [],
            "titles": [],
            "agents": [],
        }

        mapping = [
            ("skins", ITEM_TYPES["SKIN_LEVEL"]),
            ("chromas", ITEM_TYPES["SKIN_CHROMA"]),
            ("buddies", ITEM_TYPES["BUDDY"]),
            ("sprays", ITEM_TYPES["SPRAY"]),
            ("cards", ITEM_TYPES["PLAYER_CARD"]),
            ("titles", ITEM_TYPES["PLAYER_TITLE"]),
            ("agents", ITEM_TYPES["AGENT"]),
        ]

        for cat_name, item_type_id in mapping:
            url = self.pd_url(f"/store/v1/entitlements/{self.puuid}/{item_type_id}")
            try:
                resp = self.session.get(url, timeout=15)
                if resp.ok:
                    entitlements = resp.json().get("Entitlements", []) or []
                    results[cat_name] = [str(item.get("ItemID", "")).lower() for item in entitlements if item.get("ItemID")]
                    logger.debug(f"Entitlement {cat_name} ({len(results[cat_name])} öğe): {url}")
                else:
                    logger.debug(f"Entitlement {cat_name} HTTP {resp.status_code}: {url}")
            except Exception as e:
                logger.debug(f"Entitlement {cat_name} hatası ({url}): {e}")

        return results

    def get_contracts_and_missions(self) -> Dict[str, Any]:
        """Günlük/haftalık aktif görevler, Savaş Bileti ve Ajan kontrat ilerlemelerini çeker."""
        try:
            url = self.pd_url(f"/contracts/v1/contracts/{self.puuid}")
            resp = self.session.get(url, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception as e:
            logger.debug(f"contracts isteği hatası: {e}")
        return {}

    def get_match_history(self, count: int = MATCH_COUNT) -> List[str]:
        """Son maçların Match ID listesini çeker."""
        try:
            url = self.pd_url(f"/match-history/v1/history/{self.puuid}?startIndex=0&endIndex={count}")
            resp = self.session.get(url, timeout=20)
            if resp.ok:
                history = resp.json().get("History", []) or []
                match_ids = []
                for item in history:
                    mid = item.get("MatchID") or item.get("matchId")
                    if mid:
                        match_ids.append(mid)
                return match_ids
        except Exception as e:
            logger.debug(f"match-history isteği hatası: {e}")
        return []

    def get_match_details(self, match_id: str) -> Dict[str, Any]:
        """Tek bir maçın ayrıntılı istatistiklerini çeker."""
        try:
            url = self.pd_url(f"/match-details/v1/matches/{match_id}")
            resp = self.session.get(url, timeout=20)
            if resp.ok:
                return resp.json()
        except Exception as e:
            logger.debug(f"match-details isteği hatası: {e}")
        return {}

    def get_penalties(self) -> Dict[str, Any]:
        """Hesap cezalarını ve kısıtlamalarını çeker."""
        try:
            url = self.pd_url("/restrictions/v3/penalties")
            resp = self.session.get(url, timeout=15)
            if resp.ok:
                return resp.json()
        except Exception as e:
            logger.debug(f"penalties isteği hatası: {e}")
        return {"Penalties": [], "Infractions": []}

    def close(self):
        """Oturumu kapatır."""
        self.session.close()
