import yt_dlp
import os # Keep os import

url = "https://www.youtube.com/watch?v=TMou-6_4w10" # Example URL
# Corrected path relative to src/utils/
output_dir = "../../data/input_videos"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Configuración de yt-dlp (Keeping original Spanish comment as example if present)
# yt-dlp configuration
ydl_opts = {
    # Path template for output files
    "outtmpl": os.path.join(output_dir, '%(title)s.%(ext)s'),
    # Final video format
    "merge_output_format": "mp4",
    # Use cookies from browser (e.g., Chrome) if needed for restricted videos
    "cookiesfrombrowser": ('chrome',),
    # Alternative: specify cookies file path:
    # "cookies": "cookies.txt"
    "quiet": False, # Show standard output
    "noplaylist": True, # Only download single video
    # Preferred format selection
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
}

print(f"Starting download for: {url}")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print("Download complete.")
except Exception as e:
    print(f"An error occurred during download: {e}")