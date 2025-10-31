import os, re, sys, requests
from datetime import datetime
from requests.adapters import HTTPAdapter, Retry

def make_session():
    session = requests.Session()
    retries = Retry(
        total=3, backoff_factor=2,
        status_forcelist=[429,500,502,503,504],
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

session = make_session()
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.youtube.com"}

def get_yt_hls(video_id):
    if video_id.startswith('@'):
        url = f"https://www.youtube.com/{video_id}/live"
    else:
        url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        m = re.search(r'"hlsManifestUrl":"([^"]+)"', r.text)
        if m:
            return m.group(1).replace("\\u0026", "&")
    except Exception as e:
        print(f"Error fetching {video_id}: {e}")
    return None

def generate_m3u8_playlist(input_file="links.txt", output_file="playlist.m3u8"):
    if not os.path.exists(input_file):
        print(f"Missing {input_file}")
        sys.exit(1)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    playlist = [f"#EXTM3U", f"# Generated on {now}", "#EXT-X-VERSION:3"]
    found = 0
    seen = set()

    for line in open(input_file, "r", encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            name, vid = [p.strip() for p in line.split("|")]
            if vid in seen: continue
            seen.add(vid)
            hls = get_yt_hls(vid)
            if hls:
                playlist += [f"#EXTINF:-1,{name}", "#EXT-X-PROGRAM-ID:1", hls]
                found += 1
        except Exception as e:
            print(f"Error parsing line {line}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(playlist))
    print(f"✅ Saved {output_file} with {found} streams.")

if __name__ == "__main__":
    generate_m3u8_playlist()
