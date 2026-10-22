import os
import sys
import glob
from pathlib import Path
from dotenv import load_dotenv

# Pastikan console Windows mendukung output UTF-8 (Emoji & simbol)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()

# ==============================================================================
# MODE EKSEKUSI (LOCAL vs GITHUB ACTIONS)
# ==============================================================================
# Nilai yang didukung: "local" atau "github_action"
# Default: Jika terdeteksi di runner GitHub Actions, otomatis "github_action".
# Jika di komputer lokal, default "local". Anda bisa memaksa ganti di sini.
IS_IN_GITHUB = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
RUN_MODE = os.environ.get("APP_RUN_MODE", "github_action" if IS_IN_GITHUB else "local")

# ==============================================================================
# KONFIGURASI AUDIO & VOICEOVER (TTS)
# ==============================================================================
# Karakter Suara:
# - "id-ID-GadisNeural" (Wanita - ramah, jernih, ekspresif) -> DEFAULT
# - "id-ID-ArdiNeural" (Pria - berwibawa, nada edukasi/trivia)
TTS_VOICE = os.environ.get("TTS_VOICE", "id-ID-GadisNeural")
TTS_RATE = "+0%"  # Atur kecepatan narasi, contoh: "+5%" atau "-5%"
TTS_VOLUME = "+0%"

# Volume Mixing Audio
VOICEOVER_VOLUME = 1.0  # 100% suara narator
BGM_VOLUME = 0.15       # 15% musik latar agar narasi terdengar dominan

# ==============================================================================
# OTOMATISASI UPLOAD YOUTUBE
# ==============================================================================
# False = Mode Review Manual: Video dikirim ke Telegram, Anda klik tombol "Upload YouTube" jika setuju.
# True  = Mode Full Autopilot: Otomatis di-upload ke YouTube Shorts tanpa perlu klik tombol.
AUTO_UPLOAD_YOUTUBE = os.environ.get("AUTO_UPLOAD_YOUTUBE", "false").lower() == "true"

# ==============================================================================
# KONFIGURASI TOPIK UNTUK SCHEDULER
# ==============================================================================
# Pilihan Mode:
# - "ai_auto"   : Opsi A - Gemini AI otomatis membuat ide topik unik & bikin penasaran (DEFAULT)
# - "file_list" : Opsi B - Membaca baris demi baris dari file TOPICS_FILE
SCHEDULER_TOPIC_MODE = os.environ.get("SCHEDULER_TOPIC_MODE", "ai_auto")
TOPICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daftar_topik.txt")
HISTORY_TOPICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "riwayat_topik.txt")

# ==============================================================================
# DIREKTORI & ASSETS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "assets", "videos")
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# ==============================================================================
# RESOLUSI & FORMAT VIDEO (SHORTS 9:16)
# ==============================================================================
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_FPS = 24

# ==============================================================================
# DETEKSI IMAGEMAGICK (UNTUK MOVIEPY TEXTCLIP)
# ==============================================================================
def get_imagemagick_binary():
    # 1. Cek environment variable
    custom_bin = os.environ.get("IMAGEMAGICK_BINARY")
    if custom_bin and os.path.exists(custom_bin):
        return custom_bin

    if os.name == "nt":
        # Jalur umum di Windows
        candidates = [
            r"E:\motivasibackup\motivasi\ImageMagick\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
            r"E:\motivasi\ImageMagick\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
        ]
        # Cari di Program Files
        candidates.extend(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))
        candidates.extend(glob.glob(r"C:\Program Files (x86)\ImageMagick*\magick.exe"))

        for path in candidates:
            if os.path.exists(path):
                im_dir = os.path.dirname(os.path.abspath(path))
                os.environ["MAGICK_HOME"] = im_dir
                coders_dir = os.path.join(im_dir, "modules", "coders")
                if os.path.exists(coders_dir):
                    os.environ["MAGICK_CODER_MODULE_PATH"] = coders_dir
                os.environ["MAGICK_CONFIGURE_PATH"] = im_dir
                if im_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = im_dir + os.pathsep + os.environ.get("PATH", "")
                return path

        return "magick.exe"
    else:
        # Linux / GitHub Actions
        for path in ["/usr/bin/convert", "/usr/local/bin/convert", "convert"]:
            if os.path.exists(path) or path == "convert":
                return path
        return "convert"

IMAGEMAGICK_BINARY = get_imagemagick_binary()

# ==============================================================================
# GITHUB ACTIONS INTEGRATION
# ==============================================================================
GITHUB_REPO = os.environ.get("GITHUB_REPO", "feriwidiyanto25-svg/motivasi-sarkas")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
