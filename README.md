# VALORANT Account Checker & Pro Database v2.0

VALORANT oyuncu profillerini, envanterlerini, mağaza rotasyonlarını ve dereceli geçmişlerini güvenli bir şekilde analiz eden, yerel **SQLite veritabanı** üzerinde kronolojik olarak loglayan ve **dash.valorant-api.com** üzerindeki 30 API uç noktasının tamamını kullanan açık kaynaklı bir hesap yönetim ve denetleme aracıdır.

---

## 🌟 Temel Özellikler

### 1. Kapsamlı Hesap ve Envanter Analizi
* **Profil & Seviye**: Hesap seviyesi, seviye çerçevesi (`levelborders`), hesap puanı (AP), seviye ilerleme yüzdesi ve günlük ilk galibiyet bonusu sayacı.
* **Cüzdan Bakiyeleri**: VALORANT Puanı (VP), Radyanit Puanı (RP) ve Kingdom Kredisi (KC) miktarları ve resmi simgeleri.
* **Dereceli (MMR) Durumu**: Güncel Kademe (Demir'den Radyant'a kadar kademe rozeti ve rengi), Kademe Puanı (RR), Zirve Kademe (Peak Rank) ve aktif kısımda oynanmamışsa önceki kısım derecesi.
* **Kuşanılmış Yükleme (Loadout)**: Silahlara takılı skinler, kroma renkleri, seviyeler, takılı silah uğurlukları (buddies), 4 sprey yuvası ve kuşanılan oyuncu kartı/unvanı.
* **Tüm Silah Skinleri**: Sahip olunan tüm özel skinler; silah adına göre gruplama, tema serisi etiketleri (`themes`), nadirlik rozetleri (`contenttiers`) ve arama filtresi.
* **Tam Ajan Kadrosu (30 Ajan)**: Oynanabilir tüm ajanların listesi, "Açık/Kullanılabilir" ve "Kilitli" durumu, ajan rolleri, yetenekleri ve portreleri.
* **Savaş Bileti & Kontratlar**: Aktif sezon pasosunun (Battle Pass) toplam kazanılan XP'si, bölüm durumu ve ajan kontrat ilerlemeleri.
* **Gelişmiş Mağaza**: Günlük 4 skin teklifinin VP fiyatları, kalan süre geri sayımı, Öne Çıkan Paket (Featured Bundle), Gece Pazarı (Night Market) ve Kingdom Kredisi Aksesuar Mağazası (Accessory Store).
* **Maç Geçmişi**: Son 20 maçın harita görseli (`maps`), oyun modu (`gamemodes`), oynanan ajan, K/D/A, ACS, skor ve galibiyet/mağlubiyet analizi.
* **Cezalar ve Yaptırımlar**: Kuyruk kısıtlamaları, oyun yasakları, uyarılar ve ceza bitiş tarihleri.

---

### 2. Dahili SQLite Veritabanı ve Zaman Damgalı Loglama
* `database/valochecker.db` üzerinde iki ana tablo bulunur:
  * `accounts`: Kontrol edilen profillerin özet durumunu ve toplam kontrol sayısını tutar.
  * `check_logs`: Her kontrolde hesabın o anki durumunun tam JSON snapshot'ını ve zaman damgasını saklar.
* Kontroller arasındaki seviye, bakiye, rank ve skin değişimleri geçmiş loglar üzerinden kıyaslanabilir.

---

### 3. dash.valorant-api.com Üzerindeki 30 Uç Nokta Kataloğu

