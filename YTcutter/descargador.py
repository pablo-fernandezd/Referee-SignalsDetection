import yt_dlp

url = "https://www.youtube.com/watch?v=TMou-6_4w10"
output_dir = "../dataVideo"

# Configuración de yt-dlp
ydl_opts = {
    "outtmpl": f"{output_dir}/%(title)s.%(ext)s",  # Guardar en dataVideo
    "merge_output_format": "mp4",                   # Formato final
    "cookies": "cookies.txt"                        # Para videos restringidos
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
