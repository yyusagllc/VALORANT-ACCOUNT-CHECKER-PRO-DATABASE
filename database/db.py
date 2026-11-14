"""
VALORANT ACCOUNT CHECKER & DATABASE
SQLite Veritabanı Yöneticisi ve CRUD İşlemleri
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Veritabanı bağlantısı döndürür."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Gerekli tabloları ve indeksleri oluşturur."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. HESAPLAR TABLOSU
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            puuid TEXT PRIMARY KEY,
            game_name TEXT,
            tag_line TEXT,
            riot_id TEXT NOT NULL,
            region TEXT NOT NULL,
            country TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            total_checks INTEGER DEFAULT 1,
            last_level INTEGER DEFAULT 0,
            last_xp INTEGER DEFAULT 0,
            last_total_ap INTEGER DEFAULT 0,
            last_rank_tier INTEGER DEFAULT 0,
            last_rank_name TEXT DEFAULT 'Derecesiz',
            last_rr INTEGER DEFAULT 0,
            last_peak_rank TEXT DEFAULT 'Derecesiz',
            last_vp INTEGER DEFAULT 0,
            last_rp INTEGER DEFAULT 0,
            last_kc INTEGER DEFAULT 0,
            last_penalty_status TEXT DEFAULT 'Temiz',
            last_skins_count INTEGER DEFAULT 0,
            last_card_image TEXT,
            last_title TEXT
        );
        """)

        # 2. DETAYLI KONTROL LOGLARI TABLOSU
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS check_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_puuid TEXT NOT NULL,
            check_date TEXT NOT NULL,
            check_date_local TEXT NOT NULL,
            region TEXT NOT NULL,
            riot_id TEXT NOT NULL,
            level INTEGER DEFAULT 0,
            current_xp INTEGER DEFAULT 0,
            total_ap INTEGER DEFAULT 0,
            first_win_status TEXT,
            first_win_detail TEXT,
            rank_name TEXT,
            rank_tier INTEGER DEFAULT 0,
            ranked_rating INTEGER DEFAULT 0,
            peak_rank TEXT,
            leaderboard_rank INTEGER DEFAULT 0,
            wallet_vp INTEGER DEFAULT 0,
            wallet_rp INTEGER DEFAULT 0,
            wallet_kc INTEGER DEFAULT 0,
            penalty_status TEXT,
            penalty_active_count INTEGER DEFAULT 0,
            penalty_detail TEXT,
            skins_count INTEGER DEFAULT 0,
            matches_count INTEGER DEFAULT 0,
            equipped_card_url TEXT,
            equipped_title TEXT,
            snapshot_json TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (account_puuid) REFERENCES accounts(puuid) ON DELETE CASCADE
        );
        """)

        # 3. İÇERİK ÖNBELLEK TABLOSU (valorant-api.com için)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_cache (
            cache_key TEXT PRIMARY KEY,
            endpoint_name TEXT NOT NULL,
            language TEXT NOT NULL,
            data_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # İndeksler
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_updated ON accounts(updated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_puuid_date ON check_logs(account_puuid, check_date DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON check_logs(check_date DESC);")
        conn.commit()


class DatabaseManager:
    """Veritabanı işlemlerini yöneten sınıf."""

    def __init__(self):
        init_db()

    @staticmethod
    def now_timestamps() -> Tuple[str, str]:
        """UTC ISO formatında ve yerel Türkçe formatında zaman damgaları üretir."""
        now_utc = datetime.now(timezone.utc)
        iso_str = now_utc.isoformat()
        local_str = now_utc.astimezone().strftime("%d.%m.%Y %H:%M:%S")
        return iso_str, local_str

    def save_account_check(self, snapshot: Dict[str, Any], notes: str = "") -> int:
        """
        Bir hesap kontrolünü detaylıca loglar ve hesap kaydını günceller/oluşturur.
        snapshot: Kontrol edilen hesaba ait tüm verileri içeren zengin sözlük.
        Döndürür: Oluşturulan check_logs id numarası.
        """
        iso_now, local_now = self.now_timestamps()

        account_info = snapshot.get("account", {})
        puuid = account_info.get("puuid")
        if not puuid:
            raise ValueError("Kayıt için PUUID zorunludur.")

        game_name = account_info.get("game_name", "")
        tag_line = account_info.get("tag_line", "")
        riot_id = f"{game_name}#{tag_line}" if (game_name and tag_line) else account_info.get("riot_id", puuid[:8])
        region = account_info.get("region", "eu")
        country = account_info.get("country", "")

        level_info = snapshot.get("level", {})
        level = level_info.get("level", 0) or 0
        current_xp = level_info.get("xp", 0) or 0
        total_ap = level_info.get("total_ap", 0) or 0

        first_win = snapshot.get("first_win", {})
        first_win_status = first_win.get("status", "Bilinmiyor")
        first_win_detail = first_win.get("detail", "")

        rank_info = snapshot.get("rank", {})
        rank_name = rank_info.get("rank_name", "Derecesiz")
        rank_tier = rank_info.get("rank_tier", 0) or 0
        rr = rank_info.get("ranked_rating", 0) or 0
        peak_rank = rank_info.get("peak_rank", rank_name)
        leaderboard_rank = rank_info.get("leaderboard_rank", 0) or 0

        wallet = snapshot.get("wallet", {})
        vp = wallet.get("VP", 0) or 0
        rp = wallet.get("RP", 0) or 0
        kc = wallet.get("KC", 0) or 0

        penalty_info = snapshot.get("penalties", {})
        penalty_status = penalty_info.get("status", "Temiz")
        penalty_active_count = penalty_info.get("active_count", 0) or 0
        penalty_detail = penalty_info.get("detail", "")

        skins_list = snapshot.get("owned_skins", [])
        skins_count = len(skins_list) if isinstance(skins_list, list) else 0

        matches = snapshot.get("matches", [])
        matches_count = len(matches) if isinstance(matches, list) else 0

        loadout = snapshot.get("loadout", {})
        equipped_card = loadout.get("identity", {}).get("card", {}).get("wideArt") or loadout.get("identity", {}).get("card", {}).get("smallIcon") or ""
        equipped_title = loadout.get("identity", {}).get("title", {}).get("titleText") or loadout.get("identity", {}).get("title", {}).get("displayName") or ""

        # JSON serileştirme
        snapshot_json = json.dumps(snapshot, ensure_ascii=False, default=str)

        with get_connection() as conn:
            cursor = conn.cursor()

            # 1. Accounts tablosunu kontrol et ve güncelle / ekle
            cursor.execute("SELECT puuid, total_checks, created_at FROM accounts WHERE puuid = ?", (puuid,))
            existing = cursor.fetchone()

            if existing:
                total_checks = existing["total_checks"] + 1
                cursor.execute("""
                UPDATE accounts SET
                    game_name = ?,
                    tag_line = ?,
                    riot_id = ?,
                    region = ?,
                    country = ?,
                    updated_at = ?,
                    total_checks = ?,
                    last_level = ?,
                    last_xp = ?,
                    last_total_ap = ?,
                    last_rank_tier = ?,
                    last_rank_name = ?,
                    last_rr = ?,
                    last_peak_rank = ?,
                    last_vp = ?,
                    last_rp = ?,
                    last_kc = ?,
                    last_penalty_status = ?,
                    last_skins_count = ?,
                    last_card_image = ?,
                    last_title = ?
                WHERE puuid = ?
                """, (
                    game_name, tag_line, riot_id, region, country,
                    iso_now, total_checks, level, current_xp, total_ap,
                    rank_tier, rank_name, rr, peak_rank,
                    vp, rp, kc, penalty_status, skins_count,
                    equipped_card, equipped_title, puuid
                ))
            else:
                cursor.execute("""
                INSERT INTO accounts (
                    puuid, game_name, tag_line, riot_id, region, country,
                    created_at, updated_at, total_checks,
                    last_level, last_xp, last_total_ap,
                    last_rank_tier, last_rank_name, last_rr, last_peak_rank,
                    last_vp, last_rp, last_kc, last_penalty_status,
                    last_skins_count, last_card_image, last_title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    puuid, game_name, tag_line, riot_id, region, country,
                    iso_now, iso_now,
                    level, current_xp, total_ap,
                    rank_tier, rank_name, rr, peak_rank,
                    vp, rp, kc, penalty_status,
                    skins_count, equipped_card, equipped_title
                ))

            # 2. Check Logs tablosuna yeni kontrol kaydı ekle
            cursor.execute("""
            INSERT INTO check_logs (
                account_puuid, check_date, check_date_local, region, riot_id,
                level, current_xp, total_ap,
                first_win_status, first_win_detail,
                rank_name, rank_tier, ranked_rating, peak_rank, leaderboard_rank,
                wallet_vp, wallet_rp, wallet_kc,
                penalty_status, penalty_active_count, penalty_detail,
                skins_count, matches_count,
                equipped_card_url, equipped_title,
                snapshot_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                puuid, iso_now, local_now, region, riot_id,
                level, current_xp, total_ap,
                first_win_status, first_win_detail,
                rank_name, rank_tier, rr, peak_rank, leaderboard_rank,
                vp, rp, kc,
                penalty_status, penalty_active_count, penalty_detail,
                skins_count, matches_count,
                equipped_card, equipped_title,
                snapshot_json, notes
            ))

            log_id = cursor.lastrowid
            conn.commit()
            return log_id

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Tüm hesapları son güncelleme sırasına göre listeler."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_account(self, puuid: str) -> Optional[Dict[str, Any]]:
        """Tek bir hesabın temel bilgilerini ve en son log kaydını getirir."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE puuid = ?", (puuid,))
            row = cursor.fetchone()
            if not row:
                return None

            account = dict(row)
            # En son log kaydını çek
            cursor.execute(
                "SELECT * FROM check_logs WHERE account_puuid = ? ORDER BY id DESC LIMIT 1",
                (puuid,)
            )
            latest_log = cursor.fetchone()
            if latest_log:
                latest_log_dict = dict(latest_log)
                try:
                    latest_log_dict["snapshot"] = json.loads(latest_log_dict["snapshot_json"])
                except Exception:
                    latest_log_dict["snapshot"] = {}
                account["latest_log"] = latest_log_dict
            else:
                account["latest_log"] = None

            return account

    def get_account_logs(self, puuid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Bir hesaba ait geçmiş kontrol loglarını kronolojik olarak (en yeniden eskiye) getirir."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, account_puuid, check_date, check_date_local, region, riot_id,
                   level, current_xp, total_ap, first_win_status, rank_name, rank_tier,
                   ranked_rating, peak_rank, wallet_vp, wallet_rp, wallet_kc,
                   penalty_status, penalty_active_count, skins_count, matches_count,
                   equipped_card_url, equipped_title, notes
            FROM check_logs
            WHERE account_puuid = ?
            ORDER BY id DESC
            LIMIT ?
            """, (puuid, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_log(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Belirli bir kontrol kaydını tam snapshot verisiyle birlikte getirir."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM check_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            try:
                data["snapshot"] = json.loads(data["snapshot_json"])
            except Exception:
                data["snapshot"] = {}
            return data

    def delete_account(self, puuid: str) -> bool:
        """Bir hesabı ve tüm geçmiş loglarını siler."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE puuid = ?", (puuid,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_log(self, log_id: int) -> bool:
        """Tek bir kontrol logunu siler."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM check_logs WHERE id = ?", (log_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_database_stats(self) -> Dict[str, Any]:
        """Veritabanı genel durum istatistiklerini döndürür."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_accounts FROM accounts")
            total_accounts = cursor.fetchone()["total_accounts"]

            cursor.execute("SELECT COUNT(*) as total_checks FROM check_logs")
            total_checks = cursor.fetchone()["total_checks"]

            cursor.execute("SELECT MAX(check_date_local) as last_check FROM check_logs")
            last_check = cursor.fetchone()["last_check"] or "Henüz kontrol yok"

            db_size_bytes = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0
            db_size_kb = round(db_size_bytes / 1024, 2)

            return {
                "total_accounts": total_accounts,
                "total_checks": total_checks,
                "last_check": last_check,
                "db_size_kb": db_size_kb,
                "db_path": str(DATABASE_PATH),
            }

    # ========================================================
    # Önbellek Yönetimi (valorant-api.com)
    # ========================================================

    def cache_endpoint(self, endpoint_name: str, language: str, data: Any):
        """Uç nokta verisini SQLite'a önbelleğe yazar."""
        key = f"{endpoint_name}:{language}"
        now_iso = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(data, ensure_ascii=False)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO content_cache (cache_key, endpoint_name, language, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = excluded.updated_at
            """, (key, endpoint_name, language, data_json, now_iso))
            conn.commit()

    def get_cached_endpoint(self, endpoint_name: str, language: str, max_age_hours: int = 24) -> Optional[Any]:
        """Önbellekte geçerli veri varsa döndürür."""
        key = f"{endpoint_name}:{language}"
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data_json, updated_at FROM content_cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return None

            try:
                updated_dt = datetime.fromisoformat(row["updated_at"])
                age = (datetime.now(timezone.utc) - updated_dt).total_seconds() / 3600
                if age <= max_age_hours:
                    return json.loads(row["data_json"])
            except Exception:
                pass

            return None


# Global veritabanı örneği
db = DatabaseManager()
