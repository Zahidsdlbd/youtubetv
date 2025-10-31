import os
import re
import sys
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter, Retry

# ---------- HTTP session with retries ----------
def make_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = make_session()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.youtube.com/",
    "Origin": "https://www.youtube.com",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------- Core: find HLS manifest ----------
def get_yt_hls(video_id_or_handle: str):
    """
    Returns an HLS manifest URL for a YouTube video ID or channel handle (@handle),
    or None if not found / not live.
    """
    vid = video_id_or_handle.strip()
    if not vid:
        return None

    # Handles: @channelname → /live ; Video IDs → watch?v=
    if vid.startswith("@"):
        url = f"https://www.youtube.com/{vid}/live"
    else:
        url = f"https://www.youtube.com/watch?v={vid}"

    try:
        r = SESSION.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] HTTP error for {vid}: {e}")
        return None

    html = r.text

    # Primary pattern: "hlsManifestUrl":"<url>"
    m = re.search(r'"hlsManifestUrl":"([^"]+)"', html)
    if m:
        hls = m.group(1).replace("\\u0026", "&")
        print(f"[OK] HLS found for {vid}")
        return hls

    # Fallback: sometimes escaped inside playerResponse objects
    m2 = re.search(r'"hlsManifestUrl"\\s*:\\s*"([^"]+)"', html)
    if m2:
        hls = m2.group(1).replace("\\u0026", "&").replace("\\/", "/")
        print(f"[OK] HLS (fallback) found for {vid}")
        return hls

    print(f"[INFO] No active HLS found for {vid} (likely not live).")
    return None

# ---------- Main builder ----------
def generate_m3u8_playlist(input_file="links.txt", output_file="playlist.m3u8"):
    if not os.path.exists(input_file):
        print(f"[FATAL] Input file '{input_file}' not found.")
        sys.exit(1)

    # Header with timestamp (UTC)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    playlist = [ "#EXTM3U", f"# Generated on {ts}", "#EXT-X-VERSION:3" ]

    streams_found = 0
    seen = set()

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue

            parts = [p.strip() for p in raw.split("|")]
            if len(parts) != 2:
                print(f"[SKIP] Malformed line (expected 'Name | ID'): {raw}")
                continue

            channel_name, vid = parts
            if vid in seen:
                print(f"[SKIP] Duplicate ID/handle: {vid}")
                continue
            seen.add(vid)

            hls = get_yt_hls(vid)
            if not hls:
                continue

            # M3U8 entries
            playlist.append(f"")
            playlist.append(f"#EXTINF:-1,{channel_name}")
            playlist.append("#EXT-X-PROGRAM-ID:1")
            playlist.append(hls)
            streams_found += 1

    # Always write file (even if 0 streams) so the workflow can diff reliably
    try:
        with open(output_file, "w", encoding="utf-8") as out:
            out.write("\n".join(playlist) + "\n")
        print(f"[DONE] Wrote '{output_file}'. Active streams: {streams_found}")
    except Exception as e:
        print(f"[FATAL] Could not write '{output_file}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate_m3u8_playlist()
