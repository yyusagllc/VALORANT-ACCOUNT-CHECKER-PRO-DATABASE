"""
VALORANT ACCOUNT CHECKER & DATABASE
Hesap Kontrol Motoru ve Veri Zenginleştirme
dash.valorant-api.com ve Riot istemci API'lerini birleştirerek hiçbir veri eksik kalmayacak şekilde tam snapshot üretir.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import AP_PER_LEVEL, MATCH_COUNT, PENALTY_EFFECTS, STARTER_AGENT_UUIDS
from database.db import db
from services.content_service import content_service
from services.riot_service import (
    RiotClient,
    format_remaining_duration,
    format_time_local,
    parse_timestamp,
)

logger = logging.getLogger("ValoChecker.Engine")


class CheckerEngine:
    """Hesap kontrolünü yürüten ve veritabanı logunu oluşturan motor."""

    def __init__(self):
        content_service.ensure_initialized()

    def run_check(self, client: RiotClient, notes: str = "") -> Dict[str, Any]:
        """
        RiotClient üzerinden tüm verileri çeker, zenginleştirir, veritabanına kaydeder
        ve tam hesap verisi snapshot'ını döndürür.
        """
        logger.info(f"Hesap kontrolü başlatılıyor: {client.riot_id} ({client.region.upper()})")

        # 1. KİMLİK VE PROFİL BİLGİSİ
        account_identity = {
            "puuid": client.puuid,
            "game_name": client.game_name or "Oyuncu",
            "tag_line": client.tag_line or "VALO",
            "riot_id": client.riot_id,
            "region": client.region,
            "country": client.user_info.get("country", ""),
        }

        # 2. HESAP SEVİYESİ VE XP
        level_raw = client.get_account_xp()
        level_data = self._process_level(level_raw)
        first_win_data = self._process_first_win(level_raw)

        # 3. CÜZDAN / BAKİYELER (VP, RP, KC)
        wallet_raw = client.get_wallet()
        wallet_data = {
            "VP": wallet_raw.get("VP", 0),
            "RP": wallet_raw.get("RP", 0),
            "KC": wallet_raw.get("KC", 0),
            "currencies_meta": {
                "VP": {"name": "VALORANT Puanı", "symbol": "VP", "color": "#ff4655"},
                "RP": {"name": "Radyanit Puanı", "symbol": "RP", "color": "#00ffb3"},
                "KC": {"name": "Kingdom Kredisi", "symbol": "KC", "color": "#f0bd4f"},
            }
        }

        # 4. DERECELİ KADEME VE MMR (Sezon bazlı tam çözümleme)
        mmr_raw = client.get_mmr()
        rank_data = self._process_rank(mmr_raw)

        # 5. KUŞANILMIŞ ENVANTER (Kullanıcı talebi doğrultusunda pasifleştirildi)
        loadout_data = {
            "identity": {
                "card": content_service.resolve_card(""),
                "title": content_service.resolve_title(""),
                "border_uuid": "",
                "hide_account_level": False,
            },
            "guns": [],
            "sprays": [],
        }

        # 6. CEZALAR VE KISITLAMALAR
        penalties_raw = client.get_penalties()
        penalties_data = self._process_penalties(penalties_raw)

        # 7. GÜNLÜK MAĞAZA (Skinler, Fiyatlar, Paket, Gece Pazarı)
        storefront_raw = client.get_storefront()
        store_data = self._process_storefront(storefront_raw)

        # 8. GÖREVLER VE SAVAŞ BİLETİ KONTRATLARI
        contracts_raw = client.get_contracts_and_missions()
        missions_data = self._process_missions_and_contracts(contracts_raw)

        # 9. TÜM SAHİP OLUNAN ENVANTER (Skinler, Uğurluklar, Spreyler, Kartlar, Unvanlar, Ajanlar)
        entitlements_raw = client.get_all_entitlements()
        inventory_data = self._process_inventory(entitlements_raw, contracts_raw=contracts_raw)

        # 10. MAÇ GEÇMİŞİ VE MAÇ DETAYLARI
        match_ids = client.get_match_history(count=MATCH_COUNT)
        matches_data = self._process_matches(client, match_ids)

        # 11. KONTROL ZAMAN BİLGİSİ
        now_utc = datetime.now(timezone.utc)
        check_time_iso = now_utc.isoformat()
        check_time_local = now_utc.astimezone().strftime("%d.%m.%Y %H:%M:%S")

        # 12. BİRLEŞİK TAM SNAPSHOT
        snapshot = {
            "account": account_identity,
            "check_time_iso": check_time_iso,
            "check_time_local": check_time_local,
            "level": level_data,
            "first_win": first_win_data,
            "wallet": wallet_data,
            "rank": rank_data,
            "penalties": penalties_data,
            "loadout": loadout_data,
            "inventory": inventory_data,
            "owned_skins": inventory_data["skins"],
            "owned_skins_stats": inventory_data["skins_stats"],
            "store": store_data,
            "missions": missions_data,
            "contracts": missions_data.get("contracts", {}),
            "battlepass": missions_data.get("battlepass"),
            "matches": matches_data,
            "notes": notes,
        }

        # 13. VERİTABANINA LOG KAYDI YAPMA
        log_id = db.save_account_check(snapshot, notes=notes)
        snapshot["log_id"] = log_id

        logger.info(f"Hesap başarıyla kontrol edildi ve loglandı! Log ID: {log_id}")
        return snapshot

    # ========================================================
    # YARDIMCI İŞLEME METOTLARI
    # ========================================================

    def _process_level(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Seviye ve AP hesaplamalarını yapar."""
        progress = raw.get("Progress") or raw.get("progress") or {}
        level = progress.get("Level") or progress.get("level") or raw.get("Level") or 1
        xp = progress.get("XP") or progress.get("xp") or raw.get("XP") or 0

        try:
            level = int(level)
            xp = int(xp)
        except Exception:
            level = 1
            xp = 0

        total_ap = max(0, (level - 1) * AP_PER_LEVEL + xp)
        progress_percent = min(max((xp / AP_PER_LEVEL) * 100, 0), 100)
        remaining_xp = max(0, AP_PER_LEVEL - xp)

        border = content_service.resolve_level_border(level)

        return {
            "level": level,
            "xp": xp,
            "total_ap": total_ap,
            "ap_per_level": AP_PER_LEVEL,
            "remaining_xp": remaining_xp,
            "progress_percent": round(progress_percent, 1),
            "progress_text": f"{xp:,} / {AP_PER_LEVEL:,} AP".replace(",", "."),
            "border_icon": border.get("icon", ""),
            "border_level": border.get("level", 1),
        }

    def _process_first_win(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Günlük ilk galibiyet durumunu ve kalan süreyi hesaplar."""
        now = datetime.now(timezone.utc)
        last_time = parse_timestamp(raw.get("LastTimeGrantedFirstWin"))
        next_time = parse_timestamp(raw.get("NextTimeFirstWinAvailable"))

        if next_time:
            if next_time > now:
                remaining_sec = (next_time - now).total_seconds()
                detail = f"Yeniden hazır olmasına: {format_remaining_duration(int(remaining_sec))}"
                if last_time:
                    detail += f" (Son: {format_time_local(last_time)})"
                return {
                    "status": "Beklemede / Alındı",
                    "badge_class": "claimed",
                    "is_ready": False,
                    "detail": detail,
                    "next_available": format_time_local(next_time),
                    "last_granted": format_time_local(last_time),
                }
            return {
                "status": "Hazır",
                "badge_class": "ready",
                "is_ready": True,
                "detail": "Günlük ilk galibiyet bonusu (1.000 AP) şu an alınabilir!",
                "next_available": "Hemen",
                "last_granted": format_time_local(last_time),
            }

        if last_time:
            elapsed = (now - last_time).total_seconds()
            if elapsed < 86400:
                remaining_sec = 86400 - elapsed
                return {
                    "status": "Alındı",
                    "badge_class": "claimed",
                    "is_ready": False,
                    "detail": f"Son bonus: {format_time_local(last_time)} | Yenilenmeye: {format_remaining_duration(int(remaining_sec))}",
                    "next_available": format_remaining_duration(int(remaining_sec)),
                    "last_granted": format_time_local(last_time),
                }
            return {
                "status": "Hazır",
                "badge_class": "ready",
                "is_ready": True,
                "detail": "Son bonusun üzerinden 24 saat geçmiş, bonus hazır!",
                "next_available": "Hemen",
                "last_granted": format_time_local(last_time),
            }

        return {
            "status": "Bilinmiyor",
            "badge_class": "unknown",
            "is_ready": False,
            "detail": "Riot API bonus süresi döndürmedi.",
            "next_available": "Bilinmiyor",
            "last_granted": "Bilinmiyor",
        }

    def _process_rank(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """MMR verisinden güncel kademe, RR, geçen sezon ve tüm zamanların zirve kademesini eksiksiz çıkarır."""
        queue_skills = raw.get("QueueSkills", {}).get("competitive", {}) or {}
        latest_update = raw.get("LatestCompetitiveUpdate", {}) or {}
        seasonal_info = queue_skills.get("SeasonalInfoBySeasonID", {}) or {}

        current_season_uuid = content_service.get_current_season_uuid()
        current_season_data = seasonal_info.get(current_season_uuid) if current_season_uuid else None

        current_tier = 0
        rr = 0
        wins = 0
        games = 0
        leaderboard_rank = 0

        # 1. Öncelik: Aktif Kısım verisi
        if current_season_data:
            current_tier = current_season_data.get("CompetitiveTier", 0) or 0
            rr = current_season_data.get("RankedRating", 0) or 0
            wins = current_season_data.get("NumberOfWins", 0) or 0
            games = current_season_data.get("NumberOfGames", 0) or 0
            leaderboard_rank = current_season_data.get("LeaderboardRank", 0) or 0

        # 2. Öncelik: LatestCompetitiveUpdate
        if current_tier == 0:
            tier_upd = latest_update.get("TierAfterUpdate")
            if tier_upd is not None and tier_upd > 0:
                current_tier = tier_upd
                rr = latest_update.get("RankedRatingAfterUpdate", 0) or 0
                leaderboard_rank = latest_update.get("LeaderboardRank", 0) or 0

        # 3. Zirve Kademe (Peak Rank) ve Geçmiş En İyi Sezonu Bul
        peak_tier = current_tier
        peak_season_name = "Mevcut Kısım"
        prev_act_tier = 0
        prev_act_name = ""

        for s_id, s_data in seasonal_info.items():
            s_tier = s_data.get("CompetitiveTier", 0) or 0
            s_wins = s_data.get("NumberOfWins", 0) or 0
            s_name = content_service.resolve_season_name(s_id)

            if s_tier > peak_tier:
                peak_tier = s_tier
                peak_season_name = s_name

            # Eğer oyuncu bu kısım henüz oynamadıysa, en son oynadığı geçmiş kısmı bul
            if current_tier == 0 and s_tier > 0 and s_id != current_season_uuid:
                prev_act_tier = s_tier
                prev_act_name = s_name

        tier_resolved = content_service.resolve_rank(current_tier)
        peak_resolved = content_service.resolve_rank(peak_tier)
        prev_resolved = content_service.resolve_rank(prev_act_tier) if prev_act_tier > 0 else None

        return {
            "rank_tier": current_tier,
            "rank_name": tier_resolved["name"],
            "rank_color": tier_resolved["color"],
            "rank_icon": tier_resolved["icon"],
            "ranked_rating": rr,
            "peak_tier": peak_tier,
            "peak_rank": peak_resolved["name"],
            "peak_rank_icon": peak_resolved["icon"],
            "peak_season_name": peak_season_name,
            "previous_act_rank": prev_resolved["name"] if prev_resolved else None,
            "previous_act_season": prev_act_name if prev_resolved else None,
            "leaderboard_rank": leaderboard_rank,
            "seasonal_wins": wins,
            "seasonal_games": games,
        }

    def _process_penalties(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Cezaları, kısıtlamaları ve ihlalleri ayrıştırır."""
        now = datetime.now(timezone.utc)
        penalties_list = raw.get("Penalties", []) or []
        infractions_list = raw.get("Infractions", []) or []

        infraction_names = {}
        for inf in infractions_list:
            if isinstance(inf, dict):
                inf_id = str(inf.get("ID") or inf.get("Id") or "").lower()
                name = inf.get("Name") or inf.get("RatingName") or "Kural İhlali"
                if inf_id:
                    infraction_names[inf_id] = name

        records = []
        active_count = 0

        for p in penalties_list:
            if not isinstance(p, dict):
                continue

            effects = []
            for effect_key, label in PENALTY_EFFECTS.items():
                if p.get(effect_key):
                    effects.append(label)
            if not effects:
                effects.append("Hesap Yaptırımı")

            expiry = parse_timestamp(p.get("Expiry") or p.get("expiry"))
            games_remaining = p.get("GamesRemaining") or p.get("gamesRemaining")
            try:
                games_remaining = int(games_remaining) if games_remaining is not None else None
            except Exception:
                games_remaining = None

            is_active = False
            if expiry and expiry > now:
                is_active = True
            elif games_remaining and games_remaining > 0:
                is_active = True

            state = "Aktif" if is_active else ("Süresi Dolmuş" if expiry else "Tamamlanmış")
            if is_active:
                active_count += 1

            inf_id = str(p.get("InfractionID") or "").lower()
            inf_name = infraction_names.get(inf_id, "Oyun İçi Davranış")
            start_date = parse_timestamp(p.get("IssuingGameStartUnixMillis"))

            records.append({
                "type": ", ".join(effects),
                "is_active": is_active,
                "state": state,
                "badge_class": "bad" if is_active else "good",
                "expiry": format_time_local(expiry) if expiry else "Belirtilmemiş",
                "games_remaining": games_remaining if games_remaining is not None else "—",
                "infraction": inf_name,
                "issued_date": format_time_local(start_date) if start_date else "Bilinmiyor",
            })

        if active_count > 0:
            status = "Aktif Ceza Var"
            status_class = "bad"
            detail = f"Hesap üzerinde {active_count} aktif ceza/kısıtlama bulunuyor."
        elif records:
            status = "Geçmiş Cezalar Mevcut"
            status_class = "good"
            detail = f"{len(records)} adet geçmiş ceza kaydı bulundu, hepsi tamamlanmış/süresi dolmuş."
        else:
            status = "Temiz (Ceza Yok)"
            status_class = "good"
            detail = "Hesap üzerinde herhangi bir ceza veya yaptırım kaydı bulunmamaktadır."

        return {
            "status": status,
            "status_class": status_class,
            "active_count": active_count,
            "detail": detail,
            "records": records,
        }

    def _process_loadout(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Kuşanılmış silah skinleri, spreyler (tüm 4 yuva), kart, unvan ve çerçeveyi çözer."""
        loadout_core = raw.get("loadout") or raw.get("Loadout") or raw
        identity = loadout_core.get("Identity") or loadout_core.get("identity") or raw.get("Identity") or {}
        card_uuid = identity.get("PlayerCardID") or identity.get("playerCardId") or ""
        title_uuid = identity.get("PlayerTitleID") or identity.get("playerTitleId") or ""
        border_uuid = identity.get("PreferredLevelBorderID") or identity.get("preferredLevelBorderId") or ""

        card_info = content_service.resolve_card(card_uuid)
        title_info = content_service.resolve_title(title_uuid)

        equipped_guns = []
        guns_list = loadout_core.get("Guns") or loadout_core.get("guns") or raw.get("Guns") or []
        for g in guns_list:
            w_uuid = g.get("ID") or g.get("id") or ""
            weapon_meta = content_service.resolve_weapon(w_uuid) if w_uuid else {}
            base_weapon_name = weapon_meta.get("name") or "Silah"
            base_weapon_icon = weapon_meta.get("icon") or ""

            chroma_uuid = g.get("ChromaID") or g.get("chromaId")
            level_uuid = g.get("SkinLevelID") or g.get("skinLevelId")
            skin_uuid = g.get("SkinID") or g.get("skinId")
            buddy_uuid = g.get("CharmID") or g.get("CharmLevelID") or g.get("charmId")

            # Sıralı akıllı çözümleme: Chroma -> Level -> Skin
            skin_resolved = None
            for candidate_uuid in [chroma_uuid, level_uuid, skin_uuid]:
                if candidate_uuid:
                    res = content_service.resolve_skin(candidate_uuid)
                    if res and res.get("skin_name") != "Standart Silah":
                        skin_resolved = res
                        break

            if not skin_resolved and (skin_uuid or level_uuid or chroma_uuid):
                skin_resolved = content_service.resolve_skin(skin_uuid or level_uuid or chroma_uuid)

            if not skin_resolved:
                skin_resolved = {
                    "skin_uuid": skin_uuid or "",
                    "weapon_name": base_weapon_name,
                    "skin_name": f"Standart {base_weapon_name}",
                    "theme_name": "Standart",
                    "icon": base_weapon_icon,
                    "rarity": "Standart",
                    "rarity_color": "#ece8e1",
                    "rarity_icon": "",
                }

            if not skin_resolved.get("icon"):
                skin_resolved["icon"] = base_weapon_icon

            if skin_resolved.get("weapon_name") in ("Standart", "Bilinmeyen Silah") and base_weapon_name:
                skin_resolved["weapon_name"] = base_weapon_name

            buddy_resolved = content_service.resolve_buddy(buddy_uuid) if buddy_uuid else None

            is_custom = not (
                skin_resolved["skin_name"].lower().startswith("standart") or
                skin_resolved["skin_name"].lower() == "standart silah"
            )

            equipped_guns.append({
                "weapon_uuid": w_uuid,
                "weapon_name": skin_resolved["weapon_name"],
                "skin_name": skin_resolved["skin_name"],
                "theme_name": skin_resolved.get("theme_name", ""),
                "icon": skin_resolved["icon"],
                "rarity": skin_resolved["rarity"],
                "rarity_color": skin_resolved["rarity_color"],
                "rarity_icon": skin_resolved.get("rarity_icon", ""),
                "is_custom": is_custom,
                "buddy": buddy_resolved["name"] if buddy_resolved else None,
                "buddy_icon": buddy_resolved["icon"] if buddy_resolved else None,
            })

        equipped_sprays = []
        sprays_list = loadout_core.get("Sprays") or loadout_core.get("sprays") or raw.get("Sprays") or []
        for s in sprays_list:
            spray_uuid = s.get("SprayID") or s.get("sprayId")
            slot_id = s.get("EquipSlotID") or s.get("equipSlotId")
            spray_resolved = content_service.resolve_spray(spray_uuid)
            equipped_sprays.append({
                "slot_id": slot_id,
                "name": spray_resolved["name"],
                "icon": spray_resolved["icon"],
            })

        return {
            "identity": {
                "card": card_info,
                "title": title_info,
                "border_uuid": border_uuid,
                "hide_account_level": identity.get("HideAccountLevelFromOthers", False),
            },
            "guns": equipped_guns,
            "sprays": equipped_sprays,
        }

    def _process_storefront(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Günlük mağaza 4 skinini, fiyatlarını (VP), paketi, gece pazarını ve aksesuar mağazasını ayrıştırır."""
        daily_offers = []
        skins_panel = raw.get("SkinsPanelLayout") or raw.get("skinsPanelLayout") or {}
        single_offers = skins_panel.get("SingleItemOffers") or skins_panel.get("singleItemOffers") or []
        store_offers = skins_panel.get("SingleItemStoreOffers") or skins_panel.get("singleItemStoreOffers") or []
        remaining_sec = skins_panel.get("SingleItemOffersRemainingDurationInSeconds") or skins_panel.get("singleItemOffersRemainingDurationInSeconds") or 0

        # Fiyat ve Reward haritası oluştur (OfferID -> VP maliyeti ve Reward ItemID)
        offer_to_price = {}
        offer_to_item = {}
        for so in store_offers:
            offer_id = str(so.get("OfferID") or so.get("offerId") or "").lower()
            cost = so.get("Cost") or so.get("cost") or {}
            vp_price = list(cost.values())[0] if cost else 1775
            if offer_id:
                offer_to_price[offer_id] = vp_price

            rewards = so.get("Rewards") or so.get("rewards") or []
            for r in rewards:
                item_id = r.get("ItemID") or r.get("itemId")
                if item_id:
                    offer_to_item[offer_id] = str(item_id).lower()
                    break

        seen_skin_uuids = set()

        # 1. single_offers listesinden çöz
        for s_id in single_offers:
            s_str = str(s_id).lower()
            skin = content_service.resolve_skin(s_str)
            # Eğer doğrudan eşleşmediyse reward item ID üzerinden dene
            if (not skin or skin.get("skin_name") == "Standart Silah") and s_str in offer_to_item:
                skin = content_service.resolve_skin(offer_to_item[s_str])

            price = offer_to_price.get(s_str, 1775)
            skin_uuid = skin.get("skin_uuid") or s_str
            if skin_uuid and skin_uuid not in seen_skin_uuids and skin.get("skin_name") != "Standart Silah":
                seen_skin_uuids.add(skin_uuid)
                daily_offers.append({
                    "skin_uuid": skin_uuid,
                    "weapon_name": skin.get("weapon_name", "Silah"),
                    "skin_name": skin.get("skin_name", "Bilinmeyen Skin"),
                    "theme_name": skin.get("theme_name", ""),
                    "icon": skin.get("icon", ""),
                    "rarity": skin.get("rarity", "Standart"),
                    "rarity_color": skin.get("rarity_color", "#ece8e1"),
                    "price": price,
                })

        # 2. Eğer daily_offers 4'ten azsa ve store_offers varsa, store_offers üzerinden eksikleri tamamla
        if len(daily_offers) < 4 and store_offers:
            for so in store_offers:
                offer_id = str(so.get("OfferID") or so.get("offerId") or "").lower()
                cost = so.get("Cost") or so.get("cost") or {}
                price = list(cost.values())[0] if cost else 1775

                target_item_id = offer_to_item.get(offer_id, offer_id)
                skin = content_service.resolve_skin(target_item_id)
                if not skin or skin.get("skin_name") == "Standart Silah":
                    skin = content_service.resolve_skin(offer_id)

                skin_uuid = skin.get("skin_uuid") or target_item_id
                if skin_uuid and skin_uuid not in seen_skin_uuids:
                    seen_skin_uuids.add(skin_uuid)
                    daily_offers.append({
                        "skin_uuid": skin_uuid,
                        "weapon_name": skin.get("weapon_name", "Silah"),
                        "skin_name": skin.get("skin_name", "Bilinmeyen Skin"),
                        "theme_name": skin.get("theme_name", ""),
                        "icon": skin.get("icon", ""),
                        "rarity": skin.get("rarity", "Standart"),
                        "rarity_color": skin.get("rarity_color", "#ece8e1"),
                        "price": price,
                    })

        # Öne çıkan paket
        bundle_info = None
        featured_bundle = raw.get("FeaturedBundle") or raw.get("featuredBundle") or {}
        bundle_data = featured_bundle.get("Bundle") or featured_bundle.get("bundle") or {}
        if not bundle_data and featured_bundle.get("Bundles"):
            sub_bundles = featured_bundle.get("Bundles") or []
            if isinstance(sub_bundles, list) and len(sub_bundles) > 0:
                bundle_data = sub_bundles[0]

        bundle_uuid = bundle_data.get("DataAssetID") or bundle_data.get("dataAssetId") or bundle_data.get("ID") or bundle_data.get("id")
        if bundle_uuid:
            res_b = content_service.resolve_bundle(bundle_uuid)
            base_cost_dict = bundle_data.get("TotalBaseCost") or bundle_data.get("totalBaseCost") or {}
            disc_cost_dict = bundle_data.get("TotalDiscountedCost") or bundle_data.get("totalDiscountedCost") or {}
            total_base = list(base_cost_dict.values())[0] if base_cost_dict else 0
            total_disc = list(disc_cost_dict.values())[0] if disc_cost_dict else total_base

            bundle_items = []
            for b_item in bundle_data.get("Items") or bundle_data.get("items") or []:
                item_details = b_item.get("Item") or b_item.get("item") or {}
                item_id = item_details.get("ItemID") or item_details.get("itemId")
                res_skin = content_service.resolve_skin(item_id)
                bundle_items.append({
                    "name": res_skin["skin_name"],
                    "icon": res_skin["icon"],
                    "base_price": b_item.get("BasePrice", 0),
                    "discounted_price": b_item.get("DiscountedPrice", 0),
                })

            rem_duration = featured_bundle.get("BundleRemainingDurationInSeconds") or featured_bundle.get("bundleRemainingDurationInSeconds") or 0
            bundle_info = {
                "bundle_uuid": bundle_uuid,
                "name": res_b["name"],
                "icon": res_b["icon"],
                "remaining_seconds": rem_duration,
                "remaining_duration_text": format_remaining_duration(rem_duration),
                "total_base_cost": total_base,
                "total_discounted_cost": total_disc,
                "items": bundle_items,
            }

        # Gece Pazarı (Bonus Store)
        bonus_store = raw.get("BonusStore") or raw.get("bonusStore") or {}
        night_market_offers = []
        bonus_rem_sec = bonus_store.get("BonusStoreRemainingDurationInSeconds") or bonus_store.get("bonusStoreRemainingDurationInSeconds") or 0
        for offer in bonus_store.get("BonusStoreOffers") or bonus_store.get("bonusStoreOffers") or []:
            offer_obj = offer.get("Offer") or offer.get("offer") or {}
            rewards = offer_obj.get("Rewards") or offer_obj.get("rewards") or []
            discount_percent = offer.get("DiscountPercent") or offer.get("discountPercent") or 0
            disc_costs = offer.get("DiscountCosts") or offer.get("discountCosts") or {}
            orig_costs = offer_obj.get("Cost") or offer_obj.get("cost") or {}
            cost = list(disc_costs.values())[0] if disc_costs else 0
            orig_cost = list(orig_costs.values())[0] if orig_costs else cost
            discount_saved = max(0, orig_cost - cost)

            target_item_id = None
            for reward in rewards:
                target_item_id = reward.get("ItemID") or reward.get("itemId")
                if target_item_id:
                    break
            if not target_item_id:
                target_item_id = offer_obj.get("OfferID") or offer_obj.get("offerId")

            r_skin = content_service.resolve_skin(target_item_id) if target_item_id else None
            if not r_skin or r_skin.get("skin_name") == "Standart Silah":
                off_id = offer_obj.get("OfferID") or offer_obj.get("offerId")
                if off_id:
                    r_skin = content_service.resolve_skin(off_id)

            if not r_skin:
                r_skin = {
                    "skin_uuid": target_item_id or "",
                    "weapon_name": "Silah",
                    "skin_name": "Gece Pazarı Kaplaması",
                    "theme_name": "",
                    "icon": "",
                    "rarity": "Özel",
                    "rarity_color": "#a855f7",
                }

            night_market_offers.append({
                "skin_uuid": r_skin.get("skin_uuid") or target_item_id,
                "weapon_name": r_skin.get("weapon_name", "Silah"),
                "skin_name": r_skin.get("skin_name", "Gece Pazarı Skini"),
                "theme_name": r_skin.get("theme_name", ""),
                "icon": r_skin.get("icon", ""),
                "rarity": r_skin.get("rarity", "Seçkin"),
                "rarity_color": r_skin.get("rarity_color", "#a855f7"),
                "original_cost": orig_cost,
                "discounted_cost": cost,
                "discount_percent": discount_percent,
                "discount_saved": discount_saved,
            })

        # Aksesuar Mağazası (Accessory Store - Kingdom Credits)
        accessory_store = raw.get("AccessoryStore") or raw.get("accessoryStore") or {}
        acc_offers = []
        for acc_o in accessory_store.get("AccessoryStoreOffers") or accessory_store.get("accessoryStoreOffers") or []:
            off = acc_o.get("Offer") or acc_o.get("offer") or {}
            off_cost = off.get("Cost") or off.get("cost") or {}
            kc_price = list(off_cost.values())[0] if off_cost else 0
            for rew in off.get("Rewards") or off.get("rewards") or []:
                rew_id = rew.get("ItemID") or rew.get("itemId")
                card_r = content_service.resolve_card(rew_id)
                if card_r.get("wideArt"):
                    acc_offers.append({"name": card_r["name"], "icon": card_r["wideArt"], "cost_kc": kc_price, "type": "Kart"})
                else:
                    spray_r = content_service.resolve_spray(rew_id)
                    if spray_r.get("name") != "Sprey":
                        acc_offers.append({"name": spray_r["name"], "icon": spray_r["icon"], "cost_kc": kc_price, "type": "Sprey"})
                    else:
                        buddy_r = content_service.resolve_buddy(rew_id)
                        acc_offers.append({"name": buddy_r["name"], "icon": buddy_r["icon"], "cost_kc": kc_price, "type": "Uğurluk"})

        return {
            "daily_offers": daily_offers,
            "remaining_seconds": remaining_sec,
            "remaining_duration_text": format_remaining_duration(remaining_sec),
            "featured_bundle": bundle_info,
            "night_market": {
                "is_active": len(night_market_offers) > 0,
                "offers": night_market_offers,
                "remaining_seconds": bonus_rem_sec,
                "remaining_duration_text": format_remaining_duration(bonus_rem_sec) if bonus_rem_sec else "Bilinmiyor",
            },
            "accessory_store": {
                "is_active": len(acc_offers) > 0,
                "offers": acc_offers,
            }
        }

    def _process_inventory(self, all_entitlements: Dict[str, List[str]], contracts_raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Tüm envanter kategorilerini (Skinler, Uğurluklar, Spreyler, Kartlar, Unvanlar, Ajanlar) ayrıştırır."""
        # 1. Silah Skinleri
        unique_skins = {}
        weapons_grouped = {}
        rarity_counts = {}

        for item_uuid in all_entitlements.get("skins", []):
            skin = content_service.resolve_skin(item_uuid)
            skin_name = skin.get("skin_name", "")
            weapon_name = skin.get("weapon_name", "Standart")

            if skin_name.lower().startswith("standart ") or skin_name.lower() == "standart":
                continue

            unique_key = f"{weapon_name}:{skin_name}"
            if unique_key not in unique_skins:
                entry = {
                    "skin_uuid": skin.get("skin_uuid"),
                    "weapon_name": weapon_name,
                    "skin_name": skin_name,
                    "theme_name": skin.get("theme_name", ""),
                    "icon": skin.get("icon"),
                    "rarity": skin.get("rarity", "Standart"),
                    "rarity_color": skin.get("rarity_color", "#ece8e1"),
                    "rarity_icon": skin.get("rarity_icon", ""),
                }
                unique_skins[unique_key] = entry
                if weapon_name not in weapons_grouped:
                    weapons_grouped[weapon_name] = []
                weapons_grouped[weapon_name].append(entry)

                rarity = entry["rarity"]
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        skins_list = list(unique_skins.values())
        skins_list.sort(key=lambda s: (s["weapon_name"], s["skin_name"]))

        # 2. Uğurluklar (Buddies)
        buddies_list = []
        for b_uuid in all_entitlements.get("buddies", []):
            res_b = content_service.resolve_buddy(b_uuid)
            if res_b.get("name") and res_b["name"] != "Uğurluk":
                buddies_list.append(res_b)

        # 3. Spreyler
        sprays_list = []
        for s_uuid in all_entitlements.get("sprays", []):
            res_s = content_service.resolve_spray(s_uuid)
            if res_s.get("name") and res_s["name"] != "Sprey":
                sprays_list.append(res_s)

        # 4. Oyuncu Kartları
        cards_list = []
        for c_uuid in all_entitlements.get("cards", []):
            res_c = content_service.resolve_card(c_uuid)
            if res_c.get("wideArt") or res_c.get("largeArt"):
                cards_list.append(res_c)

        # 5. Oyuncu Unvanları
        titles_list = []
        for t_uuid in all_entitlements.get("titles", []):
            res_t = content_service.resolve_title(t_uuid)
            if res_t.get("titleText"):
                titles_list.append(res_t)

        # 6. Ajanlar (Tüm 26 Oynanabilir Ajan Kadrosu + Açık/Kilitli Durumu)
        owned_agent_ids = set(str(a).lower() for a in all_entitlements.get("agents", []))
        for starter_uuid in STARTER_AGENT_UUIDS:
            owned_agent_ids.add(starter_uuid.lower())

        # Kontratlar üzerinden açılmış ajanları da kontrol et (Secondary fallback)
        if contracts_raw:
            contracts_list = contracts_raw.get("Contracts") or contracts_raw.get("contracts") or []
            for c in contracts_list:
                c_id = str(c.get("ContractDefinitionID") or c.get("contractDefinitionId") or "").lower()
                res_c = content_service.resolve_contract(c_id)
                if res_c.get("relationType") == "Agent" and res_c.get("relationUuid"):
                    prog = c.get("ContractProgression") or c.get("contractProgression") or {}
                    total_xp = prog.get("TotalProgressionEarned", 0) or 0
                    lvl_reached = prog.get("ProgressionLevelReached", 0) or 0
                    if total_xp >= 175000 or lvl_reached >= 5 or c.get("State") == "completed":
                        owned_agent_ids.add(str(res_c["relationUuid"]).lower())

        all_playable_agents = [a for a in content_service.get_agents() if a.get("isPlayableCharacter")]
        agents_roster = []
        for agent_raw in all_playable_agents:
            a_uuid = str(agent_raw.get("uuid", "")).lower()
            is_unlocked = a_uuid in owned_agent_ids
            role_obj = agent_raw.get("role", {}) or {}
            abilities_raw = agent_raw.get("abilities", []) or []
            abilities_list = []
            for ab in abilities_raw:
                if ab.get("displayName"):
                    abilities_list.append({
                        "slot": ab.get("slot", ""),
                        "name": ab.get("displayName", ""),
                        "description": ab.get("description", ""),
                        "icon": ab.get("displayIcon", ""),
                    })

            agents_roster.append({
                "uuid": a_uuid,
                "name": agent_raw.get("displayName", "Ajan"),
                "role": role_obj.get("displayName", "Ajan"),
                "role_icon": role_obj.get("displayIcon", ""),
                "description": agent_raw.get("description", ""),
                "icon": agent_raw.get("displayIcon", ""),
                "fullPortrait": agent_raw.get("fullPortrait", ""),
                "killfeedPortrait": agent_raw.get("killfeedPortrait", ""),
                "is_unlocked": is_unlocked,
                "abilities": abilities_list,
            })

        # Açık olanları önce, sonra alfabetik sırala
        agents_roster.sort(key=lambda a: (not a["is_unlocked"], a["name"]))
        unlocked_count = sum(1 for a in agents_roster if a["is_unlocked"])

        return {
            "skins": skins_list,
            "buddies": buddies_list,
            "sprays": sprays_list,
            "cards": cards_list,
            "titles": titles_list,
            "agents": [a for a in agents_roster if a["is_unlocked"]],
            "agents_roster": agents_roster,
            "skins_stats": {
                "total_custom_skins": len(skins_list),
                "total_weapons_covered": len(weapons_grouped),
                "rarity_distribution": rarity_counts,
            },
            "counts": {
                "skins": len(skins_list),
                "buddies": len(buddies_list),
                "sprays": len(sprays_list),
                "cards": len(cards_list),
                "titles": len(titles_list),
                "unlocked_agents": unlocked_count,
                "total_agents": len(agents_roster),
                "agents": unlocked_count,
            }
        }

    def _process_missions_and_contracts(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Görevler, Savaş Bileti ve Ajan kontrat ilerlemelerini tam çözümler."""
        daily_missions = []
        weekly_missions = []

        missions_list = raw.get("Missions") or raw.get("missions") or []
        for m in missions_list:
            m_id = m.get("ID") or m.get("id")
            res_m = content_service.resolve_mission(m_id)
            complete = m.get("Complete", False) or m.get("complete", False)
            objectives = m.get("Objectives") or m.get("objectives") or {}
            progress_val = list(objectives.values())[0] if objectives else 0
            target_val = res_m["progressToComplete"]

            m_entry = {
                "title": res_m["title"],
                "xp_reward": res_m["xpGrant"],
                "progress": progress_val,
                "target": target_val,
                "complete": complete,
            }

            if res_m.get("xpGrant", 0) > 4000:
                weekly_missions.append(m_entry)
            else:
                daily_missions.append(m_entry)

        # Kontratlar ve Savaş Bileti Ayrıştırma
        contracts_list = raw.get("Contracts") or raw.get("contracts") or []
        active_special_uuid = raw.get("ActiveSpecialContract") or raw.get("activeSpecialContract") or ""

        battlepass = None
        if active_special_uuid:
            res_bp = content_service.resolve_contract(active_special_uuid)
            bp_contract_data = next((c for c in contracts_list if str(c.get("ContractDefinitionID") or c.get("contractDefinitionId") or "").lower() == str(active_special_uuid).lower()), {})
            prog = bp_contract_data.get("ContractProgression") or bp_contract_data.get("contractProgression") or {}
            battlepass = {
                "contract_uuid": active_special_uuid,
                "name": res_bp["name"],
                "total_xp": prog.get("TotalProgressionEarned", 0),
                "display_icon": res_bp.get("displayIcon", ""),
                "chapters_count": len(res_bp.get("chapters", [])),
            }

        # Aktif Ajan Kontratları
        agent_contracts = []
        for c in contracts_list:
            c_id = str(c.get("ContractDefinitionID") or c.get("contractDefinitionId") or "").lower()
            res_c = content_service.resolve_contract(c_id)
            if res_c.get("relationType") == "Agent":
                prog = c.get("ContractProgression") or c.get("contractProgression") or {}
                total_xp = prog.get("TotalProgressionEarned", 0)
                if total_xp > 0:
                    agent_contracts.append({
                        "name": res_c["name"],
                        "agent_uuid": res_c["relationUuid"],
                        "total_xp": total_xp,
                        "state": c.get("State") or c.get("state") or "",
                    })
        agent_contracts.sort(key=lambda x: x["total_xp"], reverse=True)

        return {
            "daily_missions": daily_missions,
            "weekly_missions": weekly_missions,
            "has_missions": len(daily_missions) > 0 or len(weekly_missions) > 0,
            "battlepass": battlepass,
            "agent_contracts": agent_contracts,
        }

    def _process_matches(self, client: RiotClient, match_ids: List[str]) -> List[Dict[str, Any]]:
        """Son maçları detaylarıyla ve KDA/ACS/Skor ile işler."""
        processed_matches = []
        user_puuid = str(client.puuid or "").lower()

        for mid in match_ids[:MATCH_COUNT]:
            details = client.get_match_details(mid)
            if not details:
                continue

            match_info = details.get("matchInfo", {}) or {}
            map_id = match_info.get("mapId", "")
            map_data = content_service.resolve_map(map_id)
            game_mode = content_service.resolve_mode(match_info.get("queueID") or match_info.get("gameMode", ""))

            start_time = parse_timestamp(match_info.get("gameStartMillis"))
            start_time_text = format_time_local(start_time)

            players = details.get("players", []) or []
            user_player = next((p for p in players if str(p.get("subject", "")).lower() == user_puuid), None)
            if not user_player:
                continue

            agent_uuid = user_player.get("characterId")
            agent_data = content_service.resolve_agent(agent_uuid)

            stats = user_player.get("stats", {}) or {}
            kills = stats.get("kills", 0) or 0
            deaths = stats.get("deaths", 0) or 0
            assists = stats.get("assists", 0) or 0
            score = stats.get("score", 0) or 0
            rounds_played = stats.get("roundsPlayed", 1) or 1
            kd_ratio = round(kills / max(1, deaths), 2)
            acs = round(score / max(1, rounds_played))

            user_team_id = user_player.get("teamId")
            teams = details.get("teams", []) or []
            user_team = next((t for t in teams if str(t.get("teamId")).lower() == str(user_team_id).lower()), {})
            enemy_team = next((t for t in teams if str(t.get("teamId")).lower() != str(user_team_id).lower()), {})

            won = user_team.get("won")
            rounds_won = user_team.get("roundsWon", 0) or 0
            rounds_lost = enemy_team.get("roundsWon", 0) or 0

            result_text = "Galibiyet" if won is True else ("Mağlubiyet" if won is False else "Beraberlik")
            result_class = "win" if won is True else ("loss" if won is False else "draw")

            processed_matches.append({
                "match_id": mid,
                "date": start_time_text,
                "map_name": map_data["name"],
                "map_splash": map_data["splash"],
                "game_mode": game_mode,
                "agent_name": agent_data["name"],
                "agent_role": agent_data["role"],
                "agent_icon": agent_data["killfeedPortrait"] or agent_data["icon"],
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "kd_ratio": kd_ratio,
                "acs": acs,
                "kda_text": f"{kills}/{deaths}/{assists}",
                "score_text": f"{rounds_won} - {rounds_lost}",
                "result": result_text,
                "result_class": result_class,
            })

        return processed_matches


checker_engine = CheckerEngine()
