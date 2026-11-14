"""
VALORANT ACCOUNT CHECKER & DATABASE
Komut Satırı Arayüzü (CLI Runner)
Terminal üzerinden kontrol, veritabanı listeleme ve geçmiş sorgulama sağlar.
"""

import argparse
import sys
import webbrowser
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import AUTH_URL, DEFAULT_REGION, SUPPORTED_REGIONS
from database.db import db
from services.checker_engine import checker_engine
from services.content_service import content_service
from services.html_exporter import generate_account_html_report
from services.riot_service import RiotClient

console = Console()


def print_banner():
    banner_text = (
        "[bold red]VALORANT ACCOUNT CHECKER & DATABASE[/bold red]\n"
        "[dim]Hesap Kontrolü, SQLite Veritabanı, Detaylı Loglama & 21 Endpoint[/dim]"
    )
    console.print(Panel(banner_text, border_style="red", expand=False))


def cli_check(region: Optional[str] = None, notes: str = ""):
    """Terminal üzerinden hesap kontrolü yapar ve veritabanına kaydeder."""
    print_banner()

    reg = (region or "").strip().lower()
    if not reg:
        reg_input = console.input(f"[bold cyan]Bölge seçin (eu/na/ap/kr/latam/br)[/bold cyan] [yellow][{DEFAULT_REGION}][/yellow]: ").strip().lower()
        reg = reg_input or DEFAULT_REGION

    if reg not in SUPPORTED_REGIONS:
        console.print(f"[bold red]Hata:[/bold red] Geçersiz bölge: '{reg}'. Desteklenenler: {', '.join(SUPPORTED_REGIONS.keys())}")
        return

    console.print(f"\n[bold green]✓[/bold green] Seçilen Bölge: [bold white]{SUPPORTED_REGIONS[reg]}[/bold white]")
    console.print("\n[bold yellow]Riot Giriş Sayfası Açılıyor...[/bold yellow]")

    try:
        webbrowser.open(AUTH_URL)
    except Exception:
        pass

    console.print("[dim]Tarayıcınız açılmadıysa şu adrese gidin:[/dim]")
    console.print(f"[cyan]{AUTH_URL}[/cyan]\n")
    console.print("[bold yellow]Giriş yaptıktan sonra yönlendirildiğiniz sayfanın adres çubuğundaki URL'yi buraya yapıştırın:[/bold yellow]")

    redirect_url = console.input("[bold cyan]Yönlendirme URL'si:[/bold cyan] ").strip()
    if not redirect_url:
        console.print("[bold red]URL girilmedi. İşlem iptal edildi.[/bold red]")
        return

    client = None
    with console.status("[bold green]Riot API ile bağlantı kuruluyor ve tüm uç noktalar taranıyor...", spinner="dots"):
        try:
            content_service.ensure_initialized()
            client = RiotClient(region=reg)
            client.authenticate_url(redirect_url)

            snapshot = checker_engine.run_check(client, notes=notes)

        except Exception as e:
            console.print(f"\n[bold red]Kontrol Başarısız Oldu:[/bold red] {e}")
            if client:
                client.close()
            return

    console.print("\n[bold green]✓ HESAP BAŞARIYLA KONTROL EDİLDİ VE VERİTABANINA LOGLANDI![/bold green]\n")

    # Sonuçları Terminalde Göster
    display_snapshot_cli(snapshot)

    # HTML Raporunu Üret ve Aç
    try:
        report_path = generate_account_html_report(snapshot, open_in_browser=True)
        console.print(f"\n[bold green]✓ HTML Raporu oluşturuldu ve tarayıcıda açıldı:[/bold green]\n[cyan]{report_path}[/cyan]\n")
    except Exception as ex:
        console.print(f"[yellow]HTML raporu kaydedilemedi:[/yellow] {ex}")

    if client:
        client.close()


