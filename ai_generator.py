import os
import json
import random
import google.generativeai as genai
import config

# ==========================================
# KATEGORI SPESIFIK UNTUK SUDUT PANDANG KREATIF
# ==========================================
# Digunakan untuk mencegah AI mengulang tema yang sama di setiap jadwal scheduler
KATEGORI_PROMPTS = [
    "anatomi & reaksi tubuh manusia (contoh: merinding saat takut/dingin, cegukan, menguap menular, sidik jari unik, kedutan mata, jari keriput di air)",
    "makanan, minuman, dan dapur (contoh: sensasi pedas cabai, air dingin vs hangat saat haus, bau bawang bikin nangis, rasa manis bikin ketagihan)",
    "gadget, internet, dan kebiasaan digital (contoh: tombol spasi keyboard paling panjang, mode pesawat HP, susunan QWERTY, kenapa layar biru bikin melek)",
    "psikologi, otak manusia, dan perilaku sosial (contoh: efek door-doorway/lupa saat pindah ruangan, deja vu, canggung saat hening, mimpi saat tidur)",
    "asal-usul benda sehari-hari dan fasilitas umum (contoh: garis merah di kaca belakang mobil, lubang kecil di gembok, resleting, dasi, uang kertas/koin)",
    "fenomena alam, cuaca, dan hewan sekitar (contoh: bau tanah basah/petrichor saat hujan, semut berpapasan selalu berhenti, kucing mendengkur, nyamuk mendengung)",
    "bahasa, istilah unik, dan kebiasaan masyarakat (contoh: kenapa jabat tangan pakai tangan kanan, kenapa bersulang membenturkan gelas, asal-usul istilah sehari-hari)"
]

def load_topic_history(history_file=None, max_items=40):
    """Membaca riwayat topik yang pernah dibuat agar tidak diulang oleh AI."""
    history_file = history_file or getattr(config, "HISTORY_TOPICS_FILE", os.path.join(config.BASE_DIR, "riwayat_topik.txt"))
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        return lines[-max_items:]
    except Exception:
        return []

def save_topic_to_history(topic, history_file=None):
    """Menyimpan topik baru ke file riwayat."""
    history_file = history_file or getattr(config, "HISTORY_TOPICS_FILE", os.path.join(config.BASE_DIR, "riwayat_topik.txt"))
    try:
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(f"{topic}\n")
    except Exception as e:
        print(f"Peringatan: Gagal menyimpan riwayat topik: {e}")

