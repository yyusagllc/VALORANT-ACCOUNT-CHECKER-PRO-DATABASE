"""
VALORANT ACCOUNT CHECKER & DATABASE
valorant-api.com İçerik ve Uç Nokta Servisi
dash.valorant-api.com üzerindeki tüm 30 uç noktayı tam olarak destekler, önbelleğe alır ve çözer.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import (
    ALL_CONTENT_ENDPOINTS,
    CURRENCY_IDS,
    DEFAULT_LANGUAGE,
    MODE_NAMES,
    VALORANT_API_BASE,
)
from database.db import db

logger = logging.getLogger("ValoChecker.ContentService")


class ContentService:
    """dash.valorant-api.com tüm 30 uç noktasını yöneten ve çözümleyen servis."""

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self.language = language
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ValoChecker/2.0"})
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Hızlı arama için bellekteki lookup haritaları
        self._memory_cache: Dict[str, Any] = {}
        self._weapons_map: Dict[str, Dict[str, Any]] = {}
        self._skins_map: Dict[str, Dict[str, Any]] = {}
        self._agents_map: Dict[str, Dict[str, Any]] = {}
        self._maps_map: Dict[str, Dict[str, Any]] = {}
        self._cards_map: Dict[str, Dict[str, Any]] = {}
        self._titles_map: Dict[str, Dict[str, Any]] = {}
        self._buddies_map: Dict[str, Dict[str, Any]] = {}
        self._sprays_map: Dict[str, Dict[str, Any]] = {}
        self._bundles_map: Dict[str, Dict[str, Any]] = {}
        self._comp_tiers_map: Dict[int, Dict[str, Any]] = {}
        self._content_tiers_map: Dict[str, Dict[str, Any]] = {}
        self._currencies_map: Dict[str, Dict[str, Any]] = {}
        self._modes_map: Dict[str, Dict[str, Any]] = {}
        self._gear_map: Dict[str, Dict[str, Any]] = {}
        self._borders_map: Dict[str, Dict[str, Any]] = {}
        self._seasons_map: Dict[str, Dict[str, Any]] = {}
        self._themes_map: Dict[str, Dict[str, Any]] = {}
        self._contracts_map: Dict[str, Dict[str, Any]] = {}
        self._ceremonies_map: Dict[str, Dict[str, Any]] = {}
        self._events_map: Dict[str, Dict[str, Any]] = {}
        self._missions_map: Dict[str, Dict[str, Any]] = {}
        self._objectives_map: Dict[str, Dict[str, Any]] = {}
        self._version_cache: Optional[Dict[str, Any]] = None

        self._current_season_uuid: Optional[str] = None
        self._initialized = False

    # ========================================================
    # GENEL VERİ ÇEKME VE ÖNBELLEKLEME
    # ========================================================

    def fetch_endpoint(self, endpoint_name: str, language: Optional[str] = None, use_cache: bool = True) -> Any:
        """
        Belirtilen uç noktadan veri çeker (örn: 'agents', 'weapons/skins', 'missions').
        Önce bellek, sonra SQLite önbellek, en son HTTP isteği yapar.
        """
        lang = language or self.language
        clean_ep = endpoint_name.strip("/").lower()
        cache_key = f"{clean_ep}:{lang}"

        if use_cache and cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        if use_cache:
            cached_data = db.get_cached_endpoint(clean_ep, lang, max_age_hours=24)
            if cached_data is not None:
                self._memory_cache[cache_key] = cached_data
                return cached_data

        url = f"{VALORANT_API_BASE}/{clean_ep}"
        params = {}
        if clean_ep != "version":
            params["language"] = lang

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            res_json = resp.json()
            data = res_json.get("data", res_json)

            self._memory_cache[cache_key] = data
            db.cache_endpoint(clean_ep, lang, data)
            return data
        except Exception as e:
            logger.warning(f"Uç nokta çekilemedi: {clean_ep} ({e})")
            cached_data = db.get_cached_endpoint(clean_ep, lang, max_age_hours=168)
            if cached_data is not None:
                return cached_data
            return [] if clean_ep != "version" else {}

    # ========================================================
    # TÜM DASH.VALORANT-API.COM UÇ NOKTALARI
    # ========================================================

    def get_agents(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("agents", language) or []

    def get_weapons(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("weapons", language) or []

    def get_weapon_skins(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("weapons/skins", language) or []

    def get_weapon_chromas(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("weapons/skinchromas", language) or []

    def get_weapon_levels(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("weapons/skinlevels", language) or []

    def get_maps(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("maps", language) or []

    def get_playercards(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("playercards", language) or []

    def get_buddies(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("buddies", language) or []

    def get_buddy_levels(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("buddies/levels", language) or []

    def get_sprays(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("sprays", language) or []

    def get_spray_levels(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("sprays/levels", language) or []

    def get_bundles(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("bundles", language) or []

    def get_competitivetiers(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("competitivetiers", language) or []

    def get_ceremonies(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("ceremonies", language) or []

    def get_contenttiers(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("contenttiers", language) or []

    def get_contracts(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("contracts", language) or []

    def get_currencies(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("currencies", language) or []

    def get_events(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("events", language) or []

    def get_flex(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("flex", language) or []

    def get_gamemodes(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("gamemodes", language) or []

    def get_gamemode_equippables(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("gamemodes/equippables", language) or []

    def get_gear(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("gear", language) or []

    def get_levelborders(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("levelborders", language) or []

    def get_missions(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("missions", language) or []

    def get_objectives(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("objectives", language) or []

    def get_playertitles(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("playertitles", language) or []

    def get_seasons(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("seasons", language) or []

    def get_competitive_seasons(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("seasons/competitive", language) or []

    def get_themes(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_endpoint("themes", language) or []

    def get_version(self) -> Dict[str, Any]:
        if not self._version_cache:
            self._version_cache = self.fetch_endpoint("version", use_cache=False) or {}
        return self._version_cache

    def get_client_version_string(self) -> str:
        v = self.get_version()
        return v.get("riotClientVersion") or "release-13.10-shipping-18-5893614"

    # ========================================================
    # BAŞLATMA VE TÜM ÖĞELERİ İNDEKSLEME
    # ========================================================

    def ensure_initialized(self):
        """Tüm uç noktalardan gelen verileri zengin arama indekslerine dönüştürür."""
        if self._initialized:
            return

        # 1. Silahlar ve Skinler
        weapons_data = self.get_weapons()
        for w in weapons_data:
            w_uuid = str(w.get("uuid", "")).lower()
            w_name = w.get("displayName", "Silah")
            w_category = (w.get("category", "") or "").split("::")[-1]
            w_icon = w.get("displayIcon", "")

            self._weapons_map[w_uuid] = {
                "uuid": w_uuid,
                "name": w_name,
                "category": w_category,
                "icon": w_icon,
                "shopData": w.get("shopData"),
            }

            for skin in w.get("skins", []):
                s_uuid = str(skin.get("uuid", "")).lower()
                s_name = skin.get("displayName", w_name)
                s_icon = skin.get("displayIcon") or w_icon
                content_tier_uuid = str(skin.get("contentTierUuid") or "").lower()
                theme_uuid = str(skin.get("themeUuid") or "").lower()

                skin_entry = {
                    "skin_uuid": s_uuid,
                    "weapon_uuid": w_uuid,
                    "weapon_name": w_name,
                    "skin_name": s_name,
                    "icon": s_icon,
                    "content_tier_uuid": content_tier_uuid,
                    "theme_uuid": theme_uuid,
                    "chromas": skin.get("chromas", []),
                    "levels": skin.get("levels", []),
                }

                self._skins_map[s_uuid] = skin_entry

                # Tüm seviye ve kromaları da indeksle
                for level in skin.get("levels", []):
                    lvl_uuid = str(level.get("uuid", "")).lower()
                    if lvl_uuid:
                        self._skins_map[lvl_uuid] = {
                            **skin_entry,
                            "level_icon": level.get("displayIcon") or s_icon,
                        }

                for chroma in skin.get("chromas", []):
                    chr_uuid = str(chroma.get("uuid", "")).lower()
                    if chr_uuid:
                        self._skins_map[chr_uuid] = {
                            **skin_entry,
                            "chroma_icon": chroma.get("fullRender") or chroma.get("displayIcon") or chroma.get("swatch") or s_icon,
                        }

        # 2. Ajanlar
        agents_data = self.get_agents()
        for a in agents_data:
            a_uuid = str(a.get("uuid", "")).lower()
            role = a.get("role", {}) or {}
            self._agents_map[a_uuid] = {
                "uuid": a_uuid,
                "name": a.get("displayName", "Bilinmeyen Ajan"),
                "role": role.get("displayName", "Ajan"),
                "icon": a.get("displayIcon", ""),
                "fullPortrait": a.get("fullPortrait", ""),
                "killfeedPortrait": a.get("killfeedPortrait", ""),
                "isPlayable": a.get("isPlayableCharacter", False),
            }

        # 3. Haritalar
        maps_data = self.get_maps()
        for m in maps_data:
            m_uuid = str(m.get("uuid", "")).lower()
            m_url = str(m.get("mapUrl", "")).lower()
            m_name = m.get("displayName", "Harita")
            map_entry = {
                "uuid": m_uuid,
                "name": m_name,
                "url": m_url,
                "splash": m.get("splash", ""),
                "displayIcon": m.get("displayIcon", ""),
                "coordinates": m.get("coordinates", ""),
            }
            self._maps_map[m_uuid] = map_entry
            if m_url:
                self._maps_map[m_url] = map_entry
                parts = m_url.strip("/").split("/")
                if parts:
                    self._maps_map[parts[-1].lower()] = map_entry

        # 4. Dereceli Kademeleri (Competitive Tiers)
        comp_data = self.get_competitivetiers()
        if comp_data:
            latest_comp = comp_data[-1].get("tiers", [])
            for t in latest_comp:
                tier_id = t.get("tier", 0)
                self._comp_tiers_map[tier_id] = {
                    "tier": tier_id,
                    "name": t.get("tierName", "Derecesiz"),
                    "divisionName": t.get("divisionName", ""),
                    "color": "#" + (t.get("color", "ffffff")[:6]),
                    "icon": t.get("largeIcon") or t.get("smallIcon") or "",
                    "smallIcon": t.get("smallIcon") or "",
                }

        # 5. İçerik Nadirlikleri (Content Tiers)
        content_data = self.get_contenttiers()
        for c in content_data:
            c_uuid = str(c.get("uuid", "")).lower()
            self._content_tiers_map[c_uuid] = {
                "uuid": c_uuid,
                "name": c.get("displayName", "Standart"),
                "color": "#" + (c.get("highlightColor", "ffffff")[:6]),
                "icon": c.get("displayIcon", ""),
            }

        # 6. Oyuncu Kartları
        cards_data = self.get_playercards()
        for c in cards_data:
            c_uuid = str(c.get("uuid", "")).lower()
            self._cards_map[c_uuid] = {
                "uuid": c_uuid,
                "name": c.get("displayName", "Oyuncu Kartı"),
                "smallIcon": c.get("smallIcon", ""),
                "wideArt": c.get("wideArt", ""),
                "largeArt": c.get("largeArt", ""),
            }

        # 7. Oyuncu Unvanları
        titles_data = self.get_playertitles()
        for t in titles_data:
            t_uuid = str(t.get("uuid", "")).lower()
            self._titles_map[t_uuid] = {
                "uuid": t_uuid,
                "name": t.get("displayName", ""),
                "titleText": t.get("titleText") or t.get("displayName") or "",
            }

        # 8. Silah Uğurlukları (Buddies)
        buddies_data = self.get_buddies()
        for b in buddies_data:
            b_uuid = str(b.get("uuid", "")).lower()
            b_entry = {
                "uuid": b_uuid,
                "name": b.get("displayName", "Uğurluk"),
                "icon": b.get("displayIcon", ""),
            }
            self._buddies_map[b_uuid] = b_entry
            for lvl in b.get("levels", []):
                lvl_uuid = str(lvl.get("uuid", "")).lower()
                if lvl_uuid:
                    self._buddies_map[lvl_uuid] = {
                        "uuid": lvl_uuid,
                        "name": lvl.get("displayName", b_entry["name"]),
                        "icon": lvl.get("displayIcon") or b_entry["icon"],
                    }

        # 9. Spreyler
        sprays_data = self.get_sprays()
        for s in sprays_data:
            s_uuid = str(s.get("uuid", "")).lower()
            s_entry = {
                "uuid": s_uuid,
                "name": s.get("displayName", "Sprey"),
                "icon": s.get("fullTransparentIcon") or s.get("displayIcon", ""),
                "animation": s.get("animationPng") or s.get("animationGif") or "",
            }
            self._sprays_map[s_uuid] = s_entry
            for lvl in s.get("levels", []):
                lvl_uuid = str(lvl.get("uuid", "")).lower()
                if lvl_uuid:
                    self._sprays_map[lvl_uuid] = {
                        "uuid": lvl_uuid,
                        "name": lvl.get("displayName", s_entry["name"]),
                        "icon": lvl.get("displayIcon") or s_entry["icon"],
                    }

        # 10. Paketler (Bundles)
        bundles_data = self.get_bundles()
        for b in bundles_data:
            b_uuid = str(b.get("uuid", "")).lower()
            self._bundles_map[b_uuid] = {
                "uuid": b_uuid,
                "name": b.get("displayName", "Paket"),
                "icon": b.get("displayIcon") or b.get("verticalPromoImage") or "",
            }

        # 11. Para Birimleri
        currencies_data = self.get_currencies()
        for c in currencies_data:
            c_uuid = str(c.get("uuid", "")).lower()
            self._currencies_map[c_uuid] = {
                "uuid": c_uuid,
                "name": c.get("displayName", "Para Birimi"),
                "icon": c.get("displayIcon", "") or c.get("largeIcon", ""),
            }

        # 12. Sezonlar ve Aktif Kısım
        seasons_data = self.get_seasons()
        now_dt = datetime.now(timezone.utc)
        latest_act_uuid = None
        for s in seasons_data:
            s_uuid = str(s.get("uuid", "")).lower()
            s_name = s.get("displayName", "Sezon")
            s_type = s.get("type", "")
            self._seasons_map[s_uuid] = {
                "uuid": s_uuid,
                "name": s_name,
                "type": s_type,
            }

            if s_type == "EAresSeasonType::Act":
                latest_act_uuid = s_uuid
                start = s.get("startTime")
                end = s.get("endTime")
                if start and end:
                    try:
                        s_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        e_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                        if s_dt <= now_dt <= e_dt:
                            self._current_season_uuid = s_uuid
                    except Exception:
                        pass

        if not self._current_season_uuid and latest_act_uuid:
            self._current_season_uuid = latest_act_uuid

        # 13. Seviye Çerçeveleri (Level Borders)
        borders_data = self.get_levelborders()
        for b in borders_data:
            b_uuid = str(b.get("uuid", "")).lower()
            lvl_num = b.get("startingLevel", 1)
            b_icon = b.get("levelNumberAppearance") or b.get("smallPlayerCardAppearance") or ""
            border_entry = {
                "uuid": b_uuid,
                "level": lvl_num,
                "icon": b_icon,
            }
            self._borders_map[b_uuid] = border_entry
            self._borders_map[str(lvl_num)] = border_entry

        # 14. Görevler ve Hedefler
        missions_data = self.get_missions()
        for m in missions_data:
            m_uuid = str(m.get("uuid", "")).lower()
            self._missions_map[m_uuid] = {
                "uuid": m_uuid,
                "title": m.get("title", ""),
                "type": m.get("type", ""),
                "xpGrant": m.get("xpGrant", 0),
                "progressToComplete": m.get("progressToComplete", 1),
            }

        objectives_data = self.get_objectives()
        for o in objectives_data:
            o_uuid = str(o.get("uuid", "")).lower()
            self._objectives_map[o_uuid] = {
                "uuid": o_uuid,
                "directive": o.get("directive", ""),
            }

        # 15. Oyun Modları
        modes_data = self.get_gamemodes()
        for m in modes_data:
            m_uuid = str(m.get("uuid", "")).lower()
            m_name = m.get("displayName", "Oyun Modu")
            m_icon = m.get("displayIcon", "")
            asset_path = str(m.get("assetPath", "")).lower()
            entry = {"uuid": m_uuid, "name": m_name, "icon": m_icon}
            self._modes_map[m_uuid] = entry
            if asset_path:
                self._modes_map[asset_path] = entry

        # 16. Temalar (Themes)
        themes_data = self.get_themes()
        for t in themes_data:
            t_uuid = str(t.get("uuid", "")).lower()
            self._themes_map[t_uuid] = {
                "uuid": t_uuid,
                "name": t.get("displayName", "Tema"),
                "icon": t.get("displayIcon", ""),
            }

        # 17. Ekipman / Zırhlar (Gear)
        gear_data = self.get_gear()
        for g in gear_data:
            g_uuid = str(g.get("uuid", "")).lower()
            self._gear_map[g_uuid] = {
                "uuid": g_uuid,
                "name": g.get("displayName", "Zırh"),
                "description": g.get("description", ""),
                "icon": g.get("displayIcon", ""),
                "shopData": g.get("shopData", {}),
            }

        # 18. Kontratlar (Contracts)
        contracts_data = self.get_contracts()
        for c in contracts_data:
            c_uuid = str(c.get("uuid", "")).lower()
            c_content = c.get("content", {}) or {}
            self._contracts_map[c_uuid] = {
                "uuid": c_uuid,
                "name": c.get("displayName", "Kontrat"),
                "relationType": c_content.get("relationType", ""),
                "relationUuid": str(c_content.get("relationUuid", "")).lower(),
                "displayIcon": c.get("displayIcon", ""),
                "chapters": c_content.get("chapters", []),
            }

        # 19. Seremoniler (Ceremonies)
        ceremonies_data = self.get_ceremonies()
        for cr in ceremonies_data:
            cr_uuid = str(cr.get("uuid", "")).lower()
            self._ceremonies_map[cr_uuid] = {
                "uuid": cr_uuid,
                "name": cr.get("displayName", "Seremoni"),
                "assetPath": cr.get("assetPath", ""),
            }

        self._initialized = True

    # ========================================================
    # ÇÖZÜMLEME METOTLARI
    # ========================================================

    def get_current_season_uuid(self) -> Optional[str]:
        self.ensure_initialized()
        return self._current_season_uuid

    def resolve_theme(self, uuid: str) -> str:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._themes_map.get(cleaned, {}).get("name", "")

    def resolve_contract(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._contracts_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Bilinmeyen Kontrat",
            "relationType": "",
            "relationUuid": "",
            "displayIcon": "",
            "chapters": [],
        })

    def resolve_gear(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._gear_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Zırh",
            "icon": "",
        })

    def resolve_level_border(self, level: int) -> Dict[str, Any]:
        self.ensure_initialized()
        best_border = None
        for b in sorted(self._borders_map.values(), key=lambda x: x.get("level", 0)):
            lvl = b.get("level")
            if isinstance(lvl, int) and lvl <= level:
                best_border = b
        if best_border:
            return best_border
        return {"level": 1, "icon": ""}

    def resolve_skin(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        skin = self._skins_map.get(cleaned)
        if skin:
            content_tier = self._content_tiers_map.get(skin["content_tier_uuid"], {})
            theme_name = self.resolve_theme(skin.get("theme_uuid", ""))
            return {
                "skin_uuid": skin["skin_uuid"],
                "weapon_name": skin["weapon_name"],
                "skin_name": skin["skin_name"],
                "theme_name": theme_name,
                "icon": skin.get("chroma_icon") or skin.get("level_icon") or skin["icon"],
                "rarity": content_tier.get("name", "Standart"),
                "rarity_color": content_tier.get("color", "#ece8e1"),
                "rarity_icon": content_tier.get("icon", ""),
            }
        return {
            "skin_uuid": cleaned,
            "weapon_name": "Standart",
            "skin_name": "Standart Silah",
            "theme_name": "",
            "icon": "",
            "rarity": "Standart",
            "rarity_color": "#ece8e1",
            "rarity_icon": "",
        }

    def resolve_weapon(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._weapons_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Bilinmeyen Silah",
            "category": "Silah",
            "icon": "",
        })

    def resolve_agent(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._agents_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Bilinmeyen Ajan",
            "role": "Ajan",
            "icon": "",
            "killfeedPortrait": "",
        })

    def resolve_map(self, map_identifier: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(map_identifier or "").lower().strip()

        if cleaned in self._maps_map:
            return self._maps_map[cleaned]

        for key, val in self._maps_map.items():
            if key in cleaned or cleaned in key:
                return val

        return {"name": "Bilinmeyen Harita", "splash": "", "displayIcon": ""}

    def resolve_rank(self, tier_number: int) -> Dict[str, Any]:
        self.ensure_initialized()
        tier_info = self._comp_tiers_map.get(tier_number)
        if tier_info:
            return tier_info

        return {
            "tier": tier_number,
            "name": "Derecesiz" if tier_number == 0 else f"Kademe {tier_number}",
            "color": "#9eabb8",
            "icon": "",
            "smallIcon": "",
        }

    def resolve_card(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._cards_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Oyuncu Kartı",
            "smallIcon": "",
            "wideArt": "",
            "largeArt": "",
        })

    def resolve_title(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._titles_map.get(cleaned, {
            "uuid": cleaned,
            "name": "",
            "titleText": "",
        })

    def resolve_buddy(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._buddies_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Uğurluk",
            "icon": "",
        })

    def resolve_spray(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._sprays_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Sprey",
            "icon": "",
        })

    def resolve_bundle(self, uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(uuid or "").lower()
        return self._bundles_map.get(cleaned, {
            "uuid": cleaned,
            "name": "Öne Çıkan Paket",
            "icon": "",
        })

    def resolve_mission(self, mission_uuid: str) -> Dict[str, Any]:
        self.ensure_initialized()
        cleaned = str(mission_uuid or "").lower()
        m = self._missions_map.get(cleaned, {})
        return {
            "uuid": cleaned,
            "title": m.get("title") or "Günlük / Haftalık Görev",
            "xpGrant": m.get("xpGrant", 1000),
            "progressToComplete": m.get("progressToComplete", 1),
        }

    def resolve_season_name(self, season_uuid: str) -> str:
        self.ensure_initialized()
        cleaned = str(season_uuid or "").lower()
        return self._seasons_map.get(cleaned, {}).get("name", "Sezon")

    def resolve_mode(self, mode_identifier: str) -> str:
        if not mode_identifier:
            return "Bilinmiyor"

        raw = str(mode_identifier).strip().casefold().replace("\\", "/").replace(" ", "")

        if raw in MODE_NAMES:
            return MODE_NAMES[raw]

        for code, label in MODE_NAMES.items():
            if code in raw:
                return label

        self.ensure_initialized()
        for k, v in self._modes_map.items():
            if k in raw or raw in k:
                return v.get("name", "Özel Mod")

        return "Bilinmeyen Oyun Modu" if ("/game/" in raw or "_gamemode" in raw) else mode_identifier

    def get_endpoints_catalog(self) -> List[Dict[str, Any]]:
        catalog = []
        for ep in ALL_CONTENT_ENDPOINTS:
            key = f"{ep['id']}:{self.language}"
            is_cached = key in self._memory_cache or db.get_cached_endpoint(ep['id'], self.language) is not None
            catalog.append({
                "id": ep["id"],
                "name": ep["name"],
                "path": ep["path"],
                "full_url": f"{VALORANT_API_BASE}{ep['path']}",
                "description": ep["description"],
                "is_cached": is_cached,
            })
        return catalog


content_service = ContentService()
