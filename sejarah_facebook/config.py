import os
import sys
from dotenv import load_dotenv

# ==============================================================================
# KONFIGURASI PROYEK KHUSUS: SEJARAH & MISTERI FACEBOOK REELS
# Terisolasi penuh dari proyek YouTube Shorts.
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Muat environment variable dari .env root
load_dotenv(os.path.join(ROOT_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Direktori Aset Khusus Sejarah
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# File Riwayat Topik Anti-Duplikasi Khusus Sejarah
TOPICS_HISTORY_FILE = os.path.join(BASE_DIR, "riwayat_topik_sejarah.txt")

# Pastikan direktori penting selalu ada
for d in [ASSETS_DIR, IMAGES_DIR, AUDIO_DIR, TEMP_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# ==============================================================================
# KONFIGURASI FACEBOOK REELS API
# ==============================================================================
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")

# ==============================================================================
# KONFIGURASI SUARA (VOICEOVER) KHUSUS DOKUMENTER
# ==============================================================================
# id-ID-ArdiNeural: Suara Pria berat, berwibawa, dan misterius ala National Geographic
TTS_VOICE = "id-ID-ArdiNeural"
TTS_RATE = "+0%"
VOICEOVER_VOLUME = 1.0
BGM_VOLUME = 0.16

# ==============================================================================
# RESOLUSI & VISUAL STYLE
# ==============================================================================
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_FPS = 24

# Palet Warna Tipografi Dokumenter
COLOR_GOLD = (245, 158, 11, 255)      # Emas Kuno (#F59E0B) untuk kata kunci/tahun
COLOR_IVORY = (248, 250, 252, 255)   # Putih Gading (#F8FAFC) untuk teks narasi
BRAND_WATERMARK = "ARSIP SEJARAH"     # Watermark pembeda branding

# Jalur Font dari aset root
FONT_PATH = os.path.join(ROOT_DIR, "assets", "Poppins-Black.ttf")
if not os.path.exists(FONT_PATH):
    FONT_PATH = "DejaVu-Sans-Bold"
