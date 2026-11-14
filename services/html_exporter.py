"""
VALORANT ACCOUNT CHECKER & DATABASE
Kendi Başına Çalışabilen (Standalone) HTML Rapor Oluşturucu
dash.valorant-api.com ve Riot API'lerinden çekilen tüm verileri (Mağaza fiyatları, tüm envanter, görevler, maç istatistikleri) eksiksiz HTML raporuna döker.
"""

import html
import os
import webbrowser
from pathlib import Path
from typing import Any, Dict

from config import REPORTS_DIR


def esc(value: Any, default: str = "—") -> str:
    """HTML kaçış karakterlerini temizler."""
    if value is None or value == "":
        return default
    return html.escape(str(value))


def num_tr(value: Any) -> str:
    """Sayıları Türkçe formatta (binlik nokta) biçimlendirir."""
    if value is None:
        return "0"
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return str(value)


def generate_account_html_report(snapshot: Dict[str, Any], open_in_browser: bool = False) -> str:
    """
    Hesap snapshot verisini zengin bir HTML raporuna dönüştürür ve dosyaya yazar.
    Döndürür: Oluşturulan dosyanın mutlak dosya yolu.
    """
    account = snapshot.get("account", {})
    riot_id = account.get("riot_id", "Bilinmeyen Hesap")
    region = (account.get("region") or "eu").upper()
    puuid = account.get("puuid", "")
    check_time = snapshot.get("check_time_local", "")

    level = snapshot.get("level", {})
    lvl_num = level.get("level", 1)
    xp_num = level.get("xp", 0)
    total_ap = level.get("total_ap", 0)
    progress_percent = level.get("progress_percent", 0)
    progress_text = level.get("progress_text", "")
    remaining_xp = level.get("remaining_xp", 0)

    wallet = snapshot.get("wallet", {})
    vp = wallet.get("VP", 0)
    rp = wallet.get("RP", 0)
    kc = wallet.get("KC", 0)

    rank = snapshot.get("rank", {})
    rank_name = rank.get("rank_name", "Derecesiz")
    rank_icon = rank.get("rank_icon", "")
    rank_color = rank.get("rank_color", "#9eabb8")
    rr = rank.get("ranked_rating", 0)
    peak_rank = rank.get("peak_rank", "Derecesiz")
    peak_season = rank.get("peak_season_name", "")
    prev_act = rank.get("previous_act_rank")

    first_win = snapshot.get("first_win", {})
    first_win_status = first_win.get("status", "Bilinmiyor")
    first_win_detail = first_win.get("detail", "")
    first_win_class = first_win.get("badge_class", "unknown")

    penalties = snapshot.get("penalties", {})
    penalty_status = penalties.get("status", "Temiz")
    penalty_class = penalties.get("status_class", "good")
    penalty_detail = penalties.get("detail", "")

    loadout = snapshot.get("loadout", {})
    card = loadout.get("identity", {}).get("card", {})
    card_banner = card.get("wideArt") or card.get("largeArt") or ""
    card_title = loadout.get("identity", {}).get("title", {}).get("titleText") or ""

    inventory = snapshot.get("inventory", {}) or {}
    owned_skins = inventory.get("skins") or snapshot.get("owned_skins", []) or []
    owned_stats = inventory.get("skins_stats") or snapshot.get("owned_skins_stats", {}) or {}
    total_custom_skins = owned_stats.get("total_custom_skins", len(owned_skins))
    buddies = inventory.get("buddies", [])
    sprays = inventory.get("sprays", [])
    cards = inventory.get("cards", [])
    titles = inventory.get("titles", [])
    agents = inventory.get("agents", [])

    store = snapshot.get("store", {})
    daily_offers = store.get("daily_offers", []) or []
    shop_remaining = store.get("remaining_duration_text", "Bilinmiyor")

    missions = snapshot.get("missions", {}) or {}
    matches = snapshot.get("matches", []) or []

    # 1. GÜNLÜK MAĞAZA KARTLARI (FİYATLAR DAHİL)
    daily_cards_html = []
    for item in daily_offers:
        daily_cards_html.append(f"""
        <div class="shop-card" style="border-top: 3px solid {esc(item.get('rarity_color', '#ff4655'))};">
            <div class="shop-thumb-wrap">
                <img src="{esc(item.get('icon', ''))}" alt="{esc(item.get('skin_name'))}" loading="lazy" class="shop-thumb" />
            </div>
            <div class="shop-info">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span class="rarity-tag" style="background:{esc(item.get('rarity_color', '#344454'))}33; color:{esc(item.get('rarity_color', '#ff4655'))}; border-color:{esc(item.get('rarity_color', '#ff4655'))}66;">
                        {esc(item.get('rarity', 'Standart'))}
                    </span>
                    <strong style="color:var(--accent-red); font-size:13px;">{num_tr(item.get('price', 1775))} VP</strong>
                </div>
                <strong class="shop-name">{esc(item.get('skin_name'))}</strong>
                <small class="shop-sub">{esc(item.get('weapon_name'))}</small>
            </div>
        </div>
        """)

    # 2. KUŞANILMIŞ SİLAHLAR
    equipped_guns = loadout.get("guns", []) or []
    equipped_cards_html = []
    for gun in equipped_guns:
        buddy_html = f"<div class='equipped-buddy'><span>Uğurluk:</span> <strong>{esc(gun.get('buddy'))}</strong></div>" if gun.get("buddy") else ""
        equipped_cards_html.append(f"""
        <div class="loadout-gun-card">
            <div class="gun-header">
                <span class="gun-type">{esc(gun.get('weapon_name'))}</span>
                <span class="gun-rarity" style="color: {esc(gun.get('rarity_color'))};">{esc(gun.get('rarity'))}</span>
            </div>
            <div class="gun-image-wrap">
                <img src="{esc(gun.get('icon', ''))}" alt="{esc(gun.get('skin_name'))}" loading="lazy" class="gun-image" />
            </div>
            <div class="gun-footer">
                <strong class="gun-skin-name">{esc(gun.get('skin_name'))}</strong>
                {buddy_html}
            </div>
        </div>
        """)

    # 3. SAHİP OLUNAN SKİNLER
    skins_cards_html = []
    for s in owned_skins:
        skins_cards_html.append(f"""
        <div class="skin-item-card" style="border-color: {esc(s.get('rarity_color'))}44;">
            <div class="skin-thumb-box">
                <img src="{esc(s.get('icon', ''))}" alt="{esc(s.get('skin_name'))}" loading="lazy" class="skin-thumb" />
            </div>
            <div class="skin-meta">
                <span class="skin-badge" style="color: {esc(s.get('rarity_color'))};">{esc(s.get('rarity'))}</span>
                <strong class="skin-title">{esc(s.get('skin_name'))}</strong>
                <small class="skin-weapon">{esc(s.get('weapon_name'))}</small>
            </div>
        </div>
        """)

    # 4. MAÇ TABLOSU
    match_rows_html = []
    for m in matches:
        res_class = m.get("result_class", "draw")
        match_rows_html.append(f"""
        <tr>
            <td>
                <div class="map-cell">
                    <img src="{esc(m.get('map_splash', ''))}" class="map-mini" />
                    <strong>{esc(m.get('map_name'))}</strong>
                </div>
            </td>
            <td>{esc(m.get('game_mode'))}</td>
            <td>
                <div class="agent-cell">
                    <img src="{esc(m.get('agent_icon', ''))}" class="agent-mini" />
                    <span>{esc(m.get('agent_name'))}</span>
                </div>
            </td>
            <td><strong>{esc(m.get('kda_text'))}</strong> <small>({esc(m.get('kd_ratio'))} K/D)</small></td>
            <td><strong>{esc(m.get('acs', '—'))}</strong></td>
            <td><strong class="score-text">{esc(m.get('score_text'))}</strong></td>
            <td class="{res_class}"><strong>{esc(m.get('result'))}</strong></td>
            <td class="date-cell">{esc(m.get('date'))}</td>
        </tr>
        """)

    if not match_rows_html:
        match_rows_html.append("<tr><td colspan='8' class='empty-cell'>Kayıtlı maç bulunamadı.</td></tr>")

    # 5. CEZA KAYITLARI
    penalty_rows_html = []
    for p in penalties.get("records", []):
        penalty_rows_html.append(f"""
        <tr>
            <td><strong>{esc(p.get('type'))}</strong></td>
            <td class="{esc(p.get('badge_class'))}"><strong>{esc(p.get('state'))}</strong></td>
            <td>{esc(p.get('expiry'))}</td>
            <td>{esc(p.get('games_remaining'))}</td>
            <td>{esc(p.get('infraction'))}</td>
            <td>{esc(p.get('issued_date'))}</td>
        </tr>
        """)

    if not penalty_rows_html:
        penalty_rows_html.append("<tr><td colspan='6' class='empty-cell'>Hesapta herhangi bir ceza veya kısıtlama kaydı yok.</td></tr>")

    rank_detail_text = f"Kademe Puanı (RR): <strong>{esc(rr)} / 100</strong> &bull; Zirve: <strong>{esc(peak_rank)}</strong> ({esc(peak_season)})"
    if prev_act and rank.get("rank_tier") == 0:
        rank_detail_text += f" &bull; Geçen Kısım: <strong>{esc(prev_act)}</strong>"

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(riot_id)} - VALORANT Hesap Raporu</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0b1218;
            --bg-card: #15222e;
            --border: #293847;
            --text-main: #ece8e1;
            --text-muted: #94a3b8;
            --accent-red: #ff4655;
            --accent-green: #34d399;
            --accent-yellow: #f0bd4f;
            --accent-purple: #c084fc;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-base);
            color: var(--text-main);
            font-family: 'Inter', -apple-system, sans-serif;
            min-height: 100vh;
            line-height: 1.5;
            padding-bottom: 60px;
        }}
        header.hero-header {{
            position: relative;
            background: #111b24;
            border-bottom: 2px solid var(--border);
            overflow: hidden;
            padding: 40px 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .hero-banner-bg {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background-image: url('{esc(card_banner)}');
            background-size: cover;
            background-position: center;
            opacity: 0.15;
            filter: blur(8px);
        }}
        .hero-content {{
            position: relative;
            max-width: 1300px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 24px;
        }}
        .hero-profile {{
            display: flex;
            align-items: center;
            gap: 24px;
        }}
        .rank-avatar-box {{
            width: 88px;
            height: 88px;
            background: #1e2d3b;
            border: 2px solid var(--accent-red);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        .rank-avatar-box img {{
            width: 80%;
            height: 80%;
            object-fit: contain;
        }}
        .hero-text h1 {{
            font-size: 32px;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .region-badge {{
            font-size: 13px;
            font-weight: 700;
            background: var(--accent-red);
            color: #fff;
            padding: 3px 10px;
            border-radius: 6px;
        }}
        .hero-subtitle {{
            color: var(--accent-yellow);
            font-size: 14px;
            margin-top: 4px;
        }}
        .hero-meta {{
            text-align: right;
            color: var(--text-muted);
            font-size: 13px;
        }}
        .container {{
            max-width: 1300px;
            margin: 35px auto;
            padding: 0 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 35px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 22px;
        }}
        .stat-card small {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
            display: block;
            margin-bottom: 8px;
        }}
        .stat-card strong.value {{
            font-size: 28px;
            font-weight: 800;
            color: #fff;
        }}
        .wallet-row {{
            display: flex;
            gap: 16px;
            margin-top: 6px;
            font-size: 18px;
            font-weight: 700;
        }}
        .wallet-item.vp {{ color: #ff4655; }}
        .wallet-item.rp {{ color: #00ffb3; }}
        .wallet-item.kc {{ color: #f0bd4f; }}
        .progress-track {{
            height: 8px;
            background: #243545;
            border-radius: 10px;
            margin-top: 14px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: var(--accent-red);
        }}
        .stat-detail {{
            margin-top: 10px;
            font-size: 12px;
            color: var(--text-muted);
        }}
        h2.section-title {{
            font-size: 20px;
            font-weight: 800;
            margin-bottom: 18px;
            border-left: 4px solid var(--accent-red);
            padding-left: 12px;
            text-transform: uppercase;
        }}
        section {{
            margin-bottom: 40px;
        }}
        .shop-grid, .loadout-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px;
        }}
        .shop-card, .loadout-gun-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }}
        .shop-thumb-wrap, .gun-image-wrap {{
            height: 110px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #111b24;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 12px;
        }}
        .shop-thumb, .gun-image {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        .shop-name, .gun-skin-name {{
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            display: block;
        }}
        .shop-sub, .gun-type {{
            color: var(--text-muted);
            font-size: 12px;
        }}
        .rarity-tag {{
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid;
            display: inline-block;
        }}
        .table-wrap {{
            overflow-x: auto;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            min-width: 800px;
        }}
        th, td {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }}
        th {{
            background: #182836;
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
        }}
        .map-cell, .agent-cell {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .map-mini {{
            width: 50px;
            height: 32px;
            border-radius: 4px;
            object-fit: cover;
        }}
        .agent-mini {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #1a2734;
            object-fit: cover;
        }}
        .win, .good, .ready {{ color: var(--accent-green); font-weight: 700; }}
        .loss, .bad, .claimed {{ color: var(--accent-red); font-weight: 700; }}
        .draw, .unknown {{ color: var(--accent-yellow); font-weight: 700; }}
        .empty-cell {{
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
        }}
        .skins-collection-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
            gap: 14px;
            max-height: 520px;
            overflow-y: auto;
        }}
        .skin-item-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
        }}
        .skin-thumb-box {{
            height: 75px;
            background: #111b24;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 6px;
            margin-bottom: 8px;
        }}
        .skin-thumb {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        .skin-title {{
            font-size: 13px;
            font-weight: 700;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .skin-weapon {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .skin-badge {{
            font-size: 10px;
            font-weight: 700;
            display: block;
        }}
        footer {{
            text-align: center;
            color: #64748b;
            font-size: 12px;
            margin-top: 50px;
            line-height: 1.8;
        }}
    </style>
</head>
<body>

    <header class="hero-header">
        <div class="hero-banner-bg"></div>
        <div class="hero-content">
            <div class="hero-profile">
                <div class="rank-avatar-box">
                    <img src="{esc(rank_icon)}" alt="{esc(rank_name)}" />
                </div>
                <div class="hero-text">
                    <h1>{esc(riot_id)} <span class="region-badge">{esc(region)}</span></h1>
                    <div class="hero-subtitle">
                        {esc(card_title, 'Ajan')} &bull; PUUID: <code>{esc(puuid[:12])}...</code>
                    </div>
                </div>
            </div>
            <div class="hero-meta">
                <div>Kontrol Tarihi: <strong>{esc(check_time)}</strong></div>
                <div>Durum: <span class="{esc(penalty_class)}">{esc(penalty_status)}</span></div>
            </div>
        </div>
    </header>

    <div class="container">

        <!-- İSTATİSTİK KARTLARI -->
        <section class="stats-grid">
            <div class="stat-card">
                <small>Hesap Seviyesi</small>
                <strong class="value">{esc(lvl_num)}</strong>
                <div class="progress-track">
                    <div class="progress-fill" style="width: {progress_percent}%;"></div>
                </div>
                <div class="stat-detail">{esc(progress_text)} &bull; {num_tr(remaining_xp)} AP kaldı</div>
            </div>

            <div class="stat-card">
                <small>Rekabete Dayalı Kademe</small>
                <strong class="value" style="color: {esc(rank_color)};">
                    {esc(rank_name)}
                </strong>
                <div class="stat-detail">{rank_detail_text}</div>
            </div>

            <div class="stat-card">
                <small>Cüzdan / Bakiyeler</small>
                <div class="wallet-row">
                    <div class="wallet-item vp">{num_tr(vp)} VP</div>
                    <div class="wallet-item rp">{num_tr(rp)} RP</div>
                    <div class="wallet-item kc">{num_tr(kc)} KC</div>
                </div>
                <div class="stat-detail">Toplam Hesap AP: {num_tr(total_ap)}</div>
            </div>

            <div class="stat-card">
                <small>Günlük İlk Galibiyet</small>
                <strong class="value {esc(first_win_class)}">{esc(first_win_status)}</strong>
                <div class="stat-detail">{esc(first_win_detail)}</div>
            </div>

            <div class="stat-card">
                <small>Hesap Ceza Durumu</small>
                <strong class="value {esc(penalty_class)}">{esc(penalty_status)}</strong>
                <div class="stat-detail">{esc(penalty_detail)}</div>
            </div>

            <div class="stat-card">
                <small>Toplam Envanter</small>
                <strong class="value">{esc(total_custom_skins)} Skin</strong>
                <div class="stat-detail">{len(buddies)} Uğurluk &bull; {len(sprays)} Sprey &bull; {len(cards)} Kart</div>
            </div>
        </section>

        <!-- GÜNLÜK MAĞAZA -->
        <section>
            <h2 class="section-title">Günlük Mağaza Teklifleri (Kalan Süre: {esc(shop_remaining)})</h2>
            <div class="shop-grid">
                {''.join(daily_cards_html)}
            </div>
        </section>

        <!-- KUŞANILMIŞ SİLAHLAR -->
        <section>
            <h2 class="section-title">Kuşanılmış Silahlar</h2>
            <div class="loadout-grid">
                {''.join(equipped_cards_html)}
            </div>
        </section>

        <!-- SAHİP OLUNAN SKİNLER -->
        <section>
            <h2 class="section-title">Sahip Olunan Tüm Silah Skinleri ({esc(total_custom_skins)})</h2>
            <div class="skins-collection-grid">
                {''.join(skins_cards_html)}
            </div>
        </section>

        <!-- SON MAÇLAR -->
        <section>
            <h2 class="section-title">Son Maç Geçmişi</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Harita</th>
                            <th>Mod</th>
                            <th>Ajan</th>
                            <th>K / D / A</th>
                            <th>ACS</th>
                            <th>Skor</th>
                            <th>Sonuç</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(match_rows_html)}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- CEZALAR VE KISITLAMALAR -->
        <section>
            <h2 class="section-title">Ceza ve Kısıtlama Kayıtları</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Ceza Türü</th>
                            <th>Durum</th>
                            <th>Bitiş Zamanı</th>
                            <th>Kalan Maç</th>
                            <th>İhlal Nedeni</th>
                            <th>Veriliş Tarihi</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(penalty_rows_html)}
                    </tbody>
                </table>
            </div>
        </section>

    </div>

    <footer>
        VALORANT Account Checker &bull; dash.valorant-api.com ve Yerel Veritabanı ile Oluşturuldu.<br>
        Riot Games tarafından desteklenen resmi bir araç değildir. Oturum belirteçlerinizi kimseyle paylaşmayınız.
    </footer>

</body>
</html>
"""

    safe_name = "".join(c for c in riot_id if c.isalnum() or c in ("-", "_")).lower() or "account"
    filename = f"valorant_report_{safe_name}.html"
    file_path = REPORTS_DIR / filename

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = str(file_path.resolve())

    if open_in_browser:
        webbrowser.open(f"file:///{abs_path}")

    return abs_path
