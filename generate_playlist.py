import os
import sys
from datetime import datetime
import yt_dlp

print("🚀 YouTube HLS Playlist Generator (yt-dlp powered)")

# ---------------- Helper functions ---------------- #

def normalize_to_watch_url(token: str) -> str:
    """
    Accepts @handle, videoId, or any YouTube URL and returns a valid YouTube link.
    - @handle -> https://www.youtube.com/@handle/live
    - videoId -> https://www.youtube.com/watch?v=videoId
    - full URL -> returned as-is
    """
    token = token.strip()
    if not token:
        return None

    if token.startswith("@"):
        return f"https://www.youtube.com/{token}/live"

    if token.startswith("http://") or token.startswith("https://"):
        return token

    # Assume plain video id
    return f"https://www.youtube.com/watch?v={token}"


def extract_hls_url(url: str) -> str | None:
    """
    Uses yt-dlp to extract the best HLS (.m3u8) URL if available.
    Returns an m3u8 URL or None if not found / not live.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # Force yt-dlp to get the best actual stream URLs
        "format": "bestvideo+bestaudio/best",
        "geo_bypass": True,
        "source_address": "0.0.0.0",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"[DEBUG] Extracted info for {url}: {info.get('title')}")
    except yt_dlp.utils.DownloadError as e:
        print(f"[WARN] yt-dlp could not extract from {url}: {e}")
        return None
    except Exception as e:
        print(f"[WARN] Unexpected extractor error for {url}: {e}")
        return None

    # --- Find the best HLS .m3u8 URL ---
    formats = info.get("formats", []) or []
    hls_candidates = []
    for f in formats:
        proto = f.get("protocol") or ""
        url_f = f.get("url")
        if not url_f:
            continue
        if "m3u8" in proto or (isinstance(url_f, str) and ".m3u8" in url_f):
            hls_candidates.append((f.get("tbr", 0) or 0, url_f))

    if hls_candidates:
        hls_candidates.sort(key=lambda x: x[0])
        chosen = hls_candidates[-1][1]
        return chosen

    # Fallback: some live streams expose "url" directly
    fallback = info.get("url")
    if isinstance(fallback, str) and ".m3u8" in fallback:
        return fallback

    return None


# ---------------- Main generator ---------------- #

def generate_m3u8_playlist(input_file="links.txt", output_file="playlist.m3u8"):
    if not os.path.exists(input_file):
        print(f"[FATAL] Missing {input_file}. Please create it.")
        sys.exit(1)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines_out = ["#EXTM3U", f"# Generated on {now}", "#EXT-X-VERSION:3"]

    total = 0
    added = 0
    seen = set()

    with open(input_file, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 2:
                print(f"[SKIP] Malformed line (use 'Name | id/handle/url'): {line}")
                continue

            name, token = parts
            if token in seen:
                print(f"[SKIP] Duplicate: {token}")
                continue
            seen.add(token)
            total += 1

            url = normalize_to_watch_url(token)
            if not url:
                print(f"[SKIP] Could not normalize: {token}")
                continue

            print(f"[INFO] Processing {name} ({url})...")
            hls = extract_hls_url(url)
            if hls:
                lines_out.append(f"#EXTINF:-1,{name}")
                lines_out.append("#EXT-X-PROGRAM-ID:1")
                lines_out.append(hls)
                added += 1
                print(f"[OK] Added HLS for {name}")
            else:
                lines_out.append(f"#EXTINF:-1,{name} (offline)")
                print(f"[INFO] No HLS for {name} (not live or restricted).")

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("\n".join(lines_out) + "\n")

    print(f"[DONE] {added}/{total} entries produced HLS. Wrote '{output_file}'.")


if __name__ == "__main__":
    generate_m3u8_playlist()