def display_snapshot_cli(snapshot: dict):
    """Snapshot verilerini şık terminal tablolarıyla yazdırır."""
    acc = snapshot.get("account", {})
    lvl = snapshot.get("level", {})
    rank = snapshot.get("rank", {})
    wallet = snapshot.get("wallet", {})
    penalties = snapshot.get("penalties", {})
    first_win = snapshot.get("first_win", {})
    owned_skins = snapshot.get("owned_skins", [])
    store = snapshot.get("store", {})
    matches = snapshot.get("matches", [])

    # 1. Genel Bilgiler Tablosu
    info_table = Table(title=f"Hesap Kimliği: {acc.get('riot_id')} ({acc.get('region', '').upper()})", border_style="red")
    info_table.add_column("Parametre", style="cyan", no_wrap=True)
    info_table.add_column("Değer", style="white")

    info_table.add_row("Riot ID", f"[bold]{acc.get('riot_id')}[/bold]")
    info_table.add_row("PUUID", acc.get("puuid", ""))
    info_table.add_row("Bölge", acc.get("region", "").upper())
    info_table.add_row("Hesap Seviyesi", f"[bold green]{lvl.get('level')}[/bold green] ({lvl.get('progress_text', '')})")
    info_table.add_row("Toplam Hesap AP", f"{lvl.get('total_ap', 0):,}".replace(",", "."))
    info_table.add_row("Dereceli Kademe", f"[bold yellow]{rank.get('rank_name')}[/bold yellow] ({rank.get('ranked_rating', 0)} RR)")
    info_table.add_row("Zirve Kademe", str(rank.get("peak_rank", "")))
    info_table.add_row("Cüzdan Bakiyesi", f"[red]{wallet.get('VP', 0):,} VP[/red] | [green]{wallet.get('RP', 0):,} RP[/green] | [yellow]{wallet.get('KC', 0):,} KC[/yellow]".replace(",", "."))
    info_table.add_row("Günlük İlk Galibiyet", f"{first_win.get('status')} - {first_win.get('detail', '')}")
    info_table.add_row("Ceza Durumu", f"[{'green' if penalties.get('status_class') == 'good' else 'red'}]{penalties.get('status')}[/]")
    info_table.add_row("Özel Silah Skinleri", f"[bold cyan]{len(owned_skins)} adet[/bold cyan]")
    info_table.add_row("Kontrol Tarihi", snapshot.get("check_time_local", ""))

    console.print(info_table)

    # 2. Günlük Mağaza
    daily_offers = store.get("daily_offers", [])
    if daily_offers:
        store_table = Table(title=f"Günlük Mağaza Teklifleri (Kalan Süre: {store.get('remaining_duration_text')})", border_style="yellow")
        store_table.add_column("Silah", style="cyan")
        store_table.add_column("Skin Adı", style="bold white")
        store_table.add_column("Nadirlik", style="magenta")

        for item in daily_offers:
            store_table.add_row(item.get("weapon_name", ""), item.get("skin_name", ""), item.get("rarity", "Standart"))

        console.print(store_table)

    # 3. Son Maçlar Tablosu
    if matches:
        match_table = Table(title=f"Son {len(matches)} Maç Geçmişi", border_style="blue")
        match_table.add_column("Tarih", style="dim")
        match_table.add_column("Harita", style="cyan")
        match_table.add_column("Mod", style="white")
        match_table.add_column("Ajan", style="yellow")
        match_table.add_column("K/D/A", style="bold")
        match_table.add_column("Skor", style="white")
        match_table.add_column("Sonuç", style="bold")

        for m in matches[:10]:
            res_style = "green" if m.get("result") == "Galibiyet" else ("red" if m.get("result") == "Mağlubiyet" else "yellow")
            match_table.add_row(
                m.get("date", ""),
                m.get("map_name", ""),
                m.get("game_mode", ""),
                m.get("agent_name", ""),
                f"{m.get('kda_text')} ({m.get('kd_ratio')} KD)",
                m.get("score_text", ""),
                f"[{res_style}]{m.get('result')}[/{res_style}]"
            )

        console.print(match_table)


