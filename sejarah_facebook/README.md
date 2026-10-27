# 🏛️ Proyek Dokumenter Sejarah Facebook Reels

Proyek terisolasi khusus untuk membuat video dokumenter sejarah viral di Facebook Reels secara full-autopilot.

---

### 🌟 Fitur Utama
1. **Naskah Storytelling Sejarah Otomatis (Gemini AI):**
   - Mengambil topik misteri peradaban dunia, taktik perang gila, dan sejarah Nusantara.
   - Dilengkapi Hook anti-skip bertema serial (`Arsip Sejarah: Bagian X`) dan penutup pemicu debat/komentar.
   - Otomatis menghasilkan 5 prompt visual bahasa Inggris siap pakai untuk Flow / MCP.
2. **Karakter Suara Pria Berwibawa (Edge TTS):**
   - Menggunakan vokal `id-ID-ArdiNeural` bergaya dokumenter Discovery/National Geographic.
3. **Visual Sinematik Kuno:**
   - Multi-gambar berganti setiap ~4 detik dengan efek slow zoom.
   - True Gaussian Defocus Bokeh Mask atas-bawah.
   - Tipografi warna **Emas Arkeologi (`#F59E0B`)** dan **Putih Gading (`#F8FAFC`)**.
   - Badge watermark: `🏛️ ARSIP SEJARAH`.
4. **Uploader Facebook Reels (Meta Graph API):**
   - Upload otomatis ke Facebook Page Anda.
   - Jika token belum diset, otomatis berjalan dalam mode preview/simulasi.

---

### 🚀 Cara Menjalankan

Dari root direktori workspace, jalankan:
```bash
# Menggunakan topik otomatis dari AI:
python -m sejarah_facebook.run_sejarah

# Menggunakan topik khusus yang Anda inginkan:
python -m sejarah_facebook.run_sejarah --topik "Taktik Pasukan Gajah Hannibal yang Menghancurkan Romawi"

# Hanya render video lokal tanpa upload:
python -m sejarah_facebook.run_sejarah --skip-upload
```

---

### 🔑 Cara Mengaktifkan Upload Otomatis Facebook Reels

1. Buat **Facebook Page (Halaman)** di Facebook.
2. Buka [Meta for Developers](https://developers.facebook.com/) -> Buat App tipe **Business**.
3. Tambahkan produk **Facebook Login for Business** dan minta izin `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
4. Ambil **Page Access Token** dan **Page ID**.
5. Simpan di environment variable:
   ```env
   FB_PAGE_ID="ID_HALAMAN_ANDA"
   FB_PAGE_ACCESS_TOKEN="TOKEN_HALAMAN_ANDA"
   ```

