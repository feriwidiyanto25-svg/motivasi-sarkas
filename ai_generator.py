import json
import google.generativeai as genai

# ==========================================
# UTILITAS JSON
# ==========================================
def extract_json(text):
    text = (text or "").strip()
    if "```json" in text:
        text = text.replace("```json", "")
    text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("JSON object tidak ditemukan.", text, 0)
    decoder = json.JSONDecoder()
    result, _ = decoder.raw_decode(text[start:])
    return result

# ==========================================
# VALIDASI HASIL AI
# ==========================================
def validate_result(hasil):
    required_fields = ["title", "scenes", "visual_context", "bg_keywords"]

    for field in required_fields:
        if field not in hasil:
            return None, f"AI tidak menghasilkan field: {field}"

    if not isinstance(hasil["title"], str) or not hasil["title"].strip():
        return None, "Field title harus berupa teks dan tidak boleh kosong."
    
    if not isinstance(hasil["visual_context"], str) or len(hasil["visual_context"]) < 5:
        return None, "Field visual_context tidak valid atau terlalu pendek."

    if not isinstance(hasil["scenes"], list) or len(hasil["scenes"]) == 0:
        return None, "Field scenes harus berupa array/list kalimat."
    
    hasil["scenes"] = [s.strip() for s in hasil["scenes"] if isinstance(s, str) and s.strip()]

    if not isinstance(hasil["bg_keywords"], list):
        return None, "bg_keywords harus berupa array."

    cleaned_keywords = list(dict.fromkeys([k.strip() for k in hasil["bg_keywords"] if isinstance(k, str) and k.strip()]))
    if not cleaned_keywords:
        return None, "bg_keywords tidak boleh kosong."

    hasil["bg_keywords"] = cleaned_keywords[:4]
    hasil["bg_keyword"] = hasil["bg_keywords"][0]

    return hasil, None

