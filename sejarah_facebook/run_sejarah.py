import os
import sys
import argparse

# Pastikan console Windows mendukung output UTF-8
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Pastikan path modul terbaca dengan benar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from . import config
from .ai_generator import generate_history_script
from .video_engine import render_history_video
from .fb_uploader import upload_to_facebook_reels

def main():
    parser = argparse.ArgumentParser(description="Autopilot Video Dokumenter Sejarah Facebook Reels")
    parser.add_argument("--topik", type=str, default="", help="Topik kustom (kosongkan untuk auto-generate)")
    parser.add_argument("--skip-upload", action="store_true", help="Lewati proses upload, hanya render lokal")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("      [START] MEMULAI PROYEK DOKUMENTER SEJARAH FACEBOOK      ")
    print("="*60)

    # 1. GENERATE IDE & NASKAH DOKUMENTER
    print("\n1. Membuat Naskah Storytelling Sejarah via Gemini AI...")
    naskah = generate_history_script(topic=args.topik if args.topik else None)

    print(f"\n[+] Judul Video : {naskah.get('title')}")
    print(f"[+] Serial      : {naskah.get('series_tag')}")
    print(f"[+] Jumlah Babak: {len(naskah.get('scenes', []))} scenes")

    # Tampilkan prompt gambar yang dihasilkan untuk Flow / MCP
    image_prompts = naskah.get("image_prompts", [])
    if image_prompts:
        print("\n[+] Prompt Visual yang Disiapkan untuk Flow / MCP:")
        for idx, p in enumerate(image_prompts, 1):
            print(f"  [{idx}] {p}")

    # 2. RENDER VIDEO DOKUMENTER
    print("\n2. Merakit Video Dokumenter Sinematik...")
    video_path = render_history_video(naskah)

    if not video_path or not os.path.exists(video_path):
        print("[-] Gagal merender video sejarah.")
        return False

    print(f"[+] Video berhasil dirakit: {video_path}")

    # 3. UPLOAD KE FACEBOOK REELS
    if args.skip_upload:
        print("[INFO] Mode --skip-upload aktif. Video disimpan di folder output.")
        return True

    print("\n3. Memproses Publikasi ke Facebook Reels...")
    title = naskah.get("title", "Arsip Sejarah Dunia")
    caption = naskah.get("caption", f"{title}\n\n#SejarahDunia #MisteriKuno #ArsipSejarah")

    result = upload_to_facebook_reels(video_path, title=title, description=caption)
    print(f"Status Publikasi: {result.get('status')}")

    print("\n" + "="*60)
    print("         SELESAI! PROSES SEJARAH FACEBOOK TUNTAS         ")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    main()

