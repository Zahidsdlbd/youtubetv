import requests
import re
import os

# --- Core Scraper Function ---
def get_yt_hls(video_id):
    """Fetches the HLS manifest URL for a YouTube video ID or channel handle."""
    if video_id.startswith('@'):
        # For channel handles, use the /live URL
        url = f"https://www.youtube.com/{video_id}/live"
    else:
        # For standard video IDs
        url = f"https://www.youtube.com/watch?v={video_id}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com"
    }
    
    try:
        # Fetch the YouTube page content
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status() # Raise exception for bad status codes
        
        # Search for the HLS manifest URL in the page source
        match = re.search(r'"hlsManifestUrl":"([^"]+)"', r.text)
        
        if match:
            # Clean up the escaped ampersands
            hls_url = match.group(1).replace('\\u0026', '&')
            print(f"Found HLS URL for {video_id}")
            return hls_url
    except Exception as e:
        print(f"Error fetching HLS for {video_id}: {e}")
        pass
        
    return None

# --- Main Playlist Generator ---
def generate_m3u8_playlist(input_file="links.txt", output_file="playlist.m3u8"):
    """Reads input links, scrapes HLS URLs, and generates the M3U8 playlist."""
    
    # Start the M3U8 file content
    playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    
    # Read the input links file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            links = f.readlines()
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return

    # Process each link
    for line in links:
        line = line.strip()
        if not line or line.startswith('#'):
            continue # Skip empty lines or comments
            
        try:
            # Expected format: "Channel Name | Video ID or Handle"
            parts = [part.strip() for part in line.split('|')]
            if len(parts) != 2:
                print(f"Skipping malformed line: {line}")
                continue
                
            channel_name, video_id = parts
            
            # 1. Get the actual HLS URL
            hls_url = get_yt_hls(video_id)
            
            if hls_url:
                # 2. Format it into M3U8 entry
                # Use EXTINF:-1 for live/unknown duration
                playlist_content += f'\n#EXTINF:-1, {channel_name}\n'
                # Optional: Add a program ID (common for playlists)
                playlist_content += '#EXT-X-PROGRAM-ID:1\n' 
                playlist_content += f'{hls_url}\n'
            else:
                print(f"Failed to get HLS for {channel_name} ({video_id}). Skipping.")
                
        except Exception as e:
            print(f"An unexpected error occurred processing line '{line}': {e}")
            
    # Write the final playlist content to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print(f"\nSuccessfully generated and saved '{output_file}'. Total entries: {playlist_content.count('#EXTINF')}")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    # Ensure dependencies are installed if run locally
    # In GitHub Actions, 'pip install requests' handles this
    generate_m3u8_playlist()