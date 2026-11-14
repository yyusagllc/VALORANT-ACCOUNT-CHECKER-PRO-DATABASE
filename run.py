"""
VALORANT ACCOUNT CHECKER & DATABASE
Evrensel Başlatıcı (Launcher)
Varsayılan olarak Web Uygulaması ve Veritabanı Arayüzünü başlatır ve tarayıcıyı açar.
--cli bayrağı verilirse komut satırı arayüzünü (CLI) çalıştırır.
--port <port> ile özel port belirlenebilir.
"""

import sys
import threading
import time
import webbrowser
import uvicorn

from config import DEFAULT_PORT, SERVER_HOST, get_free_port, is_port_in_use


def open_browser(url: str):
    """Sunucu hazır olduğunda tarayıcıyı açar."""
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def start_web_server(port: int):
    """FastAPI Web Arayüzünü ve REST API sunucusunu başlatır."""
    server_url = f"http://{SERVER_HOST}:{port}"

    print("=" * 65)
    print("         VALORANT ACCOUNT CHECKER & DATABASE v2.0")
    print("=" * 65)
    print(f" Web Arayüzü: {server_url}")
    print(f" Veritabanı : valochecker.db (SQLite)")
    print(f" API Belgesi: {server_url}/docs")
    print("=" * 65)

    if port != DEFAULT_PORT:
        print(f" [BİLGİ] Port {DEFAULT_PORT} sisteminizde başka bir uygulama tarafından")
        print(f"         kullanıldığı için otomatik olarak {port} portuna geçildi.")
        print("=" * 65)

    print(" Tarayıcınız otomatik olarak açılıyor...")
    print(" Durdurmak için: CTRL + C tuşlarına basın.\n")

    threading.Thread(target=open_browser, args=(server_url,), daemon=True).start()

    uvicorn.run(
        "app:app",
        host=SERVER_HOST,
        port=port,
        log_level="info",
        reload=False
    )


def main():
    if "--cli" in sys.argv:
        # CLI modunda çalıştır
        import cli
        sys.argv.remove("--cli")
        cli.main()
        return

    # Port argümanı kontrolü (--port 8080)
    target_port = None
    if "--port" in sys.argv:
        try:
            idx = sys.argv.index("--port")
            target_port = int(sys.argv[idx + 1])
            sys.argv.pop(idx + 1)
            sys.argv.pop(idx)
        except Exception:
            pass

    if target_port is None:
        target_port = get_free_port(DEFAULT_PORT, SERVER_HOST)
    else:
        if is_port_in_use(target_port, SERVER_HOST):
            print(f"[UYARI] Belirtilen port ({target_port}) kullanımda. Uygun bir port aranıyor...")
            target_port = get_free_port(target_port, SERVER_HOST)

    start_web_server(target_port)


if __name__ == "__main__":
    main()
