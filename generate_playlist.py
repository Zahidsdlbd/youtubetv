import requests
import re
import os
import sys

# --- Core Scraper Function ---
def get_yt_hls(video_id):
    """
    Fetches the HLS manifest URL for a YouTube video ID or channel handle.
    Returns the HLS URL (str) or None on failure.
    """
    if video_id.startswith('@'):
        # For channel handles, use the /live URL
        url = f"https://www.youtube.com/{video_id}/live"
    else:
        # For standard video IDs
        url = f"https://www.youtube.com/watch?v={video_id}"
        
    headers = {
        # Using a standard browser User-Agent
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com"
    }
    
    try:
        # Fetch the YouTube page content
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status() # Raise exception for bad status codes (e.g., 404)
        
        # Search for the HLS manifest URL using regex
        # This key is typically present for active live streams
        match = re.search(r'"hlsManifestUrl":"([^"]+)"', r.text)
        
        if match:
            # Clean up the escaped ampersands (\u0026 -> &)
            hls_url = match.group(1).replace('\\u0026', '&')
            print(f"Found HLS URL for {video_id}")
            return hls_url
        else:
            print(f"HLS manifest not found in page source for {video_id}.")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching {video_id}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Connection Error fetching {video_id}: {e}")
    except Exception as e:
        print(f"Unexpected Error fetching HLS for {video_id}: {e}")
        
    return None

# --- Main Playlist Generator ---
def generate_m3u8_playlist(input_file="links.txt", output_file="playlist.m3u8"):
    """Reads input links, scrapes HLS URLs, and generates the M3U8 playlist file."""
    
    # Initialize the M3U8 file content with required headers
    playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
    streams_found = 0
    
    # Read the input links file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            links = f.readlines()
    except FileNotFoundError:
        print(f"FATAL ERROR: Input file '{input_file}' not found. Exiting.")
        sys.exit(1) # Exit the script if the required input file is missing

    # Process each link
    for line in links:
        line = line.strip()
        if not line or line.startswith('#'):
            continue # Skip empty lines or comments
            
        try:
            # Expected format: "Channel Name | Video ID or Handle"
            parts = [part.strip() for part in line.split('|')]
            
            if len(parts) != 2:
                print(f"Skipping malformed line: '{line}' - Must be 'Name | ID'")
                continue
                
            channel_name, video_id = parts
            
            # 1. Get the actual HLS URL
            hls_url = get_yt_hls(video_id)
            
            if hls_url:
                # 2. Format it into M3U8 entry
                # Use EXTINF:-1 for live streams (duration is unknown)
                playlist_content += f'\n#EXTINF:-1, {channel_name}\n'
                # Optional: Program ID is good practice for playlists
                playlist_content += '#EXT-X-PROGRAM-ID:1\n' 
                playlist_content += f'{hls_url}\n'
                streams_found += 1
            else:
                print(f"Failed to get active HLS stream for {channel_name} ({video_id}). Skipping.")
                
        except Exception as e:
            print(f"An unexpected error occurred while processing line '{line}': {e}")
            
    # Write the final playlist content to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(playlist_content)
        print(f"\n✅ Successfully generated and saved '{output_file}'. Total active streams found: {streams_found}")
    except Exception as e:
        print(f"FATAL ERROR: Could not write output file '{output_file}': {e}")

if __name__ == "__main__":
    generate_m3u8_playlist()
