"""
VALORANT ACCOUNT CHECKER & DATABASE
Entegrasyon ve Doğrulama Testleri
"""

import os
from database.db import db
from services.content_service import content_service
from services.html_exporter import generate_account_html_report
from app import app


def run_tests():
    # Başlangıçta eski test verisi varsa temizle
    db.delete_account("test-puuid-integration-12345")
    print("[1] Veritabanı CRUD Testleri Başlatılıyor...")
    test_snapshot = {
        "account": {
            "puuid": "test-puuid-integration-12345",
            "game_name": "TestAgent",
            "tag_line": "TR1",
            "riot_id": "TestAgent#TR1",
            "region": "eu",
            "country": "TUR"
        },
        "check_time_iso": "2026-11-12T18:50:00Z",
        "check_time_local": "12.11.2026 18:50:00",
        "level": {
            "level": 45,
            "xp": 2350,
            "total_ap": 222350,
            "progress_percent": 47.0,
            "progress_text": "2.350 / 5.000 AP",
            "remaining_xp": 2650
        },
        "first_win": {
            "status": "Hazır",
            "badge_class": "ready",
            "detail": "Bonus hazır!"
        },
        "wallet": {"VP": 1750, "RP": 120, "KC": 4500},
        "rank": {
            "rank_tier": 12,
            "rank_name": "ALTIN 1",
            "rank_color": "#e2b342",
            "rank_icon": "https://media.valorant-api.com/competitivetiers/03621f52-4cd8-5e33-722a-cc94159c952f/12/largeicon.png",
            "ranked_rating": 64,
            "peak_rank": "PLATİN 2"
        },
        "penalties": {
            "status": "Temiz",
            "status_class": "good",
            "detail": "Hesap üzerinde ceza kaydı yok.",
            "records": []
        },
        "loadout": {
            "identity": {
                "card": {"wideArt": "", "displayName": "Standart Kart"},
                "title": {"titleText": "Ajan"}
            },
            "guns": []
        },
        "owned_skins": [
            {"weapon_name": "Vandal", "skin_name": "Asil Vandal", "rarity": "Premium Edition", "rarity_color": "#d1548d"},
            {"weapon_name": "Phantom", "skin_name": "İyon Phantom", "rarity": "Premium Edition", "rarity_color": "#d1548d"}
        ],
        "owned_skins_stats": {"total_custom_skins": 2},
        "store": {"daily_offers": [], "remaining_duration_text": "12 saat"},
        "matches": [
            {
                "map_name": "Ascent",
                "game_mode": "Rekabete Dayalı",
                "agent_name": "Jett",
                "kda_text": "21/14/5",
                "kd_ratio": 1.5,
                "score_text": "13 - 9",
                "result": "Galibiyet",
                "result_class": "win",
                "date": "12.11.2026 17:30"
            }
        ]
    }

    # 1. Kaydet
    log_id = db.save_account_check(test_snapshot, notes="Entegrasyon Testi")
    print(f"✓ Test kaydı loglandı! Log ID: {log_id}")

    # 2. Hesabı Sorgula
    acc = db.get_account("test-puuid-integration-12345")
    assert acc is not None, "Hesap veritabanında bulunamadı!"
    assert acc["riot_id"] == "TestAgent#TR1"
    assert acc["last_level"] == 45
    assert acc["last_vp"] == 1750
    assert acc["latest_log"] is not None
    print(f"✓ Hesap başarıyla getirildi: {acc['riot_id']} (Toplam Kontrol: {acc['total_checks']})")

    # 3. İkinci Kontrolü Kaydet (total_checks artışını doğrula)
    test_snapshot["level"]["level"] = 46
    test_snapshot["wallet"]["VP"] = 2100
    log_id_2 = db.save_account_check(test_snapshot, notes="İkinci Kontrol")
    acc_updated = db.get_account("test-puuid-integration-12345")
    assert acc_updated["total_checks"] == 2
    assert acc_updated["last_level"] == 46
    assert acc_updated["last_vp"] == 2100
    print(f"✓ İkinci kontrol doğrulandı: Level: {acc_updated['last_level']}, VP: {acc_updated['last_vp']}, Toplam Kontrol: {acc_updated['total_checks']}")

    # 4. Geçmiş Logları Sorgula
    logs = db.get_account_logs("test-puuid-integration-12345")
    assert len(logs) == 2, f"Beklenen 2 log, bulunan {len(logs)}"
    print(f"✓ Hesap geçmiş logları sayısı: {len(logs)}")

    # 5. Tekil Log Getirme
    single_log = db.get_log(log_id)
    assert single_log is not None
    assert "snapshot" in single_log
    assert single_log["snapshot"]["account"]["riot_id"] == "TestAgent#TR1"
    print("✓ Tekil log ve JSON snapshot deserialization doğrulandı.")

    # 6. HTML Rapor Üretimi
    print("\n[2] HTML Rapor Üretim Testi...")
    report_path = generate_account_html_report(test_snapshot, open_in_browser=False)
    assert os.path.exists(report_path), "HTML rapor dosyası oluşturulamadı!"
    print(f"✓ HTML Raporu başarıyla oluşturuldu: {report_path}")

    # 7. Content Service ve 30 Uç Nokta
    print("\n[3] 30 Uç Nokta İçerik Servisi Testi...")
    content_service.ensure_initialized()
    catalog = content_service.get_endpoints_catalog()
    assert len(catalog) == 30, f"Beklenen 30 uç nokta, bulunan: {len(catalog)}"
    print(f"✓ 30 uç noktanın tamamı katalogda mevcut.")

    # Örnek Çözümleyiciler (Resolvers)
    resolved_skin = content_service.resolve_skin("e7c63390-eda7-46e0-bb7a-a6abdacd2433")
    print(f"✓ Skin Çözümleme: {resolved_skin['skin_name']}")

    resolved_rank = content_service.resolve_rank(15)
    print(f"✓ Rank Çözümleme (Tier 15): {resolved_rank['name']}")

    # 8. FastAPI Rotaları
    print("\n[4] FastAPI Rotaları Doğrulaması...")
    route_paths = [r.path for r in app.routes]
    expected_routes = [
        "/",
        "/api/check",
        "/api/accounts",
        "/api/accounts/{puuid}",
        "/api/accounts/{puuid}/logs",
        "/api/logs/{log_id}",
        "/api/stats",
        "/api/export/html/{puuid}",
        "/api/content/endpoints",
        "/api/content/{endpoint_id:path}",
    ]
    for exp in expected_routes:
        assert exp in route_paths, f"Eksik rota: {exp}"
    print(f"✓ Tüm kritik API ve Web rotaları ({len(route_paths)} adet) aktif.")

    # Temizlik
    db.delete_account("test-puuid-integration-12345")
    assert db.get_account("test-puuid-integration-12345") is None
    print("✓ Test verisi temizlendi.")

    print("\n=======================================================")
    print("   TÜM ENTEGRASYON VE DOĞRULAMA TESTLERİ BAŞARIYLA GEÇTİ!")
    print("=======================================================")


if __name__ == "__main__":
    run_tests()