def cli_list():
    """Veritabanındaki hesapları listeler."""
    print_banner()
    accounts = db.get_accounts()

    if not accounts:
        console.print("[yellow]Veritabanında kayıtlı hesap bulunmuyor. 'python cli.py check' ile yeni hesap tarayabilirsiniz.[/yellow]")
        return

    table = Table(title=f"Veritabanındaki Kayıtlı Hesaplar ({len(accounts)} Hesap)", border_style="green")
    table.add_column("Riot ID", style="bold white")
    table.add_column("Bölge", style="cyan")
    table.add_column("Seviye", style="green")
    table.add_column("Kademe (Rank)", style="yellow")
    table.add_column("Cüzdan (VP/RP/KC)", style="magenta")
    table.add_column("Ceza", style="white")
    table.add_column("Kontrol Sayısı", style="dim")
    table.add_column("Son Kontrol Tarihi", style="dim")

    for acc in accounts:
        table.add_row(
            acc.get("riot_id", ""),
            acc.get("region", "").upper(),
            f"Lv. {acc.get('last_level', 1)}",
            f"{acc.get('last_rank_name', 'Derecesiz')} ({acc.get('last_rr', 0)} RR)",
            f"{acc.get('last_vp', 0)} / {acc.get('last_rp', 0)} / {acc.get('last_kc', 0)}",
            f"[{'green' if acc.get('last_penalty_status') == 'Temiz' else 'red'}]{acc.get('last_penalty_status')}[/]",
            str(acc.get("total_checks", 1)),
            acc.get("updated_at", "").replace("T", " ")[:19]
        )

    console.print(table)


def cli_history(identifier: str):
    """Belirli bir hesabın geçmiş kontrol loglarını listeler."""
    print_banner()

    accounts = db.get_accounts()
    target_puuid = None
    target_name = None

    for acc in accounts:
        if acc["puuid"].lower() == identifier.lower() or acc["riot_id"].lower() == identifier.lower():
            target_puuid = acc["puuid"]
            target_name = acc["riot_id"]
            break

    if not target_puuid:
        console.print(f"[bold red]Hata:[/bold red] '{identifier}' ile eşleşen hesap bulunamadı.")
        return

    logs = db.get_account_logs(target_puuid)
    if not logs:
        console.print(f"[yellow]{target_name} için log kaydı bulunamadı.[/yellow]")
        return

    table = Table(title=f"{target_name} - Kontrol Tarihçesi ({len(logs)} Log)", border_style="cyan")
    table.add_column("Log ID", style="dim")
    table.add_column("Kontrol Tarihi", style="bold white")
    table.add_column("Seviye", style="green")
    table.add_column("Kademe", style="yellow")
    table.add_column("VP / RP / KC", style="magenta")
    table.add_column("Ceza Durumu", style="white")
    table.add_column("Skin", style="cyan")

    for l in logs:
        table.add_row(
            f"#{l.get('id')}",
            l.get("check_date_local", ""),
            f"Lv. {l.get('level')}",
            f"{l.get('rank_name')} ({l.get('ranked_rating')} RR)",
            f"{l.get('wallet_vp')} / {l.get('wallet_rp')} / {l.get('wallet_kc')}",
            l.get("penalty_status", "Temiz"),
            f"{l.get('skins_count')} skin"
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="VALORANT Account Checker & Database CLI")
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")

    # check
    check_parser = subparsers.add_parser("check", help="Yeni bir Valorant hesabı kontrol et ve logla")
    check_parser.add_argument("-r", "--region", help="Bölge (eu, na, ap, kr, latam, br)")
    check_parser.add_argument("-n", "--notes", default="", help="Kontrol notu")

    # list
    subparsers.add_parser("list", help="Veritabanındaki kayıtlı hesapları listele")

    # history
    hist_parser = subparsers.add_parser("history", help="Bir hesabın kontrol tarihçesini listele")
    hist_parser.add_argument("identifier", help="Riot ID (Örn: Oyuncu#TR1) veya PUUID")

    args = parser.parse_args()

    if args.command == "check":
        cli_check(region=args.region, notes=args.notes)
    elif args.command == "list":
        cli_list()
    elif args.command == "history":
        cli_history(args.identifier)
    else:
        # Parametresiz çalıştırıldığında doğrudan kontrol başlat
        cli_check()


if __name__ == "__main__":
    main()