# ==========================================
# GENERATE NASKAH EDUKASI MENDALAM
# ==========================================
def generate_naskah(topik, api_key, model_name="gemini-2.5-flash"):
    if not api_key or api_key.strip() == "":
        return {"error": "Gemini API Key wajib diisi!"}
    if not topik or not topik.strip():
        return {"error": "Topik wajib diisi!"}

    genai.configure(api_key=api_key.strip())

    try:
        model = genai.GenerativeModel(model_name)

        # Prompt disesuaikan untuk membatasi panjang naskah
        prompt = f"""
Kamu adalah penulis naskah utama untuk channel edukasi bernama "kenapaYa?".

IDENTITAS CHANNEL:
kenapaYa? membahas pertanyaan sederhana yang sering muncul dalam kehidupan sehari-hari,
tetapi jarang benar-benar kita pikirkan jawabannya.

Tujuan setiap video adalah membuat penonton berkata:

"Eh iya juga..."
"Baru kepikiran."
"Ternyata begitu."

Channel dapat membahas berbagai bidang:
- sains
- biologi
- fisika
- psikologi
- sejarah
- bahasa
- budaya
- teknologi
- matematika
- kebiasaan manusia
- fenomena sehari-hari
- asal-usul suatu istilah
- asal-usul suatu sistem

Jangan menganggap semua pertanyaan harus dijawab dengan pendekatan sains.
Gunakan bidang yang paling tepat untuk pertanyaan tersebut.

==================================================
INPUT
==================================================

TOPIK:
"{topik}"

==================================================
ATURAN DURASI
==================================================

Naskah WAJIB disesuaikan dengan target durasi.

Gunakan kecepatan narasi bahasa Indonesia sekitar 2.2 sampai 2.6 kata per detik.

Gunakan perkiraan berikut:

8–15 detik:
18–40 kata, 2–3 scene.

16–30 detik:
35–75 kata, sekitar 3 scene.

31–60 detik:
70–150 kata, sekitar 3–5 scene.

61–90 detik:
135–225 kata, sekitar 4–5 scene.

91–120 detik:
200–300 kata, sekitar 5–6 scene.

121–150 detik:
265–375 kata, sekitar 6–7 scene.

ATURAN PENTING:

- Jangan memaksakan jumlah kata sampai memenuhi batas atas.
- Jangan menambahkan informasi yang tidak penting hanya untuk memperpanjang video.
- Jika pertanyaan dapat dijawab dengan singkat, buat naskah tetap singkat.
- Jika pertanyaan membutuhkan sejarah atau penjelasan bertahap, gunakan durasi yang tersedia untuk membangun penjelasan.
- Jangan membuat scene tambahan hanya untuk mengejar jumlah scene.
- Total naskah harus terasa natural ketika dibacakan dengan suara manusia.
- Target durasi adalah panduan, bukan alasan untuk membuat naskah bertele-tele.

==================================================
IDENTIFIKASI JENIS PERTANYAAN
==================================================

Sebelum menulis naskah, tentukan pendekatan yang paling tepat.

1. ASAL-USUL / SEJARAH

Gunakan untuk pertanyaan seperti:
- Kenapa 1 menit = 60 detik?
- Kenapa kalender punya 12 bulan?
- Kenapa disebut kaki lima?
- Kenapa alfabet dimulai dari A?

Fokus pada:
- asal mula
- peradaban atau pihak yang berperan
- alasan sistem tersebut muncul
- bagaimana sistem berkembang
- mengapa masih digunakan sampai sekarang

2. SAINS / FISIKA / BIOLOGI

Gunakan untuk:
- Kenapa langit berwarna biru?
- Kenapa air laut asin?
- Kenapa kita cegukan?

3. PSIKOLOGI / PERILAKU

Gunakan untuk:
- Kenapa kita lupa setelah masuk kamar?
- Kenapa kita mengecek HP tanpa alasan?
- Kenapa menguap bisa menular?

4. BAHASA

Gunakan untuk:
- Kenapa air bening disebut air putih?
- Kenapa matahari disebut terbit?
- Kenapa orang tua berarti ayah dan ibu?

5. MATEMATIKA / LOGIKA

Gunakan untuk:
- Kenapa lingkaran punya 360 derajat?
- Kenapa 1 jam punya 60 menit?
- Kenapa sistem tertentu menggunakan angka tertentu?

6. TEKNOLOGI

Gunakan untuk:
- Kenapa baterai HP cepat habis?
- Kenapa WiFi kadang lambat?
- Kenapa komputer menggunakan 0 dan 1?

7. KEHIDUPAN SEHARI-HARI

Gunakan untuk pertanyaan tentang benda, makanan,
kebiasaan, atau fenomena yang sering dialami manusia.

Jika pertanyaan masuk ke beberapa kategori,
pilih kategori yang paling relevan terhadap inti pertanyaan.

==================================================
STRUKTUR NASKAH
==================================================

Susun scene berdasarkan kebutuhan topik dan durasi.

SCENE AWAL — HOOK

Mulai dengan pertanyaan atau fakta yang langsung membuat penonton penasaran.

Hindari pembukaan seperti:
"Pada video kali ini..."
"Halo semuanya..."
"Apakah kalian tahu..."

Langsung masuk ke pertanyaan.

SCENE BERIKUTNYA — FENOMENA

Tunjukkan mengapa pertanyaan tersebut menarik,
aneh, atau sebenarnya sering kita alami.

SCENE PENJELASAN — OPSIONAL SESUAI TOPIK

Berikan alasan utama secara jelas.

SCENE LATAR BELAKANG — OPSIONAL

Jika topik membutuhkan sejarah, perkembangan,
proses, atau konteks tambahan, jelaskan secara singkat.

SCENE FAKTA MENARIK — OPSIONAL

Berikan fakta yang memperkuat rasa "ternyata".

SCENE KESIMPULAN

Jawab pertanyaan utama secara sederhana dan memuaskan.

Untuk video pendek, gabungkan beberapa fungsi scene
jika diperlukan.

==================================================
GAYA NARASI
==================================================

Gunakan bahasa Indonesia sehari-hari.

Gaya harus:
- natural
- ringan
- cerdas
- penasaran
- mudah dipahami
- enak didengar ketika dibacakan
- tidak terasa seperti buku pelajaran

Gunakan istilah ilmiah hanya jika diperlukan.
Jika menggunakan istilah teknis, langsung jelaskan dengan bahasa sederhana.

Hindari:
- kalimat terlalu panjang
- pengulangan informasi
- pembukaan formal
- kesimpulan yang terlalu panjang
- clickbait yang menyesatkan
- klaim berlebihan

==================================================
AKURASI
==================================================

Jangan mengarang.

Bedakan:
- fakta yang sudah kuat
- penjelasan yang masuk akal
- teori atau hipotesis
- asal-usul yang masih diperdebatkan

Jika suatu fakta atau asal-usul tidak diketahui secara pasti,
katakan demikian.

Jangan membuat cerita sejarah hanya agar narasi terdengar menarik.

==================================================
VISUAL
==================================================

"visual_context" harus menjelaskan visual utama
yang dapat menggambarkan topik secara langsung.

Gunakan bahasa Inggris.

Visual harus:
- mudah divisualisasikan
- relevan dengan topik
- sinematik
- cocok untuk video edukasi
- tanpa watermark
- tanpa logo
- tanpa teks yang harus muncul di dalam gambar

==================================================
BACKGROUND KEYWORDS
==================================================

Buat maksimal 4 keyword visual dalam bahasa Inggris.

Keyword harus berupa objek, tempat, aktivitas,
atau konsep yang benar-benar berkaitan dengan topik.

Hindari keyword terlalu umum seperti:
"education"
"knowledge"
"interesting"
"science"

==================================================
OUTPUT
==================================================

OUTPUT WAJIB JSON MURNI.

Jangan gunakan markdown.
Jangan gunakan ```json.
Jangan menambahkan teks di luar JSON.

Format:

{{
    "title": "Judul yang menarik",
    "scenes": [
        "Kalimat narasi scene 1...",
        "Kalimat narasi scene 2...",
        "Kalimat narasi scene 3..."
    ],
    "visual_context": "Detailed English visual description...",
    "bg_keywords": [
        "keyword 1",
        "keyword 2",
        "keyword 3",
        "keyword 4"
    ]
}}

Pastikan JSON valid dan dapat langsung diproses oleh json.loads().

Pastikan panjang total scenes sesuai dengan TARGET DURASI.
"""

        response = model.generate_content(prompt)
        teks = (getattr(response, "text", "") or "").strip()

        if not teks:
            return {"error": "Gemini tidak menghasilkan teks."}

        try:
            hasil = extract_json(teks)
        except json.JSONDecodeError as e:
            return {"error": f"Format JSON dari AI tidak valid: {str(e)}"}

        hasil, validation_error = validate_result(hasil)
        if validation_error:
            return {"error": validation_error}

        print("\n========== CONTENT ENGINE ==========")
        print(f"Title: {hasil['title']}")
        for i, scene in enumerate(hasil['scenes']):
            print(f"Scene {i+1}: {scene}")
        print(f"Total {len(hasil['scenes'])} Scenes dihasilkan.")
        print("====================================\n")

        return hasil

    except Exception as e:
        return {"error": f"Gagal menghubungi AI: {str(e)}"}
