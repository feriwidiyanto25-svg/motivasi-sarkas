import json
import google.generativeai as genai


# ==========================================
# UTILITAS JSON
# ==========================================
def extract_json(text):
    """
    Mencoba mengambil object JSON pertama dari response Gemini.
    Lebih tahan terhadap response seperti:
    "Berikut hasilnya: {...}"
    """

    text = (text or "").strip()

    # Bersihkan markdown fence
    if "```json" in text:
        text = text.replace("```json", "")

    text = text.replace("```", "").strip()

    # Coba langsung
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Cari object JSON pertama
    start = text.find("{")

    if start == -1:
        raise json.JSONDecodeError(
            "JSON object tidak ditemukan.",
            text,
            0
        )

    decoder = json.JSONDecoder()

    result, _ = decoder.raw_decode(
        text[start:]
    )

    return result


# ==========================================
# VALIDASI HASIL AI
# ==========================================
def validate_result(hasil):
    required_fields = [
        "title",
        "setup_1",
        "setup_2",
        "punchline",
        "visual_context",
        "bg_keywords"
    ]

    # ------------------------------------------
    # FIELD WAJIB
    # ------------------------------------------
    for field in required_fields:

        if field not in hasil:
            return (
                None,
                f"AI tidak menghasilkan field: {field}"
            )

    # ------------------------------------------
    # STRING FIELD
    # ------------------------------------------
    string_fields = [
        "title",
        "setup_1",
        "setup_2",
        "punchline",
        "visual_context"
    ]

    for field in string_fields:

        if not isinstance(
            hasil[field],
            str
        ):
            return (
                None,
                f"Field {field} harus berupa teks."
            )

        hasil[field] = hasil[field].strip()

        if not hasil[field]:
            return (
                None,
                f"Field {field} tidak boleh kosong."
            )

    # ------------------------------------------
    # BG KEYWORDS
    # ------------------------------------------
    if not isinstance(
        hasil["bg_keywords"],
        list
    ):
        return (
            None,
            "bg_keywords harus berupa array."
        )

    cleaned_keywords = []

    for keyword in hasil["bg_keywords"]:

        if not isinstance(
            keyword,
            str
        ):
            continue

        keyword = keyword.strip()

        if keyword:
            cleaned_keywords.append(
                keyword
            )

    # Hapus duplicate
    cleaned_keywords = list(
        dict.fromkeys(
            cleaned_keywords
        )
    )

    if not cleaned_keywords:
        return (
            None,
            "bg_keywords tidak boleh kosong."
        )

    # Maksimal 4 keyword
    hasil["bg_keywords"] = (
        cleaned_keywords[:4]
    )

    # Compatibility dengan app.py lama
    hasil["bg_keyword"] = (
        hasil["bg_keywords"][0]
    )

    # ------------------------------------------
    # VALIDASI PANJANG TEKS
    # ------------------------------------------
    title_words = len(
        hasil["title"].split()
    )

    setup1_words = len(
        hasil["setup_1"].split()
    )

    setup2_words = len(
        hasil["setup_2"].split()
    )

    punchline_words = len(
        hasil["punchline"].split()
    )

    if title_words > 9:
        return (
            None,
            (
                "Title terlalu panjang. "
                f"Maksimal 9 kata, "
                f"hasil: {title_words}."
            )
        )

    if setup1_words > 12:
        return (
            None,
            (
                "Setup 1 terlalu panjang. "
                f"Maksimal 12 kata, "
                f"hasil: {setup1_words}."
            )
        )

    if setup2_words > 12:
        return (
            None,
            (
                "Setup 2 terlalu panjang. "
                f"Maksimal 12 kata, "
                f"hasil: {setup2_words}."
            )
        )

    if punchline_words > 10:
        return (
            None,
            (
                "Punchline terlalu panjang. "
                f"Maksimal 10 kata, "
                f"hasil: {punchline_words}."
            )
        )

    # ------------------------------------------
    # VALIDASI VISUAL CONTEXT
    # ------------------------------------------
    if len(hasil["visual_context"]) < 5:
        return (
            None,
            "visual_context terlalu pendek."
        )

    return hasil, None


