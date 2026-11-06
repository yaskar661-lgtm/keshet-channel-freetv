import time
import threading
from flask import Flask, Response, request, redirect
import requests
import os

app = Flask(__name__)

HEADERS = {
    "User-Agent": "SmartOsTV",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,he;q=0.8",
    "Origin": "https://www.mako.co.il",
    "Referer": "https://www.mako.co.il/",
    "Accept-Encoding": "identity",
}

CHANNELS = {
    "k12": {
        "master": "https://mako-streaming.akamaized.net/stream/hls/live/2033791/k12/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/stream/hls/live/2033791/k12/",
    },
    "k12wad": {
        "master": "https://mako-streaming.akamaized.net/stream/hls/live/2033791/k12n12wad/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/stream/hls/live/2033791/k12n12wad/",
    },
    "comedy": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_comedy/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_comedy/"
    },
    "drama": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_drama/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_drama/"
    },
    "music": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_music/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_music/"
    },
    "food": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_food/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_food/"
    },
    "erets": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/erets/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/erets/"
    },
    "savri": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/savri/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/savri/"
    },
    "ch24live": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/ch24live/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/ch24live/"
    },
    "t24": {
        "master": "https://mako-streaming.akamaized.net/direct/hls/live/2035340/ch24live/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/direct/hls/live/2035340/ch24live/"
    }  
}

cache = {
    "ticket": None
}

def update_ticket_background():
    """Ticket'ı (hdnea) arka planda 5 dakikada bir yeniler."""
    while True:
        try:
            s = requests.Session()
            res = s.get(
                "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=ngt&lp=/stream/hls/live/2033791/k12/index.m3u8?as=1&rv=AKAMAI",
                headers=HEADERS
            ).json()
            cache["ticket"] = res["tickets"][0]["ticket"]
            print("[INFO] Ticket başarıyla güncellendi.")
        except Exception as e:
            print(f"[ERROR] Ticket güncelleme hatası: {e}")
        
        time.sleep(300) # 5 dakika

@app.route("/isr/<name>.m3u8")
def serve_playlist(name):
    """Kanal için güncel bileti ekler ve Cloudflare Worker adresine yönlendirir (redirect)."""
    if name not in CHANNELS:
        return "Channel not found", 404
    
    data = CHANNELS[name]
    toki = cache.get("ticket", "")
    
    master_url = data["master"]
    
    # Master URL ile bileti birleştirme
    if master_url.endswith(".m3u8") and toki:
        master_url_with_ticket = f"{master_url}?{toki}"
    else:
        master_url_with_ticket = master_url
    
    # İstediğin formatta Worker adresine yönlendiriyoruz (302 Geçici Yönlendirme)
    guard_url = f"https://guard.sekobes.workers.dev/?url={master_url_with_ticket}"
    return redirect(guard_url, code=302)

@app.route("/restart")
def restart_server():
    """Sunucuyu öldürmeden (veya döngüyü kesmeden) yeniden başlatır."""
    def delayed_restart():
        time.sleep(1)
        python = sys.executable
        os.execl(python, python, *sys.argv)

    threading.Thread(target=delayed_restart).start()
    return {"status": "success", "message": "Sunucu yeniden başlatılıyor..."}, 200

if __name__ == "__main__":
    t = threading.Thread(target=update_ticket_background, daemon=True)
    t.start()
    
    try:
        s = requests.Session()
        res = s.get(
            "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=ngt&lp=/stream/hls/live/2033791/k12/index.m3u8?as=1&rv=AKAMAI",
            headers=HEADERS
        ).json()
        cache["ticket"] = res["tickets"][0]["ticket"]
    except:
        pass

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