Proje, [dash.valorant-api.com](https://dash.valorant-api.com/) üzerinde yer alan 30 uç noktanın tamamını hem arka planda veri zenginleştirme için kullanır hem de Web Arayüzündeki **"API Veri Gezgini"** sekmesinde canlı olarak sunar:

| # | Uç Nokta | Açıklama |
|---|---|---|
| 1 | `/agents` | Tüm oynanabilir ve NPC ajanlar, yetenekler ve roller |
| 2 | `/weapons` | 21 temel silah türü, hasar verileri ve mağaza maliyetleri |
| 3 | `/weapons/skins` | 1.400+ silah skini, ikonlar ve seviyeler |
| 4 | `/weapons/skinchromas` | Skinlerin tüm renk varyantları ve video önizlemeleri |
| 5 | `/weapons/skinlevels` | Skin yükseltme kademeleri, VFX ve bitiriş animasyonları |
| 6 | `/maps` | Harita splash görselleri, taktik koordinatlar ve radar haritaları |
| 7 | `/playercards` | 1.000+ oyuncu kartı (küçük ikon, geniş banner ve dikey sanat afişi) |
| 8 | `/buddies` | Silah uğurlukları (gun charms) |
| 9 | `/buddies/levels` | Uğurluk seviye varyasyonları |
| 10 | `/sprays` | Spreyler, animasyonlu formatlar ve tam saydam ikonlar |
| 11 | `/sprays/levels` | Sprey seviye türevleri |
| 12 | `/bundles` | Güncel ve geçmiş öne çıkan koleksiyon mağaza paketleri |
| 13 | `/competitivetiers` | Demir 1'den Radyant'a tüm rütbeler, kademe ikonları ve renkleri |
| 14 | `/ceremonies` | Tur/maç sonu seremonileri (Kusursuz, As, Debriyaj vb.) |
| 15 | `/contenttiers` | Skin nadirlik kademeleri (Select, Deluxe, Premium, Exclusive, Ultra) |
| 16 | `/contracts` | Ajan ve Savaş Bileti sözleşmeleri, ödül bölümleri |
| 17 | `/currencies` | VP, RP, Kingdom Kredisi ve Ajan Jetonu para birimleri |
| 18 | `/events` | Oyun içi özel etkinlik takvimleri |
| 19 | `/flex` | Ekstra ifade ve aksesuar yuvaları |
| 20 | `/gamemodes` | Oyun modları (Rekabete Dayalı, Tam Gaz, Ölüm Kalım vb.) |
| 21 | `/gamemodes/equippables` | Özel modlara has kuşanılabilir ekipmanlar |
| 22 | `/gear` | Zırh ve kalkan ekipmanları |
| 23 | `/levelborders` | Hesap seviyesine göre açılan profil çerçeve görselleri |
| 24 | `/missions` | 980+ görev şablonu ve XP ödülleri |
| 25 | `/objectives` | Görev tamamlama şartları ve hedefleri |
| 26 | `/playertitles` | Oyuncu unvanları |
| 27 | `/seasons` | Bölüm (Episode) ve Kısım (Act) başlangıç/bitiş tarihleri |
| 28 | `/seasons/competitive` | Dereceli sezonları ve eşleşme tabloları |
| 29 | `/themes` | Skin temaları (Asil, Yağmacı, Kuronami, Ejder vb.) |
| 30 | `/version` | Riot istemci sürümü ve altyapı bilgisi |

---

## 🔒 Güvenlik ve Gizlilik Mimarisi

* **Şifresiz Çalışma Prensibi**: Bu yazılım asla kullanıcı adı veya şifre talep etmez ve şifre kaydetmez.
* **OAuth 2.0 Token Yöntemi**: Kullanıcı kendi tarayıcısında resmi Riot Games oturum açma sayfasına gider, giriş yaptıktan sonra oluşan yetkilendirme yönlendirme bağlantısı (`playvalorant.com/opt_in#access_token=...`) ile işlem yapılır.
* **Tamamen Yerel (Local-Only)**: Tüm veriler yerel bilgisayarınızdaki SQLite dosyasında saklanır. Harici hiçbir üçüncü parti sunucuya veri gönderilmez; yalnızca Riot Games resmi sunucuları ve valorant-api.com ile haberleşilir.

---

## 🛠️ Kurulum

### Gereksinimler
* Python 3.10 veya üzeri
* `pip` paket yöneticisi

### Adımlar

1. Depoyu klonlayın veya zip olarak indirin:
```bash
git clone https://github.com/yyusagllc/VALORANT-ACCOUNT-CHECKER-PRO-DATABASE.git
cd VALORANT-ACCOUNT-CHECKER-PRO-DATABASE
```

2. Sanal ortam oluşturun ve aktif edin (Opsiyonel ama tavsiye edilir):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

3. Gerekli bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

---

## 🚀 Kullanım

### 1. Web Dashboard (Önerilen)
Uygulamayı modern web arayüzü ile başlatmak için:
```bash
python run.py
```
*(veya `python main.py`)*

* Sunucu otomatik olarak uygun bir porta bağlanır (varsayılan: `http://127.0.0.1:8000`, meşgulse `8001`).
* Tarayıcınız otomatik olarak kontrol paneline yönlendirilir.
* REST API dokümantasyonuna `http://127.0.0.1:8000/docs` adresinden erişebilirsiniz.

### 2. Terminal (CLI) Modu
Komut satırı üzerinden zengin arayüzle işlem yapmak için:
```bash
# Yeni bir hesap kontrolü yap
python cli.py check

# Veritabanında kayıtlı hesapları listele
python cli.py list

# Belirli bir hesabın kontrol geçmişini incele
python cli.py history "Oyuncu#TR1"
```

---

## 📖 Hesap Kontrolü Nasıl Yapılır?

1. Web arayüzündeki **"Riot Giriş Sayfasını Aç"** bağlantısına tıklayın.
2. Açılan resmi Riot Games sayfasında hesabınıza giriş yapın.
3. Giriş yaptıktan sonra tarayıcınızın adres çubuğundaki yönlendirme bağlantısını (`https://playvalorant.com/opt_in#access_token=...`) kopyalayın.
4. Kopyaladığınız bağlantıyı arayüzdeki kutucuğa yapıştırıp **"Hesabı Kontrol Et"** butonuna basın.
5. Sistem hesabı tüm kategorilerde analiz edecek, veritabanına loglayacak ve tüm sonuçları sekmeler halinde gösterecektir. Dilerseniz tek tıkla **HTML Raporu** olarak dışa aktarabilirsiniz.

---

## 📁 Proje Mimarisi

```
ValoChecker2/
├── app.py                      # FastAPI web sunucusu ve REST API rotaları
├── cli.py                      # Rich tabanlı interaktif terminal arayüzü
├── config.py                   # Port tespiti, 30 API kataloğu, shard ve sabitler
├── main.py                     # Ana giriş noktası
├── run.py                      # Otomatik port ve tarayıcı yöneticili başlatıcı
├── requirements.txt            # Python bağımlılıkları
├── .gitignore                  # Git takip dışı dosyalar listesi
├── .env.example                # Örnek çevre değişkenleri
├── database/
│   ├── db.py                   # SQLite ORM/yönetici (accounts, check_logs, content_cache)
│   └── .gitkeep
├── services/
│   ├── content_service.py      # 30 valorant-api.com uç noktasını yöneten ve çözen servis
│   ├── riot_service.py         # Riot OAuth, PVP, PD, Mağaza ve MMR istemcisi
│   ├── checker_engine.py       # Veri zenginleştirme, snapshot üretimi ve loglama motoru
│   └── html_exporter.py        # Kendi başına çalışan karanlık temalı HTML rapor üretici
├── web/
│   ├── templates/
│   │   └── index.html          # Dashboard HTML şablonu
│   └── static/
│       ├── css/style.css       # Özel koyu tema tasarım stilleri
│       └── js/app.js           # Dinamik frontend ve API Gezgini mantığı
└── reports/
    └── .gitkeep                # Üretilen HTML raporların kayıt dizini
```

---

## ⚖️ Yasal Uyarı ve Sorumluluk Reddi (Disclaimer)

Bu proje Riot Games tarafından onaylanmamıştır ve Riot Games veya VALORANT'ın yapımında veya yönetiminde resmi olarak yer alan kişilerin görüşlerini yansıtmamaktadır. VALORANT ve Riot Games, Riot Games, Inc.'in tescilli ticari markalarıdır.

Bu yazılım yalnızca kişisel hesap kontrolü ve eğitim/geliştirme amaçlarıyla hazırlanmış açık kaynaklı bir araçtır.