# ==========================================
# GENERATE NASKAH
# ==========================================
def generate_naskah(
    topik,
    api_key,
    model_name="gemini-2.5-flash"
):

    # ==========================================
    # VALIDASI API KEY
    # ==========================================
    if not api_key or api_key.strip() == "":
        return {
            "error": "Gemini API Key wajib diisi!"
        }

    # ==========================================
    # VALIDASI TOPIK
    # ==========================================
    if not topik or not topik.strip():
        return {
            "error": "Topik / keresahan wajib diisi!"
        }

    # ==========================================
    # GEMINI
    # ==========================================
    genai.configure(
        api_key=api_key.strip()
    )

    try:

        model = genai.GenerativeModel(
            model_name
        )

        # ==========================================
        # CONTENT + VISUAL ENGINE
        # ==========================================
        prompt = f"""
Kamu adalah creative director dan penulis
konten pengetahuan short-form Indonesia.

==================================================
KARAKTER
==================================================

Kamu adalah pembuat konten pengetahuan yang mampu
menjelaskan fenomena sehari-hari dengan cara:

- sederhana
- menarik
- mudah dipahami
- conversational
- membuat penasaran
- berdasarkan fakta
- tidak mengarang informasi

Konten bukan motivasi.
Konten bukan opini.
Konten bukan berita.
Konten bukan kumpulan fakta random.

Fokus utama adalah:
MENJELASKAN SESUATU YANG MENARIK
DENGAN DASAR PENGETAHUAN YANG DAPAT DIVERIFIKASI.

TOPIK:
"{topik}"


==================================================
RESEARCH / GOOGLE SEARCH GROUNDING
==================================================

Sebelum menulis script, gunakan Google Search
untuk mencari dan memverifikasi informasi terkait topik.

JANGAN hanya mengandalkan ingatan model.

Cari sumber yang menjelaskan fenomena tersebut.
Prioritaskan sumber berdasarkan urutan berikut:

1. penelitian ilmiah / jurnal peer-reviewed
2. universitas dan lembaga penelitian
3. pemerintah dan institusi resmi
4. organisasi ilmiah/profesional
5. ensiklopedia atau sumber edukasi terpercaya
6. media atau artikel sekunder berkualitas yang memiliki referensi

Jika memungkinkan, periksa minimal 2 sumber independen
untuk fakta utama.

Jangan menganggap banyak artikel sebagai banyak sumber
jika semuanya hanya menyalin satu sumber asli.

Jika sumber primer tersedia, prioritaskan sumber primer.

==================================================
ATURAN SUMBER
==================================================

Gunakan informasi yang benar-benar didukung oleh hasil pencarian.

JANGAN:

- mengarang fakta
- mengarang penelitian
- mengarang nama ilmuwan
- mengarang angka
- mengarang tanggal
- mengarang institusi
- mengarang kutipan
- mengarang URL
- membuat klaim hanya karena terdengar menarik
- menggunakan informasi yang tidak didukung sumber

Jika sebuah detail tidak dapat diverifikasi,
JANGAN masukkan detail tersebut.

Jika sumber terpercaya memiliki perbedaan penjelasan,
jangan memilih secara sembarangan.
Gunakan penjelasan yang paling kuat dan umum didukung
oleh sumber yang ditemukan.

Jika bukti belum pasti, gunakan bahasa yang sesuai seperti:
- "salah satu faktornya..."
- "penelitian menunjukkan..."
- "salah satu penjelasannya..."
- "bukti saat ini menunjukkan..."

Jangan menggunakan "pasti", "selalu", "satu-satunya",
atau "100%" jika sumber tidak benar-benar mendukungnya.

==================================================
FACT VS INTERPRETATION
==================================================

Pisahkan fakta dengan cara penyampaian.

FAKTA:
Informasi yang didukung oleh sumber hasil pencarian.

INTERPRETASI:
Cara sederhana untuk menjelaskan fakta tersebut
kepada penonton.

Interpretasi boleh dibuat conversational,
tetapi tidak boleh mengubah makna fakta.

==================================================
TUJUAN EMOSI
==================================================

Penonton harus mengalami:

1. "Eh, iya juga."
2. "Kenapa bisa begitu?"
3. "Oh ternyata..."
4. "Serius?"
5. "Baru tahu."

Tujuan utama adalah:
PENASARAN → PENJELASAN → REVEAL PENGETAHUAN.

Jangan langsung memberikan jawaban utama.

==================================================
TITLE / KNOWLEDGE HOOK
==================================================

Fungsi:
Menjadi slide pembuka seperti thumbnail yang hidup.

Judul harus membuat penonton ingin mengetahui
jawaban dari topik tersebut.

Judul harus:
- menarik
- spesifik
- natural
- mudah dipahami
- relevan langsung dengan topik
- memancing rasa penasaran
- tidak clickbait kosong
- tidak memberikan seluruh jawaban

Variasikan bentuk judul.

Boleh menggunakan:
- pertanyaan
- fenomena aneh
- fakta yang bertentangan dengan intuisi
- kebiasaan sehari-hari
- perbandingan
- pernyataan yang membuat penasaran

JANGAN selalu menggunakan:
- "Tahukah kamu..."
- "Ternyata..."
- "Kenapa..."
- "Fakta menarik tentang..."

Maksimal 9 kata.
Ideal 4–8 kata.

==================================================
SETUP 1 = CURIOSITY HOOK
==================================================

Fungsi:
Membuat penonton langsung penasaran dengan fenomena.

Harus:
- langsung masuk ke topik
- natural
- conversational
- mudah dipahami
- menarik sejak kalimat pertama
- membuat penonton ingin tahu alasannya

Jangan langsung memberikan jawaban utama.

Maksimal 12 kata.
Ideal 6–10 kata.

==================================================
SETUP 2 = EXPLANATION BAIT
==================================================

Fungsi:
Memberikan konteks dan petunjuk menuju jawaban.

Setup 2 harus:
- memberikan konteks
- memberikan petunjuk menuju jawaban
- memperkenalkan mekanisme atau penyebab
- tetap menyimpan inti penjelasan untuk bagian akhir

Jangan mengulang Setup 1.
Jangan memasukkan fakta random.
Jangan terdengar seperti buku pelajaran.

Maksimal 12 kata.
Ideal 7–11 kata.

==================================================
PUNCHLINE = KNOWLEDGE REVEAL
==================================================

PUNCHLINE BUKAN JOKE.

PUNCHLINE adalah REVEAL PENGETAHUAN.

Fungsi:
Memberikan jawaban atau fakta utama yang membuat penonton:
"Oh... ternyata begitu."

Harus:
- faktual
- jelas
- singkat
- mudah dipahami
- langsung menjawab rasa penasaran
- menjadi payoff dari setup sebelumnya

Jangan membuat twist hanya agar terdengar mengejutkan.
Jangan mengarang fakta.

Maksimal 10 kata.
Ideal 5–10 kata.

Jika sedikit lebih banyak kata diperlukan agar akurat,
prioritaskan akurasi daripada memaksakan kalimat terlalu pendek.

==================================================
GAYA PENJELASAN
==================================================

Tulislah seperti seseorang sedang menjelaskan sesuatu
kepada temannya.

Gunakan:
- bahasa Indonesia natural
- bahasa sehari-hari
- kalimat pendek
- istilah sederhana
- voice-over friendly

Jika istilah teknis diperlukan,
gunakan tetapi jelaskan dengan bahasa sederhana.

Hindari:
- bahasa akademis yang kaku
- definisi textbook
- paragraf panjang
- jargon berlebihan
- gaya Wikipedia
- gaya artikel berita

==================================================
VARIASI KONTEN
==================================================

Setiap video harus terasa berbeda.

Gunakan sudut yang paling cocok dengan topik:

1. Kenapa sesuatu terjadi?
2. Bagaimana sesuatu bekerja?
3. Apa yang sebenarnya terjadi?
4. Mengapa manusia melakukan sesuatu?
5. Mengapa benda memiliki sifat tertentu?
6. Dari mana sebuah fenomena berasal?
7. Kesalahpahaman yang sering dipercaya
8. Perbandingan yang mengejutkan
9. Sebab dan akibat
10. Proses yang tidak terlihat
11. Sejarah singkat sebuah fenomena
12. Fakta yang bertentangan dengan intuisi

Jangan memaksakan semua topik menjadi "fakta mengejutkan".

==================================================
ANTI MISINFORMASI
==================================================

Jika terdapat informasi populer yang belum tentu benar,
jangan gunakan hanya karena populer.

Jika fenomena memiliki beberapa faktor,
jangan menyebut satu faktor sebagai satu-satunya penyebab
kecuali sumber benar-benar mendukungnya.

Jika penelitian belum sepakat,
jangan membuat seolah-olah jawabannya sudah pasti.

==================================================
VISUAL ENGINE
==================================================

Selain naskah, tentukan konsep visual yang benar-benar
membantu menjelaskan fenomena dalam script.

Visual bukan sekadar dekorasi.

Visual harus dapat menggambarkan:
- objek utama
- aktivitas
- proses
- lingkungan
- fenomena
- situasi yang sedang dijelaskan

Buat:

visual_context
=
deskripsi konkret tentang situasi visual
yang paling cocok dengan script.

Contoh:

Topik:
"Kenapa es mengapung?"

visual_context:
"ice cubes floating in a clear glass of water"

BUKAN:
"science"

==================================================
BG KEYWORDS
==================================================

Buat 2–4 keyword Pexels dalam bahasa Inggris.

Keyword harus:
- konkret
- visual
- mudah dicari di Pexels
- berhubungan langsung dengan topik
- memungkinkan ditemukan footage nyata

Contoh:
[
    "coffee roasting",
    "coffee beans close up",
    "pouring coffee"
]

Bukan:
[
    "knowledge",
    "science",
    "interesting"
]

==================================================
ANTI-RANDOM VISUAL
==================================================

Visual harus mempertimbangkan:
- topik
- setup 1
- setup 2
- punchline / reveal
- objek utama
- proses yang dijelaskan

Jangan memilih visual hanya karena keyword terdengar mirip.

==================================================
QUALITY CHECK
==================================================

Sebelum menghasilkan JSON, pastikan:

1. Topik jelas?
2. Hook membuat penasaran?
3. Setup 2 memberikan konteks?
4. Reveal benar-benar menjawab pertanyaan?
5. Informasi didukung hasil pencarian?
6. Ada klaim yang terdengar dibuat-buat?
7. Ada angka/detail yang tidak diperlukan?
8. Ada klaim absolut yang tidak didukung?
9. Script terasa seperti Wikipedia?
10. Script terasa seperti tulisan AI?
11. Bahasa nyaman untuk voice-over?
12. Informasi tidak berulang?
13. Visual benar-benar menggambarkan topik?
14. Keyword Pexels konkret?
15. Penonton mendapatkan pengetahuan baru?

Jika fakta meragukan, hapus atau sederhanakan.
Jika reveal terlalu generik, buat lebih informatif.
Jika hook terlalu biasa, buat lebih memancing rasa ingin tahu.
Jika visual terlalu umum, buat lebih spesifik.

==================================================
OUTPUT
==================================================

Kembalikan HANYA JSON VALID.

Tidak ada markdown.
Tidak ada ```json.
Tidak ada penjelasan tambahan.

JANGAN menambahkan field lain.

Gunakan TEPAT struktur JSON berikut.

PENTING:
Field "punchline" TETAP bernama "punchline"
karena field tersebut digunakan oleh video engine.
Isinya sekarang adalah KNOWLEDGE REVEAL,
bukan joke/punchline humor.

Format:

{{
    "title": "...",
    "setup_1": "...",
    "setup_2": "...",
    "punchline": "...",
    "visual_context": "...",
    "bg_keywords": [
        "...",
        "...",
        "..."
    ]
}}

"""

        # ==========================================
        # GENERATE
        # ==========================================
        response = model.generate_content(
            prompt
        )

        teks = (
            getattr(
                response,
                "text",
                ""
            ) or ""
        ).strip()

        if not teks:
            return {
                "error": "Gemini tidak menghasilkan teks."
            }

        # ==========================================
        # PARSE JSON
        # ==========================================
        try:

            hasil = extract_json(
                teks
            )

        except json.JSONDecodeError as e:

            return {
                "error": (
                    "Format JSON dari AI tidak valid: "
                    f"{str(e)}"
                )
            }

        # ==========================================
        # VALIDASI
        # ==========================================
        hasil, validation_error = (
            validate_result(
                hasil
            )
        )

        if validation_error:
            return {
                "error": validation_error
            }

        # ==========================================
        # LOG
        # ==========================================
        title_words = len(
            hasil["title"].split()
        )

        setup1_words = len(
            hasil["setup_1"].split()
        )

        setup2_words = len(
            hasil["setup_2"].split()
        )

        punchline_words = len(
            hasil["punchline"].split()
        )

        print("")
        print(
            "========== CONTENT ENGINE =========="
        )

        print(
            f"Title     ({title_words} kata): "
            f"{hasil['title']}"
        )

        print(
            f"Setup 1   ({setup1_words} kata): "
            f"{hasil['setup_1']}"
        )

        print(
            f"Setup 2   ({setup2_words} kata): "
            f"{hasil['setup_2']}"
        )

        print(
            f"Punchline ({punchline_words} kata): "
            f"{hasil['punchline']}"
        )

        print(
            f"Visual    : "
            f"{hasil['visual_context']}"
        )

        print(
            "Keywords  : "
            f"{hasil['bg_keywords']}"
        )

        print(
            "===================================="
        )
        print("")

        return hasil

    except Exception as e:

        return {
            "error": (
                "Gagal menghubungi AI: "
                f"{str(e)}"
            )
        }
