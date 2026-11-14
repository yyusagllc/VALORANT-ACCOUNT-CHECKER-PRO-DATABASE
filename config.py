"""
VALORANT ACCOUNT CHECKER & DATABASE
Konfigürasyon ve Sabit Değerler
dash.valorant-api.com üzerindeki tüm 30 uç noktayı kapsar.
"""

import os
import socket
from pathlib import Path

# Temel Dizinler
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "valochecker.db"
REPORTS_DIR = BASE_DIR / "reports"

# Rapor Klasörü Oluşturma
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Sunucu Ayarları
SERVER_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", 8000))


def is_port_in_use(port: int, host: str = SERVER_HOST) -> bool:
    """Portun kullanımda olup olmadığını kontrol eder."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def get_free_port(start_port: int = DEFAULT_PORT, host: str = SERVER_HOST) -> int:
    """Belirtilen port doluysa sıradaki ilk boş portu (8001, 8002 vb.) bulur."""
    if not is_port_in_use(start_port, host):
        return start_port

    for p in range(start_port + 1, start_port + 100):
        if not is_port_in_use(p, host):
            return p

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


SERVER_PORT = get_free_port()
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# Riot API Ayarları
DEFAULT_REGION = "eu"
SUPPORTED_REGIONS = {
    "eu": "Avrupa (EU)",
    "na": "Kuzey Amerika (NA)",
    "ap": "Asya Pasifik (AP)",
    "kr": "Kore (KR)",
    "latam": "Latin Amerika (LATAM)",
    "br": "Brezilya (BR)",
}

MATCH_COUNT = 20
AP_PER_LEVEL = 5000

# Riot Kimlik Doğrulama URL'si
AUTH_URL = (
    "https://auth.riotgames.com/authorize?"
    "client_id=play-valorant-web-prod&nonce=1"
    "&redirect_uri=https://playvalorant.com/opt_in"
    "&response_type=token%20id_token&scope=account%20openid"
)

ENTITLEMENTS_URL = "https://entitlements.auth.riotgames.com/api/token/v1"
USERINFO_URL = "https://auth.riotgames.com/userinfo"

# PVP / PD Temel Adresleri
PVP_BASE_URL = "https://pd.{region}.a.pvp.net"
SHARED_BASE_URL = "https://shared.{region}.a.pvp.net"

# Valorant-API.com Temel Adresi
VALORANT_API_BASE = "https://valorant-api.com/v1"
DEFAULT_LANGUAGE = "tr-TR"

# Riot İstemci Platform Bilgisi (Resmi Base64 Formatı)
PLATFORM_DATA = {
    "platformType": "PC",
    "platformOS": "Windows",
    "platformOSVersion": "10.0.19042.1.256.64bit",
    "platformChipset": "Unknown",
}
# Riot API istemci platform başlığının WAF/Storefront uyumlu standart base64 kodlaması
CLIENT_PLATFORM_B64 = "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"

# Bölge -> Shard Eşleştirmesi (LATAM ve BR -> NA shard'ına yönlendirilir)
REGION_TO_SHARD = {
    "eu": "eu",
    "na": "na",
    "ap": "ap",
    "kr": "kr",
    "latam": "na",
    "br": "na",
}

# Varsayılan Başlangıç Ajanları (Riot entitlements listesinde olmasa dahi tüm hesaplarda açık olan ajanlar)
STARTER_AGENT_UUIDS = [
    "9f0d8ba9-4140-b941-57d3-a7ad57c6b417",  # BRIMSTONE
    "add6443a-41bd-e414-f6ad-e58d267f4e95",  # JETT
    "eb93336a-449b-9c1b-0a54-a891f7921d69",  # PHOENIX
    "569fdd95-4d10-43ab-ca70-79becc718b46",  # SAGE
    "320b2a48-4d9b-a075-30f1-1f93a9b638fa",  # SOVA
]

# Para Birimi UUID Eşleştirmeleri
CURRENCY_IDS = {
    "VP": "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741",       # Valorant Points
    "RP": "e59aa87c-4cbf-517a-5983-6e81511be9b7",       # Radianite Points
    "KC": "85ca954a-41f2-ce94-9b45-8ca3dd39a00d",       # Kingdom Credits
    "AGENTS": "f08d4ae3-939c-4576-ab26-09ce1f23bb37",   # Ajan Jetonu / Unlock
}

# Envanter Tür UUID'leri (Riot Entitlements API - Doğrulanmış Gerçek UUID'ler)
ITEM_TYPES = {
    "SKIN_LEVEL": "e7c63390-eda7-46e0-bb7a-a6abdacd2433",          # Silah Skin Seviyeleri
    "SKIN_CHROMA": "3ad1b2b2-acdb-4524-852f-954a76ddae0a",         # Skin Renk Varyantları (Chromas)
    "AGENT": "01bb38e1-da47-4e6a-9b3d-945fe4655707",               # Açılan Ajanlar (Agents)
    "CONTRACT_DEFINITION": "f85cb6f7-33e5-4dc8-b609-ec7212301948",  # Kontrat Tanımları
    "BUDDY": "dd3bf334-87f3-40bd-b043-682a57a8dc3a",               # Silah Uğurlukları (Gun Charms)
    "SPRAY": "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475",               # Spreyler
    "PLAYER_CARD": "3f296c07-64c3-494c-923b-fe692a4fa1bd",         # Oyuncu Kartları (Player Cards)
    "PLAYER_TITLE": "de7caa6b-adf7-4588-bbd1-143831e786c6",        # Oyuncu Unvanları (Player Titles)
}

# Türkçe Oyun Modu İsimleri
MODE_NAMES = {
    "competitive": "Rekabete Dayalı",
    "unrated": "Derecesiz",
    "swiftplay": "Tam Gaz",
    "deathmatch": "Ölüm Kalım Savaşı",
    "spikerush": "Spike'a Hücum",
    "hurm": "Takımlı Ölüm Kalım Savaşı",
    "skirmish2v2": "2'ye 2 Çatışma",
    "ggteam": "Tırmanış",
    "onefa": "Kopya",
    "snowball": "Kartopu Çatışması",
    "fortcollins": "Alanı Geri Al",
    "premier": "Premier",
    "custom": "Özel Oyun",
}

# Ceza Etki İsimleri
PENALTY_EFFECTS = {
    "GameBanEffect": "Oyun Yasağı (Ban)",
    "QueueRestrictionEffect": "Kuyruk Kısıtlaması",
    "QueueDelayEffect": "Eşleştirme Bekleme Cezası",
    "RankedRatingPenaltyEffect": "Dereceli Puanı Cezası",
    "RiotRestrictionEffect": "Riot Hesap Kısıtlaması",
    "WarningEffect": "Resmi Uyarı",
    "XPMultiplierEffect": "XP Cezası / Çarpanı",
    "PremierRestrictionEffect": "Premier Kısıtlaması",
    "DelayedPenaltyEffect": "Bekleyen Ceza",
    "RMSNotifyEffect": "Riot Bildirimi",
}

# DASH.VALORANT-API.COM ÜZERİNDEKİ TÜM UÇ NOKTALAR KATALOĞU (30 Uç Nokta)
ALL_CONTENT_ENDPOINTS = [
    {"id": "agents", "name": "Ajanlar (Agents)", "path": "/agents", "description": "Tüm oynanabilir ve NPC ajanlar, yetenekleri, rolleri ve portreleri"},
    {"id": "weapons", "name": "Silahlar (Weapons)", "path": "/weapons", "description": "Tüm silahlar, istatistikleri, mağaza maliyetleri ve skinleri"},
    {"id": "weapons/skins", "name": "Silah Skinleri (Weapon Skins)", "path": "/weapons/skins", "description": "Oyundaki 1.400+ silah skininin tamamı ve görselleri"},
    {"id": "weapons/skinchromas", "name": "Skin Kromaları (Chromas)", "path": "/weapons/skinchromas", "description": "Skinlerin tüm renk varyantları ve video önizlemeleri"},
    {"id": "weapons/skinlevels", "name": "Skin Seviyeleri (Skin Levels)", "path": "/weapons/skinlevels", "description": "Skin seviye yükseltmeleri, ses ve bitiriş efektleri"},
    {"id": "maps", "name": "Haritalar (Maps)", "path": "/maps", "description": "Tüm haritalar, koordinatları, taktik radar ve görsel splashları"},
    {"id": "playercards", "name": "Oyuncu Kartları (Player Cards)", "path": "/playercards", "description": "1.000+ Oyuncu kartı; küçük simge, geniş banner ve dikey sanat afişleri"},
    {"id": "buddies", "name": "Silah Uğurlukları (Buddies)", "path": "/buddies", "description": "900+ Silah süsü ve takılabilir charm nesnesi"},
    {"id": "buddies/levels", "name": "Uğurluk Seviyeleri (Buddy Levels)", "path": "/buddies/levels", "description": "Silah süslerinin seviye ve simge türevleri"},
    {"id": "sprays", "name": "Spreyler (Sprays)", "path": "/sprays", "description": "900+ Grafiti ve sprey, animasyonlu formatları"},
    {"id": "sprays/levels", "name": "Sprey Seviyeleri (Spray Levels)", "path": "/sprays/levels", "description": "Sprey seviye varyantları"},
    {"id": "bundles", "name": "Mağaza Paketleri (Bundles)", "path": "/bundles", "description": "Öne çıkan silah ve içerik koleksiyon paketleri"},
    {"id": "competitivetiers", "name": "Dereceli Kademeleri (Competitive Tiers)", "path": "/competitivetiers", "description": "Demir'den Radyant'a kadar tüm rütbeler, kademe ikonları ve renkleri"},
    {"id": "ceremonies", "name": "Seremoniler (Ceremonies)", "path": "/ceremonies", "description": "Tur ve maç sonu seremonileri (Kusursuz, As, Debriyaj vb.)"},
    {"id": "contenttiers", "name": "İçerik Nadirlikleri (Content Tiers)", "path": "/contenttiers", "description": "Skin nadirlik seviyeleri (Select, Deluxe, Premium, Exclusive, Ultra)"},
    {"id": "contracts", "name": "Kontratlar (Contracts)", "path": "/contracts", "description": "Ajan ve Savaş Bileti sözleşmeleri, ödül bölümleri"},
    {"id": "currencies", "name": "Para Birimleri (Currencies)", "path": "/currencies", "description": "VP, RP, Kingdom Kredisi ve Ajan Jetonları"},
    {"id": "events", "name": "Etkinlikler (Events)", "path": "/events", "description": "Oyun içi özel etkinlikler ve dönemleri"},
    {"id": "flex", "name": "Flex / Aksesuar (Flex)", "path": "/flex", "description": "Ekstra ifade ve aksesuar yuvaları"},
    {"id": "gamemodes", "name": "Oyun Modları (Game Modes)", "path": "/gamemodes", "description": "Dereceli, Tam Gaz, Ölüm Kalım gibi oyun modları ve kuralları"},
    {"id": "gamemodes/equippables", "name": "Mod Ekipmanları (Equippables)", "path": "/gamemodes/equippables", "description": "Özel modlara has kuşanılabilir ekipmanlar"},
    {"id": "gear", "name": "Ekipman / Kalkanlar (Gear)", "path": "/gear", "description": "Hafif kalkan, ağır kalkan ve zırh ekipmanları"},
    {"id": "levelborders", "name": "Seviye Çerçeveleri (Level Borders)", "path": "/levelborders", "description": "Hesap seviyesine göre açılan profil çerçeve görselleri"},
    {"id": "missions", "name": "Görevler (Missions)", "path": "/missions", "description": "980+ Günlük ve haftalık görev şablonu, XP ödülleri"},
    {"id": "objectives", "name": "Görev Hedefleri (Objectives)", "path": "/objectives", "description": "Görev tamamlama şart ve hedefleri"},
    {"id": "playertitles", "name": "Oyuncu Unvanları (Player Titles)", "path": "/playertitles", "description": "450+ Kart altında görünen unvan metni"},
    {"id": "seasons", "name": "Sezonlar / Kısımlar (Seasons)", "path": "/seasons", "description": "Bölüm (Episode) ve Kısım (Act) başlangıç/bitiş tarihleri"},
    {"id": "seasons/competitive", "name": "Dereceli Sezonları (Competitive Seasons)", "path": "/seasons/competitive", "description": "Dereceli rekabet dönemleri ve eşleşme tabloları"},
    {"id": "themes", "name": "Temalar (Themes)", "path": "/themes", "description": "Skin serisi temaları (Asil, Yağmacı, Kuronami, Ejder vb.)"},
    {"id": "version", "name": "İstemci Sürümü (Version)", "path": "/version", "description": "Güncel Riot istemci sürümü, derleme ve altyapı bilgisi"}
]
