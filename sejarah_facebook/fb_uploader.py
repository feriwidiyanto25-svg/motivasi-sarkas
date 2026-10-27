import os
import requests
from . import config

def upload_to_facebook_reels(video_path, title, description):
    """
    Meng-upload video MP4 ke Facebook Reels menggunakan Meta Graph API.
    Jika FB_PAGE_ID atau FB_PAGE_ACCESS_TOKEN belum diisi,
    sistem otomatis berjalan dalam mode SIMULASI (Dry-Run / Preview Lokal).
    """
    page_id = config.FB_PAGE_ID
    access_token = config.FB_PAGE_ACCESS_TOKEN

    if not page_id or not access_token:
        print("\n=======================================================")
        print("  ℹ️ SIMULASI UPLOAD FACEBOOK REELS (TOKEN BELUM DIISI)")
        print("=======================================================")
        print(f"Video Siap Diupload : {video_path}")
        print(f"Judul Reel          : {title}")
        print(f"Caption / Deskripsi :\n{description}")
        print("-------------------------------------------------------")
        print("Petunjuk:")
        print("Untuk mengaktifkan upload otomatis ke Facebook Reels:")
        print("1. Dapatkan PAGE_ID dan PAGE_ACCESS_TOKEN di Meta for Developers.")
        print("2. Set environment variable: FB_PAGE_ID dan FB_PAGE_ACCESS_TOKEN.")
        print("=======================================================\n")
        return {"status": "dry_run", "message": "Video siap diupload. Token belum diset."}

    file_size = os.path.getsize(video_path)
    print(f"\n📤 Memulai Upload ke Facebook Reels (Page ID: {page_id})...")

    try:
        # FASE 1: Inisialisasi Upload Session
        init_url = f"https://graph.facebook.com/v19.0/{page_id}/video_reels"
        headers = {"Authorization": f"OAuth {access_token}"}
        init_payload = {"upload_phase": "start"}

        init_res = requests.post(init_url, headers=headers, json=init_payload, timeout=30)
        init_data = init_res.json()

        if "video_id" not in init_data or "upload_url" not in init_data:
            print(f"❌ Gagal inisialisasi sesi Facebook: {init_data}")
            return {"status": "error", "error": init_data}

        video_id = init_data["video_id"]
        upload_url = init_data["upload_url"]
        print(f"✅ Sesi upload aktif. Video ID: {video_id}")

        # FASE 2: Transfer File Biner Video
        print("Sedang mentransfer data video ke server Facebook...")
        upload_headers = {
            "Authorization": f"OAuth {access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream"
        }

        with open(video_path, "rb") as f:
            upload_res = requests.post(upload_url, headers=upload_headers, data=f, timeout=120)

        if upload_res.status_code not in (200, 201):
            print(f"❌ Gagal transfer file video: {upload_res.text}")
            return {"status": "error", "error": upload_res.text}

        print("✅ Transfer file video selesai.")

        # FASE 3: Publikasikan Reel
        print("Mempublikasikan Reel ke Halaman Facebook...")
        publish_payload = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "title": title
        }

        publish_res = requests.post(init_url, headers=headers, json=publish_payload, timeout=30)
        publish_data = publish_res.json()

        if publish_data.get("success"):
            print(f"\n🎉 SUKSES! Video berhasil tayang di Facebook Reels (ID: {video_id})")
            return {"status": "success", "video_id": video_id}
        else:
            print(f"⚠️ Respon publish Facebook: {publish_data}")
            return {"status": "warning", "response": publish_data}

    except Exception as e:
        print(f"❌ Error saat upload Facebook Reels: {e}")
        return {"status": "error", "error": str(e)}