# ==========================================
# PENGAMBILAN TOPIK OTOMATIS (OPSI A / OPSI B)
# ==========================================
def get_topic(api_key=None, mode=None, model_name="gemini-2.5-flash"):
    """
    Mengambil topik berdasarkan konfigurasi:
    - Opsi A ('ai_auto'): Gemini AI membuat ide topik trivia/paradox baru dengan sistem Anti-Duplikasi.
    - Opsi B ('file_list'): Mengambil baris topik dari daftar_topik.txt dan merotasinya.
    """
    mode = mode or config.SCHEDULER_TOPIC_MODE
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if mode == "file_list":
        topics_file = config.TOPICS_FILE
        if os.path.exists(topics_file):
            with open(topics_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            
            if lines:
                chosen_topic = lines[0]
                # Rotasi: pindahkan topik terpilih ke baris paling bawah agar daftar tidak habis
                remaining = lines[1:] + [chosen_topic]
                try:
                    with open(topics_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(remaining) + "\n")
                except Exception:
                    pass
                print(f"📖 Topik diambil dari file ({topics_file}): {chosen_topic}")
                save_topic_to_history(chosen_topic)
                return chosen_topic

    # Default Opsi A: Generate topik via Gemini AI dengan Anti-Duplikasi
    if not api_key:
        return "Kenapa 'keluar' tidak punya 'ke luar'?"

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(model_name)

        # 1. Pilih sudut pandang/kategori secara acak agar setiap jadwal berbeda tema
        chosen_category = random.choice(KATEGORI_PROMPTS)

        # 2. Ambil riwayat topik yang sudah pernah dibuat untuk negative prompt
        history = load_topic_history(max_items=35)
        history_instruction = ""
        if history:
            history_list_text = "\n".join([f"- {t}" for t in history[-25:]])
            history_instruction = f"""
DILARANG KERAS membuat topik yang sama atau mirip dengan daftar yang sudah pernah dibuat ini:
{history_list_text}
"""

        prompt = f"""
Kamu adalah produser konten untuk channel edukasi viral "kenapaYa?".
Buatkan 1 (SATU) pertanyaan atau fenomena sederhana yang sangat relatable, memicu rasa penasaran ("Eh iya juga ya, baru kepikiran..."), dan sering kita alami sehari-hari.

FOKUS TEMA JADWAL INI:
{chosen_category}
{history_instruction}
ATURAN WAJIB:
- Pertanyaan harus diawali dengan kata "Kenapa ..."
- Hanya kembalikan 1 kalimat pertanyaan saja.
- Harus baru, segar, unik, dan belum pernah dibahas di daftar riwayat di atas.
- Jangan ada tanda kutip, jangan ada penomoran, jangan ada penjelasan pembuka/penutup.
"""

        # Setting kreativitas tinggi (temperature 1.0) agar variasi maksimal
        generation_config = {
            "temperature": 1.0,
            "top_p": 0.95,
        }

        # Loop percobaan (maksimal 3 kali) untuk memastikan topik bukan duplikat
        for attempt in range(3):
            response = model.generate_content(prompt, generation_config=generation_config)
            topic = (getattr(response, "text", "") or "").strip().strip('"').strip("'")
            
            if topic:
                # Normalisasi perbandingan sederhana
                topic_clean = topic.lower().strip("?.! ")
                is_duplicate = any(topic_clean in h.lower() or h.lower() in topic_clean for h in history)

                if not is_duplicate:
                    save_topic_to_history(topic)
                    cat_short = chosen_category.split("(")[0].strip()
                    print(f"💡 Ide Topik Baru dari AI [{cat_short}]: {topic}")
                    return topic
                else:
                    print(f"⚠️ Topik '{topic}' mirip dengan riwayat lama, membuat ulang (percobaan {attempt + 1})...")

        # Jika lolos semua percobaan, pakai topik terakhir dan simpan
        if topic:
            save_topic_to_history(topic)
            return topic

    except Exception as e:
        print(f"Gagal generate topik otomatis dari AI: {e}")

    return "Kenapa satu menit ada 60 detik?"

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
# ==========================================
# GENERATE NASKAH KENAPAYA?
# ==========================================
# ==========================================
# GENERATE NASKAH KENAPAYA?
# ==========================================
def generate_naskah(
    topik,
    api_key,
    model_name="gemini-2.5-flash",
    duration_seconds=30
):
    if not api_key or api_key.strip() == "":
        return {"error": "Gemini API Key wajib diisi!"}

    if not topik or not topik.strip():
        return {"error": "Topik wajib diisi!"}

    # Durasi hanya digunakan sebagai panduan panjang naskah.
    # Tidak dijadikan validasi batas.
    try:
        duration_seconds = int(duration_seconds)
    except (TypeError, ValueError):
        duration_seconds = 60

    genai.configure(api_key=api_key.strip())

    try:
        model = genai.GenerativeModel(model_name)

        # ==========================================
        # PERKIRAAN PANJANG NASKAH
        # ==========================================
        # Bahasa Indonesia: kira-kira 2.2 kata/detik.
        # Kita beri ruang agar naskah tidak terlalu panjang.
        target_words = max(20, int(duration_seconds * 2.2))

        prompt = f"""
Kamu adalah penulis naskah untuk channel edukasi
bernama "kenapaYa?".

==================================================
IDENTITAS CHANNEL
==================================================

kenapaYa? membahas pertanyaan sederhana yang sering
kita alami, lihat, dengar, gunakan, atau anggap biasa,
tetapi jarang kita pikirkan alasannya.

Tujuan utama setiap video:

"Eh iya juga..."
"Baru kepikiran."
"Ternyata begitu."

Topik dapat berasal dari:

- sains
- biologi
- fisika
- psikologi
- sejarah
- bahasa
- budaya
- matematika
- teknologi
- kebiasaan manusia
- makanan
- benda sehari-hari
- fenomena alam
- asal-usul istilah
- asal-usul sistem
- kebiasaan manusia

Jangan memaksakan semua pertanyaan menjadi sains.
Gunakan pendekatan yang paling sesuai dengan topik.

==================================================
TOPIK
==================================================

"{topik}"

==================================================
TARGET DURASI
==================================================

Target durasi video:
{duration_seconds} detik.

Gunakan target tersebut sebagai panduan panjang
naskah, bukan sebagai durasi yang harus dipenuhi persis.

Perkiraan target sekitar:
{target_words} kata.

ATURAN:

- Video BOLEH lebih pendek dari target.
- Jangan memaksakan naskah menjadi panjang.
- Jangan menambahkan filler.
- Jangan mengulang informasi.
- Jangan menambahkan fakta yang tidak penting hanya
  untuk mengejar durasi.
- Jika penjelasan sudah selesai secara natural,
  akhiri naskah.
- Jika topik membutuhkan penjelasan lebih panjang,
  gunakan scene tambahan.
- Namun TOTAL naskah harus tetap dirancang agar
  tidak melebihi sekitar 180 detik ketika dibacakan
  dengan kecepatan normal.

Prioritas:

1. Akurasi.
2. Jawaban yang memuaskan.
3. Alur yang natural.
4. Keterbacaan setiap scene.
5. Durasi.

==================================================
ATURAN MICRO-SCENE — SANGAT PENTING
==================================================

Setiap item dalam "scenes" akan digunakan sebagai
SATU SLIDE / SATU POTONGAN VIDEO.

Karena itu, JANGAN membuat scene berupa paragraf.

Setiap scene harus sangat singkat.

BATAS IDEAL:

- 4 sampai 12 kata per scene.
- Usahakan maksimal sekitar 14 kata.
- Jika kalimat lebih panjang dari 14 kata,
  PECAH menjadi dua atau lebih scene.
- Satu scene hanya boleh menyampaikan SATU ide utama.
- Jangan menggabungkan dua penjelasan berbeda
  dalam satu scene.
- Jangan memasukkan penjelasan dan kesimpulan panjang
  sekaligus dalam satu scene.

CONTOH SALAH:

"Jadi, kebiasaan kita menghitung waktu dengan angka 60
merupakan warisan sistem matematika kuno yang sangat
praktis dan akhirnya tetap digunakan sampai sekarang."

Terlalu panjang.

CONTOH BENAR:

"Kenapa satu menit punya *60 DETIK*?"

"Ternyata ini *BUKAN KEBETULAN*."

"Sistem ini sudah ada sejak *ZAMAN KUNO*."

"Bangsa kuno menggunakan *SISTEM BERBASIS 60*."

"Angka 60 ternyata *SANGAT MUDAH* dibagi."

"Itulah yang membuatnya *SANGAT PRAKTIS*."

"Sistem ini kemudian bertahan *SAMPAI SEKARANG*."

"Nah, baru *KEPIKIRAN*, kan?"

==================================================
KEYWORD HIGHLIGHTING (PENTING)
==================================================

Tandai 1 sampai 2 kata penegas paling penting, dramatis, atau menarik di setiap scene dengan tanda bintang (*...*), agar teks tersebut otomatis diberi warna aksen kuning cerah (#FACC15) di video.

==================================================
ATURAN PECAH SCENE
==================================================

Jika satu kalimat terasa panjang ketika dibaca,
jangan dipaksakan menjadi satu scene.

Contoh:

SALAH:
"Semakin tua, produksi melanin di folikel rambut
berkurang sehingga rambut baru kehilangan pigmennya."

BENAR:
"Seiring usia, produksi melanin mulai menurun."

"Melanin adalah pigmen yang memberi warna rambut."

"Akibatnya, rambut baru tumbuh semakin pucat."

Jika sebuah kalimat memiliki kata:
"karena", "sehingga", "tetapi", "sementara",
"akibatnya", atau lebih dari satu gagasan,
pertimbangkan untuk memecahnya menjadi beberapa scene.

==================================================
STRUKTUR CERITA
==================================================

Gunakan struktur ini sebagai panduan.

SCENE 1:
HOOK ANTI-SKIP (SANGAT KRUSIAL - DETIK 0-2)

Detik 0 sampai 2 adalah penentu apakah penonton akan swipe atau menonton sampai habis!
Buat Hook yang langsung MENUSUK rasa penasaran atau menyentil kebiasaan relatable penonton.

PILIHAN FORMAT HOOK YANG SANGAT MEMIKAT:
1. Menusuk rasa penasaran relatable:
   - "Pernah nggak kamu kepikiran, *KENAPA*...?"
   - "Sadar nggak, setiap kali kamu..., pasti...?"
2. Paradoks / Rahasia / Mengagetkan:
   - "Ternyata ada alasan gila kenapa *[OBJEK/HAL]*...!"
   - "Bukan kebetulan, ini alasan kenapa *[OBJEK/HAL]*...!"
   - "Kenapa satu menit punya *60 DETIK*?"
   - "Kenapa otakmu sengaja bikin kamu *LUPA* pas masuk kamar?"

PANTANGAN MUTLAK SCENE 1:
- DILARANG basa-basi ("Halo semuanya", "Pada video kali ini", "Tahukah kamu").
- Harus singkat, padat (maksimal 7-10 kata), dan langsung memicu rasa ingin tahu!

SCENE BERIKUTNYA:
FENOMENA

Tunjukkan sesuatu yang familiar atau menarik.

Contoh:
"Kita memakai aturan ini setiap hari."

SCENE BERIKUTNYA:
PENJELASAN

Berikan alasan utama.

SCENE BERIKUTNYA:
KONTEKS

Jika perlu, jelaskan sejarah, proses,
matematika, budaya, atau latar belakangnya.

SCENE BERIKUTNYA:
FAKTA MENARIK

Berikan informasi yang membuat penonton berkata:
"Oh, ternyata..."

SCENE TERAKHIR:
KESIMPULAN

Jawab pertanyaan utama dengan sederhana.

Tidak semua bagian wajib digunakan.

Untuk topik sederhana, gunakan lebih sedikit scene.

Untuk topik kompleks, gunakan lebih banyak scene.

==================================================
JENIS PERTANYAAN
==================================================

Identifikasi pendekatan yang paling sesuai.

ASAL-USUL / SEJARAH:
- Kenapa 1 menit = 60 detik?
- Kenapa kalender punya 12 bulan?
- Kenapa disebut kaki lima?

SAINS:
- Kenapa langit biru?
- Kenapa air laut asin?

PSIKOLOGI:
- Kenapa kita lupa setelah masuk kamar?
- Kenapa kita mengecek HP tanpa alasan?

BAHASA:
- Kenapa air bening disebut air putih?
- Kenapa disebut matahari terbit?

MATEMATIKA / LOGIKA:
- Kenapa lingkaran 360 derajat?
- Kenapa satu jam punya 60 menit?

TEKNOLOGI:
- Kenapa baterai HP cepat habis?

KEHIDUPAN SEHARI-HARI:
- Kenapa kaca kamar mandi berembun?
- Kenapa makanan pedas terasa panas?

Jangan memaksakan satu kategori jika kategori lain
lebih tepat.

==================================================
AKURASI
==================================================

Jangan mengarang.

Jangan membuat sejarah palsu.

Jangan mengubah teori menjadi fakta.

Jangan membuat hubungan sebab-akibat yang tidak
didukung pengetahuan yang masuk akal.

Jika asal-usul atau penyebab belum diketahui secara pasti,
katakan demikian.

Jika terdapat beberapa penjelasan,
gunakan penjelasan yang paling kuat.

==================================================
GAYA BAHASA
==================================================

Gunakan bahasa Indonesia sehari-hari.

Gaya:

- natural
- ringan
- cerdas
- penasaran
- mudah dipahami
- enak didengar
- enak dibaca sebagai subtitle

Hindari:

- bahasa akademis berlebihan
- kalimat panjang
- pengulangan
- filler
- pembukaan formal
- clickbait menyesatkan

==================================================
VISUAL CONTEXT
==================================================

"visual_context" harus menggambarkan visual utama
yang paling relevan dengan topik.

Gunakan bahasa Inggris.

Visual harus:

- mudah divisualisasikan
- relevan dengan topik
- cinematic
- edukatif
- tanpa watermark
- tanpa logo
- tidak memerlukan teks di dalam gambar

==================================================
BACKGROUND KEYWORDS
==================================================

Buat maksimal 4 keyword dalam bahasa Inggris.

Keyword harus spesifik dan mudah divisualisasikan.

Jangan gunakan keyword umum seperti:

"education"
"knowledge"
"interesting"
"science"

==================================================
OUTPUT WAJIB
==================================================

Output HARUS berupa JSON MURNI.

Jangan gunakan markdown.

Jangan gunakan ```json.

Jangan menambahkan teks di luar JSON.

FORMAT HARUS SAMA PERSIS:

{{
    "title": "Judul yang menarik",
    "scenes": [
        "Kenapa satu menit punya *60 DETIK*?",
        "Ternyata ini *BUKAN KEBETULAN*.",
        "Sistem ini sudah ada sejak *ZAMAN KUNO*."
    ],
    "visual_context": "Detailed English visual description...",
    "bg_keywords": [
        "keyword 1",
        "keyword 2",
        "keyword 3",
        "keyword 4"
    ]
}}

==================================================
ATURAN FINAL
==================================================

1. "scenes" HARUS berupa array string.

2. Jangan mengubah scenes menjadi object.

SALAH:
"scenes": [
    {{
        "text": "..."
    }}
]

BENAR:
"scenes": [
    "....",
    "....",
    "...."
]

3. Setiap scene harus pendek.

4. Target ideal 4–12 kata per scene.

5. Usahakan tidak lebih dari 14 kata per scene.

6. Jika satu gagasan membutuhkan lebih dari 14 kata,
pecah menjadi beberapa scene.

7. Jangan mengurangi jumlah scene hanya supaya scene
terlihat sedikit.

8. Jangan menambahkan filler hanya untuk mengejar durasi.

9. Total durasi boleh lebih pendek dari target.

10. TOTAL naskah tidak boleh dirancang melebihi
sekitar 180 detik.

11. Jangan menambahkan field JSON lain.

12. Gunakan hanya:
title
scenes
visual_context
bg_keywords

Pastikan JSON valid dan dapat diproses menggunakan
json.loads().
"""

        response = model.generate_content(prompt)

        teks = (getattr(response, "text", "") or "").strip()

        if not teks:
            return {"error": "Gemini tidak menghasilkan teks."}

        try:
            hasil = extract_json(teks)
        except json.JSONDecodeError as e:
            return {
                "error": f"Format JSON dari AI tidak valid: {str(e)}"
            }

        hasil, validation_error = validate_result(hasil)

        if validation_error:
            return {"error": validation_error}

        print("\n========== CONTENT ENGINE ==========")
        print(f"Title: {hasil['title']}")
        print(f"Target Duration: {duration_seconds} detik")

        for i, scene in enumerate(hasil["scenes"]):
            word_count = len(scene.split())
            print(
                f"Scene {i+1} ({word_count} kata): {scene}"
            )

        print(
            f"Total {len(hasil['scenes'])} Scenes dihasilkan."
        )
        print("====================================\n")

        return hasil

    except Exception as e:
        return {
            "error": f"Gagal menghubungi AI: {str(e)}"
        }
