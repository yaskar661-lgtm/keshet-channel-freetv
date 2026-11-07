import os
import sys
import threading
import time
from flask import Flask, Response, redirect, request
import requests

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
    "n12rh": {
        "master": "https://mako-streaming.akamaized.net/n12/hls/live/20000821/k12rh/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/n12/hls/live/20000821/k12rh/",
    },
    "k12cc": {
        "master": "https://d2249b6f08tjt0.cloudfront.net/k12cc/index.m3u8",
        "base": "https://d2249b6f08tjt0.cloudfront.net/k12cc/",
    },
    "comedy": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_comedy/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_comedy/",
    },
    "drama": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_drama/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_drama/",
    },
    "music": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_music/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_music/",
    },
    "food": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_food/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/free_food/",
    },
    "erets": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/erets/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/erets/",
    },
    "savri": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/savri/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/savri/",
    },
    "ch24live": {
        "master": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/ch24live/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/evrideo/hls/live/20001278/ch24live/",
    },
    "t24": {
        "master": "https://mako-streaming.akamaized.net/direct/hls/live/2035340/ch24live/index.m3u8",
        "base": "https://mako-streaming.akamaized.net/direct/hls/live/2035340/ch24live/",
    },
}

cache = {"ticket": None, "aws-ticket": None}


def fetch_akamai_ticket():
  """Akamai biletini API'den çeker ve cache'e kaydeder."""
  try:
    s = requests.Session()
    res = s.get(
        "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=ngt&lp=/stream/hls/live/2033791/k12/index.m3u8?as=1&rv=AKAMAI",
        headers=HEADERS,
        timeout=10,
    ).json()
    cache["ticket"] = res["tickets"][0]["ticket"]
    print("[INFO] Akamai Ticket başarıyla güncellendi.")
  except Exception as e:
    print(f"[ERROR] Akamai Ticket güncelleme hatası: {e}")


def fetch_aws_ticket():
  """AWS (Cloudfront) biletini API'den çeker ve cache'e kaydeder."""
  try:
    s = requests.Session()
    res = s.get(
        "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp?et=ngt&lp=/stream/hls/live/2033791/k12/index.m3u8?as=1&rv=AWS",
        headers=HEADERS,
        timeout=10,
    ).json()
    cache["aws-ticket"] = res["tickets"][0]["ticket"]
    print("[INFO] AWS Ticket başarıyla güncellendi.")
  except Exception as e:
    print(f"[ERROR] AWS Ticket güncelleme hatası: {e}")


def update_akamai_ticket_background():
  """Akamai Ticket'ını arka planda 5 dakikada bir yeniler."""
  while True:
    time.sleep(300)
    fetch_akamai_ticket()


def update_aws_ticket_background():
  """Cloudfront için Ticket'ı arka planda 1 saatte bir yeniler."""
  while True:
    time.sleep(3.600)
    fetch_aws_ticket()


@app.route("/isr/<name>.m3u8")
def serve_playlist_worker(name):
  """Kanal için güncel Akamai bileti ekler ve Cloudflare Worker adresine yönlendirir."""
  if name not in CHANNELS:
    return "Channel not found", 404

  data = CHANNELS[name]
  toki = cache.get("ticket", "")
  master_url = data["master"]

  if master_url.endswith(".m3u8") and toki:
    master_url_with_ticket = f"{master_url}?b-in-range=0-5000&{toki}"
  else:
    master_url_with_ticket = master_url

  guard_url = f"https://guard.sekobes.workers.dev/?url={master_url_with_ticket}"
  return redirect(guard_url, code=302)


@app.route("/isr2/<name>.m3u8")
def serve_playlist_aws(name):
  """Kanal için güncel AWS bileti ekler ve doğrudan ana m3u8 adresine yönlendirir."""
  if name not in CHANNELS:
    return "Channel not found", 404

  data = CHANNELS[name]
  toki = cache.get("aws-ticket", "")
  master_url = data["master"]

  if master_url.endswith(".m3u8") and toki:
    master_url_with_ticket = f"{master_url}?b-in-range=0-5000&{toki}"
  else:
    master_url_with_ticket = master_url

  return redirect(master_url_with_ticket, code=302)


@app.route("/restart")
def restart_server():
  """Sunucuyu yeniden başlatır."""

  def delayed_restart():
    time.sleep(1)
    python = sys.executable
    os.execl(python, python, *sys.argv)

  threading.Thread(target=delayed_restart).start()
  return {"status": "success", "message": "Sunucu yeniden başlatılıyor..."}, 200


if __name__ == "__main__":
  # Uygulama başlarken ilk biletleri hemen çek
  fetch_akamai_ticket()
  fetch_aws_ticket()

  # Arka plan iş parçacıklarını başlat
  threading.Thread(
      target=update_akamai_ticket_background, daemon=True
  ).start()
  threading.Thread(target=update_aws_ticket_background, daemon=True).start()

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port, threaded=True)
